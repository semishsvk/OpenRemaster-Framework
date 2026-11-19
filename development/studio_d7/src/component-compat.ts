/**
 * UI-011 / Component compatibility & witness receipts.
 * Local, deterministic NO-GO validator. A passing structure is never a
 * positive authorisation. No runtime API, installer, signer or native IPC.
 */
import r9Baseline from "./data/snapshot-r9-baseline.json" with { type: "json" };

export const COMPONENTS = [
 "framework_core","host_api","orchestrator","orion","governor",
 "native_worker_v2","asset_labs","fidelity_evidence","component_manager"
] as const;
export type ComponentId = typeof COMPONENTS[number];
export const REQUIRED_PROTOCOLS=["R6","R10","R11","K003","NativeWorkerV2"] as const;
export type CompatibilityEntry={
 id:ComponentId;title:string;sourceMaturity:string;
 historicalSourcePresent:boolean;sourceSha256:string|null;
 localReleaseLabel:string|null;required:true;
 isolatedProcessPlanned:true;launchPolicy:"on_demand"|"disabled_pending_external_trust";
 publisherSignedBinaryVerified:false;canonicalVersionContractVerified:false;
 componentProtocolBindingsVerified:false;componentBinaryInstalledVerified:false;
 componentHealthCheckPassed:false;externalOwnerDeploymentApproval:false;
 missingEvidence:string[];
 readiness:"SOURCE_OBSERVED_ONLY"|"SOURCE_OWNER_UNRESOLVED";
 productionCanLaunch:false;
};
export type CompatibilityReport={
 schema:"OpenRemaster.StudioComponentCompatibilityReadiness.v1";
 release:"ORF-STUDIO-UI-20261018-r10";generatedUtc:string;
 status:"COMPONENT_SOURCE_MATRIX_AND_R15_WITNESS_RESEARCH_PASS__DEPLOYMENT_NO_GO";
 authority:"LOCAL_UNSIGNED_HASH_ONLY_NOT_PUBLISHER_OWNER_WITNESS";
 sourcePins:Record<string,string>;
 package:{
  architecture:"One Installer · Complete Platform · Modular Runtime";
  plannedSetup:"OpenRemasterStudio-Setup-x64.exe";
  plannedApp:"OpenRemasterStudio.exe";
  iconPolicy:"EXISTING_APPROVED_ICON_ONLY_NOT_VERIFIED";
  mandatoryComponentCount:9;sourcePresentCount:8;sourceUnresolvedCount:1;
  componentVersionContractsVerified:0;componentSignedBinariesVerified:0;
  componentInstalledReceiptsVerified:0;componentHealthChecksAccepted:0;
  componentApprovedForExecution:0;
  globalRequiredProtocolCount:5;globalProtocolBindingsVerified:0;
  globalRequiredProtocols:string[];
  perComponentDependencyEdgesEstablished:false;
  perComponentVersionCatalogProvided:false;
  minimumWindowsArchitecture:"AMD64";
  unknownVersionPolicy:"HOLD";
  downgradePolicy:"DENY";
  unknownOutcome:"HOLD_NO_AUTORETRY";
  atomicStagingDesignRequired:true;
  rollbackOnFailedHealthcheckDesignRequired:true;
  actualSignedInstallerBuilt:false;actualNativeTauriBuildPassed:false;
  approvedIconFileVerified:false;installPermitted:false;canStartAnyWorker:false;
 };
 components:CompatibilityEntry[];
 compatibilityDryRun:{
  status:"NO_SIGNED_COMPONENT_VERSION_CATALOG";canInstall:false;
  versionClaimsCount:0;approvedVersionContracts:0;
 };
 signedWitnessR15:{
  source:"OrchestratorSignedWitnessBoundary-20261018-r15";
  reviewKind:"SAME_ASSISTANT_SOURCE_AND_SYNTHETIC_TEST_ONLY";
  historicalNegativeFirstTests:85;historicalSyntheticReceiptScenarios:21;sourceHashRoles:15;
  wireEnvelope:"OFFLINE_DETACHED_ES256_SHAPE_ONLY_NO_GO";
  proposedAlgorithm:"ES256_P256_SHA256";
  newReceiptCryptographicallyVerified:false;nativeProviderBlocked:true;
  blockedNativeOracleRetried:false;independentlyAnchoredPublisherKey:false;
  currentSignedWitnessHighwaterVerified:false;globalFencedCASVerified:false;
  signedProductionOwnerAdmitted:false;stageAApproved:false;stageBApproved:false;
  stageCApproved:false;productionReceiptAccepted:false;
  permissionNow:"HOLD_NO_AUTO_RETRY";
 };
 releaseDecision:{
  status:"NO_GO";manualExternalA_B_CStillRequired:true;
  studioIconNotReplaced:true;separateWindowsSidTokenProofMissing:true;
  completeNodePythonDllShippingUnverified:true;
  assetLabsCanonicalOwnerUnresolved:true;
  productionSignedComponentCatalogMissing:true;
  realNativeProductionHostNotConnected:true;originalGamesUntouched:true;
  singleWriterDesignPreserved:true;maxGlobalHeavySlots:3;
  autoRetry:false;dispatch:false;install:false;
 };
};
const sha=/^[0-9a-f]{64}$/;
const pinnedModuleNames=new Map(r9Baseline.modules.map(m=>[m.id,m]));
const pins={
 parentR9Zip:"e78881f755c0450ced6a23de83a883fb78e164ce27ea4c62e494f806d1dc83b0",
 originalR9Snapshot:"03ed3fed73705dd12c7fd836de8079cd01d4afc3256fec687749178668acdffa",
 packagingPlanV1:"d0334dd29dc77e5c12149658c006263f41f2353e93242e9949c8340da64bf775",
 r15Checkpoint:"4bc244390aa1fb4e38541d5057480f1e296dd587618dd779af96a781e99cffaa",
 r15WireContract:"b91158517ac16bf5798044e09e011ec20b0b990cdc41c1000b12aba80e0a5e7a"
};
export const PER_COMPONENT_MISSING=[
 "PUBLISHER_SIGNED_BINARY","VERSION_BINDING","PROTOCOL_BINDINGS",
 "PROTECTED_INSTALL_RECEIPT","HEALTH_PROOF","EXTERNAL_OWNER_WITNESS"
] as const;
const isObj=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==="object"&&!Array.isArray(v);
const same=(a:Record<string,unknown>,b:Record<string,unknown>)=>
 Object.keys(a).sort().join("|")===Object.keys(b).sort().join("|") &&
 Object.entries(b).every(([k,v])=>a[k]===v);
