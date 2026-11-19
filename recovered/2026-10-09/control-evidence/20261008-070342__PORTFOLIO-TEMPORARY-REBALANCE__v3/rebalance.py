"""User-authorized temporary planning shift; not dispatch or a game checkpoint.
Reads existing evidence, publishes a new immutable planning revision, and leaves
all game worktrees, authoritative corpora, production code and live leases alone.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import copy, hashlib, json, os

ROOT=Path(__file__).resolve().parent
CP=Path(r'F:\Remaster Framework\orchestrator\control-plane')
OLD=CP/'portfolio-lanes-20261007-v2.json'
NEW=CP/'portfolio-lanes-20261008-v3.json'
PIN='2d726851edbb209e70c00c23731f8b573f0729d30cdcc0ab3591c2fdc0d92474'
FOCUS=['OpenMDK1','OpenStonekeep','OpenUltima8']
PROTECTED=['orch_k003.py','leases.py','capabilities.json','worker-commissioning.json','framework-vnext-policies.json']
EVIDENCE=[
 Path(r'F:\Remaster Framework\work\_reviews\OR-AUDIT-20261007-a43c52d9\results\report.json'),
 Path(r'F:\Remaster Framework\work\OpenStonekeep-E16\CURRENT_STATUS.md'),
 Path(r'F:\Remaster Framework\work\OpenStonekeep-E16\checkpoints\STONE-K292-E.15.md'),
 Path(r'F:\Remaster Framework\work\OpenStonekeep-E16\e17_callbacks.json'),
 Path(r'F:\Remaster Framework\work\OpenUltima8\u8-k002a\manifest.json'),
 Path(r'F:\Remaster Framework\work\OpenUltima8\u8-k002a\glob_multiset_xval.json'),
 Path(r'F:\Remaster Framework\work\OpenUltima8\u8-k002a\nonfixed_multiset_xval.json'),
 Path(r'F:\Remaster Framework\work\OpenUltima8\u8-k002a\render_map5.py'),
]

def sha(raw):return hashlib.sha256(raw).hexdigest()
def pack(value):return (json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(path,raw):
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def parse(raw):return json.loads(raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig'))

def main():
    oldraw=OLD.read_bytes()
    if sha(oldraw)!=PIN:raise RuntimeError('PLANNING_BASELINE_CHANGED')
    prior=parse(oldraw)
    protected={str(CP/n):sha((CP/n).read_bytes()) for n in PROTECTED}
    snapshots={str(p):p.read_bytes() for p in EVIDENCE}
    inputs={p:sha(raw) for p,raw in snapshots.items()}
    updated=copy.deepcopy(prior)
    entries={e['id']:e for e in updated['entries']}
    oldentries={e['id']:e for e in prior['entries']}
    now=datetime.now(timezone.utc).isoformat()
    # These observations select bounded work; stored PASS is not promoted to a fresh PASS.
    stone=parse(snapshots[str(EVIDENCE[3])])
    u8=parse(snapshots[str(EVIDENCE[4])])
    globs=parse(snapshots[str(EVIDENCE[5])])
    nonfixed=parse(snapshots[str(EVIDENCE[6])])
    observed={
      'OpenMDK1':{'scope':'Existing independent material-field audit read; original consumer identity remains unresolved.',
        'next':'Trace the original consumer of signed field +0x06 and distinguish it from flags +0x20 and selector +0x22; test counterexamples before any material binding promotion.'},
      'OpenStonekeep':{'scope':'Local CURRENT_STATUS points to E.12, but E.15 checkpoint and later callback evidence exist; reconcile evidence before continuing, not restart E.13.',
        'stored_e17_callback_levels':stone.get('level_count'),'stored_e17_errors':stone.get('errors'),
        'next':'Pin the E.15/E.16/E.17 evidence chain and close one missing callback/state-delta dependency in the three-level movement/turn graph.'},
      'OpenUltima8':{'scope':'U8-K002A baseline render directly iterates FIXED records; separate cross-validation reports expanded instances. Reconcile baseline versus materialized scene, not infer fidelity from either count.',
        'stored_baseline_objects':u8.get('objects'),'stored_expanded_objects':globs.get('ours'),
        'stored_multiset_match':globs.get('exact_multiset_match'),'stored_nonfixed_raw':nonfixed.get('total_raw_records'),
        'stored_nonfixed_nested':nonfixed.get('nested'),
        'next':'Close Map5 scene-population contract: FIXED/GLOB expansion plus NONFIXED parent/child membership and provenance; preserve multiplicity.'}
    }
    tasks={
      'OpenMDK1':(
        'Uzavrieť source-backed význam signed f3 (+0x06) a presné priradenie materiálu k payloadu pre LEVEL3.',
        'SHA-256 vstupov + originálny consumer/dataflow + nezávislé protipríklady starého modulo mapovania; flags a UV sa nesmú zameniť za materiál.',
        'Až po sémantickom dôkaze a samostatnom admission povýšiť binding; žiadny nový renderer/UV guess.'),
      'OpenStonekeep':(
        'Nadviazať na E.15/E.16/E.17 a uzavrieť jeden chýbajúci callback/state-delta kontrakt trojúrovňového movement/turn grafu.',
        'Najprv zosúladiť checkpointy podľa artefaktov a hashov; každá skúmaná hrana musí mať explicitný predpoklad, zmenu stavu a dôkaz.',
        'Povýšiť iba doložený state-qualified graf. Žiadny globálny softlock/one-way záver zo samotnej reciprocity portálov.'),
      'OpenUltima8':(
        'Uzavrieť Map5 materialization kontrakt: FIXED/GLOB runtime inštancie a NONFIXED vnorené objekty bez zámeny definícií za populáciu scény.',
        'Zdrojové hashe + multiplicity-preserving multiset cross-check + parent/child integrity + bounds; porovnať s pripnutou nezávislou implementáciou.',
        'Povýšiť len overenú materializáciu. Renderer ordering, interakcie a original-runtime fidelity sú oddelené gates; plný remaster sa implicitne neschvaľuje.')
    }
    for index,pid in enumerate(FOCUS,1):
        e=entries[pid]
        e.update(lane='FOCUS_READ_ONLY',active=True,priority=index,
          task_state='PLANNED_FOCUS_NOT_DISPATCHED',
          completion_critical_task=tasks[pid][0],validation_gate=tasks[pid][1],promotion_condition=tasks[pid][2],
          first_action=observed[pid]['next'],
          focus_scope='Read-only evidence/code inspection now; isolated CPU probes only after applicable project ownership and task safety checks.',
          heavy_execution_state='NOT_ADMITTED_OR_RUNNING',
          stop_condition='Pri chýbajúcich dôkazoch alebo obmedzení projektu zaznamenať presný blocker a prenechať fokus ďalšej pripravenej lane. Žiadny runtime/build/capture bez existujúcich admission a resource gates.',
          evidence_observation=observed[pid],
          checkpoint_claim='EXISTING_EVIDENCE_READ; NO_NEW_GAME_VERIFICATION')
    retail=entries['OpenAzrael-Retail']
    retail['suspended_task']={k:retail[k] for k in ['completion_critical_task','validation_gate','promotion_condition','first_action']}
    retail.update(lane='WARM_WAIT_EXTERNAL',active=False,priority=None,
      task_state='PAUSED_EXTERNAL_BLOCKERS_BY_USER',completion_critical_task=None,
      first_action='No recurring writer/preflight polling as the main continuation task. Resume only after a new owner instruction or actual evidence resolving the blockers.',
      validation_gate='On resumption verify real writer handoff, worker identity/host integration, then the existing Retail-specific gates.',
      promotion_condition='Nový výslovný pokyn na návrat alebo doložené odstránenie blockerov + riadne admission. Neblokovať ostatné lane čakaním na Retail.',
      stop_condition='Neplánovať nové Retail joby ani opakované kontroly nezmeneného zámku; nemení sa živý writer/ticket ani Demo closure.',
      pause_preserves_retail_as_only_active_azrael_branch=True,
      writer_queue_action='PRESERVED_NOT_RECHECKED_OR_MODIFIED_THIS_OPERATION')
    entries['OpenROTH'].update(lane='WARM_COMPLETION',priority=None,
      temporary_focus_reason='Current next runtime boot/interaction task shares unavailable execution/oracle prerequisites; keep task intact, do not fill a focus lane with repeated boot probes.')
    for pid in ['OpenRemasterFramework','OpenRemasterOrchestrator']:
        entries[pid]['planning_role']='ON_DEMAND_ONLY'
        entries[pid]['no_repeat_policy']='Do not run more equivalent canaries or denied commissioning attempts without a new concrete task, permission change, or evidence that can unlock production.'
    updated['revision']='PORTFOLIO-LANES-20261008-v3'
    updated['supersedes_revision']=prior['revision'];updated['supersedes_sha256']=PIN
    updated['updated_at_utc']=now
    updated['temporary_focus_decision']={
      'id':'TEMPORARY-NON-AZRAEL-FOCUS-20261008','authority':'EXPLICIT_USER_INSTRUCTION',
      'user_statement':'Presun zatial pracu na ine lane','recorded_at_utc':now,
      'temporary':True,'focus':FOCUS,'paused_project':'OpenAzrael-Retail',
      'prior_long_term_heavy_priority':prior['policy']['primary_heavy_priority'],
      'reason':'Use independent evidence/semantic work instead of repeatedly waiting for the same Azrael writer/native commissioning blockers.',
      'return_condition':'New owner instruction or actual blocker-resolution evidence; never implicit Demo reopening.',
      'global_admission_waived':False,'new_project_scope_authorized':False}
    p=updated['policy']
    p['long_term_heavy_priority_before_pause']=prior['policy']['primary_heavy_priority']
    p['primary_heavy_priority']=FOCUS
    p['temporary_focus_lane_ids']=FOCUS
    p['immediate_work_mode']='READ_ONLY_EVIDENCE_AND_SEMANTIC_REVIEW; NO_HEAVY_DISPATCH_IMPLIED'
    p['heavy_priority_is_not_resource_reservation']=True
    p['continue_routing']='Start with OpenMDK1, then OpenStonekeep, then OpenUltima8 based on actual readiness. Do not restart the Azrael permission/lease polling loop.'
    p['azrael_status']='RETAIL_TEMPORARILY_PAUSED; DEMO_CLOSED'
    p['azrael_recheck_policy']='Only when new evidence/authorization arrives or at explicit user request; no duplicate tickets, no lease takeover.'
    updated['coverage']['lane_counts']=dict(Counter(e['lane'] for e in entries.values()))
    updated['coverage']['paused_entries']=1
    updated['coverage']['active_entries']=21
    updated['coverage']['focused_entries']=3
    updated['scheduler_binding']='PLANNING_REGISTER_ONLY; RUNTIME_INTEGRATION_AND_ADMISSION_PENDING'
    mutable=set(FOCUS)|{'OpenAzrael-Retail','OpenROTH','OpenRemasterFramework','OpenRemasterOrchestrator'}
    checks={
      'all_23_entries_retained':set(entries)==set(oldentries) and len(entries)==23,
      'demo_record_unchanged':entries['OpenAzrael-Demo']==oldentries['OpenAzrael-Demo'],
      'all_authoritative_paths_preserved':all(entries[k]['authoritative_corpus']==v['authoritative_corpus'] for k,v in oldentries.items()),
      'other_16_entries_unchanged':all(entries[k]==v for k,v in oldentries.items() if k not in mutable),
      'exactly_three_focus_lanes':[e['id'] for e in sorted((entries[k] for k in FOCUS),key=lambda e:e['priority'])]==FOCUS and sum(e['lane']=='FOCUS_READ_ONLY' for e in entries.values())==3,
      'retail_work_paused_preserved':retail['completion_critical_task'] is None and bool(retail['suspended_task']['completion_critical_task']),
      'all_focus_tasks_have_gates':all(entries[k]['completion_critical_task'] and entries[k]['validation_gate'] and entries[k]['promotion_condition'] for k in FOCUS),
      'global_admission_preserved':updated['global_admission']==prior['global_admission'],
      'production_admission_not_relabelled':all(entries[k]['execution_admission']==v['execution_admission'] for k,v in oldentries.items()),
      'safety_constraints_preserved':all(p[k]==prior['policy'][k] for k in ['max_heavy_lanes','wip_limit_per_project','single_writer','shared_resource_leases_required','fail_closed','read_only_authoritative_corpora','frozen_phase1']),
      'historical_checkpoint_claims_preserved':all(entries[k]['latest_verified_checkpoint']==v['latest_verified_checkpoint'] for k,v in oldentries.items()),
      'evidence_inputs_unchanged':all(Path(path).read_bytes()==raw for path,raw in snapshots.items())
    }
    if not all(checks.values()):raise RuntimeError('PREPUBLICATION_VALIDATION_FAILED:'+str(checks))
    put(ROOT/'planning-before.json',oldraw)
    data=pack(updated)
    put(ROOT/'portfolio-lanes-20261008-v3.json',data)
    lock=CP/'.portfolio-lanes.write-lock'
    lock.mkdir(exist_ok=False)
    try:
        if OLD.read_bytes()!=oldraw:raise RuntimeError('BASE_CHANGED_BEFORE_PUBLICATION')
        if any(sha(Path(n).read_bytes())!=h for n,h in protected.items()):raise RuntimeError('PRODUCTION_CHANGED')
        put(NEW,data)
        if NEW.read_bytes()!=data:raise RuntimeError('READBACK_FAILED')
    finally:lock.rmdir()
    checks['new_registry_exact_readback']=NEW.read_bytes()==data
    checks['old_registry_unchanged']=OLD.read_bytes()==oldraw
    checks['protected_production_unchanged']=all(sha(Path(n).read_bytes())==h for n,h in protected.items())
    report={'schema':'OpenRemaster.TemporaryLaneRebalanceReceipt.v1','status':'PASS' if all(checks.values()) else 'FAIL',
      'scope':'PLANNING_CHANGE_AND_EXISTING_EVIDENCE_READ_ONLY',
      'registry_path':str(NEW),'registry_sha256':sha(data),'previous_registry_sha256':PIN,
      'decision':updated['temporary_focus_decision'],'lane_counts':updated['coverage']['lane_counts'],
      'selected_lane_evidence':observed,'input_sha256':inputs,'checks':checks,
      'checks_pass':sum(checks.values()),'checks_total':len(checks),
      'new_game_execution':0,'new_heavy_jobs':0,'new_game_passes':0,
      'lease_or_queue_mutations':0,'source_or_game_worktree_mutations':0,
      'production_code_or_capability_changes':0,'protected_inputs_sha256':protected,
      'automation_binding':'UPDATE_EXISTING_THREE_PLANNERS_TO_V3_WITHOUT_CHANGING_SCHEDULES',
      'recorded_at_utc':now}
    put(ROOT/'rebalance-receipt.json',pack(report))
    print(json.dumps(report,indent=2,ensure_ascii=True))
    print('RECEIPT_SHA256',sha((ROOT/'rebalance-receipt.json').read_bytes()))
    return 0 if report['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
