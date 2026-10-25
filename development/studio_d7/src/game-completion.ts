/** UI-013 historical source-bound game blocker graph; NO gameplay run or job dispatch.
 * The two projects are never ranked against each other. Editorial numbers
 * cannot represent completion percentages, success probabilities or fidelity.
 */
export type CompletionGameId="OpenMDK1"|"OpenStonekeep";
export type CompletionTask={
 id:string;priority:"P0"|"P1";
 stage:"PLAYABLE"|"REPLAY_VERIFIED"|"FIDELITY_VERIFIED"|"RUNTIME_BOUND";
 state:"EXECUTION_ADMISSION_HOLD"|"DEPENDENCY_HOLD";
 unmetDependencies:string[];
 editorialImpactScore:number;editorialHeuristic:number;evidenceSha256:string;
 modelAllowed:false;workerAllowed:false;
};
export type GameEntry={
 id:CompletionGameId;sourceCheckpoint:string;nextBlocker:string;
 acceptedStage:"NONE_INDEPENDENTLY_ATTESTED";sourceRoles:string[];
 sourceRolePins:Record<string,string>;
 firstAction:string;acceptance:string[];
 taskGraph:CompletionTask[];
 diagnostics:Record<string,unknown>;
 firstPlayableVerified:false;fidelityVerified:false;independentOwnerAdmitted:false;mayDispatch:false;
};
export type CompletionBoard={
 schema:"OpenRemaster.StudioGameCompletionReadiness.v1";
 release:"ORF-STUDIO-UI-20261018-r12";generatedUtc:string;
 sourceClass:"HISTORICAL_REAL_GAME_CHECKPOINT_TRIAGE_NOT_REAL_RUNTIME";
 status:"TWO_GAMES_SOURCE_TRIAGE_VALIDATED__GAMEPLAY_FIDELITY_HOLD";
 sourcePins:Record<string,string>;
 gameSourceSha:Record<string,string>;
 sourceCheckpointUtc:string;
 sourceSoftwareTests:{originalArchitectureR1:30;gameBridgeR1:46;totalHistorical:76};
 games:GameEntry[];
 firstDivergence:{
  status:"BLOCKED_NO_ALIGNED_GAME_TRACE_PAIR";
  validEventPairs:0;canCallOracle:false;required:string[];
 };
 policy:{
  sameAssistantSourceIntegrityNotExternalSignature:true;
  editorialImpactScoresNotPercentages:true;noCrossGameRanking:true;
  originalGameCorporaNotAccessedHere:true;originalGameRuntimeCaptureNotProduced:true;
  independentOwnerWitnessAccepted:false;currentK003GUILeaseObtained:false;
  modelInvocation:false;workerStart:false;gameDispatch:false;
  autoRetry:false;productionAdmission:"HOLD_NO_AUTO_RETRY";
  maxGlobalHeavySlots:3;singleWriter:true;
 };
};
export const COMPLETION_GAMES=["OpenMDK1","OpenStonekeep"] as const;
export const ORIGINAL_FIDELITY_GATES=[
 "Original source and edition identity",
 "Aligned original and candidate event streams",
 "Same scenario, inputs, tick and capture",
 "Independent Owner / Witness signature",
 "Independently accepted First Divergence"
] as const;
const sourcePins={
 studioParentR11:"8771434f02188076dd30e6638a2bb436e592f3b9a72224170d1c5e2589608417",
 gameBridgeSealedR1:"a930d6b9247683852edbb8188545a0315b2106ef9bd9088ea9ce0cc3b8a16a0e",
 originalK003:"644f9ef4d001a56ee9738d91ac558c5fed32967a17819245a3174b0815fe1d7a",
 sourceCheckpoint:"31c8147c482be3df0f78214a16732c6755375daaff9b345adfa7521ab0b674c1",
 sourcePins:"6475a0032be90297cb343442847a93425918d2f0c2046a262ef054a4b39dab6e",
 gameCompletionReview:"67f3c700fa48a376afb2238bcdfcffe71834ec26063e7516f1bc1a2435548b10",
 selectedNextTasks:"38e4ab24efc7a6ce73f62f9dc7f00c7d802f72ecb6adce0caa210db61fb4d628",
 firstDivergenceGate:"7a8692d743d926e6e99f19bc6d5aeca23464d996d96e8ea0941a7099353fc3ff"
};
const roles={
 mdk_checkpoint:"78c0587d9e37d371cf0f4d4010eaa0e8f38468f52d8be8e04a91181d2aa81839",
 mdk_source56:"677ff401ba133d170e1388b2164152be08fca6950027be9bdbced19ea6e45a51",
 mdk_native_admission:"1fe7ab2fa3267793d5f0ec0ba7fa0a40c9f2c215acaef8a441bc3cbc32ff93b8",
 stone_checkpoint:"2898143df6a5bd1652e83465ba6804bb22e3ead9fbebe59aaa17a8e3598c24ce",
 stone_palette:"6203e6837cc73017f33586fd4086ac24caf5912b6c14c08b15429544919db851"
};
const plain=(x:unknown):x is Record<string,unknown>=>x!==null&&typeof x==="object"&&!Array.isArray(x);
const exact=(v:Record<string,unknown>,e:Record<string,unknown>)=>
 Object.keys(v).sort().join("|")===Object.keys(e).sort().join("|") &&
 Object.entries(e).every(([k,val])=>v[k]===val);
