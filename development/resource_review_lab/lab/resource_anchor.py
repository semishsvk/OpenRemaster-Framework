"""Read-only resource snapshot and external-anchor contract review; never dispatch."""
from copy import deepcopy
from contextlib import closing
from pathlib import Path
import hashlib,re,sqlite3
from anchor import canonical,verify_current_anchor
from scope import Hold

TABLES=('owners','operations','nonce_claim','outbox','events','resource_state','resource_claims','resource_lab_metadata')
FIELDS={'schema','authority_id','scope_id','ledger_id','challenge','sequence','state_sha256',
        'issued_at','expires_at','key_id','signature'}
EXPECTED={'authority_id','scope_id','ledger_id','challenge','min_sequence'}
def _int(value,low=0):return type(value) is int and low<=value<=2**63-1
def _name(value):return type(value) is str and re.fullmatch('[A-Za-z0-9_.-]{1,128}',value) is not None
def _hash(value):return hashlib.sha256(canonical(value)).hexdigest()

def capture_resource_state(store,*,ledger_id,scope_id):
    """One read transaction; exports logical state, no key registry or side effects."""
    if not _name(ledger_id) or not _name(scope_id):raise Hold('RESOURCE_SNAPSHOT_SCOPE_INVALID')
    try:
        # mode=ro must not recreate a disappeared DB during a diagnostic read.
        with closing(sqlite3.connect(Path(store.dbpath).resolve().as_uri()+'?mode=ro',uri=True,timeout=2,isolation_level=None)) as db:
            db.row_factory=sqlite3.Row
            db.execute('BEGIN');store._validate_resources(db)
            if db.execute('PRAGMA foreign_key_check').fetchall():raise Hold('RESOURCE_SNAPSHOT_FOREIGN_KEY_HOLD')
            tables={};total=0
            for name in TABLES:
                rows=db.execute('SELECT * FROM '+name+' LIMIT 10001').fetchall()
                if len(rows)>10000:raise Hold('RESOURCE_SNAPSHOT_ROW_BOUND')
                total+=len(rows)
                if total>50000:raise Hold('RESOURCE_SNAPSHOT_TOTAL_BOUND')
                tables[name]=sorted([dict(row) for row in rows],key=lambda row:canonical(row))
            ddl=db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name LIMIT 10001").fetchall()
            if len(ddl)>10000:raise Hold('RESOURCE_SNAPSHOT_SCHEMA_BOUND')
            schema=[dict(row) for row in ddl]
        snapshot=dict(schema='OpenRemaster.ResourceLedgerSnapshot.v1',ledger_id=ledger_id,scope_id=scope_id,tables=tables,table_schema=schema)
        if len(canonical(snapshot))>8*1024*1024:raise Hold('RESOURCE_SNAPSHOT_BYTE_BOUND')
        return snapshot
    except (sqlite3.Error,ValueError,TypeError,OverflowError,RecursionError) as exc:raise Hold('RESOURCE_SNAPSHOT_UNAVAILABLE') from exc

def review_resource_anchor(store,anchor,*,expected=None,trusted_current=None,verifier=None,now=None):
    evidence={}
    def result(reason,checks=False):
        return dict(schema='OpenRemaster.ResourceAnchorReview.v1',decision='HOLD',reason=reason,
                    anchor_checks_satisfied=checks,evidence=deepcopy(evidence),scope='OFFLINE_EXTERNAL_ANCHOR_CONTRACT',
                    independent_authority_verified=False,live_freshness_verified=False,dispatch_authorized=False,
                    may_dispatch=False,may_sign=False,may_publish=False,may_promote=False,may_fallback=False,
                    automatic_retry=False,production_go=False)
    if type(expected) is not dict or set(expected)!=EXPECTED:return result('EXPECTED_ANCHOR_CONTEXT_REQUIRED')
    expected=deepcopy(expected)
    if not all(_name(expected[k]) for k in EXPECTED-{'min_sequence'}) or not _int(expected['min_sequence'],1):return result('EXPECTED_ANCHOR_CONTEXT_INVALID')
    if not _int(now) or now>253402300799:return result('VERIFIED_CLOCK_REQUIRED')
    if not callable(trusted_current) or not callable(verifier):return result('NO_INDEPENDENT_AUTHORITY')
    try:
        # Fetch once and freeze; the reused verifier must not observe a second provider view.
        current=deepcopy(trusted_current());anchor=deepcopy(anchor)
        for document in (anchor,current):
            if type(document) is not dict or set(document)!=FIELDS:return result('RESOURCE_ANCHOR_SCHEMA')
            if document['schema']!='OpenRemaster.ResourceLedgerAnchor.v1':return result('RESOURCE_ANCHOR_VERSION')
            if not all(_name(document[k]) for k in ('authority_id','scope_id','ledger_id','challenge','key_id')):return result('RESOURCE_ANCHOR_IDENTITY_INVALID')
            if not all(type(document[k]) is str and re.fullmatch('[a-f0-9]{64}',document[k]) for k in ('state_sha256','signature')):return result('RESOURCE_ANCHOR_DIGEST_INVALID')
            if not _int(document['sequence'],1) or document['sequence']<expected['min_sequence']:return result('RESOURCE_ANCHOR_SEQUENCE_HOLD')
            if not all(_int(document[k]) for k in ('issued_at','expires_at')):return result('RESOURCE_ANCHOR_TIME_INVALID')
            if not document['issued_at']<=now<document['expires_at'] or not 0<document['expires_at']-document['issued_at']<=30:return result('RESOURCE_ANCHOR_EXPIRED_OR_FUTURE')
            if any(document[k]!=expected[k] for k in EXPECTED-{'min_sequence'}):return result('RESOURCE_ANCHOR_SCOPE_MISMATCH')
        state=capture_resource_state(store,ledger_id=expected['ledger_id'],scope_id=expected['scope_id'])
        evidence.update(local_state_sha256=_hash(state),presented_anchor_sha256=_hash(anchor),current_anchor_sha256=_hash(current))
        verify_current_anchor(state,anchor,lambda:deepcopy(current),lambda doc:verifier(deepcopy(doc)) is True)
        return result('ANCHOR_CONTRACT_MATCHED_NO_EXECUTION',True)
    except Hold as exc:return result(str(exc))
    except Exception:return result('RESOURCE_ANCHOR_PROVIDER_OR_VERIFIER_UNCERTAIN')
