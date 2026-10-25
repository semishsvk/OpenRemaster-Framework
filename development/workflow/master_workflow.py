"""One advisory integration path; K003 remains the only execution scheduler."""
from glca.core import require, digest
from glca.tasks import dependency_order, propose_tests
from dev_receipt_crosswalk import observe
from intake_bridge import inspect_report

RLR_TO_GLCA={
 'RLR-01':['GLCA-001'],'RLR-02':['GLCA-001'],
 'RLR-03':['GLCA-001','GLCA-002'],'RLR-04':['GLCA-001','GLCA-002'],
 'RLR-05':['GLCA-003'],'RLR-06':['GLCA-003'],'RLR-07':['GLCA-004'],
 'RLR-08':['GLCA-005','GLCA-006'],'RLR-09':['GLCA-007']}

def advisory_package(project, tasks, completed, impacts, evidence_sha256,
                     *, governor_mode='UNKNOWN', dev_receipt=None,
                     intake_report=None, intake_context=None, model_witness=None):
    require(governor_mode in ('NORMAL','LIGHT','GAME','GAMING','UNKNOWN'),'GOVERNOR_MODE')
    ordered=dependency_order(project,tasks,completed)
    regression=propose_tests(project,impacts,evidence_sha256)
    receipt=observe(dev_receipt) if dev_receipt is not None else None
    intake=None
    inputs=[project,tasks,completed,impacts,evidence_sha256,governor_mode]
    if dev_receipt is not None:inputs.append(['dev_receipt',digest(dev_receipt)])
    if intake_report is not None or intake_context is not None:
        intake=inspect_report(intake_report,intake_context)
        require(type(intake_context) is dict and intake_context.get('project_id')==project,
                'INTAKE_ADVISORY_PROJECT_MISMATCH')
        inputs.append(['r06_intake',intake])
    observation=None
    if model_witness is not None:
        from glca.core import canonical_state_bytes
        from glca.witness import verify_model_witness
        canonical_state_bytes(model_witness)
        require(type(model_witness) is dict and set(model_witness)=={'initial','model','corpus','witness'},
                'ADVISORY_WITNESS_SCHEMA')
        require(all(type(model_witness[k]) is dict and model_witness[k].get('project')==project
                    for k in ('initial','model','corpus','witness')),'ADVISORY_WITNESS_PROJECT')
        verified=verify_model_witness(model_witness['initial'],model_witness['model'],
                                      model_witness['corpus'],model_witness['witness'])
        observation=dict(verified,project=project,
                         source_manifest_digest=model_witness['corpus']['manifest_digest'],
                         initial_state=model_witness['initial']['state_digest'],
                         ending_id=model_witness['witness']['ending_id'])
        inputs.append(['model_witness',digest(model_witness),observation])
    result=dict(schema='OpenRemaster.MasterAdvisoryPackage.v1',project=project,
                evidence_sha256=evidence_sha256,proposal_digest=digest(inputs),
                dependency_plan=ordered,regression_plan=regression,dev_build_observation=receipt,
                governor_mode=governor_mode,resource_request=dict(heavy_slots=0,max_global_heavy_slots=3),
                intake_observation=intake,
                executor='EXISTING_K003_ONLY',status='HOLD_ADMISSION_REQUIRED',
                required_authorities=['PROJECT_OWNER','WRITER_LEASE','K003','RESOURCE_GOVERNOR'],
                may_dispatch=False,may_acquire_lease=False,may_sign=False,may_publish=False,
                production_go=False)
    if observation is not None:result['model_witness_observation']=observation
    return result
