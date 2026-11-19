"""ORF SourceFreshnessGuard.v1 — *review-only* separation of source and owner state.

Consumes hashes and independently pinned R14 pilot bytes; never reads live
owner record, verifies worker credentials, grants a lease, or starts a job.
A hash/time assertion from a caller is NOT owner authority or trusted current
state. Every possible result preserves HOLD and dispatch_authorized=False.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

SCHEMA = "ORF.SourceFreshnessGuard.v1"
CAPTURE_SCHEMA = "ORF.SourceFreshnessCapture.v1"
ORIGINAL_PILOT_SCHEMA = "OpenRemaster.R14RegistryHardeningHomePCReadOnlyPilot.v1"
ORIGINAL_PILOT_STATUS = "REAL_R13_FROZEN_BASELINE_R14_ISOLATED_HARDENING_PASS_PRODUCTION_HOLD"
PINNED_R14_PILOT_SHA256 = "9ae886ee3c9357f720dcaebb730c99a8a7fc329a7779c8f42bb783990e54c865"
FRAMEWORK_ROOT = "F:\\Remaster Framework"
LIVE_OWNER_OBSERVATION = (
    FRAMEWORK_ROOT
    + "\\orchestrator\\control-plane\\state\\interactive-runtime-owner-v12.json"
)
FROZEN_OWNER_OBSERVATION_SHA256 = (
    "f4496513109a23802e6a65ee959f28f71e5db189c8c4518b554cd19c86ef766e"
)
EXPECTED_R14_ENTRIES = 62
EXPECTED_STATIC_ENTRIES = 61
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
CAPTURE_FILE_FIELDS = frozenset(("first_sha256", "second_sha256", "byte_count"))
CAPTURE_FIELDS = frozenset(("schema", "started_utc", "finished_utc", "files"))


class SourceFreshnessRejected(ValueError):
    """Fail-closed invalid evidence; no status here can authorize a worker."""


def _sha(value, label):
    if type(value) is not str or SHA256.fullmatch(value) is None:
        raise SourceFreshnessRejected(f"{label}: invalid SHA-256")
    return value


def _source_path(value):
    if type(value) is not str or len(value) > 1024 or "\x00" in value:
        raise SourceFreshnessRejected("invalid source path")
    root_prefix = FRAMEWORK_ROOT + "\\"
    if not value.casefold().startswith(root_prefix.casefold()):
        raise SourceFreshnessRejected("source outside pinned root")
    tail = value[len(root_prefix):]
    if "/" in value or ":" in tail or not tail:
        raise SourceFreshnessRejected("invalid native source path")
    parts = tail.split("\\")
    if any(x in ("", ".", "..") or x.endswith(" ") or x.endswith(".") for x in parts):
        raise SourceFreshnessRejected("path ambiguity/traversal")
    return value


def _instant(value, label):
    if type(value) is not str or STAMP.fullmatch(value) is None:
        raise SourceFreshnessRejected(f"{label}: UTC Z seconds required")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise SourceFreshnessRejected(f"{label}: invalid UTC date") from exc


def _now(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SourceFreshnessRejected("now: timezone-aware time required")
    return value.astimezone(timezone.utc)


def _unique_object(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise SourceFreshnessRejected("duplicate JSON object field")
        out[k] = v
    return out


def _bad_constant(value):
    raise SourceFreshnessRejected(f"invalid JSON constant: {value}")


def parse_pinned_r14_pilot(pilot_bytes):
    """Require literal sealed 2026-10-13 R14 pilot bytes, not caller's PASS flag."""
    if type(pilot_bytes) is not bytes or not 0 < len(pilot_bytes) <= 1048576:
        raise SourceFreshnessRejected("invalid/missing pinned pilot bytes")
    digest = hashlib.sha256(pilot_bytes).hexdigest()
    if digest != PINNED_R14_PILOT_SHA256:
        raise SourceFreshnessRejected("frozen R14 pilot SHA-256 mismatch")
    try:
        doc = json.loads(
            pilot_bytes.decode("utf-8-sig"),
            object_pairs_hook=_unique_object,
            parse_constant=_bad_constant,
        )
    except (UnicodeError, ValueError, TypeError) as exc:
        raise SourceFreshnessRejected("pinned pilot JSON invalid") from exc
    if type(doc) is not dict or doc.get("schema") != ORIGINAL_PILOT_SCHEMA:
        raise SourceFreshnessRejected("unexpected R14 pilot schema")
    if doc.get("status") != ORIGINAL_PILOT_STATUS:
        raise SourceFreshnessRejected("R14 historical status changed")
    frozen = doc.get("original_and_prior_framework_sha256")
    if type(frozen) is not dict:
        raise SourceFreshnessRejected("frozen source pin map missing")
    return frozen


