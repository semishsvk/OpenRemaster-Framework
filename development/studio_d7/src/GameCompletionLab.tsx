import {useState} from "react";
import type {CompletionBoard,CompletionGameId,CompletionTask} from "./game-completion";
import {gameTaskFilter,ORIGINAL_FIDELITY_GATES} from "./game-completion";

const names:Record<CompletionGameId,string>={
 OpenMDK1:"MDK · first authentic playable",
 OpenStonekeep:"Stonekeep · native compositor"
};
const diagnostics:Record<CompletionGameId,string>={
 OpenMDK1:"Original XPGUN provider, opcode and callback provenance",
 OpenStonekeep:"Original framebuffer index vs palette RGB evidence"
};
const pretty=(s:string)=>s.replaceAll("_"," ");
const fmt=(n:number)=>n.toLocaleString("sk-SK");
function Hold({children,className=""}:{children:React.ReactNode;className?:string}){
 return <span className={"game-hold "+className}>{children}</span>;
}
export default function GameCompletionLab({data,onReload,busy,onArchitecture,onFidelity}:{
 data:CompletionBoard|null;busy:boolean;onReload:()=>void;
 onArchitecture:()=>void;onFidelity:()=>void;
}){
 const [gameId,setGameId]=useState<CompletionGameId>(()=>
   new URLSearchParams(window.location.search).get("game")==="OpenStonekeep"?"OpenStonekeep":"OpenMDK1");
 const [priority,setPriority]=useState<"all"|"P0"|"P1">("all");
 const [taskId,setTaskId]=useState<string>("MDK56_XPGUN_PROVIDER");
 const game=data?.games.find(p=>p.id===gameId);
 const row=game?.taskGraph.find(t=>t.id===taskId)??game?.taskGraph[0];
 const shown=game?gameTaskFilter(game,priority):[];
 const isStone=gameId==="OpenStonekeep";
 const mdk=game && !isStone?game.diagnostics:null;
 const stone=game && isStone?game.diagnostics:null;
 const regions=stone?.regions as Record<string,number>|undefined;
 function selectGame(id:CompletionGameId){
   setGameId(id);
   setPriority("all");
   setTaskId(id==="OpenMDK1"?"MDK56_XPGUN_PROVIDER":"STONE_K307_COMPOSITOR");
 }
 return <section className="game-completion-page">
   <div className="page-intro">
     <div className="eyebrow">GAME-DRIVEN COMPLETION / REAL SOURCE CHECKPOINTS</div>
     <h1>Game Completion<span className="title-dot">.</span></h1>
     <p>Zdrojovo podložené blokátory z pôvodných OpenMDK1 C285 a OpenStonekeep K306. Každá hra má vlastnú postupnosť práce. Editorové skóre neurčuje percento hotovej hry ani pravdepodobnosť úspechu.</p>
   </div>
   <div className="section-banner">
     <Hold>GAMEPLAY HOLD</Hold>
     <span>HISTORICAL REAL CHECKPOINTS · NO EXECUTION · NO CROSS-GAME RANKING</span>
     <button className="top-button" disabled={busy} onClick={onReload}>{busy?"Checking…":"Reload saved evidence"}</button>
   </div>
   {!data && <div className="soft-warning">Source-bound original game completion evidence is unavailable or rejected. No task can be selected for execution, and previous data is cleared on a failed reload.</div>}
   {data && <>
     <div className="game-metrics">
       <div><small>Games with source evidence</small><strong>2</strong><span>Never ranked across games</span></div>
       <div><small>Scoped blocker tasks</small><strong>9</strong><span>4 MDK + 5 Stonekeep</span></div>
       <div><small>Original/candidate trace pairs</small><strong>0</strong><span>No fidelity oracle admission</span></div>
       <div><small>Verified playable stages</small><strong className="game-red">0</strong><span>Production HOLD_NO_AUTO_RETRY</span></div>
     </div>
     <div className="game-project-cards">
       {data.games.map(project=><button key={project.id}
         className={"game-project-tab "+(gameId===project.id?"selected":"")}
         onClick={()=>selectGame(project.id)} aria-pressed={gameId===project.id}>
         <div className="game-project-kicker"><span>{project.id}</span><Hold>HOLD</Hold></div>
         <strong>{names[project.id]}</strong>
         <small>Checkpoint {project.sourceCheckpoint} · {project.taskGraph.length} bounded blockers</small>
         <div className="game-project-footer"><span>NEXT SOURCE BARRIER</span><code>{project.nextBlocker}</code></div>
       </button>)}
     </div>
     {game && <>
       <div className={"game-completion-hero "+(isStone?"stone":"mdk")}>
         <div><div className="hero-eyebrow">{game.id} / ORIGINAL GAME EVIDENCE</div>
           <h2>{isStone?"Original compositor.":"XPGUN source provider."}<br/><span>Next blocker still holds.</span></h2>
           <p>{game.firstAction}</p>
         </div>
         <div className="game-hero-state"><span>CURRENT STAGE</span><b>NOT ACCEPTED</b><small>{game.sourceCheckpoint}</small></div>
       </div>
       <div className="game-content-columns">
         <section className="panel">
           <div className="panel-header"><div><div className="eyebrow">BOUNDED SOURCE TASK GRAPH</div><h3>Blockers and dependencies</h3></div><Hold>NO DISPATCH</Hold></div>
           <div className="game-filter-tabs">
             {(["all","P0","P1"] as const).map(filter=><button
               className={priority===filter?"selected":""} key={filter}
               aria-pressed={priority===filter} onClick={()=>setPriority(filter)}>
               {filter==="all"?"All tasks":filter+" · "+game.taskGraph.filter(t=>t.priority===filter).length}
             </button>)}
           </div>
           <div className="game-task-list">{shown.map((task:CompletionTask)=>
             <button key={task.id} onClick={()=>setTaskId(task.id)}
               className={"game-task "+(row?.id===task.id?"selected":"")}>
               <span className="game-task-number">{String(game.taskGraph.indexOf(task)+1).padStart(2,"0")}</span>
               <div><strong>{pretty(task.id)}</strong>
                 <small>{task.priority} · {pretty(task.state)} · {task.unmetDependencies.length} dependencies</small>
               </div>
               <Hold>{task.priority}</Hold>
             </button>)}</div>
           {shown.length===0&&<p className="soft-warning">No blocker matches the current priority filter.</p>}
         </section>
         <section className="panel">
           <div className="panel-header"><div><div className="eyebrow">SELECTED / NO AUTHORITY</div><h3>{row?.id??"No selected blocker"}</h3></div><Hold>HOLD</Hold></div>
           {row&&<>
             <div className="game-task-metrics">
               <div><span>Source priority</span><strong>{row.priority}</strong></div>
               <div><span>Editorial impact (ordinal only)</span><strong>{row.editorialImpactScore}</strong></div>
               <div><span>Accepted fidelity stage</span><strong>NONE</strong></div>
             </div>
             <div className="detail-section"><label>SOURCE STAGE INTENT (NOT ACCEPTED)</label>
               <code>{row.stage}</code></div>
             <div className="detail-section"><label>DEPENDENCIES NOT YET ACCEPTED</label>
               {row.unmetDependencies.length===0
                 ?<p>No task prerequisites in this historical graph. Execution and Owner admission still HOLD.</p>
                 :<div className="game-dependency-list">{row.unmetDependencies.map(dep=>
                   <button key={dep} onClick={()=>{setPriority("all");setTaskId(dep);}}>
                     <code>{dep}</code><Hold>UNMET</Hold>
                   </button>)}</div>}
             </div>
             <div className="detail-section"><label>FROZEN SOURCE SHA-256</label>
               <code>{row.evidenceSha256}</code></div>
             <div className="soft-warning">Local prioritization is a source review aid only. No model invocation, Native Worker start, K003 job, scheduler transition or game fidelity claim is permitted.</div>
           </>}
         </section>
       </div>
       <div className="game-content-columns">
         <section className="panel">
           <div className="panel-header"><div><div className="eyebrow">ACTUAL CHECKPOINT OBSERVATION</div><h3>{diagnostics[game.id]}</h3></div><Hold>TECHNICAL ≠ FIDELITY</Hold></div>
           {mdk&&<>
             <div className="game-facts">
               <div><span>Original opcode</span><strong>0x56 / {String(mdk.opcodeDecimal)}</strong></div>
               <div><span>Original source PC</span><strong>{fmt(Number(mdk.pc))}</strong></div>
               <div><span>Source model</span><strong>{String(mdk.model)}</strong></div>
               <div><span>Scoped source operations</span><strong>{String(mdk.sourceOperationsVerified)}</strong></div>
             </div>
             <div className="settings-line"><b>XCORDOOR source mechanism</b><span className="game-source-pass">PASS · SOURCE ONLY</span></div>
             <div className="settings-line"><b>Original HMO3 event</b><Hold>NOT VERIFIED</Hold></div>
             <div className="settings-line"><b>First playable</b><Hold>NOT ATTESTED</Hold></div>
             <div className="soft-warning">Opcode 0x56 / PC 43085 and XPGUN are source-evidence observations. Original provider/callback and native animation, collision/audio and real gameplay remain to be verified.</div>
           </>}
           {stone&&regions&&<>
             <div className="game-facts">
               <div><span>Index pixels with mismatch</span><strong>{fmt(Number(stone.mismatchedIndexPixels))}</strong></div>
               <div><span>Original frame pixels</span><strong>{fmt(Number(stone.framePixels))}</strong></div>
               <div><span>Palette RAM RGB correlated</span><strong>{fmt(Number(stone.sourcePaletteRgbPixelsCorrelated))}</strong></div>
               <div><span>Distinct used palette indices</span><strong>{String(stone.usedPaletteIndicesProven)}</strong></div>
             </div>
             <div className="game-pixel-legend"><span>Mismatch regions within 5 748 index pixels</span><small>Counts, not game completion</small></div>
             <div className="game-pixel-bar">{(["door","HUD","rightWall","other"] as const).map((label,i)=>
               <div key={label} className={"game-pixel-seg part-"+i} title={label+": "+regions[label]}
                style={{flexGrow:regions[label]}}/>)}</div>
             <div className="game-pixel-lines">{(["door","HUD","rightWall","other"] as const).map((label,i)=>
               <div key={label}><span className={"game-pixel-swatch part-"+i}/><strong>{label}</strong><code>{fmt(regions[label])} px</code></div>)}</div>
             <div className="settings-line"><b>Original DAC timing</b><Hold>NOT VERIFIED</Hold></div>
             <div className="soft-warning">64 000/64 000 palette RGB source correlation is distinct from index framebuffer accuracy. The 5 748 index mismatches are not repaired. No percentage here represents game completion or accepted fidelity.</div>
           </>}
         </section>
         <section className="panel">
           <div className="panel-header"><div><div className="eyebrow">GAME-SPECIFIC ACCEPTANCE GATE</div><h3>Evidence still required</h3></div><Hold>NEEDS ORACLE</Hold></div>
           <div className="game-acceptance">{game.acceptance.map((step,i)=>
             <div key={step}><span>{String(i+1).padStart(2,"0")}</span>
               <p>{step}</p><Hold>OPEN</Hold></div>)}</div>
           <div className="soft-warning">Original media remain read-only. Independent aligned gameplay replay, edition fingerprint, effective Owner/GUI lease and the Governor's GAME/LIGHT safety gates precede any native execution.</div>
         </section>
       </div>
     </>}
     <section className="panel">
       <div className="panel-header"><div><div className="eyebrow">FIRST-DIVERGENCE / SOURCE PINS</div>
         <h3>No aligned original-candidate trace pair</h3></div><Hold>0 ORIGINAL PAIRS</Hold></div>
       <div className="game-fidelity-checks">{ORIGINAL_FIDELITY_GATES.map((gate,i)=>
         <div key={gate}><span>{String(i+1).padStart(2,"0")}</span><strong>{gate}</strong><Hold>NOT ACCEPTED</Hold></div>)}</div>
       <div className="game-summary-footer"><p>Historical source validations: {data.sourceSoftwareTests.originalArchitectureR1} Architecture +
         {" "+data.sourceSoftwareTests.gameBridgeR1} Game Evidence = {data.sourceSoftwareTests.totalHistorical} tests.
         None is a new authentic runtime test in this Studio screen.</p>
         <button className="secondary-button" onClick={onArchitecture}>Open Architecture & Completion →</button>
         <button className="secondary-button" onClick={onFidelity}>Review Fidelity Gates →</button>
       </div>
       <div className="game-provenance">
         <div><small>Game evidence r1 sealed ZIP</small><code>{data.sourcePins.gameBridgeSealedR1}</code></div>
         <div><small>Original K003 scheduler source</small><code>{data.sourcePins.originalK003}</code></div>
         <div><small>Source review checkpoint</small><code>{data.sourcePins.sourceCheckpoint}</code></div>
         <div><small>Recorded historical evidence</small><code>{data.sourceCheckpointUtc}</code></div>
       </div>
       <p className="game-no-trust">Local SHA-256 proves file consistency only. This display cannot accept Owner/Witness signatures, submit an approval, create a native process, or establish game fidelity.</p>
     </section>
   </>}
 </section>;
}
