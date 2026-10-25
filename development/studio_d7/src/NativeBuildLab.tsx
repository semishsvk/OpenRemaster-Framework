import {useState} from "react";
import type {NativeBuildReport,NativeGateId} from "./native-build";
import {nativeBuildView,simulateNativeBuild} from "./native-build";
import originalNativeBuild from "./data/native-build-readiness.json";
import "./native-build.css";

type Props={
 onHostReplay:()=>void;onCompatibility:()=>void;onTrust:()=>void;
};
const display=(code:string)=>code.replaceAll("_"," ");
const shortened=(code:string)=>code.length>28?code.slice(0,15)+"…"+code.slice(-9):code;
const GATE_DETAILS:Record<NativeGateId,string>={
 T01:"Rust stable x86_64-pc-windows-msvc toolchain — not installed or approved",
 T02:"Pre-existing Microsoft MSVC compiler/linker — genuine local synthetic Win64 build and run",
 T03:"Pre-existing Windows SDK — headers, x64 libraries and vendor-signed signtool",
 T04:"Original already-approved ORION/Studio icon source with explicit provenance",
 T05:"Isolated Tauri 2 Rust executable with no live Host RPC or worker",
 T06:"Genuine native Tauri UI screenshot with visual acceptance, not a web-only render",
 T07:"Complete mandatory versioned Core/ORION/Governor/worker/Asset Labs closure",
 T08:"Publisher-signed one Windows x64 installer with protected identities and rollback",
 T09:"Independent Owner/Witness A, Windows B and native canary C signoff"
};
function Hold({children}:{children:React.ReactNode}){
 return <span className="game-hold">{children}</span>;
}
function unsafeForProductionDisabled(){
 return false;
}
export default function NativeBuildLab({onHostReplay,onCompatibility,onTrust}:Props){
 const view=nativeBuildView(originalNativeBuild);
 const evidence:NativeBuildReport|null=view.data;
 const [selected,setSelected]=useState<NativeGateId>("T02");
 const [filter,setFilter]=useState<"all"|"verified"|"blocked">("all");
 const [scenario,setScenario]=useState<"actual"|"hypothetical">("actual");
 const [section,setSection]=useState<"gates"|"steps">("gates");
 const [downloaded,setDownloaded]=useState(false);
 const gate=evidence?.gates.find(g=>g.id===selected);
 const shown=evidence?.gates.filter(row=>
   filter==="all"||(filter==="verified"?row.readyHistorical:!row.readyHistorical))??[];
 const simulation=evidence?simulateNativeBuild(evidence,scenario):null;
 function downloadTechnicalBrief(){
   if(!evidence)return;
   const lines=[
    "OPENREMASTER STUDIO — UNSIGNED LOCAL TECHNICAL READINESS BRIEF",
    "No signature, independent Owner approval, production action or deployment authority.",
    "Release: "+evidence.release,
    "Historical checkpoint: StudioMSVCNativeSmoke-20261018-r24",
    "Test-only real Windows synthetic executable: "+evidence.progress.syntheticExeSha256,
    "Historical MSVC/SDK source-scoped technical gates: 2 / 9",
    "Actual Tauri executable: NOT BUILT",
    "Approved original icon source: NOT VERIFIED",
    "External Owner A / Windows B / Canary C: NOT APPROVED",
    "Publisher signed installer: NOT BUILT",
    "PRODUCTION: HOLD_NO_AUTO_RETRY",
    "",
    "SOURCE AUTHENTICITY (local SHA is not a vendor or Owner certificate)",
    ...Object.entries(evidence.sourcePins).map(([role,sha])=>role+": "+sha),
    "",
    "REMAINING PREREQUISITES",
    ...evidence.gates.filter(g=>!g.readyHistorical)
      .map(g=>g.id+": "+g.name+" — "+g.reason),
    "",
    "Do not use this document to start K003, a worker, install Rust, create",
    "publisher keys or claim native Tauri UI fidelity or production acceptance."
   ];
   const blob=new Blob([lines.join("\n")+"\n"],{type:"text/plain;charset=utf-8"});
   const url=URL.createObjectURL(blob);
   const anchor=document.createElement("a");
   anchor.href=url;anchor.download="OpenRemaster-UNSIGNED-NativeBuild-UI015.txt";
   anchor.click();URL.revokeObjectURL(url);
   setDownloaded(true);
 }
 return <section className="native-build-page">
   <div className="page-intro">
     <div className="eyebrow">PLATFORM / WINDOWS BUILD TOOLCHAIN · SOURCE-BOUND</div>
     <h1>Native Build Lab<span className="title-dot">.</span></h1>
     <p>Skutočný úspech MSVC/Windows SDK testovacieho programu z r24. Prechod od statického Windows náhľadu k natívnemu Tauri 2 je stále podmienený Rustom, schválenou ikonou, kompatibilitou komponentov, podpisom a nezávislými bránami A/B/C.</p>
   </div>
   <div className="section-banner">
     <Hold>DESKTOP RELEASE NO-GO</Hold>
     <span>MICROSOFT-SIGNED COMPILER ≠ SIGNED OPENREMASTER STUDIO · {view.phase}</span>
     <button className="top-button" onClick={onTrust}>External A/B/C ↗</button>
   </div>
   {!evidence&&<div className="soft-warning">Native build source failed strict local provenance validation. No historical compiler success, binary acceptance or readiness is inferred.</div>}
   {evidence&&<>
     <div className="native-build-metrics">
       <div><small>Historical technical prerequisites</small><strong>2 / 9</strong>
         <span>MSVC compiler + Windows SDK source-proven</span></div>
       <div><small>Real isolated Win64 synthetic tests</small><strong>19 / 19</strong>
         <span>Original r24 run, not rerun by Studio</span></div>
       <div><small>Native Tauri executable</small><strong className="native-build-warning">NO</strong>
         <span>Rust and official icon not accepted</span></div>
       <div><small>Production approvals</small><strong className="native-build-warning">0</strong>
         <span>Owner A · Windows B · Canary C</span></div>
     </div>
     <div className="game-completion-hero native-build-hero">
       <div><div className="hero-eyebrow">REAL MICROSOFT WIN64 TEST / NEVER A STUDIO BUILD</div>
        <h2>The compiler runs.<br/><span>The product isn't signed.</span></h2>
        <p>MSVC {evidence.tooling.msvcVersion} / Windows SDK {evidence.tooling.sdkVersion} successfully produced and ran a synthetic AMD64 program, exit 0. Original branded OpenRemaster Studio executable and signed One Installer were not built.</p>
       </div>
       <div className="game-hero-state"><span>TECHNICAL READINESS</span><b>2 / 9</b><small>PRODUCTION NO-GO</small></div>
     </div>
     <div className="native-build-columns">
       <section className="panel">
         <div className="panel-header"><div><div className="eyebrow">R23 → R24 DETERMINISTIC READINESS</div>
           <h3>Technical gate matrix</h3></div><Hold>7 OPEN</Hold></div>
         <div className="native-build-filters">
           {(["all","verified","blocked"] as const).map(group=><button
             key={group} aria-pressed={filter===group}
             className={filter===group?"active":""} onClick={()=>setFilter(group)}>
             {group==="all"?"All 9":group==="verified"?"Source-proven 2":"Blocked 7"}
           </button>)}
         </div>
         <div className="native-build-gates">{shown.map(item=><button
            key={item.id} aria-pressed={selected===item.id}
            className={"native-build-gate "+(selected===item.id?"selected":"")}
            onClick={()=>setSelected(item.id)}>
           <span className="native-build-index">{item.id}</span>
           <span className="native-build-gate-info"><strong>{item.name}</strong>
             <small>{item.wasReadyInR23?"r23 source already present":item.readyHistorical?"New r24 source verified":"Not accepted or available"}</small></span>
           <span className={"native-build-pill "+(item.readyHistorical?"passed":"blocked")}>
             {item.readyHistorical?"MSVC/SDK PASS":"HOLD"}
           </span>
          </button>)}</div>
       </section>
       <section className="panel">
         <div className="panel-header"><div><div className="eyebrow">SELECTED / ORIGINAL SOURCE CONTRACT</div>
          <h3>{gate?gate.id+" · "+gate.name:"No selected gate"}</h3></div>
          <Hold>NOT PRODUCT ACCEPTED</Hold></div>
         {gate&&<>
           <div className="native-build-details">
             <div><small>Historical r23 (PATH-only)</small><strong>{gate.wasReadyInR23?"READY":"NOT FOUND / BLOCKED"}</strong></div>
             <div><small>Historical r24 (source-verified)</small><strong>{gate.readyHistorical?"TECHNICAL PASS":"NO-GO"}</strong></div>
           </div>
           <div className="detail-section"><label>REQUIRED</label><p>{GATE_DETAILS[gate.id]}</p></div>
           <div className="detail-section"><label>R24 GROUNDING</label><p>{gate.reason}</p></div>
           <div className="detail-section"><label>PRE-DEFINED DEPENDENCY</label><p>{gate.prerequisites}</p></div>
           <div className="soft-warning">The historical technical-pass marker is not a signed component version, installed Native Worker, trusted app binary or external Owner approval.</div>
           <button className="secondary-button" onClick={onCompatibility}>Check mandatory component compatibility →</button>
         </>}
       </section>
     </div>
     <section className="panel">
       <div className="panel-header">
         <div><div className="eyebrow">ACTUAL WINDOWS PROGRAM / BOUNDED EXPLORATORY TEST</div>
         <h3>Binary evidence and source-controlled prerequisites</h3></div>
         <Hold>NO TAURI / NO INSTALLER</Hold>
       </div>
       <div className="native-build-binary">
         <div><small>Generated EXE (synthetic test only)</small><strong>PE32+ · AMD64 · console</strong></div>
         <div><small>Windows loader hardening</small><strong>ASLR · high-entropy · DEP/NX</strong></div>
         <div><small>Original Win64 execution</small><strong>EXIT 0 · 64-bit pointers</strong></div>
         <div><small>External source review</small><strong>UNSIGNED / LOCAL SHA ONLY</strong></div>
       </div>
       <div className="native-build-hash"><span>Test-only executable SHA-256 (not copied to Studio)</span>
         <code>{evidence.progress.syntheticExeSha256}</code></div>
       <div className="native-build-switcher">
         {(["gates","steps"] as const).map(view=><button key={view}
          className={section===view?"active":""} aria-pressed={section===view}
          onClick={()=>setSection(view)}>
          {view==="gates"?"Native prerequisite chain":"Original D01–D07 release plan"}
         </button>)}
       </div>
       {section==="gates"?
        <div className="native-build-chain">{evidence.gates.map(g=><div key={g.id}>
           <span>{g.id}</span><strong>{g.name}</strong>
           <span className={"native-build-pill "+(g.readyHistorical?"passed":"blocked")}>{g.readyHistorical?"TECHNICAL":"HOLD"}</span>
         </div>)}</div>:
         <div className="native-build-chain">{evidence.requiredSteps.map(s=><div key={s.id}>
          <span>{s.id}</span><strong>{s.title}</strong>
          <span className="native-build-pill blocked">{s.sourceStatus.replaceAll("_"," ")}</span>
         </div>)}</div>}
     </section>
     <div className="native-build-columns">
       <section className="panel">
         <div className="panel-header"><div><div className="eyebrow">PROVENANCE OF PREINSTALLED VENDOR TOOLS</div>
          <h3>Microsoft signatures: toolchain only</h3></div><span className="native-build-pill passed">HISTORICAL VALID</span></div>
         <div className="native-build-tooling">{evidence.tooling.historicalSignedMicrosoftTools.map(tool=><div key={tool.role}>
          <strong>{tool.role}</strong><span>Microsoft Authenticode Valid at r24</span>
          <code>{shortened(tool.sha256)}</code>
         </div>)}</div>
         <div className="soft-warning">Microsoft's code signature authenticates the compiler/linker/SDK tools reported in r24. It does NOT sign this UI, the generated synthetic program, the ORION icon, a Studio EXE or the publisher's future installer.</div>
       </section>
       <section className="panel">
         <div className="panel-header"><div><div className="eyebrow">LOCAL HYPOTHETICAL PLANNING</div>
          <h3>No shortcut to deployment</h3></div><Hold>NO-GO</Hold></div>
         <div className="setting-row"><div><strong id="native-build-hypothetical-scenario-label">Imagine approved Rust and original icon available</strong>
           <p>Changes only the hypothetical description. Does not install a toolchain, create a certificate, grant an Owner lease or change source evidence.</p></div>
           <button type="button" role="switch" aria-labelledby="native-build-hypothetical-scenario-label" aria-checked={scenario==="hypothetical"} disabled={unsafeForProductionDisabled()}
             className={"toggle "+(scenario==="hypothetical"?"on":"")}
             onClick={()=>setScenario(s=>s==="actual"?"hypothetical":"actual")}><span/></button>
         </div>
         <div className="native-build-scenario">
           <strong>{simulation?.status}</strong>
           <p>{simulation?.explanation}</p>
           <small>Signed installer: NO · Native Tauri EXE: NO · Dispatch: NO</small>
         </div>
         <button className="secondary-button" onClick={downloadTechnicalBrief}>Download UNSIGNED local technical brief ↓</button>
         {downloaded&&<p className="native-build-footnote">Local text draft generated. No submission, signing or approval performed.</p>}
         <button className="secondary-button" onClick={onHostReplay}>Return to Inspector Host Replay →</button>
       </section>
     </div>
     <section className="panel">
       <div className="panel-header"><div><div className="eyebrow">ORIGINAL SHA SOURCE CHECKPOINTS</div>
        <h3>Immutable research inputs</h3></div><Hold>NOT AN OWNER SIGNATURE</Hold></div>
       <div className="native-build-source-grid">{Object.entries(evidence.sourcePins).map(([role,sha])=><div key={role}>
          <span>{display(role)}</span><code>{sha}</code>
        </div>)}</div>
       <div className="soft-warning">The native r24 executable is a disposable bounded compiler smoke. It is not distributed in the Studio ZIP, and the original K003, game media, workers, signing keys and Windows services are unchanged.</div>
     </section>
   </>}
 </section>;
}
