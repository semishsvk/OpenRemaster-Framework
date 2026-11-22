/**
 * Studio read-only projector of the sealed OpenRemaster r18a Gate A review.
 *
 * Immutable bundled historical evidence: NOT a live Host API, Owner signer,
 * Cosmos witness, permission grant, browser fetch or native job.
 * Even a perfectly valid snapshot NEVER authorizes A, B, C or execution.
 */
export const R18A_SOURCE = {
  studioR11: "8771434f02188076dd30e6638a2bb436e592f3b9a72224170d1c5e2589608417",
  ownerR18a: "b44a54cfa3a068966691ae8c73b3cb82fff29f0ecd42956290b60d136698175f",
  checkpointR18a: "39bce8528299f1178e77c03132823510eec34d0fc14a08425492eeaf7eedf731",
  projection: "b0f40ce8b776486c69f2b984621f8c6201b559ef54eaba6721453a28ceece8f7",
} as const;
export const GATE_A_IDS = [
  "A01_ROOT_OF_TRUST","A02_INDEPENDENT_WITNESS_TENANT",
  "A03_SIGNER_ROLE_CUSTODY","A04_REAL_COSMOS_CAS",
  "A05_CRYPTO_RECEIPT","A06_KEY_ROTATION_REVOCATION",
  "A07_SIGNED_CURRENT_HIGHWATER","A08_UNKNOWN_OUTCOME_RECOVERY",
  "A09_DISTINCT_OWNER_ACCEPTANCE",
] as const;
export const GATE_A_WAVES = [
  ["A01_ROOT_OF_TRUST"],
  ["A02_INDEPENDENT_WITNESS_TENANT"],
  ["A03_SIGNER_ROLE_CUSTODY","A04_REAL_COSMOS_CAS"],
  ["A05_CRYPTO_RECEIPT"],
  ["A06_KEY_ROTATION_REVOCATION"],
  ["A07_SIGNED_CURRENT_HIGHWATER"],
  ["A08_UNKNOWN_OUTCOME_RECOVERY"],
  ["A09_DISTINCT_OWNER_ACCEPTANCE"],
] as const;
const ROLE_COUNTS = [3,3,3,2,2,3,2,2,2] as const;
const PINNED_DEPS = [
  [],
  [GATE_A_IDS[0]],
  [GATE_A_IDS[0],GATE_A_IDS[1]],
  [GATE_A_IDS[1]],
  [GATE_A_IDS[0],GATE_A_IDS[2],GATE_A_IDS[3]],
  [GATE_A_IDS[2],GATE_A_IDS[4]],
  [GATE_A_IDS[3],GATE_A_IDS[4],GATE_A_IDS[5]],
  [GATE_A_IDS[3],GATE_A_IDS[4],GATE_A_IDS[6]],
  GATE_A_IDS.slice(0,8),
] as const;

type GateAId = typeof GATE_A_IDS[number];
export type GateAItem = {
  id: GateAId;
  required_role_aliases: string[];
  predecessors: string[];
  external_evidence_task: string;
  role_metadata_available: false;
  real_crypto_or_origin_verified: false;
  dependency_authenticated: false;
  current_status: "NEEDS_SEPARATE_OUT_OF_BAND_EVIDENCE";
};
export type GateAWave = {wave:number;gate_ids:string[];not_an_execution_schedule:true};
export type GateABundle = {
  schema:"OpenRemaster.StudioGateAReviewProjection.v19";
  classification:"HISTORICAL_LOCAL_SOURCE_ONLY_NO_PRODUCTION_AUTHORITY";
  sourceStudioR11ZipSha256:typeof R18A_SOURCE.studioR11;
  sourceOwnerR18aZipSha256:typeof R18A_SOURCE.ownerR18a;
  sourceOwnerR18aCheckpointSha256:typeof R18A_SOURCE.checkpointR18a;
  historicalSourceTestsPassed:83;
  gateCount:9;roleFieldCount:22;reviewWaveCount:8;
  approvedExternally:false;independentlySignedEvidenceCount:0;
  currentNativeTaskQueried:false;currentOwnerWitnessQueried:false;
  mayDispatch:false;mayAutoRetry:false;mayInstall:false;mayStartWorker:false;
  firstReview:"A01_ROOT_OF_TRUST";
  waves:GateAWave[];gates:GateAItem[];
  disclaimer:string;
};
const isObj=(x:unknown):x is Record<string,unknown>=>
  x!==null && typeof x==="object" && !Array.isArray(x);
const exactKeys=(o:Record<string,unknown>,keys:readonly string[])=>
  Object.keys(o).sort().join("|")===keys.slice().sort().join("|");
const eqStrArray=(x:unknown,arr:readonly string[]) =>
  Array.isArray(x) && x.length===arr.length &&
  x.every((v,i)=>v===arr[i]);
const uniqueSafeRoles=(value:unknown,count:number) =>
  Array.isArray(value) && value.length===count &&
  value.every(v=>typeof v==="string" && /^[a-z][a-z0-9_]{2,63}$/.test(v)) &&
  new Set(value).size===count;
const TOP_FIELDS=[
  "schema","classification","sourceStudioR11ZipSha256",
  "sourceOwnerR18aZipSha256","sourceOwnerR18aCheckpointSha256",
  "historicalSourceTestsPassed","gateCount","roleFieldCount",
  "reviewWaveCount","approvedExternally","independentlySignedEvidenceCount",
  "currentNativeTaskQueried","currentOwnerWitnessQueried","mayDispatch",
  "mayAutoRetry","mayInstall","mayStartWorker","firstReview","waves","gates",
  "disclaimer",
] as const;
const GATE_FIELDS=[
  "id","required_role_aliases","predecessors","external_evidence_task",
  "role_metadata_available","real_crypto_or_origin_verified",
  "dependency_authenticated","current_status"
] as const;
const WAVE_FIELDS=["wave","gate_ids","not_an_execution_schedule"] as const;

