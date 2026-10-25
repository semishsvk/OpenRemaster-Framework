"""No-dispatch compatibility check against the unchanged D7 and K003 contracts."""
import hashlib,json
from pathlib import Path
from jsonschema import Draft202012Validator
from admission_boundary_base import canonical
from resource_observation import review_resource_observation
from dev_receipt_crosswalk import observe

SCHEMA_SHA256='aa126363777186df589b0a27a35006f6f570b834108cd8501291f30432fac006'

def _strict(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('DUPLICATE_KEY')
            result[key]=value
        return result
    return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE')))

def review_d7_compatibility(request,identity_inputs,observation,*,expected_identity=None,
                            expected_resource=None,owner_keys=None,envelope_keys=None,now=None,dev_result=None):
    evidence={};observation_result=None;checks=dict(request_contract_matches=False,dev_result_observed=False,identity_resource_contract_matches=False,k003_shape_matches=False,d7_build_kind_supported=False)
    def result(reason):
        return dict(schema='OpenRemaster.D7CompatibilityReview.v1',decision='HOLD',reason=reason,
                    checks=dict(checks),evidence=dict(evidence),dev_receipt_observation=observation_result,scope='OFFLINE_EXISTING_CONTRACT_COMPATIBILITY',
                    worker_called=False,k003_invoked=False,query_performed=False,receipt_created=False,
                    independent_admission_verified=False,production_signature_required_for_development=False,
                    dispatch_authorized=False,may_dispatch=False,may_sign=False,may_publish=False,
                    may_promote=False,may_fallback=False,automatic_retry=False,production_go=False)
    if type(request) is not dict or set(request)!={'action','operation_id','scenario'}:return result('D7_REQUEST_SCHEMA')
    if request['action'] not in ('submit','status') or type(request['operation_id']) is not str or len(request['operation_id'])!=32 or any(c not in '0123456789abcdef' for c in request['operation_id']) or request['scenario']!='build_studio_dev':return result('D7_REQUEST_SCOPE')
    if type(expected_identity) is not dict or type(expected_identity.get('shadow_context')) is not dict:return result('EXPECTED_IDENTITY_REQUIRED')
    context=expected_identity['shadow_context']
    if request['operation_id']!=context.get('operation_id') or request['scenario']!=context.get('capability'):return result('D7_REQUEST_IDENTITY_MISMATCH')
    checks['request_contract_matches']=True
    if dev_result is not None:
        try:
            if type(dev_result) is not dict or len(canonical(dev_result))>65536:return result('DEV_RESULT_SHAPE_OR_BOUND')
            if dev_result.get('operation_id')!=request['operation_id']:return result('DEV_RESULT_OPERATION_MISMATCH')
            if dev_result.get('production_go') is not False:return result('DEV_RESULT_PRODUCTION_OVERCLAIM')
            observation_result=observe(dev_result)
            evidence['dev_result_sha256']=hashlib.sha256(canonical(dev_result)).hexdigest()
            if observation_result.get('status')=='REJECT':return result('DEV_RESULT_SCHEMA')
            checks['dev_result_observed']=True
        except (TypeError,ValueError,RecursionError):return result('DEV_RESULT_MALFORMED')
    if request['action']=='status':return result('D7_STATUS_QUERY_ONLY_NO_EXECUTION_OR_QUERY_PERFORMED')
    if type(identity_inputs) is not dict or type(identity_inputs.get('request')) is not dict:return result('IDENTITY_INPUT_REQUIRED')
    try:
        if canonical(request)!=canonical(identity_inputs['request']):return result('D7_SIGNED_REQUEST_MISMATCH')
        reviewed=review_resource_observation(identity_inputs,observation,expected_identity=expected_identity,expected_resource=expected_resource,owner_keys=owner_keys,envelope_keys=envelope_keys,now=now)
        evidence['resource_review_sha256']=hashlib.sha256(canonical(reviewed)).hexdigest()
        if not reviewed['resource_checks_satisfied']:return result('RESOURCE_'+reviewed['reason'])
        checks['identity_resource_contract_matches']=True
        raw=identity_inputs['job_bytes']
        if type(raw) is not bytes or not 0<len(raw)<=65536:return result('K003_JOB_BOUND')
        path=Path(__file__).resolve().parent.parent/'schemas/orch-k003-job.schema.json';schema_bytes=path.read_bytes()
        if hashlib.sha256(schema_bytes).hexdigest()!=SCHEMA_SHA256:return result('K003_SCHEMA_SOURCE_DRIFT')
        schema=_strict(schema_bytes);job=_strict(raw)
        Draft202012Validator.check_schema(schema)
        errors=list(Draft202012Validator(schema).iter_errors(job))
        evidence.update(k003_schema_sha256=SCHEMA_SHA256,job_bytes_sha256=hashlib.sha256(raw).hexdigest())
        if errors:return result('K003_JOB_DOES_NOT_MATCH_EXISTING_SCHEMA')
        checks['k003_shape_matches']=True
        supported=schema['properties']['execution']['properties']['kind']['enum']
        if 'build_studio_dev' not in supported:return result('D7_BUILD_KIND_NOT_SUPPORTED_BY_PINNED_K003_NO_EXECUTABLE_FALLBACK')
        # A future schema update is not automatically admission: this version remains pinned.
        return result('EXPLICIT_ADAPTER_OWNER_RESOURCE_AND_K003_ACCEPTANCE_REQUIRED')
    except (OSError,ValueError,TypeError,KeyError,RecursionError,OverflowError):return result('MALFORMED_OR_UNAVAILABLE_COMPATIBILITY_EVIDENCE')
