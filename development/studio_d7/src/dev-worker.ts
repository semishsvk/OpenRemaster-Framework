export type NativeInvoke = (command: string, args?: Record<string, unknown>) => Promise<unknown>;
declare global { interface Window { __TAURI_INTERNALS__?: {invoke: NativeInvoke} } }

export type Capabilities = {worker_compiled: boolean; worker_ready: boolean; worker_scope: string | null; reason: string; control_ready?: boolean; recovery_supported?: boolean; log_archive_supported?: boolean;preflight?:Preflight};
export type DevResult = {
  schema: 'OpenRemaster.DevWorkflowResult.v1' | 'OpenRemaster.DevWorkflowResult.v2'; state: string; operation_id: string;
  production_go: false; independent_authority: false; engine: 'unsigned-studio-dev-build';
  dev_receipt_verified: boolean; launch_count?: number; reason?: string; ack?: unknown; commit?: unknown;
  control_scope?: string; control_verified?: boolean; evidence_sha256?: string;
  recovery?: {allowed: boolean; reason: string};
  not_admitted?: {schema:'OpenRemaster.NotAdmitted.v1';operation_id:string;scope:string;attempt_id:string;reason:string;record_sha256:string;production_go:false};
  resolution?: {disposition: 'ACKNOWLEDGED_NO_RETRY'; operation_id: string; scope: string; evidence_sha256: string; archive_manifest_sha256: string; record_sha256: string; reason: string; new_operation_allowed: true; production_go: false} | null;
  archive?: {path: string; operation_id: string; evidence_sha256: string; manifest_sha256: string; log_count: number; retention: string} | null;
  logs?: Record<string, string>;
  worker?: {elapsed_seconds?: number; artifacts?: {studio_exe: string; studio_exe_sha256: string}};
};
export const legacyOperationKey = 'orf-unified-dev-build-operation';
const states = ['REQUESTED', 'QUEUED', 'RUNNING', 'ACKNOWLEDGED', 'STARTED', 'COMMITTED', 'HOLD', 'DENIED', 'BUSY', 'NOT_FOUND'];
export const activeStates = ['REQUESTED', 'QUEUED', 'RUNNING', 'ACKNOWLEDGED', 'STARTED'];
export const phaseLabels: Record<string, string> = {
  REQUESTED: 'Request sent · waiting for saved acknowledgment', QUEUED: 'Queued by HomePC worker', RUNNING: 'Building on HomePC', ACKNOWLEDGED: 'Acknowledged',
  STARTED: 'Building', COMMITTED: 'Build complete', HOLD: 'Held for review',
  DENIED: 'Request denied', BUSY: 'Worker busy', NOT_FOUND: 'Saved operation not found',
};
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid DEV response');
  return value as Record<string, unknown>;
}
const hex = (value: unknown, length: number): value is string => typeof value === 'string' && new RegExp(`^[a-f0-9]{${length}}$`).test(value);
const text = (value: unknown, limit: number): value is string => typeof value === 'string' && value.length <= limit;

export function parseCapabilities(raw: unknown): Capabilities {
  const value = object(raw);
  if (value.schema !== 'OpenRemaster.StudioCapabilities.v1' || value.production_go !== false
      || typeof value.worker_compiled !== 'boolean' || typeof value.worker_ready !== 'boolean'
      || !text(value.reason, 512) || (value.worker_ready && !value.worker_compiled)
      || ['control_ready','recovery_supported','log_archive_supported'].some(key => value[key] !== undefined && typeof value[key] !== 'boolean')
      || (value.control_ready === true && !value.worker_compiled)
      || (value.worker_compiled ? !hex(value.worker_scope, 64) : value.worker_scope !== null)) {
    throw Error('Native capability response was rejected');
  }
  if(value.preflight!==undefined)parsePreflight(value.preflight,value.worker_scope);
  return value as Capabilities;
}

