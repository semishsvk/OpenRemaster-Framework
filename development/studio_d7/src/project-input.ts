import type {Artifact, Build, Gate, Identity, PhysicalObservation, ProjectInput, SourceCheckpoint, Verification} from './unified-project-state';

type Obj = Record<string, unknown>;
const gates: readonly string[] = ['PASS', 'FAIL', 'HOLD', 'BLOCKED', 'UNKNOWN'];
const sha = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const git = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{40}$/.test(v);
const text = (v: unknown, limit: number): v is string => typeof v === 'string' && v.length > 0 && v.length <= limit && !/[\x00-\x1f\x7f]/.test(v);
function need(ok: unknown): asserts ok { if (!ok) throw Error('PROJECT_INPUT_INVALID'); }
function object(v: unknown, keys: readonly string[]): Obj {
  need(v !== null && typeof v === 'object' && !Array.isArray(v));
  const proto = Object.getPrototypeOf(v);
  need(proto === Object.prototype || proto === null);
  const names = Reflect.ownKeys(v);
  need(names.length === keys.length && names.every(k => typeof k === 'string' && keys.includes(k)));
  for (const k of keys) need(Object.getOwnPropertyDescriptor(v, k)?.value !== undefined);
  return v as Obj;
}
function array(v: unknown, max: number): unknown[] {
  need(Array.isArray(v) && v.length <= max && Object.keys(v).length === v.length);
  need(Object.getPrototypeOf(v) === Array.prototype);
  need(Reflect.ownKeys(v).length === v.length + 1);
  for (let i = 0; i < v.length; i++) need(Object.getOwnPropertyDescriptor(v, String(i))?.value !== undefined);
  return v;
}
function identity(v: Obj, expected: Identity): void {
  need(text(v.project, 100) && text(v.edition, 80));
  need(v.project === expected.project && v.edition === expected.edition);
}
function epoch(v: unknown, now: number, ttl: number): number {
  need(Number.isSafeInteger(v) && Number(v) >= 0 && Number(v) <= now && now - Number(v) <= ttl);
  return v as number;
}
function gate(v: unknown): Gate { need(typeof v === 'string' && gates.includes(v)); return v as Gate; }

/** Manifest paths are relative identifiers; the Host alone resolves them.
 * This never converts a renderer path into a filesystem read request.
 */