/** Refuse unknown fields and all local/production self-promotion. */
export function validateGateAHandoff(raw:unknown):raw is GateABundle{
  if(!isObj(raw) || !exactKeys(raw,TOP_FIELDS) ||
     raw.schema!=="OpenRemaster.StudioGateAReviewProjection.v19" ||
     raw.classification!=="HISTORICAL_LOCAL_SOURCE_ONLY_NO_PRODUCTION_AUTHORITY" ||
     raw.sourceStudioR11ZipSha256!==R18A_SOURCE.studioR11 ||
     raw.sourceOwnerR18aZipSha256!==R18A_SOURCE.ownerR18a ||
     raw.sourceOwnerR18aCheckpointSha256!==R18A_SOURCE.checkpointR18a ||
     raw.historicalSourceTestsPassed!==83 || raw.gateCount!==9 ||
     raw.roleFieldCount!==22 || raw.reviewWaveCount!==8 ||
     raw.firstReview!==GATE_A_IDS[0] ||
     raw.approvedExternally!==false ||
     raw.independentlySignedEvidenceCount!==0 ||
     raw.currentNativeTaskQueried!==false ||
     raw.currentOwnerWitnessQueried!==false ||
     raw.mayDispatch!==false || raw.mayAutoRetry!==false ||
     raw.mayInstall!==false || raw.mayStartWorker!==false ||
     typeof raw.disclaimer!=="string" ||
     !raw.disclaimer.includes("Historical review") ||
     raw.disclaimer.length>250 ||
     !Array.isArray(raw.gates) || raw.gates.length!==9 ||
     !Array.isArray(raw.waves) || raw.waves.length!==8) return false;

  let nRoles=0;
  for(let i=0;i<GATE_A_IDS.length;i++){
    const gate=raw.gates[i];
    if(!isObj(gate) || !exactKeys(gate,GATE_FIELDS) ||
       gate.id!==GATE_A_IDS[i] ||
       !uniqueSafeRoles(gate.required_role_aliases,ROLE_COUNTS[i]) ||
       !eqStrArray(gate.predecessors,PINNED_DEPS[i]) ||
       typeof gate.external_evidence_task!=="string" ||
       gate.external_evidence_task.length<25 ||
       gate.external_evidence_task.length>300 ||
       gate.role_metadata_available!==false ||
       gate.real_crypto_or_origin_verified!==false ||
       gate.dependency_authenticated!==false ||
       gate.current_status!=="NEEDS_SEPARATE_OUT_OF_BAND_EVIDENCE") return false;
    nRoles+=ROLE_COUNTS[i];
  }
  if(nRoles!==22)return false;

  for(let i=0;i<GATE_A_WAVES.length;i++){
    const wave=raw.waves[i];
    if(!isObj(wave) || !exactKeys(wave,WAVE_FIELDS) ||
       wave.wave!==i+1 || wave.not_an_execution_schedule!==true ||
       !eqStrArray(wave.gate_ids,GATE_A_WAVES[i]))return false;
  }
  return true;
}
export type GateAView={
  status:"HOLD"; authority:"UNSIGNED_LOCAL_SOURCE";
  sourceHistorical:true; currentHostVerified:false;
  canDispatch:false; canRetry:false; canInstall:false; canSign:false;
  gateCount:number; rolesRequired:number; independentlyApproved:number;
  firstExternalStep:"A01_ROOT_OF_TRUST"; data:GateABundle|null;
};
export function gateAView(raw:unknown):GateAView{
  const data=validateGateAHandoff(raw)?raw:null;
  return {
    status:"HOLD",authority:"UNSIGNED_LOCAL_SOURCE",
    sourceHistorical:true,currentHostVerified:false,
    canDispatch:false,canRetry:false,canInstall:false,canSign:false,
    gateCount:data?9:0,rolesRequired:data?22:0,independentlyApproved:0,
    firstExternalStep:"A01_ROOT_OF_TRUST",data,
  };
}
export function unsignedGateReviewBrief(raw:unknown,gateId:GateAId):string{
  const v=gateAView(raw);
  if(!v.data)throw Error("GATE_A_SOURCE_REJECTED");
  const entry=v.data.gates.find(g=>g.id===gateId);
  if(!entry)throw Error("UNKNOWN_REVIEW_GATE");
  return [
    "OPENREMASTER STUDIO / INDEPENDENT OWNER GATE A / UNSIGNED BRIEF",
    "Historical local research source; NEVER an approval, signature, current state or dispatch permit.",
    "Owner handoff r18a SHA256: "+R18A_SOURCE.ownerR18a,
    "Review requirement: "+entry.id,
    "Missing external evidence: "+entry.external_evidence_task,
    "Required reviewer roles:",...entry.required_role_aliases.map(role=>"- "+role),
    "Unaccepted prerequisites:",...(entry.predecessors.length?entry.predecessors.map(x=>"- "+x):["- none, first external trust-root request"]),
    "All nine external proofs still missing. No Gate A/B/C authority.",
    "HOLD_NO_AUTO_RETRY | ONE K003 | ONE WRITER | MAX THREE HEAVY SLOTS | NO V2 TO V1 FALLBACK"
  ].join("\n")+"\n";
}
