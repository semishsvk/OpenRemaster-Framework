"""Restore-seed materialization negative canaries; no interactive game launch."""
import json,subprocess,sys,tempfile,uuid
from pathlib import Path
from fidelity_seed_saves_v1 import stage_seed_saves
from fidelity_runtime_isolation_v1 import IsolationError,sha256
ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
source=ROOT/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"/"znemesis.000"
assert source.is_file()
digest=sha256(source)
def expect(reason,f):
 try:f()
 except IsolationError as e:
  assert e.reason==reason,(reason,e.reason);return
 raise AssertionError("FAIL_OPEN "+reason)
with tempfile.TemporaryDirectory(dir=ROOT/"runtime-test"/"results",prefix="save-seed-test-") as temp:
 dest=Path(temp)
 expect("SAVE_SEED_HASH_MISMATCH",lambda:stage_seed_saves(dest,"OpenZork",[{
   "path":str(source),"sha256":"0"*64}]))
 expect("GAME_SEED_ADAPTER_NOT_COMMISSIONED",lambda:stage_seed_saves(dest,"OpenROTH",[{
   "path":str(source),"sha256":digest}]))
 wrong=ROOT/"source"/"Zork Nemesis"/"ZNEMESIS.INI"
 expect("SAVE_SEED_SOURCE_OUTSIDE_PROJECT",lambda:stage_seed_saves(dest,"OpenZork",[{
   "path":str(wrong),"sha256":sha256(wrong)}]))
 with tempfile.TemporaryDirectory(dir=ROOT/"work"/"OpenZork"/"staging",prefix="seed-invalid-canary-") as invalid:
  damaged=Path(invalid)/"znemesis.000"
  damaged.write_bytes(b"CORRUPTED_GOLDEN_SAVE_NOT_ZNSG" * 8)
  expect("SAVE_SEED_MAGIC_INVALID",lambda:stage_seed_saves(dest,"OpenZork",[{
    "path":str(damaged),"sha256":sha256(damaged)}]))
 done=stage_seed_saves(dest,"OpenZork",[{"path":str(source),"sha256":digest}])
 assert done["status"]=="PASS_SOURCE_READ_ONLY"
 assert done["entries"][0]["source_kind"]=="PINNED_EVIDENCE"
 assert done["entries"][0]["seed_scene"]=="vb30"
 assert done["entries"][0]["seed_view"]==1058
 assert sha256(source)==digest and (dest/"znemesis.000").is_file()
 assert sha256(dest/"znemesis.000")==digest
 expect("SAVE_SEED_TARGET_ALREADY_EXISTS",lambda:stage_seed_saves(dest,"OpenZork",[{
   "path":str(source),"sha256":digest}]))
assert sha256(source)==digest
job_id="openzork-save-seed-guard-"+uuid.uuid4().hex[:8]
job={"schema":"ORCH-K003.Job.v1","job_id":job_id,"project":"OpenZork",
     "task":"MissingReadOnlySaveSeedCapability","inputs":[],
     "required_capabilities":["runtime.fidelity_isolated"],
     "execution":{"kind":"fidelity_runtime","runtime_kind":"scummvm",
                  "executable":str(ROOT/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"),
                  "seed_saves":[{"path":str(source),"sha256":digest}]},
     "validation":{"expected_exit_code":0}}
jp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(job_id+".json")
jp.parent.mkdir(exist_ok=True,parents=True);jp.write_text(json.dumps(job))
r=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(jp)],capture_output=True,text=True,timeout=15)
out=ROOT/"runtime-test"/"results"/job_id
rec=json.loads((out/"control-receipt.json").read_text())
assert r.returncode==2 and rec["status"]=="BLOCKED" and rec["reason"]=="READ_ONLY_SAVE_SEED_CAPABILITY_REQUIRED"
assert not (out/"result.json").exists()
print(json.dumps({"schema":"OpenRemaster.ReadOnlySaveSeedCanary.v1",
  "status":"PASS","source_sha256":digest,
  "private_copy":"SHA256_IDENTICAL","bad_hash":"REJECTED",
  "cross_project_seed":"REJECTED","bad_ZNSG_magic":"REJECTED",
  "source_kind":"PINNED_EVIDENCE","source_writes":0,
  "missing_capability":"BLOCKED_NO_GAME_LAUNCHED"}))
