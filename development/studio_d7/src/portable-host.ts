/** Studio UI-009: source-bound NW025-AC/AD/V bridge, never runnable in browser.
 * AC verified offline source paths and test suites. AD exercised Windows
 * synthetic Node->Python. Neither is a signed production Host/Owner.
 */
export type PortableEvidence={
 schema:"OpenRemaster.StudioPortableHostEvidence.v1";
 releaseId:"ORF-STUDIO-UI-20261018-r8";generatedUtc:string;
 status:"PORTABLE_BINDINGS_AND_SYNTHETIC_TRANSPORT_SOURCE_VERIFIED_PRODUCTION_HOLD";
 sourceAuthority:"UNSIGNED_LOCAL_SHA256_IS_NOT_OWNER_OR_PUBLISHER_AUTHENTICATION";
 sourcePins:Record<string,string>;
 host:{
   proof:"NW025-AC_OFFLINE_RELOCATION_AND_EXECUTABLE_BINDING";
   originalRegressionCount:188;pythonTests:118;nodeTests:70;
   regressionGroups:{name:string;tests:number}[];
   negativeCases:7;emptyExecutableNegativeCases:2;
   runtimeManifestFiles:759;pythonRuntimeFiles:757;nodeRuntimeFiles:2;
   runtimeManifestFilesReadOnlyRehashed:759;runtimeManifestBytesReadOnlyRehashed:127210300;
   candidatePinsVerifiedByAC:849;
   relativeRuntimePaths:true;noUserProvidedExecutablePath:true;
   noPathFallback:true;noRuntimeBinaryCopiedIntoStudio:true;
   installedPythonNodePathsUsedForRelocatedService:false;
   fullOfflineHostRerunWasNW025AC:true;
   liveProductionHostRPCs:0;ownerWitnessAuthenticated:false;
 };
 transport:{
  proof:"NW025-AD_ACTUAL_WIN32_JOB_OWNED_SYNTHETIC_NODE_PYTHON";
  windowsJobBoundedSyntheticInvocations:7;passed:7;sourcePinsRechecked:764;
  serviceKind:"SYNTHETIC_FIXTURE_NOT_REAL_INSPECTOR";
  processesBoundToJobBeforeResume:true;killOnCloseUsed:true;
  testProcessCap:6;
  testCases:{mode:string;passed:true;processChain:string;allRecordedTestProcessesStopped:true;status:string}[];
  allRecordedTestProcessesStopped:true;liveInspectorRPCs:0;
  originalGamesTouched:false;canExecuteProductionJobs:false;
 };
 nodeProposedShippingSubset:{
   nodeExecutable:"node.exe";license:"LICENSE";licenseExactVersionMatched:true;
   npmProposed:false;npxProposed:false;corepackProposed:false;
   sourceProposalAcceptedForProduction:false;
   independentLicenseReviewDone:false;
 };
 deployment:{
  sourceRuntimeClosureInTestedACContext:true;
  authenticRealInspectorPortabilityTested:false;
  separateCleanWindowsMachineTested:false;
  transitiveDynamicDllShippingAcceptance:false;
  completeLegalRedistributionApproval:false;
  externalSignerOwnerWitnessApproved:false;
  studioTauri2ExeBuilt:false;approvedExistingStudioIconFileVerified:false;
  signedOneInstallerBuilt:false;runtimeConfigProductionAdmitted:false;
  jobDispatchAllowed:false;automaticRetry:false;status:"HOLD_NO_AUTO_RETRY";
 };
};
const fixedSourcePins={
 parentR7ZipSha256:"aca85e09eac5961a765d6e416e7fb32a3ff0caf27666905ee753f88d116b54a6",
 acSourceZipSha256:"b35c5dc790d0314619a106612a8c734069e1d4cbf67eca37b64da5ec9471c040",
 adSourceZipSha256:"399b3c210418090fb0337d14c2bfb7ced20752e538f5fadf1fa176226a324bfa",
 acRuntimeManifestSha256:"2544a185765586b53d500cb83d7719c0cef48080d81a5b8c171306046c5a5749",
 nodeProposal:"ffe343d59f88a1b1ced30863f8c7d225e31dad004fdf6905b3c3671e2c5a353a",
 portableRegression:"9a285594ac3cc0440da9c937c51077a8450bc63e808f942e9135fa26c952ff60",
 portableNegative:"d7fedae5a2b6c841646cb4253d51140a08be5d443fc79f6817d58ac92020f25c",
 portablePackageReceipt:"2ca2ed88e19183701ba9db6417859bfd349d2d3c18d2b1702db4fccf60894e63",
 transportResult:"2d1b9f3b33ad3622eb76f386a0ea71f05df9ba753127160f7b301b6ca05809ce",
 transportReceipt:"35de0c2e0dfffd42a7afe6c8988f94434a80e31ae98d952fa4f371424ede539f",
 transportCases:"b17e840def0de13a9e0c7359a25f687ce5b6f8722a8935ef9e3ab29c22ec7a67"
};
export const PORTABLE_TEST_GROUPS=[
 {name:"host_contract",tests:23},{name:"inspector_api",tests:28},
 {name:"registry_adapter",tests:27},{name:"cache",tests:28},
 {name:"original_registry",tests:12},{name:"session",tests:23},
 {name:"bridge",tests:16},{name:"consumer",tests:31}
] as const;
export const SYNTHETIC_CASES=[
 {mode:"success",status:"EXITED"},
 {mode:"wrong_id",status:"EXITED"},
 {mode:"stderr",status:"EXITED"},
 {mode:"nonzero",status:"EXITED"},
 {mode:"duplicate",status:"EXITED"},
 {mode:"timeout",status:"JOB_TIMEOUT_HOLD"},
 {mode:"orphan",status:"JOB_DESCENDANT_SURVIVED_PARENT_HOLD"}
] as const;
const asObj=(x:unknown):x is Record<string,unknown>=>x!==null&&typeof x==="object"&&!Array.isArray(x);
function fields(actual:Record<string,unknown>,reference:Record<string,unknown>):boolean{
 return Object.keys(actual).sort().join("|")===Object.keys(reference).sort().join("|") &&
   Object.entries(reference).every(([name,value])=>actual[name]===value);
}
export function validatePortableHost(raw:unknown):raw is PortableEvidence{
 if(!asObj(raw)||raw.schema!=="OpenRemaster.StudioPortableHostEvidence.v1" ||
   raw.releaseId!=="ORF-STUDIO-UI-20261018-r8" ||
   raw.status!=="PORTABLE_BINDINGS_AND_SYNTHETIC_TRANSPORT_SOURCE_VERIFIED_PRODUCTION_HOLD" ||
   raw.sourceAuthority!=="UNSIGNED_LOCAL_SHA256_IS_NOT_OWNER_OR_PUBLISHER_AUTHENTICATION" ||
   typeof raw.generatedUtc!=="string" || !Number.isFinite(Date.parse(raw.generatedUtc)) ||
   !asObj(raw.sourcePins)||!asObj(raw.host)||!asObj(raw.transport)||
   !asObj(raw.nodeProposedShippingSubset)||!asObj(raw.deployment))return false;
 if(!fields(raw.sourcePins,fixedSourcePins))return false;
 const h=raw.host;
 const expectedHost={
  proof:"NW025-AC_OFFLINE_RELOCATION_AND_EXECUTABLE_BINDING",
  originalRegressionCount:188,pythonTests:118,nodeTests:70,
  negativeCases:7,emptyExecutableNegativeCases:2,
  runtimeManifestFiles:759,pythonRuntimeFiles:757,nodeRuntimeFiles:2,
  runtimeManifestFilesReadOnlyRehashed:759,runtimeManifestBytesReadOnlyRehashed:127210300,
  candidatePinsVerifiedByAC:849,relativeRuntimePaths:true,
  noUserProvidedExecutablePath:true,noPathFallback:true,
  noRuntimeBinaryCopiedIntoStudio:true,
  installedPythonNodePathsUsedForRelocatedService:false,
  fullOfflineHostRerunWasNW025AC:true,
  liveProductionHostRPCs:0,ownerWitnessAuthenticated:false
 };
 const {regressionGroups,...hRest}=h;
 if(!fields(hRest,expectedHost)||!Array.isArray(regressionGroups) ||
   regressionGroups.length!==PORTABLE_TEST_GROUPS.length ||
   !regressionGroups.every((g:unknown,i)=>asObj(g)&& fields(g,{...PORTABLE_TEST_GROUPS[i]})))return false;
 const t=raw.transport;
 const expectedTransport={
  proof:"NW025-AD_ACTUAL_WIN32_JOB_OWNED_SYNTHETIC_NODE_PYTHON",
  windowsJobBoundedSyntheticInvocations:7,passed:7,sourcePinsRechecked:764,
  serviceKind:"SYNTHETIC_FIXTURE_NOT_REAL_INSPECTOR",
  processesBoundToJobBeforeResume:true,killOnCloseUsed:true,testProcessCap:6,
  allRecordedTestProcessesStopped:true,liveInspectorRPCs:0,
  originalGamesTouched:false,canExecuteProductionJobs:false
 };
 const {testCases,...tRest}=t;
 if(!fields(tRest,expectedTransport)||!Array.isArray(testCases)||
   testCases.length!==SYNTHETIC_CASES.length||
   !testCases.every((x:unknown,i)=>asObj(x) &&
     fields(x,{...SYNTHETIC_CASES[i],passed:true,
       processChain:"WINDOWS_JOB_OWNED_NODE_BRIDGE_TO_SYNTHETIC_PYTHON",
       allRecordedTestProcessesStopped:true})))return false;
 const proposed={
  nodeExecutable:"node.exe",license:"LICENSE",
  licenseExactVersionMatched:true,npmProposed:false,npxProposed:false,
  corepackProposed:false,sourceProposalAcceptedForProduction:false,
  independentLicenseReviewDone:false
 };
 const gates={
  sourceRuntimeClosureInTestedACContext:true,
  authenticRealInspectorPortabilityTested:false,
  separateCleanWindowsMachineTested:false,
  transitiveDynamicDllShippingAcceptance:false,
  completeLegalRedistributionApproval:false,
  externalSignerOwnerWitnessApproved:false,
  studioTauri2ExeBuilt:false,approvedExistingStudioIconFileVerified:false,
  signedOneInstallerBuilt:false,runtimeConfigProductionAdmitted:false,
  jobDispatchAllowed:false,automaticRetry:false,status:"HOLD_NO_AUTO_RETRY"
 };
 return fields(raw.nodeProposedShippingSubset,proposed)&&fields(raw.deployment,gates)&&
    Object.keys(raw).length===10;
}
export function portableView(raw:unknown){
 if(!validatePortableHost(raw))return {status:"HOLD" as const,data:null,code:"UNTRUSTED_PORTABLE_HOST_EVIDENCE"};
 return {status:"SOURCE_TESTED" as const,data:raw,code:"ACTUAL_SYNTHETIC_ONLY_PRODUCTION_HOLD"};
}
