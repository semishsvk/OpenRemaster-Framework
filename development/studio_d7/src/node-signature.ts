/** HomePC Windows Authenticode confirmation for the PINNED Node 24.19.0 binary.
 * This is NOT a publisher signature of OpenRemaster Studio, owner authorization,
 * or the detached official release checksum index signature.
 */
export type NodeOSSignature={
 schema:"OpenRemaster.NodeWindowsAuthenticodeObservation.v1";
 version:"24.19.0";platform:"HomePC Windows x64";targetFileName:"node.exe";
 binarySha256:string;sourceReleaseArchiveSha256:string;
 signatureStatus:"Valid";signatureType:"Authenticode";
 signerSubject:string;signerThumbprint:string;
 timestampCertificatePresent:true;signedBinaryOSVerifiedOnHomePC:true;
 nodeDistributionIndexDetachedSignatureVerified:false;
 studioHostPublisherSignatureVerified:false;ownerWitnessSignerVerified:false;
 installerBuilt:false;automaticRetry:false;productionAdmission:"HOLD";
};
const EXPECTED={
 schema:"OpenRemaster.NodeWindowsAuthenticodeObservation.v1",
 version:"24.19.0", platform:"HomePC Windows x64", targetFileName:"node.exe",
 binarySha256:"3602f2bb1a10f2cbab4c36886218a33c1ab3db87290e73b033c46c77147d0237",
 sourceReleaseArchiveSha256:"57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73",
 signatureStatus:"Valid",signatureType:"Authenticode",
 signerSubject:"CN=OpenJS Foundation, O=OpenJS Foundation, L=San Francisco, S=California, C=US",
 signerThumbprint:"8ea1d142ea3f46023baca38c23a7e7ae6afce30c",
 timestampCertificatePresent:true,signedBinaryOSVerifiedOnHomePC:true,
 nodeDistributionIndexDetachedSignatureVerified:false,
 studioHostPublisherSignatureVerified:false,ownerWitnessSignerVerified:false,
 installerBuilt:false,automaticRetry:false,productionAdmission:"HOLD"
} as const;
export function validateNodeSignature(raw:unknown):raw is NodeOSSignature{
 if(!raw || typeof raw!=="object" || Array.isArray(raw))return false;
 const data=raw as Record<string,unknown>;
 return Object.keys(data).sort().join("|")===Object.keys(EXPECTED).sort().join("|") &&
  Object.entries(EXPECTED).every(([k,v])=>data[k]===v);
}
export function nodeSignatureView(raw:unknown){
 const valid=validateNodeSignature(raw);
 return valid ? {status:"OS_VALID_NODE_ONLY" as const,data:raw} :
   {status:"SIGNATURE_SOURCE_HOLD" as const,data:null};
}
