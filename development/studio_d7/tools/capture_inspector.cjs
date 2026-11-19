"use strict";
/**
 * Studio UI-003 / operator-initiated SOURCE-BOUND READ-ONLY Inspector capture.
 * No HTTP listener, no UI-driven process launch, no game/worker/core invocations.
 * Fixed HomePC runtimes, unchanged NW025-R owned-job Host, pinned source and RPC methods.
 */
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawn } = require("node:child_process");
const { performance } = require("node:perf_hooks");

const ROOT = path.resolve(__dirname, "..");
const HOST = path.resolve(ROOT, "..", "host");
const PYTHON = "C:\\Users\\msemj\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe";
const TARGET = path.join(ROOT, "src", "data", "inspector-observation.json");
const MAX_IN = 8192;
const MAX_OUT = 131072;
const DEADLINE = 14500;
const FRESH_LIMIT = 30000;
const EXPECT = Object.freeze({
  "inspector_host_v1.py": "070c90a4e2cfe0e7fda3bc026fcd5cff7c43f089a803d29a9f54989dd79fb910",
  "HOST_SOURCE_PINS.json": "1f14b49d8697be862350bdb047fc0eaed116fc9eca9297f3b83c4c32a3ed5ccd",
  "inspector_session_v1.cjs": "7b3b1cc23abb8b128dbd73bdcd80996e4bcdf9b41bbb850ab7edab4dec6e618c",
  "inspector_r1\\continuation_consumer_v1.cjs": "15efdd594c9b35285c36e252b91e821cbfe83399de159ff4da220bf0a87687c1",
});
const ENGINE = Object.freeze({
  node: "3602f2bb1a10f2cbab4c36886218a33c1ab3db87290e73b033c46c77147d0237",
  python: "cce21c0e8710e304273e98ac4b2b0f5aceb639acbcd2343cbaa5c4e81619c45b",
});

