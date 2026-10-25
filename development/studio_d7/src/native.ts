/**
 * UI-004 strict interpretation of a frozen local IPC/runtime evidence report.
 * This is a diagnostic view-model only, not an admission engine.
 */
export type BinaryRecord = {
  fileName: string; sourceType: string; sha256: string; bytes: number;
  format: "PE32+"; machineHex: "0x8664"; sectionCount: number;
  directImportDllNames: string[]; directImportCount: number;
  delayImportsEnumerated: false; forwardersAndTransitiveImportsResolved: false;
};
export type NativeReadiness = {
  schema: "OpenRemaster.StudioNativeReadiness.v1";
  release: "UI-004/r3"; generatedUtc: string; method: string; platform: string;
  binaryClosure: {
    observedDirectImportsOnly: true; runtimeFullClosureVerified: false;
    importNameResolutionVerified: false; nativeLoaderPolicyVerified: false;
    relocatableNodePythonRuntime: false; binaries: {python: BinaryRecord;node: BinaryRecord};
  };
  ipcPrototype: {
    implementation:string; testedOnWindows: true; testCount:number; testResult:"PASS";
    oneShot:true; currentUserOnlyFlag:true; distinctRoleTokenTested:false;
    signedOwnerAuthenticated:false; actualTauriIPCIntegrated:false;
    canServeOriginalGameOrK003:false; noBackgroundService:true;
  };
  admission: {
    ownerSigned:false; witnessIndependent:false; windowsDistinctRoleTokenVerified:false;
    protectedInstallRootVerified:false; publisherSignatureVerified:false;
    trustedComponentManifest:false; canonicalFrameworkCoreOwnerSelected:false;
    approvedStudioIconAssetVerified:false; tauriNativeBuildTested:false;
    componentManagerProductionVerified:false; assetLabsProductionVerified:false;
    nativeWorkerV2MayRun:false; productionAdmission:"HOLD"; jobDispatch:false; autoRetry:false;
  };
  plannedPackaging: {
    target:"OpenRemasterStudio-Setup-x64.exe"; oneInstallerCompletePlatformModularRuntime:true;
    installerProduced:false; studioAppExeProduced:false; approvedIconReplacementAllowed:false;
  };
  caveat:string;
};
type Obj=Record<string,unknown>;
function isObj(v:unknown):v is Obj { return v!==null && typeof v==="object" && !Array.isArray(v); }
const SHA=/^[0-9a-f]{64}$/;
const DLL=/^[A-Z0-9._-]{3,100}\.DLL$/;
const expectedSha:Record<string,string> = {
  python:"cce21c0e8710e304273e98ac4b2b0f5aceb639acbcd2343cbaa5c4e81619c45b",
  node:"3602f2bb1a10f2cbab4c36886218a33c1ab3db87290e73b033c46c77147d0237",
};
export const REQUIRED_ADMISSION_GATES = [
  "ownerSigned", "witnessIndependent", "windowsDistinctRoleTokenVerified",
  "protectedInstallRootVerified", "publisherSignatureVerified", "trustedComponentManifest",
  "canonicalFrameworkCoreOwnerSelected", "approvedStudioIconAssetVerified",
  "tauriNativeBuildTested", "componentManagerProductionVerified",
  "assetLabsProductionVerified", "nativeWorkerV2MayRun",
] as const;
export const ADMISSION_LABELS:Record<string,string> = {
  ownerSigned:"Externally signed Owner authorization",
  witnessIndependent:"Independent current Witness",
  windowsDistinctRoleTokenVerified:"Distinct Windows role-token boundary",
  protectedInstallRootVerified:"Protected installer / install-root ACL",
  publisherSignatureVerified:"Publisher Authenticode signature",
  trustedComponentManifest:"Authenticated version compatibility manifest",
  canonicalFrameworkCoreOwnerSelected:"Canonical Framework Core owner",
  approvedStudioIconAssetVerified:"Original approved Studio icon file",
  tauriNativeBuildTested:"Windows Tauri 2 native GUI acceptance",
  componentManagerProductionVerified:"Component Manager production release",
  assetLabsProductionVerified:"Asset Labs deployable source closure",
  nativeWorkerV2MayRun:"Native Worker V2 separate commissioning",
};
function binary(v:unknown,role:"node"|"python"):v is BinaryRecord {
  if(!isObj(v) || v.fileName!==(role==="node"?"node.exe":"python.exe") ||
    v.sourceType!=="LOCAL_WINDOWS_IMAGE_OBSERVATION" ||
    v.sha256!==expectedSha[role] || !SHA.test(v.sha256 as string) || v.format!=="PE32+" || v.machineHex!=="0x8664" ||
    !Number.isSafeInteger(v.bytes) || Number(v.bytes)<10000 || Number(v.bytes)>130*1024*1024 ||
    !Number.isSafeInteger(v.sectionCount) || Number(v.sectionCount)<1 || Number(v.sectionCount)>96 ||
    v.delayImportsEnumerated!==false || v.forwardersAndTransitiveImportsResolved!==false ||
    !Array.isArray(v.directImportDllNames) || v.directImportDllNames.length>64 ||
    !Number.isSafeInteger(v.directImportCount) || v.directImportCount!==v.directImportDllNames.length ||
    !v.directImportDllNames.every(x=>typeof x==="string" && DLL.test(x)) ||
    new Set(v.directImportDllNames).size!==v.directImportDllNames.length) return false;
  return true;
}
export function validateNativeReadiness(v:unknown):v is NativeReadiness {
  if(!isObj(v) || v.schema!=="OpenRemaster.StudioNativeReadiness.v1" ||
    v.release!=="UI-004/r3" || v.method!=="PINNED_READ_ONLY_PE_IMPORT_AUDIT_PLUS_LOCAL_WINDOWS_IPC_POC" ||
    v.platform!=="Windows x64 HomePC" || typeof v.generatedUtc!=="string" ||
    !Number.isFinite(Date.parse(v.generatedUtc)) || !isObj(v.binaryClosure) ||
    !isObj(v.ipcPrototype) || !isObj(v.admission) || !isObj(v.plannedPackaging) ||
    typeof v.caveat!=="string" || v.caveat.length>600) return false;
  const b=v.binaryClosure;
  if(b.observedDirectImportsOnly!==true || b.runtimeFullClosureVerified!==false ||
    b.importNameResolutionVerified!==false || b.nativeLoaderPolicyVerified!==false ||
    b.relocatableNodePythonRuntime!==false || !isObj(b.binaries) ||
    !binary(b.binaries.python,"python") || !binary(b.binaries.node,"node")) return false;
  const i=v.ipcPrototype;
  if(i.implementation!==".NET 9 NamedPipeServerStream test-only" ||
    i.testedOnWindows!==true || i.testCount!==20 || i.testResult!=="PASS" ||
    i.oneShot!==true || i.currentUserOnlyFlag!==true ||
    i.distinctRoleTokenTested!==false || i.signedOwnerAuthenticated!==false ||
    i.actualTauriIPCIntegrated!==false || i.canServeOriginalGameOrK003!==false ||
    i.noBackgroundService!==true) return false;
  const a=v.admission;
  if(REQUIRED_ADMISSION_GATES.some(k=>a[k]!==false) ||
    a.productionAdmission!=="HOLD" || a.jobDispatch!==false || a.autoRetry!==false ||
    Object.keys(a).length!==REQUIRED_ADMISSION_GATES.length+3) return false;
  const p=v.plannedPackaging;
  if(p.target!=="OpenRemasterStudio-Setup-x64.exe" ||
    p.oneInstallerCompletePlatformModularRuntime!==true ||
    p.installerProduced!==false || p.studioAppExeProduced!==false ||
    p.approvedIconReplacementAllowed!==false) return false;
  return true;
}
export function nativeStatus(raw:unknown) {
  if(!validateNativeReadiness(raw)) return {status:"HOLD" as const,reason:"INVALID_LOCAL_READINESS",report:null};
  return {status:"HOLD" as const,reason:"PROTOTYPE_TESTED_PRODUCTION_UNADMITTED",report:raw};
}
