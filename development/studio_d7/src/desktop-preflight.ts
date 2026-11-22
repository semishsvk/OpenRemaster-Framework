/** UI-014 / frozen HomePC r21 Desktop preflight.
 * Source checks only: neither browser nor Node server executes a toolchain,
 * installs Rust, selects a publisher certificate or changes the app icon.
 */
export const DESKTOP_BLOCKERS=[
 "tauri_identifier_is_production","tauri_bundle_enabled","rust_cargo_available",
 "rustc_available","rustup_available","windows_signing_tool_available",
 "windows_installer_builder_available",
 "approved_brand_icon_material_available_in_tauri",
 "publisher_code_signing_certificate_independently_approved",
 "complete_runtime_closure_validated","native_windows_exe_built",
 "signed_one_installer_built","independent_owner_gate_A_approved",
 "windows_gate_B_approved","native_canary_gate_C_approved"
] as const;
const acceptedSourceGates={
 native_entrypoint_present:true,
 offline_web_dist_present:true,
 sealed_r20_source_integrity:true,
 tauri_rust_package_present:true,
 tauri_v2_config_present:true
};
const falseGates=Object.fromEntries(DESKTOP_BLOCKERS.map(key=>[key,false]));
const fields=(x:Record<string,unknown>, expected:Record<string,unknown>)=>
 Object.keys(x).sort().join("|")===Object.keys(expected).sort().join("|") &&
 Object.entries(expected).every(([k,v])=>x[k]===v);
const obj=(v:unknown):v is Record<string,unknown>=>v!==null && typeof v==="object" && !Array.isArray(v);
export type DesktopPreflight={
 schema:"OpenRemaster.StudioDesktopReadOnlyPreflight.v21";
 status:"DESKTOP_TOOLCHAIN_AND_APPROVAL_BLOCKED_NO_GO";
 blockers:string[];
 gates:Record<string,boolean>;
 available_executables:Record<string,null>;
 source_r20_zip_sha256:string;
 source_r20_checkpoint_sha256:string;
 tauri_identifier:"dev.openremaster.studio-shadow";
 tauri_product_name:"OpenRemaster Studio";
 tauri_bundle_active:false;tauri_icon_files:[];
 next_action:string;observed_utc_host_clock_not_trusted:string;
 no_network_or_installation:true;may_auto_retry:false;
 may_dispatch:false;may_install:false;
 native_worker_or_K003_not_started:true;
 new_scheduler_created:false;
 original_game_corpus_not_opened:true;original_r20_unchanged:true;
};
export function validateDesktopPreflight(v:unknown):v is DesktopPreflight{
 if(!obj(v) ||
   v.schema!=="OpenRemaster.StudioDesktopReadOnlyPreflight.v21" ||
   v.status!=="DESKTOP_TOOLCHAIN_AND_APPROVAL_BLOCKED_NO_GO" ||
   v.tauri_identifier!=="dev.openremaster.studio-shadow" ||
   v.tauri_product_name!=="OpenRemaster Studio" ||
   v.source_r20_zip_sha256!=="85f09b960f03528594546aaf851e2eae57efe4d28b62aa221b47129026028a21" ||
   v.source_r20_checkpoint_sha256!=="85b196e25fed615b099fc280f259fa9d3ed5b8abcf1bd6183f99815fb8b8ef4f" ||
   v.tauri_bundle_active!==false ||
   !Array.isArray(v.tauri_icon_files)||v.tauri_icon_files.length!==0 ||
   typeof v.next_action!=="string"||v.next_action.length<25||v.next_action.length>300 ||
   typeof v.observed_utc_host_clock_not_trusted!=="string" ||
   !Number.isFinite(Date.parse(v.observed_utc_host_clock_not_trusted)) ||
   v.no_network_or_installation!==true || v.may_auto_retry!==false ||
   v.may_dispatch!==false || v.may_install!==false ||
   v.native_worker_or_K003_not_started!==true ||
   v.new_scheduler_created!==false || v.original_game_corpus_not_opened!==true ||
   v.original_r20_unchanged!==true ||
   !Array.isArray(v.blockers)||v.blockers.join("|")!==DESKTOP_BLOCKERS.join("|") ||
   !obj(v.gates)||!obj(v.available_executables))return false;
 return fields(v.gates,{...acceptedSourceGates,...falseGates}) &&
   fields(v.available_executables,{cargo:null,iscc:null,makensis:null,rustc:null,rustup:null,signtool:null}) &&
   Object.keys(v).length===21;
}
export function desktopView(value:unknown){
 return validateDesktopPreflight(value)
   ? {phase:"DESKTOP_NO_GO" as const,data:value,missing:DESKTOP_BLOCKERS.length}
   : {phase:"SOURCE_REJECTED" as const,data:null,missing:null};
}