def _classify(frozen, capture, *, now):
    """Pure structural review. The input capture is NEVER independently trusted."""
    if type(frozen) is not dict or len(frozen) != EXPECTED_R14_ENTRIES:
        raise SourceFreshnessRejected("pinned R14 must contain exactly 62 paths")
    paths = set()
    for path, sha in frozen.items():
        _source_path(path)
        _sha(sha, "historical pin")
        if path.casefold() in paths:
            raise SourceFreshnessRejected("duplicate case-folded Windows path")
        paths.add(path.casefold())
    if LIVE_OWNER_OBSERVATION not in frozen:
        raise SourceFreshnessRejected("explicitly classified R14 live path missing")
    if frozen[LIVE_OWNER_OBSERVATION] != FROZEN_OWNER_OBSERVATION_SHA256:
        raise SourceFreshnessRejected("live-path original frozen SHA changed")
    if type(capture) is not dict or set(capture) != CAPTURE_FIELDS:
        raise SourceFreshnessRejected("capture schema/fields invalid")
    if capture["schema"] != CAPTURE_SCHEMA:
        raise SourceFreshnessRejected("unknown capture version")
    files = capture["files"]
    if type(files) is not dict or set(files) != set(frozen):
        raise SourceFreshnessRejected("captured source set incomplete/unexpected")
    start = _instant(capture["started_utc"], "started_utc")
    end = _instant(capture["finished_utc"], "finished_utc")
    if end < start:
        raise SourceFreshnessRejected("capture clock reversed")
    moment = _now(now)
    age = moment - end
    time_is_recent_claim = (
        end - start <= timedelta(seconds=60)
        and -timedelta(seconds=5) <= age <= timedelta(seconds=90)
    )

    source_drifts = []
    unstable_static = []
    for path in frozen:
        item = files[path]
        if type(item) is not dict or set(item) != CAPTURE_FILE_FIELDS:
            raise SourceFreshnessRejected(f"invalid hash-only capture: {path}")
        _sha(item["first_sha256"], "first source hash")
        _sha(item["second_sha256"], "second source hash")
        if type(item["byte_count"]) is not int or not 0 <= item["byte_count"] <= 67108864:
            raise SourceFreshnessRejected("invalid source size")
        if path == LIVE_OWNER_OBSERVATION:
            continue
        if item["first_sha256"] != item["second_sha256"]:
            unstable_static.append(path)
        if item["second_sha256"] != frozen[path]:
            source_drifts.append(path)
    live = files[LIVE_OWNER_OBSERVATION]
    live_stable = live["first_sha256"] == live["second_sha256"]
    live_historically_changed = live["second_sha256"] != FROZEN_OWNER_OBSERVATION_SHA256
    if source_drifts or unstable_static:
        classification = "IMMUTABLE_SOURCE_DRIFT_OR_RACE_HOLD"
    elif not live_stable:
        classification = "LIVE_OWNER_OBSERVATION_CHANGED_DURING_CAPTURE_HOLD"
    elif not time_is_recent_claim:
        classification = "CAPTURE_TIME_ASSERTION_STALE_OR_FUTURE_HOLD"
    elif live_historically_changed:
        classification = "LIVE_OWNER_OBSERVATION_CHANGED_UNATTESTED_HOLD"
    else:
        classification = "LIVE_OWNER_OBSERVATION_STILL_UNATTESTED_HOLD"
    return {
        "schema": SCHEMA,
        "status": "SOURCE_FRESHNESS_REVIEW_ONLY_HOLD",
        "classification": classification,
        "source_pilot_sha256_pinned": PINNED_R14_PILOT_SHA256,
        "sealed_pilot_bytes_verified": False,
        "historical_reference_count": EXPECTED_R14_ENTRIES,
        "immutable_expected_count": EXPECTED_STATIC_ENTRIES,
        "immutable_matched_count": EXPECTED_STATIC_ENTRIES - len(set(source_drifts + unstable_static)),
        "immutable_source_drift_paths": sorted(set(source_drifts + unstable_static)),
        "live_observation_path": LIVE_OWNER_OBSERVATION,
        "live_observation_frozen_sha256": FROZEN_OWNER_OBSERVATION_SHA256,
        "live_observation_captured_sha256": live["second_sha256"],
        "live_observation_byte_count": live["byte_count"],
        "live_observation_changed_since_frozen_pilot": live_historically_changed,
        "live_observation_stable_within_read_pair": live_stable,
        "claimed_capture_timestamp_recent": time_is_recent_claim,
        "current_owner_authority_verified": False,
        "independent_current_external_anchor_verified": False,
        "owner_scope_and_epoch_fencing_verified": False,
        "source_corpus_identity_bridge_verified": False,
        "legacy_r14_full_acceptance_reclassified_as_pass": False,
        "dispatch_authorized": False,
        "worker_execution_authorized": False,
    }


def classify_untrusted_hash_capture(*, frozen, capture, now):
    """Synthetic fixture entrypoint; always NON-AUTHORIZING."""
    return _classify(frozen, capture, now=now)


def review_sealed_r14_pilot(*, pilot_bytes, capture, now):
    """Verify historical pilot bytes, then classify source/observation separately.

    Does not verify that supplied file hashes were measured honestly, that time
    is externally trusted, or that any actor currently owns the work.
    """
    frozen = parse_pinned_r14_pilot(pilot_bytes)
    output = _classify(frozen, capture, now=now)
    output["sealed_pilot_bytes_verified"] = True
    return output