const str=(v:unknown,n:number)=>typeof v==="string"&&v.length>0&&v.length<=n;
function validEntry(row:unknown,i:number):row is CompatibilityEntry{
 if(!isObj(row))return false;
 const observed=row.historicalSourcePresent;
 const id=COMPONENTS[i];
 const frozen=pinnedModuleNames.get(id);
 if(!frozen || row.title!==frozen.title || row.sourceMaturity!==frozen.maturity ||
   row.historicalSourcePresent!==frozen.sourcePresent ||
   row.sourceSha256!==frozen.sourceSha256 ||
   row.localReleaseLabel!==(frozen.release||null) ||
   row.id!==id || !str(row.title,120) || !str(row.sourceMaturity,100) ||
   typeof observed!=="boolean" ||
   (observed ? !(typeof row.sourceSha256==="string"&&sha.test(row.sourceSha256)) :
    row.sourceSha256!==null) ||
   !(row.localReleaseLabel===null || str(row.localReleaseLabel,150)) ||
   !Array.isArray(row.missingEvidence) ||
   row.missingEvidence.join("|")!==PER_COMPONENT_MISSING.join("|") )return false;
 const expected={
  id,required:true,isolatedProcessPlanned:true,
  launchPolicy:id==="native_worker_v2"?"disabled_pending_external_trust":"on_demand",
  publisherSignedBinaryVerified:false,canonicalVersionContractVerified:false,
  componentProtocolBindingsVerified:false,componentBinaryInstalledVerified:false,
  componentHealthCheckPassed:false,externalOwnerDeploymentApproval:false,
  readiness:observed?"SOURCE_OBSERVED_ONLY":"SOURCE_OWNER_UNRESOLVED",
  productionCanLaunch:false
 };
 const fields=Object.fromEntries(Object.entries(row).filter(([k])=>
  !["title","sourceMaturity","historicalSourcePresent","sourceSha256",
    "localReleaseLabel","missingEvidence"].includes(k)));
 return same(fields,expected);
}
export function validateCompatibility(raw:unknown):raw is CompatibilityReport{
 if(!isObj(raw)||raw.schema!=="OpenRemaster.StudioComponentCompatibilityReadiness.v1" ||
   raw.release!=="ORF-STUDIO-UI-20261018-r10" ||
   raw.status!=="COMPONENT_SOURCE_MATRIX_AND_R15_WITNESS_RESEARCH_PASS__DEPLOYMENT_NO_GO" ||
   raw.authority!=="LOCAL_UNSIGNED_HASH_ONLY_NOT_PUBLISHER_OWNER_WITNESS" ||
   typeof raw.generatedUtc!=="string" || !Number.isFinite(Date.parse(raw.generatedUtc)) ||
   !isObj(raw.sourcePins)||!isObj(raw.package)||!isObj(raw.compatibilityDryRun)||
   !isObj(raw.signedWitnessR15)||!isObj(raw.releaseDecision)||
   !Array.isArray(raw.components)||raw.components.length!==9) return false;
 if(!same(raw.sourcePins,pins) ||
   raw.components.filter((c:unknown)=>isObj(c)&&c.historicalSourcePresent===true).length!==8 ||
   !raw.components.every(validEntry))return false;
 const pkg=raw.package;
 const expectedPackage={
  architecture:"One Installer · Complete Platform · Modular Runtime",
  plannedSetup:"OpenRemasterStudio-Setup-x64.exe",
  plannedApp:"OpenRemasterStudio.exe",
  iconPolicy:"EXISTING_APPROVED_ICON_ONLY_NOT_VERIFIED",
  mandatoryComponentCount:9,sourcePresentCount:8,sourceUnresolvedCount:1,
  componentVersionContractsVerified:0,componentSignedBinariesVerified:0,
  componentInstalledReceiptsVerified:0,componentHealthChecksAccepted:0,
  componentApprovedForExecution:0,globalRequiredProtocolCount:5,
  globalProtocolBindingsVerified:0,
  perComponentDependencyEdgesEstablished:false,
  perComponentVersionCatalogProvided:false,minimumWindowsArchitecture:"AMD64",
  unknownVersionPolicy:"HOLD",downgradePolicy:"DENY",
  unknownOutcome:"HOLD_NO_AUTORETRY",
  atomicStagingDesignRequired:true,rollbackOnFailedHealthcheckDesignRequired:true,
  actualSignedInstallerBuilt:false,actualNativeTauriBuildPassed:false,
  approvedIconFileVerified:false,installPermitted:false,canStartAnyWorker:false
 };
 const {globalRequiredProtocols,...pHeader}=pkg;
 if(!same(pHeader,expectedPackage) || !Array.isArray(globalRequiredProtocols) ||
   globalRequiredProtocols.join("|")!==REQUIRED_PROTOCOLS.join("|"))return false;
 if(!same(raw.compatibilityDryRun,{
  status:"NO_SIGNED_COMPONENT_VERSION_CATALOG",canInstall:false,
  versionClaimsCount:0,approvedVersionContracts:0
 }))return false;
 const witness={
  source:"OrchestratorSignedWitnessBoundary-20261018-r15",
  reviewKind:"SAME_ASSISTANT_SOURCE_AND_SYNTHETIC_TEST_ONLY",
  historicalNegativeFirstTests:85,historicalSyntheticReceiptScenarios:21,
  sourceHashRoles:15,wireEnvelope:"OFFLINE_DETACHED_ES256_SHAPE_ONLY_NO_GO",
  proposedAlgorithm:"ES256_P256_SHA256",
  newReceiptCryptographicallyVerified:false,nativeProviderBlocked:true,
  blockedNativeOracleRetried:false,independentlyAnchoredPublisherKey:false,
  currentSignedWitnessHighwaterVerified:false,globalFencedCASVerified:false,
  signedProductionOwnerAdmitted:false,stageAApproved:false,stageBApproved:false,
  stageCApproved:false,productionReceiptAccepted:false,permissionNow:"HOLD_NO_AUTO_RETRY"
 };
 const release={
  status:"NO_GO",manualExternalA_B_CStillRequired:true,studioIconNotReplaced:true,
  separateWindowsSidTokenProofMissing:true,completeNodePythonDllShippingUnverified:true,
  assetLabsCanonicalOwnerUnresolved:true,
  productionSignedComponentCatalogMissing:true,realNativeProductionHostNotConnected:true,
  originalGamesUntouched:true,singleWriterDesignPreserved:true,maxGlobalHeavySlots:3,
  autoRetry:false,dispatch:false,install:false
 };
 return same(raw.signedWitnessR15,witness)&&same(raw.releaseDecision,release)&&
  Object.keys(raw).length===11;
}
export function compatibilityView(raw:unknown){
 return validateCompatibility(raw)
   ? {status:"NO_GO" as const,kind:"SOURCE_BOUND_PLAN_ONLY" as const,data:raw}
   : {status:"NO_GO" as const,kind:"SOURCE_DRIFT_HOLD" as const,data:null};
}
/** Read-only, explicitly hypothetical local preflight. NEVER enables install. */
export function evaluateWhatIf(report:CompatibilityReport,assumeSources:boolean){
 const sourceCount=assumeSources?9:report.package.sourcePresentCount;
 const missingSource=9-sourceCount;
 return {
  status:"NO_GO" as const,
  sourceCount,missingSource,
  unsignedComponents:9,
  unknownVersionContracts:9,
  unverifiedProtocolBindings:report.package.globalRequiredProtocolCount,
  independentOwner:false,
  canInstall:false,
  note:assumeSources
    ?"HYPOTHETICAL SOURCE PRESENCE ONLY — no binaries, compatibility or signatures are inferred."
    :"Grounded in frozen original Studio r9 source observations."
 };
}