const definitions={
 OpenMDK1:{
   baseline:"C285",next:"MDK56_XPGUN_PROVIDER",roles:["mdk_checkpoint","mdk_source56","mdk_native_admission"],
   ids:["MDK56_XPGUN_PROVIDER","MDK_DOOR_RUNTIME","MDK_REPLAY","MDK_NATIVE_EVENT"],
   priorities:["P0","P0","P1","P0"],
   stages:["PLAYABLE","PLAYABLE","FIDELITY_VERIFIED","REPLAY_VERIFIED"],
   states:["EXECUTION_ADMISSION_HOLD","DEPENDENCY_HOLD","DEPENDENCY_HOLD","DEPENDENCY_HOLD"],
   scores:[7,5,4,3],heuristics:[8,4,3,5],
   deps:[[],["MDK56_XPGUN_PROVIDER"],["MDK_NATIVE_EVENT"],
      ["MDK56_XPGUN_PROVIDER","MDK_DOOR_RUNTIME"]],
   evidence:["c4a1f1efef30f75224b78b4bbec4d500d061df3e6dbc68f0477aa3756e57fce4",
     "7feddafb4c071b80df6acb3c342c50bf296cac8a2b66202d4f6d129a08f93287",
     "0111baf12ae8baad9dad7444a235b22f9c58879d985ad851d54c37784b3dc1a3",
     "f4a54afc787c31847560fb2ad03d6a0570470fe655c60922beb6322866085da3"]
 },
 OpenStonekeep:{
   baseline:"STONE-K306-VIEW011",next:"STONE_K307_COMPOSITOR",
   roles:["stone_checkpoint","stone_palette"],
   ids:["STONE_K307_COMPOSITOR","STONE_DAC_TIMING","STONE_FIDELITY",
     "STONE_GAMEPLAY_REPLAY","STONE_HUD_DOOR"],
   priorities:["P0","P1","P1","P0","P0"],
   stages:["PLAYABLE","RUNTIME_BOUND","FIDELITY_VERIFIED","REPLAY_VERIFIED","PLAYABLE"],
   states:["EXECUTION_ADMISSION_HOLD","EXECUTION_ADMISSION_HOLD","DEPENDENCY_HOLD","DEPENDENCY_HOLD","DEPENDENCY_HOLD"],
   scores:[6,4,3,3,3],heuristics:[8,6,3,5,4],
   deps:[[],[],["STONE_GAMEPLAY_REPLAY"],["STONE_HUD_DOOR","STONE_DAC_TIMING"],["STONE_K307_COMPOSITOR"]],
   evidence:["1edc69a7a610d3c78eac8d876ed7fe654da9dbb16538bd6120f4a43118f50678",
     "e12b03343130557a509593a0c8fa9812680813429d2783061eb8da1080fae4ca",
     "e12b03343130557a509593a0c8fa9812680813429d2783061eb8da1080fae4ca",
     "1edc69a7a610d3c78eac8d876ed7fe654da9dbb16538bd6120f4a43118f50678",
     "1edc69a7a610d3c78eac8d876ed7fe654da9dbb16538bd6120f4a43118f50678"]
 }
} as const;
function taskValid(x:unknown,game:CompletionGameId,i:number):boolean{
 const d=definitions[game];
 if(!plain(x) || !Array.isArray(x.unmetDependencies) ||
    x.unmetDependencies.join("|")!==d.deps[i].join("|") ||
    x.modelAllowed!==false || x.workerAllowed!==false)return false;
 const {unmetDependencies,...other}=x;
 return exact(other,{
   id:d.ids[i],priority:d.priorities[i],stage:d.stages[i],state:d.states[i],
   editorialImpactScore:d.scores[i],editorialHeuristic:d.heuristics[i],
   evidenceSha256:d.evidence[i],modelAllowed:false,workerAllowed:false
 });
}
function gameValid(x:unknown,i:number):x is GameEntry{
 const id=COMPLETION_GAMES[i];
 if(!plain(x))return false;
 const def=definitions[id];
 if(x.id!==id || x.sourceCheckpoint!==def.baseline ||
    x.nextBlocker!==def.next || x.acceptedStage!=="NONE_INDEPENDENTLY_ATTESTED" ||
    x.firstPlayableVerified!==false || x.fidelityVerified!==false ||
    x.independentOwnerAdmitted!==false || x.mayDispatch!==false ||
    !Array.isArray(x.sourceRoles) || x.sourceRoles.join("|")!==def.roles.join("|") ||
    !plain(x.sourceRolePins) ||
    !exact(x.sourceRolePins,Object.fromEntries(def.roles.map(k=>[k,roles[k as keyof typeof roles]]))) ||
    !Array.isArray(x.taskGraph) || x.taskGraph.length!==def.ids.length ||
    !x.taskGraph.every((task:unknown,j:number)=>taskValid(task,id,j)) ||
    typeof x.firstAction!=="string" || x.firstAction.length<24 || x.firstAction.length>400 ||
    !Array.isArray(x.acceptance) || x.acceptance.length!==(i===0?4:5) ||
    !x.acceptance.every((s:unknown)=>typeof s==="string"&&s.length>20&&s.length<400) ||
    !plain(x.diagnostics) || Object.keys(x).length!==14
 )return false;
 if(i===0){
   return exact(x.diagnostics,{
    kind:"ORIGINAL_OPCODE_SOURCE_PROVENANCE",
    opcodeDecimal:86,pc:43085,model:"XPGUN",
    sourceOperationsVerified:7,doorSourceMechanism:"PASS_SOURCE_ONLY",
    originalHmo3RuntimeEventVerified:false
   });
 }
 const d=x.diagnostics;
 if(!plain(d.regions)||!exact(d.regions,{door:3931,HUD:1077,rightWall:672,other:68}))return false;
 const {regions,...other}=d;
 return exact(other,{
   kind:"ORIGINAL_INDEX_PIXEL_MISMATCH",framePixels:64000,mismatchedIndexPixels:5748,
   sourcePaletteRgbPixelsCorrelated:64000,usedPaletteIndicesProven:144,dacTimingVerified:false
 });
}
export function validateGameCompletion(raw:unknown):raw is CompletionBoard{
 if(!plain(raw) || raw.schema!=="OpenRemaster.StudioGameCompletionReadiness.v1" ||
    raw.release!=="ORF-STUDIO-UI-20261018-r12" ||
    raw.sourceClass!=="HISTORICAL_REAL_GAME_CHECKPOINT_TRIAGE_NOT_REAL_RUNTIME" ||
    raw.status!=="TWO_GAMES_SOURCE_TRIAGE_VALIDATED__GAMEPLAY_FIDELITY_HOLD" ||
    typeof raw.generatedUtc!=="string" || !Number.isFinite(Date.parse(raw.generatedUtc)) ||
    typeof raw.sourceCheckpointUtc!=="string" || !Number.isFinite(Date.parse(raw.sourceCheckpointUtc)) ||
    !plain(raw.sourcePins) || !exact(raw.sourcePins,sourcePins) ||
    !plain(raw.gameSourceSha) || !exact(raw.gameSourceSha,roles) ||
    !plain(raw.sourceSoftwareTests) ||
    !exact(raw.sourceSoftwareTests,{originalArchitectureR1:30,gameBridgeR1:46,totalHistorical:76}) ||
    !Array.isArray(raw.games) || raw.games.length!==2 ||
    !raw.games.every((g:unknown,i:number)=>gameValid(g,i)) ||
    !plain(raw.firstDivergence) || !plain(raw.policy) ||
    Object.keys(raw).length!==12)return false;
 const g=raw.firstDivergence;
 const {required,...short}=g;
 if(!exact(short,{status:"BLOCKED_NO_ALIGNED_GAME_TRACE_PAIR",
    validEventPairs:0,canCallOracle:false}) ||
    !Array.isArray(required) || required.length!==5 ||
    !required.every((s:unknown)=>typeof s==="string"&&s.length>25&&s.length<250))return false;
 return exact(raw.policy,{
   sameAssistantSourceIntegrityNotExternalSignature:true,
   editorialImpactScoresNotPercentages:true,noCrossGameRanking:true,
   originalGameCorporaNotAccessedHere:true,originalGameRuntimeCaptureNotProduced:true,
   independentOwnerWitnessAccepted:false,currentK003GUILeaseObtained:false,
   modelInvocation:false,workerStart:false,gameDispatch:false,
   autoRetry:false,productionAdmission:"HOLD_NO_AUTO_RETRY",
   maxGlobalHeavySlots:3,singleWriter:true
 });
}
export function gameCompletionView(raw:unknown) {
  if(!validateGameCompletion(raw))
    return {phase:"HOLD" as const,code:"UNTRUSTED_OR_MISSING_SOURCE_SNAPSHOT",data:null};
  return {phase:"HISTORICAL_GAME_SOURCE_ONLY" as const,
    code:"ORIGINAL_GAME_RUNTIME_PAIRS_MISSING__PRODUCTION_HOLD",data:raw};
}
export function gameTaskFilter(game:GameEntry,priority:"all"|"P0"|"P1"){
  return game.taskGraph.filter(x=>priority==="all"||x.priority===priority);
}
