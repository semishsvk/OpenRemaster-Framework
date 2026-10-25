"""One advisory integration path; K003 remains the only execution scheduler."""
from glca.core import require, digest
from glca.tasks import dependency_order, propose_tests
from dev_receipt_crosswalk import observe

RLR_TO_GLCA={
 'RLR-01':['GLCA-001'],'RLR-02':['GLCA-001'],
 'RLR-03':['GLCA-001','GLCA-002'],'RLR-04':['GLCA-001','GLCA-002'],
 'RLR-05':['GLCA-003'],'RLR-06':['GLCA-003'],'RLR-07':['GLCA-004'],
 'RLR-08':['GLCA-005','GLCA-006'],'RLR-09':['GLCA-007']}

def advisory_package(project, tasks, completed, impacts, evidence_sha256,
                     *, governor_mode='UNKNOWN', dev_receipt=None):
    require(governor_mode in ('NORMAL','LIGHT','GAME','GAMING','UNKNOWN'),'GOVERNOR_MODE')
    ordered=dependency_order(project,tasks,completed)
    regression=propose_tests(project,impacts,evidence_sha256)
    receipt=observe(dev_receipt) if dev_receipt is not None else None
    return dict(schema='OpenRemaster.MasterAdvisoryPackage.v1',project=project,
                evidence_sha256=evidence_sha256,proposal_digest=digest([project,tasks,completed,impacts,evidence_sha256,governor_mode]),
                dependency_plan=ordered,regression_plan=regression,dev_build_observation=receipt,
                governor_mode=governor_mode,resource_request=dict(heavy_slots=0,max_global_heavy_slots=3),
                executor='EXISTING_K003_ONLY',status='HOLD_ADMISSION_REQUIRED',
                required_authorities=['PROJECT_OWNER','WRITER_LEASE','K003','RESOURCE_GOVERNOR'],
                may_dispatch=False,may_acquire_lease=False,may_sign=False,may_publish=False,
                production_go=False)
