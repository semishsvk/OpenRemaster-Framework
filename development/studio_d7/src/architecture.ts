/** Architecture r1 view model. Source-only, historical and always production HOLD.
 *  Exact schema checks are not signatures or live Worker observations. */
type Rec=Record<string,unknown>;
type Cap={id:string;kind:string;status:string;requires:string[]};
const own=(v:unknown):v is Rec=>typeof v==="object"&&v!==null&&!Array.isArray(v);
const hold=(msg:string):never=>{throw new Error("ARCHITECTURE_HOLD_"+msg);};
const field=(v:Rec,k:string):Rec=>{
  const x=v[k]; if(!own(x))return hold("FIELD_"+k); return x;
};
export type ArchitectureView={status:"HOLD_NO_AUTO_RETRY";sourceCount:number;
  capabilities:Cap[];trustStages:string[];runtimeVerified:false;mayDispatch:false;};
export function architectureView(input:unknown):ArchitectureView {
  if(!own(input) || input.schema!=="OpenRemaster.StudioArchitectureSnapshot.v1" ||
     input.transport!=="STATIC_READ_ONLY_DATA_NO_EXECUTION_ENDPOINT" ||
     input.source_evidence!=="LOCAL_HASH_MATCH_NOT_ATTESTED" ||
     input.source_pin_count!==16 ||
     input.source_drift!==false ||
     input.fresh_native_state_observed!==false ||
     input.dynamic_control_available!==false)return hold("SCHEMA_OR_FRESHNESS");
  const prod=field(input,"production"),cat=field(input,"capability");
  const runtime=field(input,"runtime"),host=field(input,"host_api");
  const completion=field(input,"completion"),div=field(input,"first_divergence");
  const game=field(input,"cross_game");
  if(prod.decision!=="NO_GO_PRODUCTION_HOLD" ||
     prod.review_consistent!==true || prod.k003_is_only_scheduler!==true ||
     prod.external_A!==false || prod.external_B!==false || prod.external_C!==false ||
     prod.may_dispatch!==false || prod.may_install!==false ||
     prod.may_acquire_lease!==false || prod.may_open_native_work!==false ||
     prod.may_auto_retry!==false || prod.owner_witness_CAS_verified!==false ||
     prod.signed_receipts_verified!==false ||
     runtime.may_publish!==false || runtime.signed_studio_exe_verified!==false ||
     runtime.single_installer_verified!==false ||
     cat.derived_catalog_authoritative!==false ||
     cat.may_install_or_retire_tools!==false ||
     completion.mode!=="ADVISORY_INPUT_REQUIRED" ||
     div.mode!=="DIAGNOSTIC_INPUT_REQUIRED" ||
     game.requires_game_specific_validation!==true ||
     host.version!=="v1" || host.cache_control!=="no-store" ||
     host.may_spawn_process!==false || host.may_issue_lease!==false ||
     JSON.stringify(host.methods)!=='["GET","HEAD"]')return hold("AUTHORITY");
  if(!Array.isArray(cat.capabilities) || cat.capabilities.length!==9)
    return hold("CAPABILITY_COUNT");
  const names=new Set<string>();
  const rows:Cap[]=[];
  for(const r of cat.capabilities){
    if(!own(r) || typeof r.id!=="string" || !/^[A-Z0-9-]{4,64}$/.test(r.id) ||
       names.has(r.id) || typeof r.kind!=="string" || typeof r.status!=="string" ||
       !Array.isArray(r.requires) || !r.requires.every(x=>typeof x==="string"))
       return hold("CAPABILITY");
    names.add(r.id);
    rows.push({id:r.id,kind:r.kind,status:r.status,requires:[...r.requires]});
  }
  if(!names.has("ORF-ADM-001") || !names.has("ORF-STUDIO-HOST") ||
     !rows.every(r=>r.requires.every(x=>names.has(x))))return hold("DEPENDENCIES");
  return {status:"HOLD_NO_AUTO_RETRY",sourceCount:16,capabilities:rows,
    trustStages:["A · independent Owner / Witness",
      "B · protected Windows identities / installer",
      "C · signed K003 execution canary"],
    runtimeVerified:false,mayDispatch:false};
}
