/** Read-only projection, never an execution/admission authority.
 * Observations must come from the existing native Host adapter. Report text is
 * not a physical-file observation. Until that adapter is admitted this is SOURCE_ONLY.
 */
export type ProjectPhase = 'LIVE' | 'ARCHIVED' | 'UNKNOWN' | 'HOLD';
export type Gate = 'PASS' | 'FAIL' | 'HOLD' | 'BLOCKED' | 'UNKNOWN';
export type Identity = Readonly<{project: string; edition: string}>;
export type SourceCheckpoint = Identity & Readonly<{
  checkpoint: string; commit: string; tree: string;
}>;
export type Artifact = Readonly<{
  role: 'EXE' | 'PCK'; path: string; sha256: string;
}>;
export type Build = Identity & Readonly<{
  id: string; commit: string; tree: string; engine: string;
  artifacts: readonly Artifact[]; requiresPck: boolean;
}>;
export type PhysicalObservation = Identity & Readonly<{
  buildId: string; role: 'EXE' | 'PCK'; path: string;
  exists: boolean; sha256: string | null; checkedAt: number;
  source: 'NATIVE_FILE_READ';
}>;
export type Verification = Identity & Readonly<{
  buildId: string; commit: string; tree: string;
  artifactHashes: readonly string[]; evidenceSha256: string;
  status: Gate; complete: boolean; checkedAt: number;
}>;
export type ProjectInput = Identity & Readonly<{
  archived: boolean; capturedAt: number;
  origin: 'HOST_READONLY' | 'ARCHIVED_REPORT';
  sourceCheckpoint: SourceCheckpoint | null; build: Build | null;
  observations: readonly PhysicalObservation[];
  gameplay: Verification | null; fidelity: Verification | null;
  writers: readonly string[]; admission: Gate;
  blockers: readonly string[]; nextSafeTask: string | null;
}>;
export type ProjectState = Readonly<{
  project: string; edition: string; phase: ProjectPhase;
  sourceCheckpoint: SourceCheckpoint | null; playableBuild: Build | null;
  gameplay: Gate; fidelity: Gate; writer: string | null;
  executionAdmission: Gate; lastVerifiedAt: number | null;
  blockers: readonly string[]; nextSafeTask: string | null;
  readOnly: true; executionAuthority: false;
}>;
const sha = (x: string) => /^[a-f0-9]{64}$/.test(x);
const git = (x: string) => /^[a-f0-9]{40}$/.test(x);
const fresh = (at: number, now: number, ttl: number) =>
  Number.isFinite(at) && at <= now && now - at <= ttl;
const same = (a: Identity, b: Identity) =>
  a.project === b.project && a.edition === b.edition;
function frozen<T>(value: T): T {
  if (value && typeof value === 'object') {
    for (const item of Object.values(value)) frozen(item);
    Object.freeze(value);
  }
  return value;
}
/** Millisecond timestamps, injected clock, no I/O, no lease mutation or dispatch.
 * LIVE means recent Host observation; playable/gameplay/fidelity remain separate.
 */
export function projectState(input: ProjectInput, now: number, ttl = 10_000): ProjectState {
  if (!Number.isFinite(now) || !Number.isFinite(ttl) || ttl <= 0 || ttl > 10_000)
    throw Error('INVALID_FRESHNESS_POLICY');
  // Own the returned objects; callers cannot mutate the projection after validation.
  const p: ProjectInput = structuredClone(input);
  const reasons = [...p.blockers];
  const recent = fresh(p.capturedAt, now, ttl);
  let invalid = false;
  const reject = (reason: string) => { reasons.push(reason); invalid = true; };
  const source = p.sourceCheckpoint;
  if (source && (!same(p, source) || !git(source.commit) || !git(source.tree)))
    reject('SOURCE_IDENTITY_MISMATCH');
  if (p.writers.length > 1) reject('CONFLICTING_WRITER_LEASES');
  if (p.admission === 'FAIL' || p.admission === 'HOLD' || p.admission === 'BLOCKED')
    reject('EXECUTION_' + p.admission);
  let physical = false;
  const b = p.build;
  const verifiedTimes: number[] = [];
  if (b) {
    if (!same(p, b) || !git(b.commit) || !git(b.tree) || !b.id || !b.engine ||
        !source || source.commit !== b.commit || source.tree !== b.tree)
      reject('BUILD_SOURCE_IDENTITY_MISMATCH');
    const roles = b.artifacts.map(a => a.role);
    if (roles.filter(r => r === 'EXE').length !== 1 ||
        (b.requiresPck && roles.filter(r => r === 'PCK').length !== 1) ||
        roles.filter(r => r === 'PCK').length > 1 ||
        new Set(b.artifacts.map(a => a.path.toLowerCase())).size !== b.artifacts.length)
      reject('BUILD_ARTIFACT_SET_INVALID');
    physical = b.artifacts.length > 0;
    for (const artifact of b.artifacts) {
      const matches = p.observations.filter(o => same(p, o) && o.buildId === b.id &&
        o.path === artifact.path && o.role === artifact.role);
      const o = matches[0];
      if (!sha(artifact.sha256) || matches.length !== 1 || !o ||
          o.source !== 'NATIVE_FILE_READ' || !o.exists || o.sha256 !== artifact.sha256 ||
          !fresh(o.checkedAt, now, ttl)) {
        physical = false;
        reject('ARTIFACT_UNVERIFIED:' + artifact.role);
      } else verifiedTimes.push(o.checkedAt);
    }
  }
  const verification = (v: Verification | null): Gate => {
    if (!v) return 'UNKNOWN';
    if (!b || !physical || !same(p, v) || v.buildId !== b.id ||
        v.commit !== b.commit || v.tree !== b.tree || !sha(v.evidenceSha256) ||
        !fresh(v.checkedAt, now, ttl) || !v.complete ||
        v.artifactHashes.length !== b.artifacts.length ||
        new Set(v.artifactHashes).size !== v.artifactHashes.length ||
        b.artifacts.some(a => !v.artifactHashes.includes(a.sha256))) return 'HOLD';
    return v.status;
  };
  const phase: ProjectPhase = p.archived || p.origin === 'ARCHIVED_REPORT' ? 'ARCHIVED' :
    invalid || reasons.length > 0 ? 'HOLD' : recent ? 'LIVE' : 'UNKNOWN';
  if (!recent) reasons.push('STALE_OR_FUTURE_SNAPSHOT');
  const playable = phase === 'LIVE' && physical && !invalid;
  return frozen({project:p.project, edition:p.edition, phase,
    sourceCheckpoint:source, playableBuild:playable ? b : null,
    gameplay:phase === 'LIVE' ? verification(p.gameplay) : 'HOLD',
    fidelity:phase === 'LIVE' ? verification(p.fidelity) : 'HOLD',
    writer:p.writers.length === 1 ? p.writers[0] : null,
    // Displayed observation only; never a reusable execution grant.
    executionAdmission:phase === 'LIVE' ? p.admission : 'HOLD',
    lastVerifiedAt:playable ? Math.min(p.capturedAt, ...verifiedTimes) : null,
    blockers:[...new Set(reasons)], nextSafeTask:p.nextSafeTask,
    readOnly:true, executionAuthority:false});
}