function sha(input) { return crypto.createHash("sha256").update(input).digest("hex"); }
function fingerprint(file, maxBytes = 1024 * 1024) {
  const st = fs.lstatSync(file, { bigint: true });
  if (!st.isFile() || st.isSymbolicLink() || st.size <= 0n || st.size > BigInt(maxBytes)) throw Error("FILE_REJECTED");
  const data = fs.readFileSync(file);
  const end = fs.lstatSync(file, { bigint: true });
  if (st.ino !== end.ino || st.size !== end.size || st.mtimeNs !== end.mtimeNs || data.length !== Number(st.size)) throw Error("SOURCE_CHANGED");
  return sha(data);
}
function checkPins() {
  const pins = {};
  for (const [rel, expected] of Object.entries(EXPECT)) {
    const actual = fingerprint(path.join(HOST, rel));
    if (actual !== expected) throw Error("HOST_SOURCE_DRIFT");
    pins[rel.replaceAll("\\", "/")] = actual;
  }
  if (fingerprint(process.execPath, 128 * 1024 * 1024) !== ENGINE.node ||
      fingerprint(PYTHON, 128 * 1024 * 1024) !== ENGINE.python) throw Error("RUNTIME_PIN_DRIFT");
  return pins;
}
function strictEnv() {
  return {
    SystemRoot: "C:\\Windows", WINDIR: "C:\\Windows",
    TEMP: path.join(ROOT, "capture-temp"), TMP: path.join(ROOT, "capture-temp"),
    PATH: "C:\\Windows\\System32",
    PYTHONDONTWRITEBYTECODE: "1", PYTHONNOUSERSITE: "1",
    PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1", PYTHONSAFEPATH: "1",
  };
}
function runFixedHost(request) {
  const raw = Buffer.from(JSON.stringify(request), "utf8");
  if (raw.length > MAX_IN || raw.length === 0) return Promise.reject(Error("REQUEST_TOO_LARGE"));
  return new Promise((resolve, reject) => {
    let finished = false, killed = false, outs = [], outLen = 0, errLen = 0;
    const child = spawn(PYTHON, ["-I", "-S", "-B", path.join(HOST, "host_bootstrap.py")], {
      cwd: HOST, windowsHide: true, shell: false,
      env: strictEnv(), stdio: ["pipe", "pipe", "pipe"],
    });
    const deadline = setTimeout(() => { killed = true; child.kill(); }, DEADLINE);
    child.stdout.on("data", chunk => {
      outLen += chunk.length;
      if (outLen > MAX_OUT) { killed = true; child.kill(); } else outs.push(chunk);
    });
    child.stderr.on("data", chunk => {
      errLen += chunk.length;
      if (errLen > 8192) { killed = true; child.kill(); }
    });
    child.on("error", () => { killed = true; });
    child.on("close", code => {
      if (finished) return;
      finished = true; clearTimeout(deadline);
      if (killed || code !== 0 || errLen !== 0 || outLen === 0 || outLen > MAX_OUT) {
        reject(Error("HOST_TRANSPORT_HOLD"));
      } else {
        resolve(Buffer.concat(outs).toString("utf8"));
      }
    });
    child.stdin.on("error", () => { killed = true; child.kill(); });
    child.stdin.end(raw);
  });
}
function empty(code) {
  return {
    schema: "OpenRemaster.StudioInspectorCapture.v1",
    status: "HOLD", code, captureStartedUtc: null, expiresUtc: null,
    sourceMode: "LOCAL_SIGNLESS_PINNED_HOST_OPERATOR_CAPTURE",
    sourceAuthority: "UNSIGNED_LOCAL_SHA256_ONLY",
    productionAdmission: "HOLD", ownerSelectedId: null,
    sourceCorporaTouched: false, dispatchAuthorized: false,
    nativeWorkerUsed: false, autoRetry: false, originalGamesTouched: false,
    hostReadOnly: true, records: [], total: 0, snapshot: null, hostSourcePins: {},
    requestAudit: [],
  };
}
function writeAtomically(record) {
  fs.mkdirSync(path.dirname(TARGET), { recursive: true });
  const tmp = TARGET + ".stage";
  if (fs.existsSync(tmp)) throw Error("UNEXPECTED_STAGING_FILE");
  try {
    fs.writeFileSync(tmp, JSON.stringify(record, null, 2) + "\n", { encoding: "utf8", flag: "wx" });
    fs.renameSync(tmp, TARGET);
  } finally { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); }
}
function ensure(check, code) { if (!check) throw Error(code); }
function normalizedRecord(item) {
  return {
    id: item.id, project: item.project, workstream: item.workstream,
    edition: item.edition, scope: item.scope,
    sourceSchema: item.source_schema, sourceSha256: item.source_sha256,
    reportedStatus: item.reported_status, reportedAtUtc: item.reported_at_utc,
    parentIds: [...item.parent_ids],
    observationClass: item.observation_class, freshness: item.freshness,
  };
}
async function capture() {
  fs.mkdirSync(path.join(ROOT, "capture-temp"), { recursive: true });
  const pins = checkPins();
  // Pinned, reviewed session + strict consumer already validate method-specific
  // response, correlation, security, pages, duplicate rows and source data.
  const { createSession } = require(path.join(HOST, "inspector_session_v1.cjs"));
  const session = createSession();
  const audit = [];
  let listBegan = null;
  async function ask(method, params = {}) {
    const ticket = session.begin(method, params); // clears old cards immediately
    if (method === "checkpoints.list" && listBegan === null) listBegan = Date.now();
    let reply;
    try {
      reply = await runFixedHost(ticket.request);
    } catch {
      session.fail(ticket, "TRANSPORT_HOLD");
      throw Error("HOST_TRANSPORT_HOLD");
    }
    fs.mkdirSync(path.join(ROOT, "capture-audit"), {recursive:true});
    fs.writeFileSync(path.join(ROOT, "capture-audit", "rpc-" + audit.length + ".json"), reply, {flag:"wx"});
    if (!session.complete(ticket, reply)) throw Error("HOST_RESPONSE_REJECTED");
    const state = session.snapshot();
    ensure(state.phase === "READY_READONLY" && state.decision?.production_admission === "HOLD", "UNTRUSTED_DECISION");
    ensure(state.decision.owner_selected_id === null, "OWNER_SPOOF");
    audit.push({ method, responseSha256: sha(Buffer.from(reply, "utf8")), acceptedReadOnly: true });
    return state;
  }
  try {
    const health = await ask("health.get");
    const listing = await ask("checkpoints.list", { limit: 20, offset: 0 });
    ensure(health.snapshot === listing.snapshot && health.cache_generation === listing.cache_generation, "SNAPSHOT_DRIFT");
    ensure(!listing.has_more && listing.total === listing.items.length &&
      health.checkpoint_count === listing.total && listing.total >= 1 && listing.total <= 20, "SCOPE_DRIFT");
    const items = listing.items.map(normalizedRecord);
    for (const original of listing.items) {
      const detail = await ask("checkpoints.get", { id: original.id, if_snapshot: listing.snapshot });
      ensure(detail.snapshot === listing.snapshot &&
        detail.cache_generation === listing.cache_generation &&
        JSON.stringify(detail.item) === JSON.stringify(original), "DETAIL_DRIFT");
    }
    ensure(Date.now() - listBegan <= FRESH_LIMIT, "OBSERVATION_EXPIRED");
    const pinsAfter = checkPins();
    ensure(JSON.stringify(pins) === JSON.stringify(pinsAfter), "SOURCE_CHANGED");
    const decision = listing.decision;
    ensure(decision.owner_selected_id === null && decision.production_admission === "HOLD" &&
      decision.registry_blockers.length === 1 &&
      decision.registry_blockers[0] === "EXTERNAL_OWNER_CANONICAL_SELECTION_REQUIRED", "OWNER_REPORTED_HOLD_REQUIRED");

    return {
      ...empty("SOURCE_BOUND_CAPTURE_ACCEPTED"),
      status: "SOURCE_BOUND_READONLY_CAPTURED_PRODUCTION_HOLD",
      captureStartedUtc: new Date(listBegan).toISOString(),
      expiresUtc: new Date(listBegan + FRESH_LIMIT).toISOString(),
      captureCompletedUtc: new Date().toISOString(),
      hostReadOnly: true,
      registryDecision: decision.status,
      registryBlockers: [...decision.registry_blockers],
      freshnessAssertion: listing.freshness,
      hostCheckpointScope: "ONLY_2_EXISTING_PINNED_FRAMEWORK_CHECKPOINTS_NOT_GLOBAL",
      snapshot: listing.snapshot, generation: listing.cache_generation,
      records: items, total: items.length,
      hostSourcePins: pins, requestAudit: audit,
    };
  } finally { session.close(); }
}
async function main() {
  try {
    const record = await capture();
    writeAtomically(record);
    console.log("REAL_PINNED_HOST_CAPTURE_PASS records=" + record.records.length +
      " rpc=" + record.requestAudit.length + " production=HOLD");
  } catch (err) {
    const code = /^[A-Z0-9_]{2,64}$/.test(err.message || "") ? err.message : "CAPTURE_FAILED";
    // A failed new capture cannot silently reuse an earlier successful record.
    try { writeAtomically(empty(code)); } catch { console.error("FAIL_CLOSED_WRITE_FAILED"); process.exitCode = 3; return; }
    console.error("CAPTURE_HOLD " + code);
    process.exitCode = 2;
  }
}
if (require.main === module) {
  if (process.argv.length !== 2) { console.error("ARGUMENTS_FORBIDDEN"); process.exitCode = 2; }
  else main();
}
module.exports = { normalizedRecord, empty, checkPins, capture };
