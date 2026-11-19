"""Bounded source-only interface observation. Never import or execute worker code."""
import ast
import hashlib
import re

def review_dev_boundary(source,*,expected_sha256):
    evidence={}
    def result(reason,syntax=None):
        return dict(schema='OpenRemaster.DevBoundarySourceReview.v1',decision='HOLD',reason=reason,
                    scope='PINNED_SOURCE_SYNTAX_ONLY',evidence=dict(evidence),syntax=syntax,
                    independent_admission_verified=False,owner_lease_verified=False,
                    resource_authority_verified=False,k003_compatibility_verified=False,
                    worker_liveness_verified=False,source_executed=False,dispatch_authorized=False,
                    may_dispatch=False,may_sign=False,may_publish=False,may_promote=False,
                    may_fallback=False,automatic_retry=False,production_go=False)
    if type(expected_sha256) is not str or re.fullmatch('[a-f0-9]{64}',expected_sha256) is None:return result('SOURCE_PIN_REQUIRED')
    if type(source) is not bytes or not 0<len(source)<=262144:return result('SOURCE_BOUND_OR_TYPE')
    actual=hashlib.sha256(source).hexdigest();evidence['source_sha256']=actual
    if actual!=expected_sha256:return result('SOURCE_DRIFT')
    try:
        tree=ast.parse(source.decode('utf-8-sig'),filename='<pinned-worker-source>')
        functions={};constants={}
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                if node.name in functions:return result('DUPLICATE_FUNCTION_DECLARATION')
                calls=[];sets=[]
                for child in ast.walk(node):
                    if isinstance(child,ast.Call):
                        target=child.func
                        if isinstance(target,ast.Name):calls.append(dict(target=target.id,line=child.lineno))
                        elif isinstance(target,ast.Attribute) and isinstance(target.value,ast.Name):calls.append(dict(target=target.value.id+'.'+target.attr,line=child.lineno))
                    if isinstance(child,ast.Set) and all(isinstance(v,ast.Constant) and type(v.value) is str for v in child.elts):sets.append(sorted(v.value for v in child.elts))
                functions[node.name]=dict(line=node.lineno,direct_call_syntax=calls,literal_string_sets=sets)
            elif isinstance(node,ast.Assign) and isinstance(node.value,ast.Set) and all(isinstance(v,ast.Constant) and type(v.value) is str for v in node.value.elts):
                for target in node.targets:
                    if isinstance(target,ast.Name):constants[target.id]=sorted(v.value for v in node.value.elts)
        syntax=dict(functions=functions,literal_set_constants=constants,
                    interpretation='DECLARATIONS_AND_CALL_SYNTAX_ARE_NOT_AUTHORITY_OR_CONTROL_FLOW_PROOF')
        return result('SOURCE_RECONCILED_LIVE_OWNER_RESOURCE_AND_K003_HOLD',syntax)
    except (SyntaxError,UnicodeError,ValueError,TypeError,RecursionError):return result('SOURCE_PARSE_HOLD')
