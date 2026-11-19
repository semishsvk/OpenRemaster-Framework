"""Consume existing R06 intake claims as advice, never execution authority.

No receipts are minted, paths from reports are followed, signatures verified,
leases acquired or workers started. Complete self-attestation still means HOLD.
"""
import hashlib
import json
from pathlib import Path
import re

SCHEMA='OpenRemaster.R06.LiveAuthorityIntakeReport.v1'
CONTEXT=('operation_id','work_package_sha256','project_id','capability','packet_sha256')
CANONICAL_CHECKS=('contract_schema','packet_schema','packet_hash_matches_contract',
                  'operation_matches_contract','work_package_matches_contract',
                  'packet_dispatch_false','packet_production_false')
ROLE_CHECKS={
 'host_health_receipt':('schema','not_replay_or_historical','not_fixture_only','no_stale_snapshot',
   'live_receipt_marker','current_generation_present','current_fence_present','freshness_verified',
   'project_binding','path_allowlist_verified','signature_or_secure_channel_marker'),
 'k003_admission_receipt':('schema','decision_admit','authority_authenticated','owner_admitted',
   'witness_admitted','fence_verified','production_go_false','fixture_only_false','live_receipt_marker',
   'live_authority_scope','receipt_signature_present','lease_id_present','lease_nonce_present',
   'fence_epoch_present','fence_generation_present','binding_operation_id','binding_work_package_sha256',
   'binding_project_id','binding_capability','not_development_self_signed'),
 'signature_verification_result':('verified','key_identity_present','verification_time_present',
   'verification_method_present','verified_payload_digest','operation_binding','work_package_binding',
   'not_development_self_signed'),
}
PAIR_CHECKS=('operation_binding','work_package_binding','owner_admitted','witness_admitted',
             'independence_verified','not_same_process_self_attestation','not_unsigned_local_fixture')
PRINCIPAL_CHECKS=('schema_present','role_matches','admitted','operation_binding','work_package_binding',
 'independence_verified','not_same_process_self_attestation','not_unsigned_local_fixture','not_development_scope')
FALSE_FLAGS=('authority_bound','signature_verification_performed_by_validator','synthetic_evidence_created',
             'dispatch_authorized','dispatch_performed','worker_started_by_validator','production_go')
ZERO=dict(may_dispatch=False,may_acquire_lease=False,may_sign=False,may_publish=False,
          production_go=False,independent_authority_verified=False)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

def decision(reasons,source_sha=None,context_sha=None,consistent=False,reject=False):
    reasons=sorted(set(reasons+['INDEPENDENT_CRYPTO_OWNER_LEASE_GOVERNOR_REVALIDATION_REQUIRED']))
    return dict(schema='OpenRemaster.R06.AdvisoryIntakeBridge.v1',status='REJECT' if reject else 'HOLD',
                reasons=reasons,source_report_sha256=source_sha,context_sha256=context_sha,
                structural_claims_consistent=consistent,scope='UNTRUSTED_REPORT_CLAIMS_ONLY',**ZERO)

def _context_valid(expected):
    return (type(expected) is dict and set(expected)==set(CONTEXT)
        and all(type(expected[k]) is str and 0<len(expected[k])<=256 for k in CONTEXT)
        and all(re.fullmatch('[a-f0-9]{64}',expected[k]) is not None for k in ('work_package_sha256','packet_sha256')))

