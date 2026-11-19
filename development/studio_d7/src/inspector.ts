/**
 * Zero-capability UI adapter for a bounded, operator-captured Inspector Host result.
 * Source content is untrusted strings. Never promote captured status into authority.
 * The 30-second clock relates to source observation only, NOT a production lease.
 */
export type InspectorRecord = {
  id: string;
  project: string; workstream: string; edition: string; scope: string;
  sourceSchema: string; sourceSha256: string; reportedStatus: string;
  reportedAtUtc: string | null; parentIds: string[];
  observationClass: "PINNED_CHECKPOINT_REPORT_NOT_OWNER_SIGNOFF";
  freshness: "MATCHES_PINNED_SHA256_NOT_LATEST_ASSERTION";
};
export type InspectorCapture = {
  schema: "OpenRemaster.StudioInspectorCapture.v1";
  status: "SOURCE_BOUND_READONLY_CAPTURED_PRODUCTION_HOLD" | "HOLD";
  code: string; captureStartedUtc: string | null; captureCompletedUtc?: string;
  expiresUtc: string | null; sourceMode: string; sourceAuthority: string;
  productionAdmission: "HOLD"; ownerSelectedId: null; dispatchAuthorized: false;
  nativeWorkerUsed: false; autoRetry: false; originalGamesTouched: false;
  sourceCorporaTouched: false; hostReadOnly: true;
  snapshot: string | null; total: number; records: InspectorRecord[];
  hostSourcePins: Record<string, string>;
  requestAudit: { method: string; responseSha256: string; acceptedReadOnly: boolean }[];
  registryDecision?: string; registryBlockers?: string[];
  freshnessAssertion?: string; hostCheckpointScope?: string;
  generation?: number;
};
export type CapturePhase = "HOLD" | "RECENT_READONLY" | "HISTORICAL_ONLY";
export type CaptureView = { phase: CapturePhase; capture: InspectorCapture | null; code: string; activeCount: number };

const hex64 = /^[0-9a-f]{64}$/;
const sourceRef = /^cp_[0-9a-f]{64}$/;
const snapshotRef = /^sha256:[0-9a-f]{64}$/;
const code = /^[A-Z0-9_]{2,96}$/;
const pinFiles = [
  "HOST_SOURCE_PINS.json",
  "inspector_host_v1.py",
  "inspector_session_v1.cjs",
  "inspector_r1/continuation_consumer_v1.cjs",
];
const acceptedDecision = new Set([
  "MULTI_WORKSTREAM_CONFLICT_OWNER_SELECTION_REQUIRED",
  "SINGLE_CHECKPOINT_OWNER_ACCEPTANCE_UNATTESTED",
]);
const isPlain = (x: unknown): x is Record<string, unknown> =>
  x !== null && typeof x === "object" && !Array.isArray(x);