export function artifactPath(v: unknown): v is string {
  if (!text(v, 1024) || !/^[A-Za-z0-9_./-]+$/.test(v) || v.startsWith('/') || v.includes('\\')) return false;
  return v.split('/').every(part => !!part && part !== '.' && part !== '..' &&
    !part.endsWith('.') && !/^(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)/i.test(part));
}
function artifact(v: unknown): Artifact {
  const x = object(v, ['role', 'path', 'sha256']);
  need((x.role === 'EXE' || x.role === 'PCK') && artifactPath(x.path) && sha(x.sha256));
  return {role: x.role, path: x.path, sha256: x.sha256};
}
function checkpoint(v: unknown, expected: Identity): SourceCheckpoint | null {
  if (v === null) return null;
  const x = object(v, ['project', 'edition', 'checkpoint', 'commit', 'tree']); identity(x, expected);
  need(text(x.checkpoint, 160) && git(x.commit) && git(x.tree));
  return {...expected, checkpoint: x.checkpoint, commit: x.commit, tree: x.tree};
}
function build(v: unknown, expected: Identity): Build | null {
  if (v === null) return null;
  const x = object(v, ['project', 'edition', 'id', 'commit', 'tree', 'engine', 'artifacts', 'requiresPck']); identity(x, expected);
  need(text(x.id, 160) && text(x.engine, 80) && git(x.commit) && git(x.tree) && typeof x.requiresPck === 'boolean');
  const artifacts = array(x.artifacts, 2).map(artifact);
  need(artifacts.filter(a => a.role === 'EXE').length === 1 && artifacts.filter(a => a.role === 'PCK').length === (x.requiresPck ? 1 : 0));
  need(new Set(artifacts.map(a => a.path.toLowerCase())).size === artifacts.length);
  need(artifacts.every(a => a.path.toLowerCase().endsWith(a.role === 'EXE' ? '.exe' : '.pck')));
  return {...expected, id: x.id, commit: x.commit, tree: x.tree, engine: x.engine, artifacts, requiresPck: x.requiresPck};
}
function observation(v: unknown, expected: Identity, now: number, ttl: number): PhysicalObservation {
  const x = object(v, ['project', 'edition', 'buildId', 'role', 'path', 'exists', 'sha256', 'checkedAt', 'source']); identity(x, expected);
  need(text(x.buildId, 160) && (x.role === 'EXE' || x.role === 'PCK') && artifactPath(x.path));
  need(typeof x.exists === 'boolean' && (x.exists ? sha(x.sha256) : x.sha256 === null) && x.source === 'NATIVE_FILE_READ');
  return {...expected, buildId: x.buildId, role: x.role, path: x.path, exists: x.exists, sha256: x.sha256 as string | null,
    checkedAt: epoch(x.checkedAt, now, ttl), source: 'NATIVE_FILE_READ'};
}
function verification(v: unknown, expected: Identity, now: number, ttl: number): Verification | null {
  if (v === null) return null;
  const x = object(v, ['project', 'edition', 'buildId', 'commit', 'tree', 'artifactHashes', 'evidenceSha256', 'status', 'complete', 'checkedAt']); identity(x, expected);
  need(text(x.buildId, 160) && git(x.commit) && git(x.tree) && sha(x.evidenceSha256) && typeof x.complete === 'boolean');
  const hashes = array(x.artifactHashes, 2); need(hashes.every(sha) && new Set(hashes).size === hashes.length);
  return {...expected, buildId: x.buildId, commit: x.commit, tree: x.tree, artifactHashes: [...hashes] as string[],
    evidenceSha256: x.evidenceSha256, status: gate(x.status), complete: x.complete, checkedAt: epoch(x.checkedAt, now, ttl)};
}

/** Structural boundary only. Provenance and physical file identity must be
 * established by the existing native Host producer, not by any string in IPC.
 * The caller must validate the independently selected catalog/build envelope.
 */
export function parseProjectInput(value: unknown, expected: Identity, now: number, ttl = 10_000): ProjectInput {
  need(Number.isSafeInteger(now) && now >= 0 && Number.isSafeInteger(ttl) && ttl > 0 && ttl <= 10_000);
  need(text(expected.project, 100) && text(expected.edition, 80));
  const x = object(value, ['project', 'edition', 'archived', 'capturedAt', 'origin', 'sourceCheckpoint', 'build', 'observations', 'gameplay', 'fidelity', 'writers', 'admission', 'blockers', 'nextSafeTask']);
  identity(x, expected);
  need(typeof x.archived === 'boolean' && (x.origin === 'HOST_READONLY' || x.origin === 'ARCHIVED_REPORT'));
  const source = checkpoint(x.sourceCheckpoint, expected), built = build(x.build, expected);
  need(!built || source && built.commit === source.commit && built.tree === source.tree);
  const observations = array(x.observations, 2).map(v => observation(v, expected, now, ttl));
  need(!observations.length || built !== null);
  const seen = new Set<string>();
  for (const o of observations) {
    need(built && o.buildId === built.id && built.artifacts.some(a => a.role === o.role && a.path === o.path));
    const id = o.role + ':' + o.path.toLowerCase(); need(!seen.has(id)); seen.add(id);
  }
  const writers = array(x.writers, 8); need(writers.every(v => text(v, 160)) && new Set(writers).size === writers.length);
  const blockers = array(x.blockers, 32); need(blockers.every(v => text(v, 500)));
  need(x.nextSafeTask === null || text(x.nextSafeTask, 1000));
  return {project: expected.project, edition: expected.edition, archived: x.archived,
    capturedAt: epoch(x.capturedAt, now, ttl), origin: x.origin, sourceCheckpoint: source, build: built, observations,
    gameplay: verification(x.gameplay, expected, now, ttl), fidelity: verification(x.fidelity, expected, now, ttl),
    writers: [...writers] as string[], admission: gate(x.admission), blockers: [...blockers] as string[], nextSafeTask: x.nextSafeTask};
}
