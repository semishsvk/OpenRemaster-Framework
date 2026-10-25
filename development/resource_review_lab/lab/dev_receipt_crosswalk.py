"""Read-only DEV result-to-handoff observation crosswalk, not a second scheduler.

Accepts a snapshot of the existing DevWorkflowResult.v1; never invokes the worker.
Missing immutable Git lineage remains missing instead of invented from a digest.
"""
from dual_trust_shadow import evaluate

def observe(receipt):
    valid=type(receipt) is dict and receipt.get('schema')=='OpenRemaster.DevWorkflowResult.v1'
    if not valid:
        return dict(status='REJECT',reason='UNKNOWN_RECEIPT_SCHEMA',release_eligible=False,may_dispatch=False)
    worker=receipt.get('worker',{})
    if type(worker) is not dict:worker={}
    artifacts=worker.get('artifacts',{})
    if type(artifacts) is not dict:artifacts={}
    committed=(receipt.get('state')=='COMMITTED' and worker.get('success') is True
               and receipt.get('production_go') is False and artifacts.get('profile')=='DEV_UNSIGNED')
    # Source/build hashes bind references, not trust or an immutable repository commit.
    document={
        'from':'DEVELOPMENT','to':'CANDIDATE',
        'worker':{'identity':'unified-dev-worker-05','trust_class':'DEVELOPMENT'},
        'handoff':{'project':'OpenRemaster Studio DEV',
                   'build_recipe_sha256':worker.get('build_plan_sha256'),
                   'candidate_evidence':receipt.get('operation_id'),
                   'source_integrity':worker.get('source_manifest_sha256')},
        'observations':{},'fallback_requested':False}
    return dict(schema='OpenRemaster.DevReceiptDualTrustObservation.v1',
                status='OBSERVED_COMMITTED_DEV_ONLY' if committed else 'HOLD_INCOMPLETE_DEV_RESULT',
                operation_id=receipt.get('operation_id'),release_eligible=False,
                may_dispatch=False,artifact_signature_claim=artifacts.get('signature_status'),
                decision=evaluate(document))