const str = (x: unknown, max: number): x is string => typeof x === "string" && x.length > 0 && x.length <= max;
const array = (x: unknown, max: number): x is unknown[] => Array.isArray(x) && x.length <= max;
const eqTime = (start: string, end: string): boolean => {
  const s = Date.parse(start), e = Date.parse(end);
  return Number.isFinite(s) && Number.isFinite(e) && e - s === 30_000;
};
function recordValid(row: unknown): row is InspectorRecord {
  if (!isPlain(row)) return false;
  if (!str(row.id, 67) || !sourceRef.test(row.id) ||
      !str(row.project, 160) || !str(row.workstream, 160) ||
      !str(row.edition, 160) || !str(row.scope, 160) ||
      !str(row.sourceSchema, 160) || !str(row.sourceSha256, 64) ||
      !hex64.test(row.sourceSha256) ||
      !str(row.reportedStatus, 240) ||
      !(row.reportedAtUtc === null || (str(row.reportedAtUtc, 80) && Number.isFinite(Date.parse(row.reportedAtUtc)))) ||
      !array(row.parentIds, 20) || !row.parentIds.every(x => typeof x === "string" && sourceRef.test(x) && x !== row.id) ||
      new Set(row.parentIds).size !== row.parentIds.length ||
      row.observationClass !== "PINNED_CHECKPOINT_REPORT_NOT_OWNER_SIGNOFF" ||
      row.freshness !== "MATCHES_PINNED_SHA256_NOT_LATEST_ASSERTION") return false;
  return true;
}
export function validateCapture(raw: unknown): raw is InspectorCapture {
  if (!isPlain(raw)) return false;
  if (raw.schema !== "OpenRemaster.StudioInspectorCapture.v1" ||
      raw.sourceMode !== "LOCAL_SIGNLESS_PINNED_HOST_OPERATOR_CAPTURE" ||
      raw.sourceAuthority !== "UNSIGNED_LOCAL_SHA256_ONLY" ||
      raw.productionAdmission !== "HOLD" || raw.ownerSelectedId !== null ||
      raw.dispatchAuthorized !== false || raw.nativeWorkerUsed !== false ||
      raw.autoRetry !== false || raw.originalGamesTouched !== false ||
      raw.sourceCorporaTouched !== false || raw.hostReadOnly !== true ||
      !str(raw.code, 96) || !code.test(raw.code) ||
      !array(raw.records, 20) || !Number.isSafeInteger(raw.total) || Number(raw.total) < 0 ||
      !isPlain(raw.hostSourcePins) || !array(raw.requestAudit, 22)) return false;

  if (raw.status === "HOLD") {
    return raw.records.length === 0 && raw.total === 0 && raw.snapshot === null &&
      raw.captureStartedUtc === null && raw.expiresUtc === null && raw.requestAudit.length === 0 &&
      Object.keys(raw.hostSourcePins).length === 0;
  }
  if (raw.status !== "SOURCE_BOUND_READONLY_CAPTURED_PRODUCTION_HOLD" ||
      raw.code !== "SOURCE_BOUND_CAPTURE_ACCEPTED" ||
      !str(raw.captureStartedUtc, 40) || !str(raw.expiresUtc, 40) ||
      !eqTime(raw.captureStartedUtc, raw.expiresUtc) ||
      !str(raw.captureCompletedUtc, 40) ||
      !Number.isFinite(Date.parse(raw.captureCompletedUtc)) ||
      Date.parse(raw.captureCompletedUtc) < Date.parse(raw.captureStartedUtc) ||
      Date.parse(raw.captureCompletedUtc) > Date.parse(raw.expiresUtc) ||
      !str(raw.snapshot, 71) || !snapshotRef.test(raw.snapshot) ||
      !Number.isSafeInteger(raw.generation) || Number(raw.generation) < 1 ||
      !acceptedDecision.has(String(raw.registryDecision)) ||
      raw.freshnessAssertion !== "MATCHES_PINNED_SHA256_NOT_LATEST_ASSERTION" ||
      raw.hostCheckpointScope !== "ONLY_2_EXISTING_PINNED_FRAMEWORK_CHECKPOINTS_NOT_GLOBAL" ||
      !array(raw.registryBlockers, 1) ||
      raw.registryBlockers.length !== 1 ||
      raw.registryBlockers[0] !== "EXTERNAL_OWNER_CANONICAL_SELECTION_REQUIRED" ||
      raw.total !== raw.records.length || raw.total < 1 || raw.total > 20 ||
      !raw.records.every(recordValid)) return false;
  const ids = raw.records.map((r: any) => r.id as string);
  if (new Set(ids).size !== ids.length) return false;
  const all = new Set(ids);
  if (raw.records.some((r: any) => r.parentIds.some((p: string) => !all.has(p)))) return false;

  const pins = raw.hostSourcePins;
  if (Object.keys(pins).sort().join("|") !== [...pinFiles].sort().join("|")) return false;
  if (!pinFiles.every(n => str(pins[n], 64) && hex64.test(pins[n]))) return false;
  const audit = raw.requestAudit;
  if (audit.length !== raw.records.length + 2) return false;
  const expected = ["health.get", "checkpoints.list", ...raw.records.map(() => "checkpoints.get")];
  return audit.every((item, i) => isPlain(item) && item.method === expected[i] &&
    item.acceptedReadOnly === true && str(item.responseSha256, 64) && hex64.test(item.responseSha256));
}
export function classifyCapture(raw: unknown, nowMs: number = Date.now()): CaptureView {
  if (!validateCapture(raw)) return { phase: "HOLD", code: "INVALID_CAPTURE", activeCount: 0, capture: null };
  if (raw.status === "HOLD") return { phase: "HOLD", code: raw.code, activeCount: 0, capture: raw };
  const started = Date.parse(raw.captureStartedUtc!);
  const expires = Date.parse(raw.expiresUtc!);
  if (nowMs < started - 1000) return { phase: "HOLD", code: "FUTURE_CAPTURE_TIME", activeCount: 0, capture: null };
  // Historical records are still available as explicitly marked archived evidence,
  // but they are not current Inspector session rows and cannot represent live health.
  if (nowMs >= expires) return { phase: "HISTORICAL_ONLY", code: "OBSERVATION_EXPIRED", activeCount: 0, capture: raw };
  return { phase: "RECENT_READONLY", code: "PINNED_LOCAL_READONLY", activeCount: raw.records.length, capture: raw };
}
