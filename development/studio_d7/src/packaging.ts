/** UI-007 source-bounded native dependency evidence. It NEVER admits an installer. */
export type RuntimeModulePin = {fileName:string; sha256:string; bytes:number};
export type PackagingReadiness = {
  schema:"OpenRemaster.Studio.RuntimePackagingEvidence.v1";
  releaseId:"ORF-STUDIO-UI-20261018-r6";
  generatedUtc:string;
  status:"PINNED_NATIVE_EVIDENCE_VALIDATED__INSTALLER_NO_GO";
  sourceAuthority:"LOCAL_UNSIGNED_SHA256_ONLY";
  scope:"TWO_SEPARATE_NW025_U_AND_Z_EVIDENCE_SCOPES_NOT_ONE_RUNTIME_PROOF";
  sourcePins:Record<string,string>;
  staticAudit:{
    origin:"NW025-U"; originalBinaryRootCount:37;
    directExternalNames:36; directApiSetContracts:14;
    directSystem32FilenameCandidates:22; directUnclassified:0;
    actualLoaderResolutionAccepted:false;
    boundedGraphFiles:256; boundedGraphOriginalRuntimeFiles:37;
    boundedGraphWindowsFiles:219; boundedGraphImportEdges:9331;
    boundedGraphApiSetEdges:7534; boundedGraphNoFilenameCandidateEdges:5;
    boundedGraphComplete:false;graphBudgetReached:true;
    windowsSystemDllsToIncludeInInstaller:false;
    nodeVersion:"24.19.0";pythonLicensePresent:true;pythonLicenseSha256:string;
    nodeRuntimeLicenseObtained:false;redistributionApproved:false;
  };
  loadedModuleAudit:{
    origin:"NW025-Z";observationKind:"ONE_POST_TEST_SNAPSHOT_NOT_FULL_DYNAMIC_CLOSURE";
    isolatedRuntimeSource:"NW025-Y_HISTORICAL_CANDIDATE";
    checksPassed:20;checksTotal:20;observedNativeModules:40;
    runtimeModules:17;windowsLocationModules:23;
    unexpectedModuleLocations:0;runtimeModulesMatchYManifest:true;
    fullTransientLoaderHistoryCaptured:false;cleanMachineTested:false;
    productionHostRpcInvoked:false;moduleFileNamesAndHashes:RuntimeModulePin[];
  };
  installer:{
    installerStatus:"NO_GO";installerBuilt:false;
    nodeRuntimeLicenseObtained:false;portableRuntimeClosureComplete:false;
    minimumRequiredComponentsInstalled:false;originalStudioIconVerified:false;
    publisherSignatureVerified:false;independentOwnerWitnessApproved:false;
    differentWindowsSidVerified:false;nativeTauriExecutableBuilt:false;
    productionDispatchAllowed:false;automaticRetry:false;
    originalGameDataAccessed:false;modelCalls:0;nativeWorkerStarts:0;
  };
  blockerCodes:string[];
};
const hash=/^[a-f0-9]{64}$/;
const filename=/^[A-Za-z0-9._+-]{2,110}$/;
const plain=(x:unknown):x is Record<string,unknown> => x!==null && typeof x==="object" && !Array.isArray(x);
const expectedPins={
 studioParentR5:"56d3cdeba937b019c2d345e801cf5ed8c5cb55f55d6a6494bfc05163e70e9ea5",
 uManifest:"68697d9003fdf86667eb96d53d321f93444599a38bb4be0535740b9955810ae4",
 uBoundary:"8f07a283fe6bed4b9aa3038777914869c91e17573b878ed9610d7bc36194553e",
 uGraph:"d9131a4ae15faf5938646761e8fd8385601321d7e7ec8221bde4deb9a7c7ef8e",
 zManifest:"2a74b83da5fd66ebfbb04b05b6975c50e5f16c0acdc72fa26e6eb7ac0f1cb773",
 zLoads:"7678099a60dd88a7e8bb5179d7df7f92434f0136138d03568dea7c9025798e26",
 zStdout:"15a6d54d5ea4f71d8e4d00d7f870cedbc7e785132db479aa3eee8b30a1ed206f",
 pythonLicense:"935cf13e19f8c31b497d20b05d73623431a226b230c3599bc30fa3348979bc68",
};
export const PACKAGING_BLOCKERS=[
  "GRAPH_BOUND_REACHED",
  "TRANSITIVE_DYNAMIC_APISET_LOADER_UNVERIFIED",
  "FIVE_DEEP_GRAPH_EDGES_WITHOUT_FILENAME_CANDIDATE_NOT_A_LOADER_FAILURE",
  "NODE_RUNTIME_LICENSE_NOTICE_NOT_OBTAINED",
  "CLEAN_MACHINE_AND_RELOCATION_NOT_VERIFIED",
  "PUBLISHER_AND_OWNER_WITNESS_NOT_SIGNED",
  "TAURI_RUNTIME_AND_INSTALLER_NOT_BUILT",
] as const;
export const BLOCKER_DESCRIPTIONS:Record<string,string>={
 GRAPH_BOUND_REACHED:"Static dependency graph stopped at the 256-file research limit",
 TRANSITIVE_DYNAMIC_APISET_LOADER_UNVERIFIED:"Delay imports, API-set redirection, forwarded exports and dynamic loads are not closed",
 FIVE_DEEP_GRAPH_EDGES_WITHOUT_FILENAME_CANDIDATE_NOT_A_LOADER_FAILURE:"Five deeper edges lacked a filename candidate; not evidence of a failed Windows loader",
 NODE_RUNTIME_LICENSE_NOTICE_NOT_OBTAINED:"Authoritative Node.js runtime redistribution notice is still missing",
 CLEAN_MACHINE_AND_RELOCATION_NOT_VERIFIED:"Clean-machine install, relocation and independent host launch untested",
 PUBLISHER_AND_OWNER_WITNESS_NOT_SIGNED:"Publisher, independent Owner and current Witness are not authenticated",
 TAURI_RUNTIME_AND_INSTALLER_NOT_BUILT:"Native Tauri 2 app and signed One Installer have not been built"
};
function allFields<T extends Record<string,unknown>>(v:T,values:Record<string,unknown>) {
  return Object.keys(v).sort().join("|")===Object.keys(values).sort().join("|") &&
    Object.entries(values).every(([key,value])=>v[key]===value);
}
export function validatePackagingReadiness(raw:unknown):raw is PackagingReadiness {
  if(!plain(raw) || raw.schema!=="OpenRemaster.Studio.RuntimePackagingEvidence.v1" ||
    raw.releaseId!=="ORF-STUDIO-UI-20261018-r6" ||
    raw.status!=="PINNED_NATIVE_EVIDENCE_VALIDATED__INSTALLER_NO_GO" ||
    raw.sourceAuthority!=="LOCAL_UNSIGNED_SHA256_ONLY" ||
    raw.scope!=="TWO_SEPARATE_NW025_U_AND_Z_EVIDENCE_SCOPES_NOT_ONE_RUNTIME_PROOF" ||
    typeof raw.generatedUtc!=="string" || !Number.isFinite(Date.parse(raw.generatedUtc)) ||
    !plain(raw.sourcePins) || !plain(raw.staticAudit) ||
    !plain(raw.loadedModuleAudit) || !plain(raw.installer) ||
    !Array.isArray(raw.blockerCodes)) return false;
  if(!allFields(raw.sourcePins,expectedPins) ||
    !Object.values(raw.sourcePins).every(v=>typeof v==="string" && hash.test(v)))return false;
  const u=raw.staticAudit;
  const uMust={
    origin:"NW025-U",originalBinaryRootCount:37,
    directExternalNames:36,directApiSetContracts:14,
    directSystem32FilenameCandidates:22,directUnclassified:0,
    actualLoaderResolutionAccepted:false,
    boundedGraphFiles:256,boundedGraphOriginalRuntimeFiles:37,
    boundedGraphWindowsFiles:219,boundedGraphImportEdges:9331,
    boundedGraphApiSetEdges:7534,boundedGraphNoFilenameCandidateEdges:5,
    boundedGraphComplete:false,graphBudgetReached:true,
    windowsSystemDllsToIncludeInInstaller:false,
    nodeVersion:"24.19.0",pythonLicensePresent:true,
    pythonLicenseSha256:expectedPins.pythonLicense,
    nodeRuntimeLicenseObtained:false,redistributionApproved:false
  };
  if(!allFields(u,uMust))return false;
  const z=raw.loadedModuleAudit;
  const {moduleFileNamesAndHashes,...zHeader}=z;
  const zMust={
    origin:"NW025-Z",
    observationKind:"ONE_POST_TEST_SNAPSHOT_NOT_FULL_DYNAMIC_CLOSURE",
    isolatedRuntimeSource:"NW025-Y_HISTORICAL_CANDIDATE",
    checksPassed:20,checksTotal:20,observedNativeModules:40,
    runtimeModules:17,windowsLocationModules:23,
    unexpectedModuleLocations:0,runtimeModulesMatchYManifest:true,
    fullTransientLoaderHistoryCaptured:false,cleanMachineTested:false,
    productionHostRpcInvoked:false
  };
  if(!allFields(zHeader,zMust) || !Array.isArray(moduleFileNamesAndHashes) ||
    moduleFileNamesAndHashes.length!==17) return false;
  if(!moduleFileNamesAndHashes.every((m:unknown)=>plain(m) &&
    Object.keys(m).sort().join("|")==="bytes|fileName|sha256" &&
    typeof m.fileName==="string" && filename.test(m.fileName) &&
    typeof m.sha256==="string" && hash.test(m.sha256) &&
    Number.isSafeInteger(m.bytes) && Number(m.bytes)>0)) return false;
  if(new Set(moduleFileNamesAndHashes.map(m=>m.fileName.toLowerCase())).size!==17)return false;
  const relMust={
    installerStatus:"NO_GO",installerBuilt:false,nodeRuntimeLicenseObtained:false,
    portableRuntimeClosureComplete:false,minimumRequiredComponentsInstalled:false,
    originalStudioIconVerified:false,publisherSignatureVerified:false,
    independentOwnerWitnessApproved:false,differentWindowsSidVerified:false,
    nativeTauriExecutableBuilt:false,productionDispatchAllowed:false,
    automaticRetry:false,originalGameDataAccessed:false,modelCalls:0,nativeWorkerStarts:0
  };
  const installer=raw.installer;
  if(!plain(installer) || !allFields(installer,relMust))return false;
  return raw.blockerCodes.length===PACKAGING_BLOCKERS.length &&
    raw.blockerCodes.every((v,i)=>v===PACKAGING_BLOCKERS[i]);
}
export function packagingView(raw:unknown) {
  return validatePackagingReadiness(raw)
    ? {status:"NO_GO" as const,phase:"SOURCE_AUDIT_INCOMPLETE" as const, data:raw}
    : {status:"NO_GO" as const,phase:"SOURCE_DRIFT_HOLD" as const,data:null};
}
