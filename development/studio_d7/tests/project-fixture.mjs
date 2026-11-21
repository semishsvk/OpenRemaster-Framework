export const now=1_800_000_000_000;
export function binding() {
  return {request:{project_id:'FixtureProject',edition_id:'DEMO',committed_operation_id:'a'.repeat(32),accepted_manifest_digest:'b'.repeat(64)},
    engine:'fixture',sourceCommit:'c'.repeat(40),sourceTree:'d'.repeat(40),sourceManifestSha256:'e'.repeat(64),buildPlanSha256:'f'.repeat(64),requiresPck:true,
    files:[{role:'EXE',name:'Game.exe',sha256:'1'.repeat(64),bytes:4096},{role:'PCK',name:'Game.pck',sha256:'2'.repeat(64),bytes:512}]};
}
export function response(b=binding()) {
  return {schema:'OpenRemaster.NativeFileObservation.v1',state:'LIVE',read_only:true,execution_authority:false,gameplay:'UNKNOWN',fidelity:'UNKNOWN',observed_epoch_ms:now,
    selection:{...b.request},engine:b.engine,source_commit:b.sourceCommit,source_tree:b.sourceTree,source_manifest_sha256:b.sourceManifestSha256,build_plan_sha256:b.buildPlanSha256,
    files:b.files.map((f,i)=>({...f,volume:'3'.repeat(16),file_id:String(i+4).repeat(32)}))};
}
