export type NativeInvoke = (command: string, args?: Record<string, unknown>) => Promise<unknown>;
declare global { interface Window { __TAURI_INTERNALS__?: {invoke: NativeInvoke} } }

export type Capabilities = {worker_compiled: boolean; worker_ready: boolean; worker_scope: string | null; reason: string};
export type DevResult = {
  schema: 'OpenRemaster.DevWorkflowResult.v1'; state: string; operation_id: string;
  production_go: false; independent_authority: false; engine: 'unsigned-studio-dev-build';
  dev_receipt_verified: true; launch_count?: number; reason?: string; ack?: unknown; commit?: unknown;
  logs?: Record<string, string>;
  worker?: {elapsed_seconds?: number; artifacts?: {studio_exe: string; studio_exe_sha256: string}};
};
export const legacyOperationKey = 'orf-unified-dev-build-operation';
const states = ['REQUESTED', 'ACKNOWLEDGED', 'STARTED', 'COMMITTED', 'HOLD', 'DENIED', 'BUSY', 'NOT_FOUND'];
export const activeStates = ['REQUESTED', 'ACKNOWLEDGED', 'STARTED'];
export const phaseLabels: Record<string, string> = {
  REQUESTED: 'Request sent · waiting for saved acknowledgment', ACKNOWLEDGED: 'Acknowledged',
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
      || (value.worker_compiled ? !hex(value.worker_scope, 64) : value.worker_scope !== null)) {
    throw Error('Native capability response was rejected');
  }
  return value as Capabilities;
}

export function parseDevResult(raw: unknown, operation: string): DevResult {
  if (typeof raw !== 'string' || raw.length > 131072) throw Error('Invalid DEV response size');
  const value = object(JSON.parse(raw));
  if (!hex(operation, 32) || value.operation_id !== operation || value.schema !== 'OpenRemaster.DevWorkflowResult.v1'
      || value.production_go !== false || value.independent_authority !== false
      || value.engine !== 'unsigned-studio-dev-build' || value.dev_receipt_verified !== true
      || !states.includes(String(value.state)) || (value.automatic_retry !== undefined && value.automatic_retry !== false)
      || (value.reason !== undefined && !text(value.reason, 4096))
      || (value.launch_count !== undefined && (!Number.isInteger(value.launch_count) || Number(value.launch_count) < 0 || Number(value.launch_count) > 1))) {
    throw Error('DEV response identity or scope was rejected');
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

export type OperationRecord = {schema: 'OpenRemaster.StudioOperation.v2'; scope: string; operation: string; result: DevResult | null};
export const operationKey = (scope: string) => `orf-studio-operation-v2-${scope}`;
export function readOperation(storage: Storage, scope: string): OperationRecord | null {
  const raw = storage.getItem(operationKey(scope));
  if (raw) {
    if (raw.length > 131072) throw Error('Saved operation is too large');
    const value = object(JSON.parse(raw));
    if (value.schema !== 'OpenRemaster.StudioOperation.v2' || value.scope !== scope || !hex(value.operation, 32)) {
      throw Error('Saved operation has an invalid identity');
    }
    const result = value.result === null ? null : parseDevResult(JSON.stringify(value.result), value.operation);
    return {schema: 'OpenRemaster.StudioOperation.v2', scope, operation: value.operation, result};
  }
  const legacy = storage.getItem(legacyOperationKey);
  if (!legacy) return null;
  if (!hex(legacy, 32)) throw Error('Saved legacy operation has an invalid identity');
  return {schema: 'OpenRemaster.StudioOperation.v2', scope, operation: legacy, result: null};
}
export function saveOperation(storage: Storage, scope: string, operation: string, result: DevResult | null) {
  const record: OperationRecord = {schema: 'OpenRemaster.StudioOperation.v2', scope, operation, result};
  storage.setItem(operationKey(scope), JSON.stringify(record));
  if (result && storage.getItem(legacyOperationKey) === operation) storage.removeItem(legacyOperationKey);
}
export function canStartAnother(result: DevResult | null) {
  return result?.state === 'COMMITTED' || (['DENIED', 'BUSY'].includes(result?.state ?? '') && result?.launch_count === 0);
}
