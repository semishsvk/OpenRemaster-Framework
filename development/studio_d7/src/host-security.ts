/** UI-006 actual Windows same-user named-pipe evidence, never production admission. */
export type HostSecurityReport = {
  schema:"OpenRemaster.StudioHostSecurityReadiness.v1";
  release:"ORF-STUDIO-UI-20261018-r5";
  generatedUtc:string;
  sourceMode:"PINNED_LOCAL_WINDOWS_SAME_USER_PIPE_TEST";
  sourceAuthority:"LOCAL_TEST_NO_EXTERNAL_ATTESTATION";
  status:"SAME_USER_IMPERSONATION_TESTED_PRODUCTION_HOLD";
  host:"HomePC";
  sourcePins:{
    r4ZipSha256:string; sameUserSecurityReceiptSha256:string;
    ownerR8Sha256:string; runtimeAuditSha256:string;
  };
  osProof:{
    windowsNamedPipe:true;currentUserOnly:true;
    sameUserImpersonationObserved:true;clientSidComparedInternally:true;
    clientSidPersisted:false;distinctSidAuthenticated:false;
    externalRoleTokenOrAclProof:false;roleSeparationAccepted:false;
    testCount:16;testFailures:0;testStatus:"PASS";
    oneShotNoPersistentListener:true;
  };
  installReadiness:{
    requiredComponentCount:9;installedComponentCount:0;
    requiredComponents:string[];componentManagerReleaseAccepted:false;
    portableRuntimeDllClosure:false;nodePythonTransitiveImportsVerified:false;
    nativeTauri2ExeBuilt:false;nativeTauri2WindowTested:false;
    cargoAvailableInCurrentPath:false;publisherSigningAvailable:false;
    approvedOriginalStudioIconAssetVerified:false;
    oneInstallerIdentity:"OpenRemasterStudio-Setup-x64.exe";installerCreated:false;
  };
  authority:{
    ownerSigned:false;witnessIndependent:false;fencedGlobalCasValidated:false;
    nativeWorkerV2Admitted:false;modelInvocationAllowed:false;
    jobDispatchAllowed:false;newSchedulerCreated:false;
    automaticRetry:false;productionAdmission:"HOLD";
    unknownOutcome:"HOLD_NO_AUTO_RETRY";
  };
  qualifier:string;
};
const sha=/^[0-9a-f]{64}$/;
const pins={
  r4ZipSha256:"bfa838ddd1a0b646aa1aabc254d9bfe694ee767f536f5807601e38db5326576a",
  sameUserSecurityReceiptSha256:"60673781317e9677e7c12e17fc2cf1ac449a4888390e3b94a1c6c35ce841af90",
  ownerR8Sha256:"47ac5e7223c5dedd6cefc0ec1e323338c4d07a538fc9327452a1fe8ecd03b325",
  runtimeAuditSha256:"82f3c43016f2ea7a7d0b998f64203b8e9181206b296fd98b3d7a2e0afa76959d"
};
export const RELEASE_SECURITY_GATES = [
 {id:"distinctSidAuthenticated",label:"Distinct Windows SID and cross-account token test",role:"identity"},
 {id:"externalRoleTokenOrAclProof",label:"Protected Host ACL / role-token isolation",role:"identity"},
 {id:"roleSeparationAccepted",label:"Independent role-separation acceptance",role:"identity"},
 {id:"ownerSigned",label:"External Owner authorization and signature",role:"authority"},
 {id:"witnessIndependent",label:"Independent off-host Witness",role:"authority"},
 {id:"fencedGlobalCasValidated",label:"Global fenced epoch CAS",role:"authority"},
 {id:"nativeWorkerV2Admitted",label:"Commissioned Native Worker V2 identity",role:"authority"},
 {id:"portableRuntimeDllClosure",label:"Relocatable Python/Node and complete DLL closure",role:"release"},
 {id:"nativeTauri2ExeBuilt",label:"Actual Tauri 2 Windows application",role:"release"},
 {id:"nativeTauri2WindowTested",label:"Native Tauri GUI acceptance",role:"release"},
 {id:"publisherSigningAvailable",label:"Publisher code-signing acceptance",role:"release"},
 {id:"approvedOriginalStudioIconAssetVerified",label:"Previously approved Studio icon verified",role:"release"},
 {id:"componentManagerReleaseAccepted",label:"Signed Component Manager release",role:"release"},
] as const;
const REQUIRED_MODULES=["framework_core","host_api","orchestrator","orion","governor",
  "native_worker_v2","asset_labs","fidelity_evidence","component_manager"];
