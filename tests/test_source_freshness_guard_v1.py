"""SourceFreshnessGuard v1 fixtures: snapshots, not owner admission."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import pytest

from openremaster.source_freshness_guard_v1 import (
    CAPTURE_SCHEMA,
    FRAMEWORK_ROOT,
    FROZEN_OWNER_OBSERVATION_SHA256,
    LIVE_OWNER_OBSERVATION,
    PINNED_R14_PILOT_SHA256,
    SCHEMA,
    SourceFreshnessRejected,
    classify_untrusted_hash_capture,
    parse_pinned_r14_pilot,
    review_sealed_r14_pilot,
)

NOW = datetime(2026, 10, 14, 7, 0, tzinfo=timezone.utc)


def hash_of(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fixtures():
    frozen = {
        FRAMEWORK_ROOT + "\\orchestrator\\synthetic-static\\source-%03d.py" % index:
            hash_of("immutable-source-%03d" % index)
        for index in range(61)
    }
    frozen[LIVE_OWNER_OBSERVATION] = FROZEN_OWNER_OBSERVATION_SHA256
    items = {
        path: {
            "first_sha256": sha,
            "second_sha256": sha,
            "byte_count": 100,
        }
        for path, sha in frozen.items()
    }
    capture = {
        "schema": CAPTURE_SCHEMA,
        "started_utc": "2026-10-14T06:59:44Z",
        "finished_utc": "2026-10-14T06:59:50Z",
        "files": items,
    }
    return frozen, capture


def review(frozen, capture, now=NOW):
    return classify_untrusted_hash_capture(frozen=frozen, capture=capture, now=now)


def test_classification_of_unchanged_live_state_still_holds():
    frozen, capture = fixtures()
    result = review(frozen, capture)
    assert result["status"] == "SOURCE_FRESHNESS_REVIEW_ONLY_HOLD"
    assert result["classification"] == "LIVE_OWNER_OBSERVATION_STILL_UNATTESTED_HOLD"
    assert result["immutable_matched_count"] == 61
    assert result["historical_reference_count"] == 62
    assert result["sealed_pilot_bytes_verified"] is False
    assert result["live_observation_changed_since_frozen_pilot"] is False


def test_only_live_observation_can_change_without_immutable_source_drift():
    frozen, capture = fixtures()
    capture["files"][LIVE_OWNER_OBSERVATION]["first_sha256"] = hash_of("live-v12-new")
    capture["files"][LIVE_OWNER_OBSERVATION]["second_sha256"] = hash_of("live-v12-new")
    decision = review(frozen, capture)
    assert decision["classification"] == "LIVE_OWNER_OBSERVATION_CHANGED_UNATTESTED_HOLD"
    assert decision["immutable_matched_count"] == 61
    assert decision["immutable_source_drift_paths"] == []
    assert decision["live_observation_changed_since_frozen_pilot"] is True
    assert decision["dispatch_authorized"] is False


def test_live_observation_race_is_not_equated_with_success():
    frozen, capture = fixtures()
    capture["files"][LIVE_OWNER_OBSERVATION]["second_sha256"] = hash_of("next-owner")
    result = review(frozen, capture)
    assert result["classification"] == "LIVE_OWNER_OBSERVATION_CHANGED_DURING_CAPTURE_HOLD"
    assert result["live_observation_stable_within_read_pair"] is False


def test_real_immutable_source_drift_must_hold():
    frozen, capture = fixtures()
    static = next(k for k in frozen if k != LIVE_OWNER_OBSERVATION)
    capture["files"][static]["second_sha256"] = hash_of("unapproved-patch")
    result = review(frozen, capture)
    assert result["classification"] == "IMMUTABLE_SOURCE_DRIFT_OR_RACE_HOLD"
    assert result["immutable_matched_count"] == 60
    assert result["immutable_source_drift_paths"] == [static]


def test_immutable_race_blocks_even_if_second_read_matches_frozen_hash():
    frozen, capture = fixtures()
    static = next(k for k in frozen if k != LIVE_OWNER_OBSERVATION)
    capture["files"][static]["first_sha256"] = hash_of("transient-mutation")
    result = review(frozen, capture)
    assert result["classification"] == "IMMUTABLE_SOURCE_DRIFT_OR_RACE_HOLD"
    assert result["immutable_matched_count"] == 60


def test_stale_capture_is_not_current_owner_proof():
    frozen, capture = fixtures()
    result = review(frozen, capture, now=NOW + timedelta(minutes=3))
    assert result["classification"] == "CAPTURE_TIME_ASSERTION_STALE_OR_FUTURE_HOLD"
    assert result["claimed_capture_timestamp_recent"] is False


def test_future_capture_is_not_accepted():
    frozen, capture = fixtures()
    result = review(frozen, capture, now=NOW - timedelta(seconds=20))
    assert result["classification"] == "CAPTURE_TIME_ASSERTION_STALE_OR_FUTURE_HOLD"


def test_duration_over_one_minute_is_not_a_valid_fresh_capture():
    frozen, capture = fixtures()
    capture["started_utc"] = "2026-10-14T06:58:00Z"
    result = review(frozen, capture)
    assert result["classification"] == "CAPTURE_TIME_ASSERTION_STALE_OR_FUTURE_HOLD"


def test_immutable_drift_overrides_recent_claim_and_live_observation():
    frozen, capture = fixtures()
    k = next(iter(frozen))
    capture["files"][k]["second_sha256"] = hash_of("evil-edit")
    capture["files"][LIVE_OWNER_OBSERVATION]["second_sha256"] = hash_of("next")
    capture["finished_utc"] = "2026-10-14T06:30:00Z"
    capture["started_utc"] = "2026-10-14T06:29:58Z"
    assert review(frozen, capture)["classification"] == "IMMUTABLE_SOURCE_DRIFT_OR_RACE_HOLD"


@pytest.mark.parametrize("invalid", [
    None, True, [], {}, {"extra": "record"},
])
def test_malformed_frozen_map_never_passes(invalid):
    _, capture = fixtures()
    with pytest.raises(SourceFreshnessRejected):
        review(invalid, capture)


@pytest.mark.parametrize("tamper", [
    "drop-static", "extra-captured", "drop-live", "overwrite-live-baseline",
    "bad-reference-hash", "duplicate-casefold", "out-of-root", "path-traversal",
    "wrong-separator", "trailing-dot", "ambiguous-empty-segment",
])
def test_frozen_source_identity_guards(tamper):
    frozen, capture = fixtures()
    path = next(k for k in frozen if k != LIVE_OWNER_OBSERVATION)
    if tamper == "drop-static":
        frozen.pop(path)
    elif tamper == "extra-captured":
        capture["files"]["F:\\Remaster Framework\\unknown.py"] = {
            "first_sha256": "a"*64, "second_sha256":"a"*64, "byte_count":10}
    elif tamper == "drop-live":
        frozen.pop(LIVE_OWNER_OBSERVATION)
    elif tamper == "overwrite-live-baseline":
        frozen[LIVE_OWNER_OBSERVATION] = "f" * 64
    elif tamper == "bad-reference-hash":
        frozen[path] = "n" * 64
    elif tamper == "duplicate-casefold":
        frozen[path.upper()] = frozen[path]
        frozen.pop(next(k for k in frozen if k != path and k != LIVE_OWNER_OBSERVATION))
    else:
        bad = {
            "out-of-root": r"H:\not-authorized\source.py",
            "path-traversal": r"F:\Remaster Framework\orchestrator\..\source.py",
            "wrong-separator": "F:/Remaster Framework/orchestrator/source.py",
            "trailing-dot": r"F:\Remaster Framework\orchestrator\source.",
            "ambiguous-empty-segment": "F:\\Remaster Framework\\orchestrator\\\\source.py",
        }[tamper]
        frozen[bad] = frozen.pop(path)
        capture["files"][bad] = capture["files"].pop(path)
    with pytest.raises(SourceFreshnessRejected):
        review(frozen, capture)


@pytest.mark.parametrize("change", [
    "bad-schema", "unknown-field", "no-files", "missing-file",
    "wrong-file-format", "negative-byte-count", "boolean-byte-count",
    "oversized-file", "bad-first-hash", "bad-second-hash",
    "missing-last-read", "nonobject-item", "nonobject-capture",
])
def test_capture_shape_and_type_errors_fail_closed(change):
    frozen, capture = fixtures()
    item = capture["files"][next(iter(frozen))]
    if change == "bad-schema":
        capture["schema"] = "ORF.FutureSchema.v2"
    elif change == "unknown-field":
        capture["trusted"] = True
    elif change == "no-files":
        capture["files"] = []
    elif change == "missing-file":
        capture["files"].pop(next(iter(frozen)))
    elif change == "wrong-file-format":
        item["source_values"] = {"token":"untrusted"}
    elif change == "negative-byte-count":
        item["byte_count"] = -1
    elif change == "boolean-byte-count":
        item["byte_count"] = True
    elif change == "oversized-file":
        item["byte_count"] = 70*1024*1024
    elif change == "bad-first-hash":
        item["first_sha256"] = "not-a-hash"
    elif change == "bad-second-hash":
        item["second_sha256"] = "g"*64
    elif change == "missing-last-read":
        item.pop("second_sha256")
    elif change == "nonobject-item":
        capture["files"][next(iter(frozen))] = "source"
    else:
        capture = False
    with pytest.raises(SourceFreshnessRejected):
        review(frozen, capture)


@pytest.mark.parametrize("change", [
    "naive-now", "bad-start", "bad-finish", "reverse",
    "leap-date-invalid", "timezone-offset-not-Z", "missing-time",
])
def test_time_claims_fail_closed(change):
    frozen, capture = fixtures()
    now = NOW
    if change == "naive-now":
        now = NOW.replace(tzinfo=None)
    elif change == "bad-start":
        capture["started_utc"] = "tomorrow"
    elif change == "bad-finish":
        capture["finished_utc"] = "2026-10-14T06:59:50"
    elif change == "reverse":
        capture["started_utc"] = "2026-10-14T06:59:51Z"
    elif change == "leap-date-invalid":
        capture["finished_utc"] = "2026-02-30T06:59:50Z"
    elif change == "timezone-offset-not-Z":
        capture["finished_utc"] = "2026-10-14T08:59:50+02:00"
    else:
        capture.pop("finished_utc")
    with pytest.raises(SourceFreshnessRejected):
        review(frozen, capture, now=now)


def test_returned_report_contains_no_live_owner_payload():
    frozen, capture = fixtures()
    raw = json.dumps(review(frozen, capture), sort_keys=True)
    assert '"token"' not in raw
    assert '"owner"' not in raw
    assert '"session"' not in raw
    assert "dispatch_authorized" in raw


def test_every_review_result_never_grants_dispatch():
    frozen, capture = fixtures()
    cases = []
    cases.append(review(frozen, capture))
    for modified in ("a", "b", "c"):
        changed = deepcopy(capture)
        changed["files"][LIVE_OWNER_OBSERVATION]["second_sha256"] = hash_of(modified)
        cases.append(review(frozen, changed))
    for result in cases:
        assert result["dispatch_authorized"] is False
        assert result["worker_execution_authorized"] is False
        assert result["current_owner_authority_verified"] is False
        assert result["legacy_r14_full_acceptance_reclassified_as_pass"] is False


def test_deterministic_structural_report():
    frozen, capture = fixtures()
    assert review(frozen, capture) == review(dict(reversed(list(frozen.items()))), capture)


def test_forged_pilot_bytes_are_rejected_before_any_classification():
    frozen, capture = fixtures()
    fake_pilot = json.dumps({
        "schema": "OpenRemaster.R14RegistryHardeningHomePCReadOnlyPilot.v1",
        "status": "REAL_R13_FROZEN_BASELINE_R14_ISOLATED_HARDENING_PASS_PRODUCTION_HOLD",
        "original_and_prior_framework_sha256": frozen,
    }, sort_keys=True).encode()
    assert hashlib.sha256(fake_pilot).hexdigest() != PINNED_R14_PILOT_SHA256
    with pytest.raises(SourceFreshnessRejected, match="SHA-256 mismatch"):
        parse_pinned_r14_pilot(fake_pilot)
    with pytest.raises(SourceFreshnessRejected):
        review_sealed_r14_pilot(pilot_bytes=fake_pilot, capture=capture, now=NOW)


@pytest.mark.parametrize("bad", [b"", b"{}", b"\x00", "text", None, True])
def test_missing_or_malformed_pilot_does_not_verify(bad):
    with pytest.raises(SourceFreshnessRejected):
        parse_pinned_r14_pilot(bad)
