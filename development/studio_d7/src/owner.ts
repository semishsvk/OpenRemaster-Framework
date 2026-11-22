/** Frozen external Owner/Witness r8 checkpoint as non-authoritative evidence.
 * A same-machine timestamp or local SHA never makes a release signed/admitted.
 */
export type OwnerReview = {
  schema: "OpenRemaster.OwnerWitnessEvidenceReviewCheckpoint.v8";
  status: "ISOLATED_STRUCTURAL_AND_K003_SHADOW_PASS_PRODUCTION_HOLD";
  review: "SAME_ASSISTANT_ISOLATED_TEST_ONLY";
  created_host_clock_not_external_signer: string;
  next: "EXTERNAL_OWNER_APPROVED_CUSTODY_AND_WITNESS_PROVIDER_ADMISSION";
  gateway_task: "Running"; native_task: "Disabled";
  independent_owner_acceptance: false; offhost_current_witness_validated: false;
  owner_signature_validated: false; global_fenced_epoch_CAS_validated: false;
  may_dispatch: false; may_install: false; may_acquire_lease: false; may_auto_retry: false;
  original_k003_modified: false; original_game_runtime_started: false;
  real_native_worker_started: false; new_scheduler_created: false;
  blocked_NW020_gate_retried: false;
  new_regression_tests_passed: 86;
  real_synthetic_windows_K003_process_scenarios: 6;
  source_roles_sha_verified: 9;
  pending: 0; running: 0;
  package_manifest_sha256: string; parent_r7_zip_sha256: string;
  r7_candidate_sha256: string; source_manifest_sha256: string;
};
const SHA=/^[0-9a-f]{64}$/;
const safeUTC=(value: unknown) => typeof value==="string" &&
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00$/.test(value) &&
  Number.isFinite(Date.parse(value));
const isObject=(x:unknown):x is Record<string,unknown> =>
  !!x && typeof x==="object" && !Array.isArray(x);
const falseGates=[
  "independent_owner_acceptance", "offhost_current_witness_validated",
  "owner_signature_validated", "global_fenced_epoch_CAS_validated",
  "may_dispatch","may_install","may_acquire_lease","may_auto_retry",
  "original_k003_modified","original_game_runtime_started",
  "real_native_worker_started","new_scheduler_created",
  "blocked_NW020_gate_retried",
];
export const OWNER_GATES = [
  { id:"independent_owner_acceptance", label:"External Owner approval" },
  { id:"owner_signature_validated", label:"Validated Owner signature" },
  { id:"offhost_current_witness_validated", label:"Independent current off-host Witness" },
  { id:"global_fenced_epoch_CAS_validated", label:"Global fenced epoch/CAS proof" },
] as const;
export function validateOwnerReview(raw:unknown):raw is OwnerReview {
  if(!isObject(raw) ||
    raw.schema!=="OpenRemaster.OwnerWitnessEvidenceReviewCheckpoint.v8" ||
    raw.status!=="ISOLATED_STRUCTURAL_AND_K003_SHADOW_PASS_PRODUCTION_HOLD" ||
    raw.review!=="SAME_ASSISTANT_ISOLATED_TEST_ONLY" ||
    raw.next!=="EXTERNAL_OWNER_APPROVED_CUSTODY_AND_WITNESS_PROVIDER_ADMISSION" ||
    raw.gateway_task!=="Running" || raw.native_task!=="Disabled" ||
    !safeUTC(raw.created_host_clock_not_external_signer) ||
    falseGates.some(k=>raw[k]!==false) ||
    raw.new_regression_tests_passed!==86 ||
    raw.real_synthetic_windows_K003_process_scenarios!==6 ||
    raw.source_roles_sha_verified!==9 ||
    raw.pending!==0 || raw.running!==0 ||
    !["package_manifest_sha256","parent_r7_zip_sha256","r7_candidate_sha256","source_manifest_sha256"].every(k=>
      typeof raw[k]==="string" && SHA.test(raw[k]))) return false;
  return Object.keys(raw).length===29;
}
export function ownerView(raw:unknown) {
  const evidence=validateOwnerReview(raw)?raw:null;
  return {
    status:"HOLD" as const,
    authority:"UNSIGNED_LOCAL_REVIEW_ONLY" as const,
    historical:true,
    ownerSigned:false,
    witnessOffHost:false,
    canDispatch:false,
    runningObservedNow:false,
    sourceEvidence:evidence,
  };
}