def inspect_report(report,expected):
    """Bind an R06 report to a caller's advisory context; assertions stay untrusted."""
    try:
        raw=canonical(report)
        if len(raw)>250000:return decision(['REPORT_SIZE_LIMIT'],reject=True)
        source_sha=hashlib.sha256(raw).hexdigest()
    except (TypeError,ValueError,RecursionError):return decision(['REPORT_NOT_CANONICAL_JSON'],reject=True)
    if not _context_valid(expected):return decision(['EXPECTED_CONTEXT_INVALID'],source_sha,reject=True)
    context_sha=hashlib.sha256(canonical(expected)).hexdigest()
    if type(report) is not dict or report.get('schema')!=SCHEMA:
        return decision(['UNKNOWN_INTAKE_SCHEMA'],source_sha,context_sha,reject=True)
    reasons=[];reject=False
    if report.get('read_only') is not True:reasons.append('READ_ONLY_MARKER_REQUIRED');reject=True
    for flag in FALSE_FLAGS:
        if report.get(flag) is not False:reasons.append('FORBIDDEN_OR_UNKNOWN_FLAG:'+flag);reject=True
    top=report.get('status');ready=report.get('intake_ready')
    if top not in ('PASS_LIVE_AUTHORITY_INTAKE_NO_DISPATCH','WAITING_FOR_EXTERNAL_AUTHORITY_EVIDENCE','HOLD_BEFORE_DISPATCH'):
        reasons.append('UNKNOWN_INTAKE_STATUS');reject=True
    if type(ready) is not bool:reasons.append('INTAKE_READY_BOOLEAN_REQUIRED');reject=True
    if top=='PASS_LIVE_AUTHORITY_INTAKE_NO_DISPATCH' and ready is not True:
        reasons.append('CONTRADICTORY_TOP_LEVEL_STATUS');reject=True
    if ready is True and top!='PASS_LIVE_AUTHORITY_INTAKE_NO_DISPATCH':
        reasons.append('CONTRADICTORY_TOP_LEVEL_STATUS');reject=True
    binding=report.get('canonical')
    if type(binding) is not dict:binding={}
    for key in CONTEXT:
        actual=binding.get('packet_sha256_observed' if key=='packet_sha256' else key)
        if actual!=expected[key]:reasons.append('CONTEXT_MISMATCH:'+key);reject=True
    checks=binding.get('checks',{})
    if type(checks) is not dict or any(checks.get(k) is not True for k in CANONICAL_CHECKS):
        reasons.append('CANONICAL_CHECKS_INCOMPLETE');reject=True
    evidence=report.get('evidence',{})
    if type(evidence) is not dict:evidence={};reject=True
    def row_ok(row,required,label):
        if type(row) is not dict:return False
        c=row.get('checks')
        return (row.get('present') is True and row.get('status')=='PASS'
                and row.get('failures')==[] and type(c) is dict and bool(c)
                and all(type(v) is bool or v in ('PASS','FAIL') for v in c.values())
                and all(c.get(k) is True or c.get(k)=='PASS' for k in required)
                and all(v is True or v=='PASS' for v in c.values()))
    missing=[];rejected=[]
    roles=tuple(ROLE_CHECKS)+('owner_witness_evidence',)
    for role in roles:
        row=evidence.get(role)
        if type(row) is not dict or row.get('present') is not True:
            missing.append(role);reasons.append('MISSING:'+role);continue
        if role=='owner_witness_evidence' and type(row.get('subevidence')) is dict:
            sub=row['subevidence']
            good=(row.get('status')=='PASS' and row.get('failures')==[]
                  and all(row_ok(sub.get(k),PRINCIPAL_CHECKS,k) for k in ('owner_receipt','witness_receipt')))
        else:good=row_ok(row,PAIR_CHECKS if role=='owner_witness_evidence' else ROLE_CHECKS[role],role)
        if not good:rejected.append(role);reasons.append('INCOMPLETE_OR_REJECTED:'+role)
    for label,actual in [('missing_external_evidence',missing),('rejected_external_evidence',rejected)]:
        reported=report.get(label)
        if type(reported) is not list or any(type(x) is not str for x in reported) or sorted(reported)!=sorted(actual):
            reasons.append('INCONSISTENT_SUMMARY:'+label);reject=True
    failures=report.get('failures')
    if type(failures) is not list or any(type(x) is not str for x in failures):
        reasons.append('FAILURES_LIST_INVALID');reject=True
    elif failures:reasons.append('INTAKE_REPORT_HAS_FAILURES')
    manifest=report.get('manifest')
    if not row_ok(manifest,('schema','operation_binding','work_package_binding','owner_witness_mode'),'manifest'):
        reasons.append('MANIFEST_INCOMPLETE_OR_REJECTED')
    if ready is True and (missing or rejected or failures):reasons.append('FALSE_READY_CLAIM');reject=True
    if ready is not True:reasons.append('INTAKE_NOT_READY')
    consistent=not reasons
    return decision(reasons,source_sha,context_sha,consistent,reject)

def read_report(path,expected_sha256,expected):
    """Read one explicitly selected bounded snapshot; never follow report paths."""
    if type(expected_sha256) is not str or re.fullmatch('[a-f0-9]{64}',expected_sha256) is None:
        return decision(['EXPECTED_REPORT_DIGEST_REQUIRED'],reject=True)
    try:
        path=Path(path)
        if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):
            return decision(['REPORT_LINK_FORBIDDEN'],reject=True)
        before=path.stat()
        if before.st_size>250000:return decision(['REPORT_SIZE_LIMIT'],reject=True)
        with path.open('rb') as stream:raw=stream.read(250001)
        after=path.stat()
        if len(raw)>250000 or (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            return decision(['REPORT_CHANGED_OR_OVERSIZE'],reject=True)
        observed=hashlib.sha256(raw).hexdigest()
        if observed!=expected_sha256:return decision(['REPORT_HASH_MISMATCH'],observed,reject=True)
        def unique(pairs):
            result={}
            for key,value in pairs:
                if key in result:raise ValueError('DUPLICATE_JSON_KEY')
                result[key]=value
            return result
        def nonfinite(value):raise ValueError('NONFINITE_JSON')
        report=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_constant=nonfinite)
        result=inspect_report(report,expected);result['source_file_sha256']=observed
        return result
    except (OSError,ValueError,TypeError,UnicodeError,RecursionError):
        return decision(['REPORT_UNREADABLE_OR_INVALID_JSON'],reject=True)
