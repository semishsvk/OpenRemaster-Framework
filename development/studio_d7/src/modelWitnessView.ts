/** Read-only projection of reported model evidence, never an authority verifier. */
export type EvidenceContext = {
  project: string; proposalDigest: string; modelDigest: string;
  sourceManifestDigest: string; witnessDigest: string;
};
export type ModelWitnessView = {
  state: 'absent' | 'hold' | 'recorded'; title: string; detail: string;
  steps: number | null; references: readonly [string, string][];
};
const record = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);
const hash = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const disabled = (r: Record<string, unknown>, keys: string[]) => keys.every(k => r[k] === false);
const hold = (): ModelWitnessView => ({ state: 'hold', title: 'Model evidence on hold',
  detail: 'Missing, contradictory or mismatched evidence. Execution admission and production remain on hold.', steps: null, references: [] });

export function modelWitnessView(advisory: unknown, expected?: EvidenceContext): ModelWitnessView {
  if (advisory === undefined || advisory === null) return {
    state: 'absent', title: 'No model path evidence supplied',
    detail: 'Authentic runtime verification and execution admission remain pending.', steps: null, references: [] };
  if (!record(advisory) || !record(expected)) return hold();
  if (typeof expected.project !== 'string' || !expected.project.length || expected.project.length > 256 ||
      ![expected.proposalDigest, expected.modelDigest, expected.sourceManifestDigest, expected.witnessDigest].every(hash)) return hold();
  if (advisory.schema !== 'OpenRemaster.MasterAdvisoryPackage.v1' || advisory.project !== expected.project ||
      advisory.proposal_digest !== expected.proposalDigest || advisory.status !== 'HOLD_ADMISSION_REQUIRED' ||
      advisory.executor !== 'EXISTING_K003_ONLY' ||
      !disabled(advisory, ['may_dispatch','may_acquire_lease','may_sign','may_publish','production_go'])) return hold();
  // Future authority fields must never silently introduce an operational capability.
  if (Object.keys(advisory).some(k => k.startsWith('may_') && advisory[k] !== false)) return hold();
  if (!record(advisory.resource_request) || advisory.resource_request.heavy_slots !== 0 ||
      advisory.resource_request.max_global_heavy_slots !== 3) return hold();
  const authorities = advisory.required_authorities;
  if (!Array.isArray(authorities) || authorities.length !== 4 ||
      !['PROJECT_OWNER','WRITER_LEASE','K003','RESOURCE_GOVERNOR'].every(k => authorities.includes(k))) return hold();
  const o = advisory.model_witness_observation;
  if (!record(o) || o.schema !== 'OpenRemaster.RLR.ModelWitnessResult.v1' ||
      o.status !== 'STATIC_CANDIDATE' || o.scope !== 'SUPPLIED_DECLARATIVE_MODEL_ONLY' ||
      o.project !== expected.project || o.model_digest !== expected.modelDigest ||
      o.source_manifest_digest !== expected.sourceManifestDigest || o.witness_digest !== expected.witnessDigest ||
      !disabled(o, ['original_game_validated','native_roundtrip_verified','may_dispatch','may_release',
                    'may_sign','may_publish','may_promote','may_fallback']) ||
      Object.keys(o).some(k => k.startsWith('may_') && o[k] !== false) ||
      !hash(o.initial_state) || !hash(o.final_state) ||
      typeof o.steps_checked !== 'number' || !Number.isInteger(o.steps_checked) || o.steps_checked < 0 || o.steps_checked > 1024 ||
      typeof o.ending_id !== 'string' || !o.ending_id.length || o.ending_id.length > 128) return hold();
  return { state: 'recorded', title: 'Reported model path check', steps: o.steps_checked,
    detail: 'Recorded against a supplied declarative model. Authentic runtime verification and execution admission remain pending. Production on hold.',
    references: [['Project',expected.project],['Proposal',expected.proposalDigest],['Model',expected.modelDigest],
      ['Source manifest',expected.sourceManifestDigest],['Witness',expected.witnessDigest],
      ['Initial state',o.initial_state],['Final state',o.final_state],['Declared ending',o.ending_id]] };
}
