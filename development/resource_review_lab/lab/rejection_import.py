"""Verify reported rejection snapshot bytes against caller-supplied expectations."""
import hashlib,json
from admission_boundary_base import canonical
from rejection_evidence import export_bundle,hexvalue

MAX_BYTES=262144
def review_import(raw,*,expected_bytes_sha256=None,expected_record_count=None):
    evidence={}
    def result(decision,reason,matched=False):
        return dict(schema='OpenRemaster.ShadowRejectionImportReview.v1',decision=decision,reason=reason,integrity_matched=matched,evidence=dict(evidence),expected_digest_authority_verified=False,independent_authority_verified=False,authenticated=False,durability_verified=False,complete_history_verified=False,freshness_verified=False,may_dispatch=False,may_sign=False,may_publish=False,may_promote=False,may_fallback=False,automatic_retry=False,production_go=False)
    if not hexvalue(expected_bytes_sha256,64):return result('HOLD','EXTERNAL_EXPECTED_BYTES_DIGEST_REQUIRED')
    if type(expected_record_count) is not int or not 1<=expected_record_count<=128:return result('HOLD','EXTERNAL_EXPECTED_RECORD_COUNT_REQUIRED')
    if type(raw) is not bytes or not 0<len(raw)<=MAX_BYTES:return result('REJECT','IMPORT_BYTES_BOUND')
    observed=hashlib.sha256(raw).hexdigest();evidence['observed_bytes_sha256']=observed
    if observed!=expected_bytes_sha256:return result('REJECT','EXPECTED_BYTES_DIGEST_MISMATCH')
    def unique(pairs):
        obj={}
        for key,value in pairs:
            if key in obj:raise ValueError('DUPLICATE_KEY')
            obj[key]=value
        return obj
    def nonfinite(_):raise ValueError('NONFINITE')
    try:
        document=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=nonfinite)
        if type(document) is not dict or type(document.get('records')) is not list:return result('REJECT','IMPORT_SCHEMA')
        if len(document['records'])!=expected_record_count:return result('REJECT','EXPECTED_RECORD_COUNT_MISMATCH')
        rebuilt=export_bundle(document['records'])
        if canonical(document)!=canonical(rebuilt):return result('REJECT','IMPORT_SCHEMA_OR_INTEGRITY_MISMATCH')
        evidence.update(export_sha256=rebuilt['export_sha256'],record_count=expected_record_count)
        return result('HOLD','INTEGRITY_MATCHED_REPORTED_SHADOW_ONLY',True)
    except (KeyError,ValueError,TypeError,UnicodeError,RecursionError,OverflowError):return result('REJECT','MALFORMED_OR_INVALID_IMPORT')