const isObject=(x:unknown):x is Record<string,unknown> => x!==null && typeof x==="object" && !Array.isArray(x);
const sameKeys=(x:Record<string,unknown>,list:string[])=>Object.keys(x).sort().join("|")===list.slice().sort().join("|");
export function validateHostSecurity(raw:unknown):raw is HostSecurityReport {
  if(!isObject(raw) || raw.schema!=="OpenRemaster.StudioHostSecurityReadiness.v1" ||
      raw.release!=="ORF-STUDIO-UI-20261018-r5" ||
      raw.sourceMode!=="PINNED_LOCAL_WINDOWS_SAME_USER_PIPE_TEST" ||
      raw.sourceAuthority!=="LOCAL_TEST_NO_EXTERNAL_ATTESTATION" ||
      raw.status!=="SAME_USER_IMPERSONATION_TESTED_PRODUCTION_HOLD" ||
      raw.host!=="HomePC" || typeof raw.generatedUtc!=="string" ||
      !Number.isFinite(Date.parse(raw.generatedUtc)) ||
      typeof raw.qualifier!=="string" || raw.qualifier.length>700 ||
      !isObject(raw.sourcePins) || !isObject(raw.osProof) ||
      !isObject(raw.installReadiness) || !isObject(raw.authority)) return false;
  const sourcePins=raw.sourcePins;
  if(!sameKeys(sourcePins,Object.keys(pins)) ||
      Object.entries(pins).some(([k,v])=>sourcePins[k]!==v || !sha.test(v))) return false;
  const os=raw.osProof;
  const expectedOs:Record<string,unknown>={
    windowsNamedPipe:true,currentUserOnly:true,
    sameUserImpersonationObserved:true,clientSidComparedInternally:true,
    clientSidPersisted:false,distinctSidAuthenticated:false,
    externalRoleTokenOrAclProof:false,roleSeparationAccepted:false,
    testCount:16,testFailures:0,testStatus:"PASS",oneShotNoPersistentListener:true,
  };
  if(!sameKeys(os,Object.keys(expectedOs)) ||
    Object.entries(expectedOs).some(([key,value])=>os[key]!==value)) return false;
  const install=raw.installReadiness;
  if(install.requiredComponentCount!==9 || install.installedComponentCount!==0 ||
    install.componentManagerReleaseAccepted!==false ||
    install.portableRuntimeDllClosure!==false || install.nodePythonTransitiveImportsVerified!==false ||
    install.nativeTauri2ExeBuilt!==false || install.nativeTauri2WindowTested!==false ||
    install.cargoAvailableInCurrentPath!==false || install.publisherSigningAvailable!==false ||
    install.approvedOriginalStudioIconAssetVerified!==false ||
    install.installerCreated!==false || install.oneInstallerIdentity!=="OpenRemasterStudio-Setup-x64.exe" ||
    !Array.isArray(install.requiredComponents) ||
    !sameKeys(Object.fromEntries(install.requiredComponents.map((k:string)=>[k,true])),REQUIRED_MODULES) ||
    install.requiredComponents.length!==9) return false;
  const auth=raw.authority;
  if(!sameKeys(auth,["ownerSigned","witnessIndependent","fencedGlobalCasValidated",
      "nativeWorkerV2Admitted","modelInvocationAllowed","jobDispatchAllowed",
      "newSchedulerCreated","automaticRetry","productionAdmission","unknownOutcome"])) return false;
  return auth.ownerSigned===false && auth.witnessIndependent===false &&
    auth.fencedGlobalCasValidated===false && auth.nativeWorkerV2Admitted===false &&
    auth.modelInvocationAllowed===false && auth.jobDispatchAllowed===false &&
    auth.newSchedulerCreated===false && auth.automaticRetry===false &&
    auth.productionAdmission==="HOLD" && auth.unknownOutcome==="HOLD_NO_AUTO_RETRY";
}
export function hostSecurityView(raw:unknown) {
  if(!validateHostSecurity(raw)) return {phase:"HOLD" as const,code:"INVALID_PINNED_EVIDENCE",data:null};
  return {phase:"TESTED_SAME_USER_ONLY" as const,code:"PRODUCTION_HOLD_ROLE_SEPARATION_UNVERIFIED",data:raw};
}
