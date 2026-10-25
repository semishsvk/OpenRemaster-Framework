import type { BoundedView, BoundedPlanEvidence } from "./bounded-plan";

const CASES: {key: keyof BoundedPlanEvidence["scenarios"]; label: string; note: string}[]=[
  {key:"initial",label:"Baseline",note:"Only T1 is exposed"},
  {key:"afterPass",label:"After synthetic T1 PASS",note:"T2 becomes the single proposal"},
  {key:"gameGpu",label:"GAME / GPU",note:"Heavy local model held"},
  {key:"gameOffGpu",label:"Game auto-mode OFF",note:"Shadow-only GPU candidate"},
  {key:"completed",label:"All tasks terminal",note:"No new proposal"},
  {key:"unknownPrior",label:"Prior outcome UNKNOWN",note:"Reconciliation required"},
  {key:"unchanged",label:"Same evidence recheck",note:"Identical data is still HOLD"},
  {key:"changed",label:"Changed evidence recheck",note:"Old proposal becomes stale"},
];
const short=(s:string|null|undefined)=>s ? s.slice(0,13)+"…" : "—";
export default function NextTaskLab({view,onReload,busy,onCrossplane}:{
  view:BoundedView;onReload:()=>void;busy:boolean;onCrossplane:()=>void;
}){
  const data=view.data;
  const baseline=data?.scenarios.initial;
  const progressed=data?.scenarios.afterPass;
  return <section className="tasklab">
    <div className="page-intro">
      <div className="eyebrow">PLATFORM / ORION × K003 × GOVERNOR</div>
      <h1>Next Task Lab<span className="title-dot">.</span></h1>
      <p>Bounded WorkPackage plánovanie. Toto sú historické syntetické vstupy z izolovaného testu — žiadne aktuálne zadania, aktuálny Governor stav ani živé oprávnenie Owner/Witness.</p>
    </div>
    <div className="section-banner">
      <span className="tasklab-pill">ARCHIVED / NO EXECUTION</span>
      <span>K003 remains sole scheduler · {view.code}</span>
      <button className="top-button" type="button" disabled={busy} onClick={onReload}>
        {busy?"Reading…":"Reload saved evidence"}
      </button>
    </div>
    <div className="tasklab-metrics">
      <div><span>Published model plans</span><strong>{baseline?.published??0} / 5</strong><small>One historical proposal maximum</small></div>
      <div><span>Suppressed previews</span><strong>{baseline?.suppressed??0}</strong><small>Unready proposals withheld</small></div>
      <div><span>Prior software tests</span><strong>{data?.historicalTests.total??0}</strong><small>Archived results, not rerun by this screen</small></div>
      <div><span>Current authorized jobs</span><strong className="red">0</strong><small>Production HOLD_NO_AUTO_RETRY</small></div>
    </div>
    {view.phase==="HOLD" && <div className="soft-warning">
      The archived bounded-plan record is absent or untrusted. No previous candidate is displayed.
      Reloading cannot call K003, a model or a worker.
    </div>}
    {data && <>
      <div className="tasklab-columns">
        <section className="panel">
          <div className="panel-header"><div><div className="eyebrow">HISTORICAL SHADOW PLAN</div><h3>Only the next eligible task</h3></div><span className="tasklab-pill">ONE WRITER</span></div>
          <div className="tasklab-selected">
            <span>01 / Initial snapshot</span><strong>{baseline?.taskId} · {data.tasks[0].goal}</strong>
            <p>ORION internally evaluated five local test profiles. K003 only proposed T1; the remaining four plans were not published.</p>
            <code>{short(baseline?.proposalSha256)}</code>
          </div>
          <div className="tasklab-arrow">↓ <small>Only after a synthetic T1 PASS</small></div>
          <div className="tasklab-selected secondary">
            <span>02 / Historical progress fixture</span><strong>{progressed?.taskId} · {data.tasks[1].goal}</strong>
            <p>A different proposal checksum is required. This is not a replay of the initial T1 operation.</p>
            <code>{short(progressed?.proposalSha256)}</code>
          </div>
          <div className="soft-warning">No job can be started from this view. The displayed worker capacity and PASS statuses were fixtures, not live K003/Owner receipts.</div>
        </section>
        <section className="panel">
          <div className="panel-header"><div><div className="eyebrow">DEPENDENCY CHAIN</div><h3>Five original WorkPackage tasks</h3></div><span className="tasklab-pill">SOURCE SHA</span></div>
          <div className="tasklab-tasks">
            {data.tasks.map((item,i)=><div className="tasklab-task" key={item.id}>
              <span className="tasklab-task-index">{String(i+1).padStart(2,"0")}</span>
              <div><strong>{item.id} — {item.goal}</strong><small>{item.dependsOn.length?"Requires "+item.dependsOn.join(", "):"No prerequisites"} · no execution</small><code>{item.operationId}</code></div>
              <span className="tasklab-smallhold">HOLD</span>
            </div>)}
          </div>
        </section>
      </div>
      <section className="panel">
        <div className="panel-header"><div><div className="eyebrow">FAIL-CLOSED SCENARIOS</div><h3>Changing evidence never grants authority</h3></div><span className="tasklab-pill">8 TEST CASES</span></div>
        <div className="tasklab-cases">
          {CASES.map(({key,label,note})=>{
            const scene=data.scenarios[key];
            return <div className="tasklab-case" key={key}>
              <div><strong>{label}</strong><small>{note}</small></div>
              <code>{scene.status}</code>
              <span className="tasklab-smallhold">HOLD</span>
            </div>;
          })}
        </div>
        <div className="tasklab-rechecks">
          <div><strong>Identical recheck</strong><span>{data.scenarios.unchanged.status}</span></div>
          <div><strong>Changed recheck</strong><span>{data.scenarios.changed.status}</span></div>
        </div>
      </section>
      <section className="panel">
        <div className="panel-header"><div><div className="eyebrow">IMMUTABLE SOURCE LINEAGE</div><h3>Archive identity</h3></div><span className="tasklab-pill">UNSIGNED SHA-256</span></div>
        <div className="tasklab-provenance">
          <div><small>Lifecycle r2 sealed ZIP</small><code>{data.zipSha256}</code></div>
          <div><small>Canonical K003 source</small><code>{data.originalK003Sha256}</code></div>
          {Object.entries(data.sourceMemberHashes).map(([name,value])=>
            <div key={name}><small>{name}</small><code>{value}</code></div>)}
        </div>
        <p className="tasklab-caption">Source checkpoint: {data.checkpointRecordedUtc}. These bytes were verified from a sealed local ZIP, but they are not an independent publisher, Owner or Witness signature.</p>
        <button type="button" className="secondary-button" onClick={onCrossplane}>Review Framework ↔ ORION trust gates →</button>
      </section>
    </>}
  </section>;
}
