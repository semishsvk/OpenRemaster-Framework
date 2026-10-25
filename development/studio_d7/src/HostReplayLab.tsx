import { loadStoredJson } from "./stored-json";
import {useRef,useState} from "react";
import rawHost from "./data/host-connector-evidence.json";
import rawDesktop from "./data/desktop-preflight-r21.json";
import {
 createConnectorSession,replayArchivedFixture,
 REQUIRED_METHODS,type ArchivedHostReport,type SessionState
} from "./host-connector";
import {desktopView,DESKTOP_BLOCKERS} from "./desktop-preflight";
import {validatePinnedHostReplay} from "./host-replay-auth";
import "./host-replay.css";

const titles=[
 "Paged list · first checkpoint","Paged list · pinned continuation",
 "Exact checkpoint · source read","Health · read-only status",
 "Wrong snapshot · expected HOLD","Full list · two source records"
];
const reasons=[
 "Frozen first page from the actual historical Windows Job-owned pilot",
 "Same frozen snapshot ID required for page 2 — no fallback",
 "Pinned ID, snapshot correlation and source SHA only",
 "Two historical framework checkpoints, no native game claim",
 "Deliberately wrong if_snapshot — rejects stale continuation",
 "Both historical framework checkpoint rows, not the full global portfolio"
];
const lookup=(x:Record<string,unknown>|undefined,key:string):unknown=>x?x[key]:null;
const textValue=(v:unknown)=>typeof v==="string"?v:"—";
const hash=(s:string)=>s.length>34?s.slice(0,14)+"…"+s.slice(-8):s;
export default function HostReplayLab({onTrust,onInspector,onCompatibility,onNativeBuild}:{
 onTrust:()=>void;onInspector:()=>void;onCompatibility:()=>void;onNativeBuild:()=>void;
}){
 const clock=useRef(0);
 const session=useRef<ReturnType<typeof createConnectorSession>|null>(null);
 if(!session.current)session.current=createConnectorSession({now:()=>clock.current});
 const [raw,setRaw]=useState<unknown>(rawHost);
 const [selected,setSelected]=useState(0);
 const [lastIndex,setLastIndex]=useState<number|null>(null);
 const [observed,setObserved]=useState<SessionState>(()=>session.current!.snapshot());
 const [working,setWorking]=useState(false);
 const [showBlockers,setShowBlockers]=useState(false);
 const sourceValid=validatePinnedHostReplay(raw);
 const data:ArchivedHostReport|null=sourceValid?raw:null;
 const desktop=desktopView(rawDesktop);
 const fixture=data?.responseFixtures[selected];
 const response=observed.archiveResponse?.data;
 const decision=lookup(response,"decision");
 const decisionRecord=decision && typeof decision==="object"&&!Array.isArray(decision)
   ?decision as Record<string,unknown>:undefined;
 const summary=lookup(response,"items");
 const items=Array.isArray(summary)?summary:response?.item?[response.item]:[];
 function select(index:number){
   session.current!.cancel();setObserved(session.current!.snapshot());
   setSelected(index);setLastIndex(null);
 }
 function replay(){
   if(!data || selected<0||selected>=data.responseFixtures.length)return;
   session.current!.cancel();
   const output=replayArchivedFixture(session.current!,data,selected);
   setLastIndex(selected);setObserved(output.state);
 }
 function expire(){
   clock.current+=31_000;
   setObserved(session.current!.snapshot());
 }
 function clear(){
   session.current!.cancel();setObserved(session.current!.snapshot());setLastIndex(null);
 }
 async function reload(){
   setWorking(true);
   clear();setRaw(null);
   try{
     const body:unknown=await loadStoredJson("replay");
     if(!validatePinnedHostReplay(body))throw Error("UNTRUSTED_ARCHIVED_HOST");
     setRaw(body);setSelected(0);
   }catch{
     setRaw(null);setObserved(session.current!.snapshot());
   }finally{
     setWorking(false);
   }
 }
 return <section className="host-replay-page">
  <div className="page-intro">
   <div className="eyebrow">HOST INTEGRATION / SOURCE-BOUND WINDOWS INSPECTOR PROTOCOL</div>
   <h1>Host Replay Lab<span className="title-dot">.</span></h1>
   <p>Historické skutočné odpovede Inspector Hostu z Windows Job-bound pilotu. Môžeš overiť koreláciu request/response, nesprávny snapshot a časovú platnosť bez spúšťania native procesu. Nie je to živé pripojenie ani produkčné rozhodnutie.</p>
  </div>
  <div className="section-banner">
   <span className="game-hold">OFFLINE REPLAY · HOLD</span>
   <span>{sourceValid?"EXACT SOURCE ARCHIVE VERIFIED":"SOURCE REJECTED"} · NO WINDOWS PROCESS · NO ACTIVE OWNER</span>
   <button className="top-button" disabled={working} onClick={reload}>{working?"Checking…":"Reload saved Host evidence"}</button>
  </div>
  {data?<>
   <div className="host-replay-metrics">
    <div><small>Historical OS-bound requests</small><strong>6</strong><span>Actual prior one-shot Inspector pilot</span></div>
    <div><small>Source-only successes</small><strong>5</strong><span>Read-only bounded responses</span></div>
    <div><small>Snapshot reject</small><strong>1</strong><span>Wrong snapshot → fail-closed</span></div>
    <div><small>Live production calls</small><strong className="host-replay-alert">0</strong><span>No current native transport</span></div>
   </div>
   <div className="game-completion-hero host-replay-hero">
    <div><div className="hero-eyebrow">INSPECTOR HOST CONTRACT v1.0.0</div>
     <h2>Prove the request boundary.<br/><span>Do not grant authority.</span></h2>
     <p>Three fixed methods, 8 KiB requests, 128 KiB responses. Local replay uses a synthetic clock to show the 30-second retention limit. It never contacts K003, Windows task services, models or original games.</p>
    </div>
    <div className="game-hero-state"><span>HOST AVAILABILITY</span><b>NOT CONNECTED</b><small>PRODUCTION HOLD</small></div>
   </div>
   <div className="host-replay-columns">
    <section className="panel">
     <div className="panel-header"><div><div className="eyebrow">ARCHIVED / REAL WINDOWS FIXTURES</div><h3>Six original request scenarios</h3></div>
       <span className="game-hold">SOURCE ONLY</span></div>
     <div className="host-fixture-list">{data.responseFixtures.map((entry,i)=>
      <button key={entry.request.id} onClick={()=>select(i)}
       className={"host-fixture "+(selected===i?"selected":"")} aria-pressed={selected===i}>
       <span className="host-fixture-num">{String(i+1).padStart(2,"0")}</span>
       <span className="host-fixture-info"><strong>{titles[i]}</strong><small>{entry.request.method} · {entry.response.ok?"historical success":"historical rejected snapshot"}</small></span>
       <span className={"host-fixture-pill "+(entry.response.ok?"ok":"hold")}>{entry.response.ok?"OK":"HOLD"}</span>
      </button>)}</div>
     <div className="host-source-text">{reasons[selected]}</div>
     <div className="host-action-strip">
       <button className="secondary-button" onClick={replay}>Replay selected archive</button>
       <button className="secondary-button" onClick={clear}>Clear observation</button>
       <button className="secondary-button" onClick={expire}>Advance virtual clock +31 s</button>
     </div>
     <div className="soft-warning">Buttons modify only the isolated React replay state. A valid archived response can be displayed, never submitted as a current Owner decision or native execution receipt.</div>
    </section>
    <section className="panel">
     <div className="panel-header"><div><div className="eyebrow">SESSION CORRELATION / SYNTHETIC CLOCK</div><h3>Replay result</h3></div>
       <span className="game-hold">PRODUCTION HOLD</span></div>
     <div className="host-session-state">
       <small>CURRENT LOCAL SESSION</small>
       <strong>{observed.phase==="ARCHIVED_RESPONSE"?"ARCHIVED RESPONSE":
         observed.phase==="HOLD"?"HOLD — NO CURRENT RESPONSE":observed.phase}</strong>
       <code>{observed.code}</code>
     </div>
     <div className="host-session-facts">
       <div><span>Selected original fixture</span><strong>{selected+1} / 6</strong></div>
       <div><span>Last locally replayed case</span><strong>{lastIndex===null?"NONE":lastIndex+1}</strong></div>
       <div><span>Virtual time</span><strong>{clock.current/1000} s</strong></div>
       <div><span>Read-only archived cards</span><strong>{items.length}</strong></div>
     </div>
     <div className="settings-line"><b>Proposed request method</b><strong>{fixture?.request.method}</strong></div>
     <div className="settings-line"><b>Fixed source snapshot</b><code>{hash(data.archivedSnapshot)}</code></div>
     <div className="settings-line"><b>Current production Host available</b><span className="game-hold">NO</span></div>
     <div className="settings-line"><b>Owner selected in archived data</b><span className="game-hold">NONE</span></div>
     {lastIndex!==null && data.responseFixtures[lastIndex].response.ok===false && observed.code==="ARCHIVED_SNAPSHOT_REJECTED"&&
      <div className="host-rejection">The frozen Host returned SNAPSHOT_CHANGED · HOLD_NO_FALLBACK. No automatic retry or stale card retention.</div>}
     {decisionRecord && <div className="host-decision">
      <small>ARCHIVED SOURCE-ONLY OWNER DECISION</small>
      <strong>{textValue(decisionRecord.status).replaceAll("_"," ")}</strong>
      <p>Production admission: {textValue(decisionRecord.production_admission)}; original source freshness is only pinned SHA, not live.</p>
     </div>}
     {items.length>0&&<div className="host-observed-list">
       {items.map((rec,i)=>{const x=rec as Record<string,unknown>;return <div key={i}>
        <strong>{textValue(x.workstream)}</strong>
        <small>{textValue(x.source_schema)}</small>
        <code>{hash(textValue(x.source_sha256))}</code>
       </div>;})}
      </div>}
     <p className="host-replay-hint">Observation retention: {data.hostContract.clientFreshnessLimitMs/1000}s virtual. Worker, model, game launch, native dispatch and writes remain prohibited even if the archived response passes validation.</p>
    </section>
   </div>
   <section className="panel">
    <div className="panel-header"><div><div className="eyebrow">FIXED METHOD WHITELIST</div><h3>Only three safe Inspector methods</h3></div>
     <span className="game-hold">NO NATIVE PROCESS</span></div>
    <div className="host-contract-grid">{REQUIRED_METHODS.map(m=><div key={m}>
      <strong>{m}</strong><small>JSON one-shot · fixed archive only</small><span>NO WRITE / NO DISPATCH</span>
    </div>)}</div>
    <div className="host-source-hashes">
      <div><small>Actual pilot source checkpoint SHA-256</small><code>{data.sourcePins.hostCheckpoint}</code></div>
      <div><small>Inspector API contract SHA-256</small><code>{data.sourcePins.hostApiContract}</code></div>
      <div><small>Historical Windows verification SHA-256</small><code>{data.sourcePins.windowsVerification}</code></div>
      <div><small>Studio r11 source-parent SHA-256</small><code>{data.sourcePins.parentR11}</code></div>
    </div>
   </section>
  </>:<div className="soft-warning">The archived Windows Host source is unavailable or failed strict validation. All prior observations have been cleared. No current production Host request can be made.</div>}
  <section className="panel">
   <div className="panel-header"><div><div className="eyebrow">DESKTOP PREFLIGHT · WINDOWS R21 HISTORICAL OBSERVATION</div>
    <h3>Native desktop release prerequisites</h3></div><span className="game-hold">NO-GO</span></div>
   {desktop.data?<><div className="host-desktop-metrics">
    <div><strong>5</strong><span>Non-release source prerequisites present</span></div>
    <div><strong>{desktop.missing}</strong><span>Production desktop blockers</span></div>
    <div><strong>0</strong><span>Verified Rust / signing / installer tools</span></div>
    <div><strong>NO</strong><span>Signed Studio setup executable</span></div>
   </div>
    <div className="host-desktop-actions">
     <button className="secondary-button" onClick={()=>setShowBlockers(x=>!x)}>
      {showBlockers?"Hide all missing prerequisites":"Show all 15 missing prerequisites"}
     </button>
     <button className="secondary-button" onClick={onCompatibility}>Open Compatibility Lab →</button>
     <button className="secondary-button" onClick={onNativeBuild}>Open Native Build Lab →</button>
     <button className="secondary-button" onClick={onTrust}>Open external Owner Gate A →</button>
     <button className="secondary-button" onClick={onInspector}>View historical checkpoint Inspector →</button>
    </div>
    {showBlockers&&<div className="host-desktop-blockers">{DESKTOP_BLOCKERS.map((key,i)=><div key={key}>
     <span>{String(i+1).padStart(2,"0")}</span><strong>{key.replaceAll("_"," ")}</strong><span className="game-hold">MISSING</span>
    </div>)}</div>}
    <div className="soft-warning">r21 is a previous HomePC observation, not a current machine inventory. Original approved icon, genuine Tauri 2 binary, production Windows signing identity, independent A→B→C and clean-machine runtime acceptance remain missing. No installer action is available here.</div>
   </>:<div className="soft-warning">Desktop preflight source was rejected. No native executable or installer may be assumed ready.</div>}
  </section>
 </section>;
}