export function parseDevResult(raw: unknown, operation: string, scope?: string): DevResult {
  if (typeof raw !== 'string' || raw.length > 131072) throw Error('Invalid DEV response size');
  const value = object(JSON.parse(raw));
  const controlled = value.schema === 'OpenRemaster.DevWorkflowResult.v2';
  const admitted = controlled
    ? hex(scope,64) && value.control_scope === scope && value.control_verified === true && typeof value.dev_receipt_verified === 'boolean'
    : value.schema === 'OpenRemaster.DevWorkflowResult.v1' && value.dev_receipt_verified === true && value.resolution === undefined && value.archive === undefined;
  if (!hex(operation, 32) || value.operation_id !== operation || !admitted
      || value.production_go !== false || value.independent_authority !== false
      || value.engine !== 'unsigned-studio-dev-build'
      || !states.includes(String(value.state)) || (value.automatic_retry !== undefined && value.automatic_retry !== false)
      || (value.reason !== undefined && !text(value.reason, 4096))
      || (value.launch_count !== undefined && (!Number.isInteger(value.launch_count) || Number(value.launch_count) < 0 || Number(value.launch_count) > 1))) {
    throw Error('DEV response identity or scope was rejected');
  }
  if (controlled) {
    if(value.not_admitted!==undefined) {
      const proof=object(value.not_admitted);
      if(value.state!=='DENIED'||value.launch_count!==0||proof.schema!=='OpenRemaster.NotAdmitted.v1'||proof.operation_id!==operation||proof.scope!==scope
          ||!hex(proof.attempt_id,32)||!hex(proof.record_sha256,64)||!text(proof.reason,2048)||proof.production_go!==false
          ||value.ack!=null||value.commit!=null||value.worker!=null)throw Error('Invalid not-admitted proof');
    }
    if (!hex(value.evidence_sha256,64)) throw Error('DEV observation evidence is missing');
    const recovery = object(value.recovery);
    if (typeof recovery.allowed !== 'boolean' || !text(recovery.reason,4096)) throw Error('Invalid recovery observation');
    if (value.archive !== null) {
      const archive=object(value.archive);
      if (archive.operation_id !== operation || archive.evidence_sha256 !== value.evidence_sha256
          || !hex(archive.manifest_sha256,64) || !text(archive.path,4096) || !archive.path
          || !Number.isInteger(archive.log_count) || Number(archive.log_count)<0 || Number(archive.log_count)>2
          || archive.retention !== 'KEEP_UNTIL_EXPLICIT_EXPORT_AND_REVIEW') throw Error('Invalid archive evidence');
    }
    if (value.resolution !== null) {
      const resolution=object(value.resolution), archive=object(value.archive);
      if (!['HOLD','DENIED','NOT_FOUND'].includes(String(value.state)) || resolution.operation_id !== operation || resolution.scope !== scope
          || resolution.evidence_sha256 !== value.evidence_sha256 || resolution.archive_manifest_sha256 !== archive.manifest_sha256
          || resolution.disposition !== 'ACKNOWLEDGED_NO_RETRY' || resolution.new_operation_allowed !== true || resolution.production_go !== false
          || !hex(resolution.record_sha256,64) || !text(resolution.reason,1024) || String(resolution.reason).trim().length<10) throw Error('Invalid hold resolution evidence');
    }
  }
  if (value.logs !== undefined) {
    for (const [name, content] of Object.entries(object(value.logs))) {
      if (!['stdout.log', 'stderr.log'].includes(name) || !text(content, 8192)) throw Error('Invalid DEV log tail');
    }
  }
  if (value.state === 'COMMITTED') {
    const worker = object(value.worker), artifacts = object(worker.artifacts), commit = object(value.commit), ack = object(value.ack);
    if (worker.success !== true || worker.owned_tree_stopped !== true || worker.wrapper_exit !== 0
        || commit.operation_id !== operation || ack.operation_id !== operation
        || !text(artifacts.studio_exe, 4096) || !hex(artifacts.studio_exe_sha256, 64)) {
      throw Error('Completed DEV result has incomplete artifact evidence');
    }
  }
  return value as DevResult;
}

export type OperationRecord = {schema: 'OpenRemaster.StudioOperation.v2'; scope: string; operation: string; result: DevResult | null;attempt_id?:string};
export const operationKey = (scope: string) => `orf-studio-operation-v2-${scope}`;
export function readOperation(storage: Storage, scope: string): OperationRecord | null {
  const raw = storage.getItem(operationKey(scope));
  if (raw) {
    if (raw.length > 131072) throw Error('Saved operation is too large');
    const value = object(JSON.parse(raw));
    if (value.schema !== 'OpenRemaster.StudioOperation.v2' || value.scope !== scope || !hex(value.operation, 32)) {
      throw Error('Saved operation has an invalid identity');
    }
    if(value.attempt_id!==undefined&&!hex(value.attempt_id,32))throw Error('Invalid saved attempt identity');
    const result = value.result === null ? null : parseDevResult(JSON.stringify(value.result), value.operation, scope);
    return {schema: 'OpenRemaster.StudioOperation.v2', scope, operation: value.operation, result,attempt_id:value.attempt_id as string|undefined};
  }
  const legacy = storage.getItem(legacyOperationKey);
  if (!legacy) return null;
  if (!hex(legacy, 32)) throw Error('Saved legacy operation has an invalid identity');
  return {schema: 'OpenRemaster.StudioOperation.v2', scope, operation: legacy, result: null};
}
export function saveOperation(storage: Storage, scope: string, operation: string, result: DevResult | null, attemptId?:string) {
  // Logs are a transient observation; keep the durable record small across restarts.
  const durable = result ? {...result, logs: undefined} : null;
  const old=readOperation(storage,scope);
  const attempt=attemptId??(old?.operation===operation?old.attempt_id:undefined);
  if(attempt!==undefined&&!hex(attempt,32))throw Error('Invalid attempt identity');
  const record: OperationRecord = {schema: 'OpenRemaster.StudioOperation.v2', scope, operation, result: durable,attempt_id:attempt};
  const raw = JSON.stringify(record);
  if (raw.length > 131072) throw Error('Saved operation metadata is too large');
  storage.setItem(operationKey(scope), raw);
  if (result && storage.getItem(legacyOperationKey) === operation) storage.removeItem(legacyOperationKey);
}
export function canStartAnother(result: DevResult | null, attemptId?:string) {
  // A status rejection says nothing about whether a previous submission launched.
  if(result?.not_admitted&&result.not_admitted.attempt_id!==attemptId)return false;
  return result?.state === 'COMMITTED' || (result?.schema === 'OpenRemaster.DevWorkflowResult.v2'
    && ['HOLD','DENIED','NOT_FOUND'].includes(result.state) && result.resolution?.new_operation_allowed === true);
}
import {parsePreflight, type Preflight} from './dev-diagnostics';
