"""NW-V2-002 isolated HomePC authority candidate.

No native worker execution, no production keys, no global consensus, no
queue mutations. Uses the SHA-pinned POA V1 TrustedScope contract.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
import sys
import time
from contextlib import contextmanager,closing
from pathlib import Path

POA_V1 = Path(__file__).resolve().parent.parent / "production-owner-authority-v1"
PINNED_SCOPE_SHA = "c7dc5d9000cbf21a7635e561fb19f36ec4864e0fb97e3374d70fc6b85d417420"
if hashlib.sha256((POA_V1 / "scope.py").read_bytes()).hexdigest() != PINNED_SCOPE_SHA:
    raise RuntimeError("POA_V1_SCOPE_DEPENDENCY_DRIFT")
sys.path.insert(0, str(POA_V1))
from scope import Hold, TrustedScope, resolve as resolve_scope  # noqa: E402

GRANT_SCHEMA = "OpenRemaster.POAV2IsolatedOwnerGrant.v1"
REQUEST_SCHEMA = "OpenRemaster.POAV2IsolatedAdmissionRequest.v1"
ACK_SCHEMA = "OpenRemaster.POAV2IsolatedReceiverAck.v1"
AUDIENCE = "HomePC-NativeWorker-V2-Isolated"
GRANT_PURPOSE = "OWNER_SCOPE"
ACK_PURPOSE = "NATIVE_ACK"
GENESIS = "0" * 64
HEX = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")
NONCE = re.compile(r"[A-Za-z0-9_-]{16,96}\Z")
BIND = ("project", "edition", "scenario", "source_sha256",
        "job_id", "job_sha256", "snapshot_sha256", "checkpoint_sha256",
        "operation_id", "nonce", "owner_epoch", "fence_generation",
        "policy_epoch", "owner_id", "lease_id", "heavy")
GRANT_FIELDS = set(BIND) | {"schema", "audience", "purpose", "mode",
                            "key_id", "issued_at_unix", "expires_at_unix", "signature"}
REQUEST_FIELDS = set(BIND) | {"schema", "protocol"}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise Hold(reason)


def verify_seal(document, purpose, keyring):
    require(isinstance(document, dict) and isinstance(keyring, dict), "SIGNATURE_OR_KEYRING_MISSING")
    require(document.get("purpose") == purpose and document.get("audience") == AUDIENCE,
            "SIGNATURE_DOMAIN_MISMATCH")
    key_id = document.get("key_id")
    require(isinstance(key_id, str) and key_id in keyring, "UNKNOWN_SIGNER")
    key = keyring[key_id]
    sig = document.get("signature")
    require(isinstance(key, bytes) and len(key) >= 32 and isinstance(sig, str)
            and HEX.fullmatch(sig) is not None, "INVALID_SIGNING_MATERIAL")
    body = {k: v for k, v in document.items() if k != "signature"}
    expected = hmac.new(key, canonical(body), hashlib.sha256).hexdigest()
    require(hmac.compare_digest(expected, sig), "SIGNATURE_INVALID")
    return digest(canonical(document))


def verify_grant(grant, owner_keys, now):
    require(isinstance(grant, dict) and set(grant) == GRANT_FIELDS, "OWNER_GRANT_FIELDS_INVALID")
    require(grant["schema"] == GRANT_SCHEMA and grant["mode"] == "V2_REQUIRED",
            "V2_OWNER_GRANT_REQUIRED")
    verify_seal(grant, GRANT_PURPOSE, owner_keys)
    for field in ("project", "edition", "scenario", "job_id", "operation_id",
                  "owner_id", "lease_id"):
        require(isinstance(grant[field], str) and NAME.fullmatch(grant[field]) is not None,
                "INVALID_IDENTITY_" + field)
    require(isinstance(grant["nonce"], str) and NONCE.fullmatch(grant["nonce"]) is not None,
            "INVALID_NONCE")
    for field in ("source_sha256", "job_sha256", "snapshot_sha256", "checkpoint_sha256"):
        require(isinstance(grant[field], str) and HEX.fullmatch(grant[field]) is not None,
                "INVALID_SHA_" + field)
    for field in ("owner_epoch", "fence_generation", "policy_epoch"):
        require(type(grant[field]) is int and grant[field] >= 1, "INVALID_FENCE_" + field)
    require(type(grant["heavy"]) is bool, "INVALID_HEAVY_FLAG")
    start, end = grant["issued_at_unix"], grant["expires_at_unix"]
    require(type(now) is int and type(start) is int and type(end) is int
            and start - 5 <= now < end and 0 < end - start <= 300,
            "GRANT_EXPIRED_FUTURE_OR_TOO_LONG")
    scope = TrustedScope(grant["project"], grant["edition"], grant["scenario"],
                         grant["source_sha256"], grant["owner_epoch"])
    return scope, scope.digest()


def verify_request(grant, request, job_bytes, scope):
    require(isinstance(request, dict) and set(request) == REQUEST_FIELDS,
            "ADMISSION_REQUEST_FIELDS_INVALID")
    require(request["schema"] == REQUEST_SCHEMA and request["protocol"] == "V2_REQUIRED",
            "PROTOCOL_DOWNGRADE_DENIED")
    require(all(request[field] == grant[field] for field in BIND), "SIGNED_GRANT_REQUEST_MISMATCH")
    resolve_scope(lambda _request: scope, request)
    require(type(job_bytes) is bytes and 0 < len(job_bytes) <= 65536, "JOB_BYTES_INVALID")
    require(digest(job_bytes) == grant["job_sha256"], "JOB_BYTES_SHA_MISMATCH")
    try:
        job = json.loads(job_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise Hold("INVALID_JOB_JSON") from exc
    require(isinstance(job, dict) and job.get("schema") == "ORCH-K003.Job.v1"
            and job.get("job_id") == grant["job_id"]
            and job.get("project") == grant["project"], "JOB_IDENTITY_MISMATCH")
    return digest(canonical(request))


class LocalAuthorityCandidate:
    """Test-only, SINGLE-HOST SQLite authority. Every ACK says may_dispatch=False."""

    def __init__(self, database, arena, owner_keys, ack_keys, ack_signer, *, isolated_lab=False):
        require(isolated_lab is True, "EXPLICIT_DISPOSABLE_LAB_REQUIRED")
        require(not Path(database).is_symlink(), "DATABASE_SYMLINK_DENIED")
        if Path(database).exists():
            # Read-only check before the inherited initializer can touch a foreign DB.
            with closing(sqlite3.connect(Path(database).resolve().as_uri()+"?mode=ro", uri=True)) as probe:
                try:
                    marker=probe.execute("SELECT schema FROM resource_lab_metadata").fetchall()
                except sqlite3.Error as exc:
                    raise Hold("FOREIGN_DATABASE_NOT_MIGRATED") from exc
                require(marker==[("OpenRemaster.ResourceTransactionLab.v1",)], "FOREIGN_DATABASE_NOT_MIGRATED")
        self.arena = Path(arena).resolve()
        self.dbpath = Path(database).resolve()
        require(self.arena.is_dir() and self.dbpath.parent == self.arena
                and self.dbpath.suffix == ".sqlite3"
                and not Path(database).is_symlink(), "DATABASE_MUST_BE_IN_ISOLATED_ARENA")
        require(isinstance(owner_keys, dict) and isinstance(ack_keys, dict)
                and bool(owner_keys) and bool(ack_keys)
                and all(type(x) is bytes and len(x) >= 32 for x in owner_keys.values())
                and all(type(x) is bytes and len(x) >= 32 for x in ack_keys.values())
                and not (set(owner_keys.values()) & set(ack_keys.values())),
                "PURPOSE_SEPARATED_KEYS_REQUIRED")
        require(callable(ack_signer), "INDEPENDENT_ACK_SIGNER_REQUIRED")
        self.owner_keys, self.ack_keys, self.ack_signer = owner_keys, ack_keys, ack_signer
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS resource_lab_metadata(schema TEXT PRIMARY KEY)")
            db.execute("INSERT OR IGNORE INTO resource_lab_metadata VALUES('OpenRemaster.ResourceTransactionLab.v1')")
            db.execute("CREATE TABLE IF NOT EXISTS resource_state(authority TEXT,source TEXT,fence INTEGER,policy TEXT,last_sequence INTEGER,PRIMARY KEY(authority,source))")
            db.execute("""CREATE TABLE IF NOT EXISTS resource_claims(
              operation_id TEXT PRIMARY KEY,authority TEXT,source TEXT,sequence INTEGER,
              claim_json TEXT NOT NULL,claim_sha TEXT NOT NULL,UNIQUE(authority,source,sequence),
              FOREIGN KEY(operation_id) REFERENCES operations(operation_id) DEFERRABLE INITIALLY DEFERRED)""")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS owners(
              project TEXT PRIMARY KEY, owner TEXT NOT NULL, owner_epoch INTEGER NOT NULL,
              generation INTEGER NOT NULL, policy_epoch INTEGER NOT NULL,
              lease_id TEXT NOT NULL, expires INTEGER NOT NULL,
              source_sha TEXT NOT NULL, scope_sha TEXT NOT NULL, status TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS operations(
              operation_id TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE,
              nonce TEXT NOT NULL UNIQUE, project TEXT NOT NULL,
              job_sha TEXT NOT NULL, request_sha TEXT NOT NULL,
              owner_epoch INTEGER NOT NULL, generation INTEGER NOT NULL,
              policy_epoch INTEGER NOT NULL, state TEXT NOT NULL,
              ack_json TEXT NOT NULL, heavy INTEGER NOT NULL,
              FOREIGN KEY(project) REFERENCES owners(project))""")
            db.execute("""CREATE TABLE IF NOT EXISTS nonce_claim(
              nonce TEXT PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE,
              FOREIGN KEY(operation_id) REFERENCES operations(operation_id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS outbox(
              operation_id TEXT PRIMARY KEY, ack_sha TEXT NOT NULL,
              state TEXT NOT NULL CHECK(state='ACKED_ISOLATED'),
              FOREIGN KEY(operation_id) REFERENCES operations(operation_id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS events(
              sequence INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
              operation_id TEXT NOT NULL, previous_sha TEXT NOT NULL,
              event_json TEXT NOT NULL, event_sha TEXT NOT NULL)""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.dbpath), timeout=2, isolation_level=None)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA busy_timeout=2000")
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            yield db
        finally:
            db.close()

    def tx(self, action):
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                result = action(db)
                db.commit()
                return result
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise Hold("ATOMIC_UNIQUE_CONFLICT") from exc
            except sqlite3.Error as exc:
                db.rollback()
                raise Hold("LOCAL_SQLITE_FAILURE_HOLD") from exc
            except BaseException:
                db.rollback()
                raise

    def event(self, db, kind, operation_id, details):
        last = db.execute("SELECT event_sha FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        prev = last["event_sha"] if last else GENESIS
        obj = {"kind": kind, "operation_id": operation_id,
               "details": details, "previous_sha": prev}
        event_sha = digest(canonical(obj))
        db.execute("""INSERT INTO events(kind,operation_id,previous_sha,event_json,event_sha)
                   VALUES(?,?,?,?,?)""", (kind, operation_id, prev,
                                           canonical(obj).decode("utf-8"), event_sha))

    def activate_owner(self, grant, *, expected_epoch=0, expected_generation=0, now=None):
        now = int(time.time()) if now is None else now
        scope, scope_sha = verify_grant(grant, self.owner_keys, now)
        def action(db):
            row = db.execute("SELECT * FROM owners WHERE project=?", (grant["project"],)).fetchone()
            if row:
                same = (row["owner"] == grant["owner_id"] and
                        row["owner_epoch"] == grant["owner_epoch"] and
                        row["generation"] == grant["fence_generation"] and
                        row["policy_epoch"] == grant["policy_epoch"] and
                        row["lease_id"] == grant["lease_id"] and
                        row["scope_sha"] == scope_sha and row["source_sha"] == scope.source_sha256
                        and row["expires"] == grant["expires_at_unix"] and row["status"] == "ACTIVE")
                require(same and row["expires"] > now, "OWNER_TAKEOVER_REQUIRES_SEPARATE_AUTHORITY")
                return {"status": "EXISTING_OWNER", "may_dispatch": False}
            require(expected_epoch == 0 and expected_generation == 0
                    and grant["owner_epoch"] == 1 and grant["fence_generation"] == 1,
                    "FIRST_OWNER_CAS_MISMATCH")
            db.execute("""INSERT INTO owners VALUES(?,?,?,?,?,?,?,?,?,?)""",
                       (grant["project"], grant["owner_id"], grant["owner_epoch"],
                        grant["fence_generation"], grant["policy_epoch"], grant["lease_id"],
                        grant["expires_at_unix"], grant["source_sha256"], scope_sha, "ACTIVE"))
            self.event(db, "LOCAL_OWNER_ACTIVATED", grant["operation_id"],
                       {"scope_sha256": scope_sha, "epoch": grant["owner_epoch"]})
            return {"status": "LOCAL_OWNER_ACTIVATED", "may_dispatch": False}
        return self.tx(action)

    def admit(self, grant, request, job_bytes, *, now=None, inject_fault=None, resource_check=None, clock=None):
        require(callable(resource_check), "RESOURCE_AUTHORITY_UNAVAILABLE")
        require(callable(clock), "TRANSACTION_CLOCK_REQUIRED")
        now = int(time.time()) if now is None else now
        scope, scope_sha = verify_grant(grant, self.owner_keys, now)
        req_sha = verify_request(grant, request, job_bytes, scope)
        op = grant["operation_id"]
        def action(db):
            # Refresh time after BEGIN IMMEDIATE, including signature/lease expiry.
            current=clock()
            require(type(current) is int and current>=0, "TRANSACTION_CLOCK_INVALID")
            scope, scope_sha = verify_grant(grant, self.owner_keys, current)
            verify_request(grant, request, job_bytes, scope)
            require(canonical({k:request[k] for k in BIND})==canonical({k:grant[k] for k in BIND}), "REQUEST_BINDING_TYPE_MISMATCH")
            owner = db.execute("SELECT * FROM owners WHERE project=?", (grant["project"],)).fetchone()
            require(owner is not None and owner["status"] == "ACTIVE"
                    and owner["owner"] == grant["owner_id"]
                    and owner["owner_epoch"] == grant["owner_epoch"]
                    and owner["generation"] == grant["fence_generation"]
                    and owner["policy_epoch"] == grant["policy_epoch"]
                    and owner["lease_id"] == grant["lease_id"]
                    and owner["source_sha"] == grant["source_sha256"]
                    and owner["scope_sha"] == scope_sha and owner["expires"] > current,
                    "OWNER_EPOCH_GENERATION_LEASE_OR_SOURCE_HOLD")
            require(db.execute("SELECT 1 FROM operations WHERE operation_id=?",(op,)).fetchone() is None,
                    "RESOURCE_OPERATION_ALREADY_PRESENT_QUERY_ONLY")
            resource_binding=resource_check(db,grant,request,job_bytes,current)
            require(isinstance(resource_binding,dict) and resource_binding.get("scope")=="DISPOSABLE_RESOURCE_LAB_ONLY", "RESOURCE_CLAIM_INVALID")
            resource_row=db.execute("SELECT claim_json,claim_sha FROM resource_claims WHERE operation_id=?",(op,)).fetchone()
            require(resource_row is not None and resource_row["claim_json"].encode("utf-8")==canonical(resource_binding)
                    and resource_row["claim_sha"]==digest(canonical(resource_binding))
                    and resource_binding.get("operation_id")==op
                    and resource_binding.get("may_dispatch") is False
                    and resource_binding.get("production_go") is False
                    and resource_binding.get("independent_resource_authority_verified") is False,
                    "RESOURCE_RESERVATION_NOT_BOUND")
            if inject_fault:inject_fault("AFTER_RESOURCE_RESERVATION")
            old = db.execute("""SELECT * FROM operations WHERE operation_id=?
                  OR job_id=? OR nonce=?""",
                  (op, grant["job_id"], grant["nonce"])).fetchall()
            if old:
                require(len(old) == 1 and old[0]["operation_id"] == op
                        and old[0]["job_id"] == grant["job_id"]
                        and old[0]["nonce"] == grant["nonce"]
                        and old[0]["job_sha"] == grant["job_sha256"]
                        and old[0]["request_sha"] == req_sha
                        and old[0]["owner_epoch"] == grant["owner_epoch"]
                        and old[0]["generation"] == grant["fence_generation"]
                        and old[0]["policy_epoch"] == grant["policy_epoch"],
                        "NONCE_JOB_OR_OPERATION_REPLAY_CONFLICT")
                ack = json.loads(old[0]["ack_json"])
                verify_seal(ack, ACK_PURPOSE, self.ack_keys)
                claim = db.execute("SELECT nonce FROM nonce_claim WHERE operation_id=?", (op,)).fetchone()
                outbound = db.execute("SELECT ack_sha,state FROM outbox WHERE operation_id=?", (op,)).fetchone()
                require(ack["operation_id"] == op and ack["status"] == "ISOLATED_ACCEPTED_NO_DISPATCH"
                        and ack["may_dispatch"] is False and
                        claim is not None and claim["nonce"] == grant["nonce"] and
                        outbound is not None and outbound["state"] == "ACKED_ISOLATED" and
                        outbound["ack_sha"] == digest(canonical(ack)), "STORED_ACK_INVALID")
                return ack
            active = db.execute("""SELECT project,heavy FROM operations
                WHERE state IN ('ADMITTED','STARTED','HOLD')""").fetchall()
            if grant["heavy"]:
                require(sum(int(x["heavy"]) for x in active) < 3, "FOURTH_HEAVY_SLOT_DENIED")
                require(not any(x["project"] == grant["project"] for x in active),
                        "GAME_WIP_LIMIT_DENIED")
            else:
                require(not any(x["project"] == grant["project"] for x in active),
                        "GAME_WIP_LIMIT_DENIED")
            ack_unsigned = {
                "schema": ACK_SCHEMA, "purpose": ACK_PURPOSE, "audience": AUDIENCE,
                "status": "ISOLATED_ACCEPTED_NO_DISPATCH", "may_dispatch": False,
                "operation_id": op, "job_id": grant["job_id"],
                "job_sha256": grant["job_sha256"],
                "nonce_sha256": digest(grant["nonce"].encode("utf-8")),
                "source_sha256": grant["source_sha256"],
                "owner_epoch": grant["owner_epoch"],
                "fence_generation": grant["fence_generation"],
                "policy_epoch": grant["policy_epoch"],
                "scope_sha256": scope_sha, "issued_at_unix": current,
                "resource_claim_sha256": digest(canonical(resource_binding)),
                "resource_claim":resource_binding}
            ack = self.ack_signer(dict(ack_unsigned))
            require(isinstance(ack, dict) and
                    {k: v for k, v in ack.items() if k not in ("signature", "key_id")} ==
                    ack_unsigned and ack.get("key_id") not in self.owner_keys,
                    "ACK_SIGNER_CHANGES_BINDING_OR_ROLE")
            verify_seal(ack, ACK_PURPOSE, self.ack_keys)
            db.execute("""INSERT INTO operations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (op, grant["job_id"], grant["nonce"], grant["project"],
                        grant["job_sha256"], req_sha, grant["owner_epoch"],
                        grant["fence_generation"], grant["policy_epoch"],
                        "ADMITTED", canonical(ack).decode("utf-8"), int(grant["heavy"])))
            db.execute("INSERT INTO nonce_claim(nonce,operation_id) VALUES(?,?)",
                       (grant["nonce"], op))
            if inject_fault:
                inject_fault("AFTER_NONCE_BEFORE_OUTBOX")
            db.execute("INSERT INTO outbox(operation_id,ack_sha,state) VALUES(?,?,'ACKED_ISOLATED')",
                       (op, digest(canonical(ack))))
            if inject_fault:
                inject_fault("AFTER_OUTBOX_BEFORE_EVENT")
            self.event(db, "LOCAL_ADMISSION_AND_ACK_COMMITTED", op,
                       {"job_sha256": grant["job_sha256"], "ack_sha256": digest(canonical(ack)),
                        "resource_claim_sha256":digest(canonical(resource_binding))})
            self._validate_resources(db)
            if inject_fault:
                inject_fault("BEFORE_LOCAL_COMMIT")
            return ack
        ack = self.tx(action)
        if inject_fault:
            inject_fault("AFTER_LOCAL_COMMIT_BEFORE_REPLY")
        return ack

    def _validate_resources(self, db):
        """Validate the full lab resource/ACK/event view in the caller's snapshot."""
        fields={"schema","scope","operation_id","project","authority_id","source_id","sequence",
                "owner_epoch","owner_fence","resource_fence","policy_epoch","policy_version","valid_until",
                "work_identity_sha256","observation_sha256","resource_context_sha256","resource_review_sha256",
                "independent_resource_authority_verified","may_dispatch","production_go"}
        def positive(value):return type(value) is int and 0<value<=2**63-1
        def parse(raw):
            require(type(raw) is str and len(raw)<=32768,"RESOURCE_RECORD_SIZE_OR_TYPE_HOLD")
            try:
                value=json.loads(raw)
                require(type(value) is dict and canonical(value).decode("utf-8")==raw,"NONCANONICAL_RESOURCE_RECORD")
                return value
            except (ValueError,TypeError,UnicodeError,RecursionError) as exc:raise Hold("MALFORMED_RESOURCE_RECORD") from exc
        records=db.execute("""SELECT r.*,o.project AS op_project,o.owner_epoch AS op_epoch,
            o.generation AS op_generation,o.policy_epoch AS op_policy,o.ack_json,o.job_sha
            FROM resource_claims r LEFT JOIN operations o ON r.operation_id=o.operation_id""").fetchall()
        require(len(records)==db.execute("SELECT COUNT(*) FROM operations").fetchone()[0],"RESOURCE_CLAIM_COUNTS_DIFFER")
        maxima={};claims={}
        for row in records:
            require(row['ack_json'] is not None,"ORPHAN_RESOURCE_CLAIM")
            claim=parse(row['claim_json']);ack=parse(row['ack_json'])
            require(set(claim)==fields and claim['schema']=='OpenRemaster.ResourceLabClaim.v1'
                    and claim['scope']=='DISPOSABLE_RESOURCE_LAB_ONLY',"RESOURCE_LOOKUP_CLAIM_SCHEMA")
            require(all(claim[k] is False for k in ('may_dispatch','production_go','independent_resource_authority_verified')),"RESOURCE_CLAIM_AUTHORITY_ESCALATION")
            require(all(positive(claim[k]) for k in ('sequence','owner_epoch','owner_fence','resource_fence','policy_epoch','valid_until')),"RESOURCE_CLAIM_INTEGER_TYPE")
            require(all(type(claim[k]) is str and 0<len(claim[k])<=256 for k in ('operation_id','project','authority_id','source_id','policy_version')),"RESOURCE_CLAIM_IDENTITY_TYPE")
            require(all(type(claim[k]) is str and HEX.fullmatch(claim[k]) is not None for k in ('work_identity_sha256','observation_sha256','resource_context_sha256','resource_review_sha256')),"RESOURCE_CLAIM_DIGEST_TYPE")
            require(claim['operation_id']==row['operation_id'] and claim['project']==row['op_project']
                    and claim['authority_id']==row['authority'] and claim['source_id']==row['source']
                    and claim['sequence']==row['sequence'] and claim['owner_epoch']==row['op_epoch']
                    and claim['owner_fence']==row['op_generation'] and claim['policy_epoch']==row['op_policy'],"RESOURCE_SCALAR_BINDING_HOLD")
            require(digest(row['claim_json'].encode('utf-8'))==row['claim_sha']
                    and ack.get('resource_claim_sha256')==row['claim_sha']
                    and canonical(ack.get('resource_claim'))==row['claim_json'].encode('utf-8'),"RESOURCE_LOOKUP_INTEGRITY_HOLD")
            verify_seal(ack,ACK_PURPOSE,self.ack_keys)
            require(ack['operation_id']==row['operation_id'] and ack['job_sha256']==row['job_sha']
                    and type(ack['owner_epoch']) is int and ack['owner_epoch']==claim['owner_epoch']
                    and type(ack['fence_generation']) is int and ack['fence_generation']==claim['owner_fence']
                    and type(ack['policy_epoch']) is int and ack['policy_epoch']==claim['policy_epoch']
                    and ack['may_dispatch'] is False,"RESOURCE_ACK_BINDING_HOLD")
            key=(row['authority'],row['source']);maxima[key]=max(maxima.get(key,0),row['sequence'])
            claims[row['operation_id']]=(row['claim_sha'],digest(canonical(ack)),row['job_sha'])
        for key,maximum in maxima.items():
            state=db.execute('SELECT fence,policy,last_sequence FROM resource_state WHERE authority=? AND source=?',key).fetchone()
            require(state is not None and positive(state['fence']) and type(state['policy']) is str
                    and 0<len(state['policy'])<=256 and type(state['last_sequence']) is int
                    and state['last_sequence']==maximum,"RESOURCE_HIGHWATER_INTEGRITY_HOLD")
        previous=GENESIS;commits={}
        for row in db.execute('SELECT * FROM events ORDER BY sequence').fetchall():
            event=parse(row['event_json'])
            require(event.get('previous_sha')==previous==row['previous_sha']
                    and event.get('kind')==row['kind'] and event.get('operation_id')==row['operation_id']
                    and digest(canonical(event))==row['event_sha'],"LOCAL_EVENT_CHAIN_HOLD")
            previous=row['event_sha']
            if row['kind']=='LOCAL_ADMISSION_AND_ACK_COMMITTED':
                require(row['operation_id'] in claims and row['operation_id'] not in commits,"RESOURCE_COMMIT_EVENT_CONFLICT")
                expected=claims[row['operation_id']];details=event.get('details')
                require(type(details) is dict and details.get('resource_claim_sha256')==expected[0]
                        and details.get('ack_sha256')==expected[1] and details.get('job_sha256')==expected[2],"RESOURCE_COMMIT_EVENT_BINDING_HOLD")
                commits[row['operation_id']]=True
        require(set(commits)==set(claims),"RESOURCE_COMMIT_EVENT_MISSING")

    def lookup(self, operation_id):
        require(isinstance(operation_id, str) and NAME.fullmatch(operation_id) is not None,
                "INVALID_OPERATION_ID")
        with self.connect() as db:
            db.execute('BEGIN')
            self._validate_resources(db)
            row = db.execute("""SELECT o.*, n.nonce AS claimed_nonce,
                  n.operation_id AS nonce_op, x.ack_sha AS outbox_ack_sha,
                  x.state AS outbox_state
                  FROM operations o
                  LEFT JOIN nonce_claim n ON n.operation_id=o.operation_id
                  LEFT JOIN outbox x ON x.operation_id=o.operation_id
                  WHERE o.operation_id=?""", (operation_id,)).fetchone()
            if row is None:
                return {"status": "UNKNOWN_HOLD", "may_dispatch": False, "automatic_retry": False}
            ack = json.loads(row["ack_json"])
            resource=db.execute("SELECT claim_json,claim_sha FROM resource_claims WHERE operation_id=?",(operation_id,)).fetchone()
        require(resource is not None and digest(resource["claim_json"].encode("utf-8"))==resource["claim_sha"]
                and ack.get("resource_claim_sha256")==resource["claim_sha"]
                and canonical(ack.get("resource_claim"))==resource["claim_json"].encode("utf-8"), "RESOURCE_LOOKUP_INTEGRITY_HOLD")
        verify_seal(ack, ACK_PURPOSE, self.ack_keys)
        require(ack["operation_id"] == operation_id and ack["job_sha256"] == row["job_sha"]
                and ack["status"] == "ISOLATED_ACCEPTED_NO_DISPATCH"
                and ack["may_dispatch"] is False
                and row["claimed_nonce"] == row["nonce"]
                and row["nonce_op"] == operation_id
                and row["outbox_state"] == "ACKED_ISOLATED"
                and row["outbox_ack_sha"] == digest(canonical(ack)),
                "ACK_LOOKUP_OR_ATOMIC_LEDGER_INTEGRITY_HOLD")
        return {"status": row["state"], "ack": ack, "may_dispatch": False,
                "automatic_retry": False}

    def quarantine(self, operation_id):
        def action(db):
            row = db.execute("SELECT state FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
            require(row is not None and row["state"] in ("ADMITTED", "HOLD"),
                    "INVALID_HOLD_TRANSITION")
            if row["state"] == "ADMITTED":
                db.execute("UPDATE operations SET state='HOLD' WHERE operation_id=?", (operation_id,))
                self.event(db, "UNKNOWN_OUTCOME_HOLD_NO_RETRY", operation_id, {})
            return {"status": "HOLD", "may_dispatch": False, "automatic_retry": False}
        return self.tx(action)

    def audit(self):
        with self.connect() as db:
            db.execute('BEGIN')
            self._validate_resources(db)
            require(db.execute("PRAGMA quick_check").fetchone()[0] == "ok",
                    "SQLITE_INTEGRITY_HOLD")
            require(not db.execute("PRAGMA foreign_key_check").fetchall(),
                    "FOREIGN_KEY_INTEGRITY_HOLD")
            rows = db.execute("SELECT * FROM events ORDER BY sequence").fetchall()
            records = db.execute("""SELECT o.operation_id,o.nonce,o.ack_json,o.job_sha,o.state,
                   n.nonce AS claimed_nonce, n.operation_id AS nonce_op,
                   x.ack_sha, x.state AS outbox_state
                   FROM operations o
                   LEFT JOIN nonce_claim n ON n.operation_id=o.operation_id
                   LEFT JOIN outbox x ON x.operation_id=o.operation_id""").fetchall()
            nonce_count = db.execute("SELECT COUNT(*) FROM nonce_claim").fetchone()[0]
            outbox_count = db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]
            resource_count=db.execute("SELECT COUNT(*) FROM resource_claims").fetchone()[0]
        require(len(records) == nonce_count == outbox_count,
                "ATOMIC_NONCE_OUTBOX_COUNTS_DIFFER")
        for record in records:
            ack = json.loads(record["ack_json"])
            verify_seal(ack, ACK_PURPOSE, self.ack_keys)
            require(record["state"] in ("ADMITTED", "HOLD")
                    and record["nonce"] == record["claimed_nonce"]
                    and record["nonce_op"] == record["operation_id"]
                    and record["outbox_state"] == "ACKED_ISOLATED"
                    and record["ack_sha"] == digest(canonical(ack))
                    and ack["job_sha256"] == record["job_sha"],
                    "ATOMIC_NONCE_OUTBOX_RECEIPT_CORRUPT")
        prev = GENESIS
        require(resource_count==len(records), "RESOURCE_CLAIM_COUNTS_DIFFER")
        for row in rows:
            event = json.loads(row["event_json"])
            require(event["previous_sha"] == prev and
                    digest(canonical(event)) == row["event_sha"], "LOCAL_EVENT_CHAIN_HOLD")
            prev = row["event_sha"]
        return {"status": "LOCAL_SQLITE_INVARIANTS_PASS", "events": len(rows),
                "operations": len(records), "nonce_claims": nonce_count,
                "outbox_records": outbox_count, "independent_anchor_verified": False,
                "global_cas_verified": False, "may_dispatch": False}
