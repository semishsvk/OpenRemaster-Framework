import type {ObservationRequest} from './native-file-observation';
import type {NativeInvoke} from './dev-worker';

/** Fixed read-only command. Paths, scripts, endpoints and actions are never
 * renderer arguments. The caller must still parse the unknown response against
 * an independently accepted binding; this transport confers no authority.
 */
export async function invokeFileObservation(selection: ObservationRequest, invoke: NativeInvoke): Promise<unknown> {
  const keys = ['project_id', 'edition_id', 'committed_operation_id', 'accepted_manifest_digest'] as const;
  if (!selection || typeof selection !== 'object' ||
      ![Object.prototype, null].includes(Object.getPrototypeOf(selection)) ||
      Reflect.ownKeys(selection).length !== keys.length ||
      keys.some(key => !Object.getOwnPropertyDescriptor(selection, key) ||
        !('value' in Object.getOwnPropertyDescriptor(selection, key)!))) throw Error('INVALID_OBSERVATION_REQUEST');
  const {project_id, edition_id, committed_operation_id, accepted_manifest_digest} = selection;
  if (typeof project_id !== 'string' || !/^[A-Za-z0-9_-]{1,64}$/.test(project_id) ||
      typeof edition_id !== 'string' || !/^[A-Za-z0-9_-]{1,64}$/.test(edition_id) ||
      typeof committed_operation_id !== 'string' || !/^[0-9a-f]{32}$/.test(committed_operation_id) ||
      typeof accepted_manifest_digest !== 'string' || !/^[0-9a-f]{64}$/.test(accepted_manifest_digest)) throw Error('INVALID_OBSERVATION_REQUEST');
  // Copy four verified data properties so a caller cannot mutate in-flight args.
  return invoke('local_dev_file_observation', {selection: Object.freeze({project_id, edition_id, committed_operation_id, accepted_manifest_digest})});
}

export async function readNativeFileObservation(selection: ObservationRequest): Promise<unknown> {
  const invoke = typeof window === 'undefined' ? undefined : window.__TAURI_INTERNALS__?.invoke;
  if (!invoke) throw Error('NATIVE_OBSERVATION_UNAVAILABLE');
  return invokeFileObservation(selection, invoke);
}
