"""Project/runtime/game-data binding, positive and negative fixtures without launching GUIs."""
from pathlib import Path
import hashlib,json,tempfile,subprocess,sys
from fidelity_target_binding_v1 import (
 validate_registered_target,validate_game_config_binding,registry
)
from fidelity_runtime_isolation_v1 import IsolationError
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
roots={
 "source":R/"source"/"Zork Nemesis",
 "other":R/"source"/"Need for speed",
 "dosbox":R/"source"/"Zork Nemesis"/"DOSBOX"/"DOSBox.exe",
 "dosboxx":Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe"),
 "scummvm":R/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe",
 "fixture":R/"work"/"OpenRemaster"/"fidelity_fixture"/"synthetic_scummvm_oracle.exe",
 "ini":R/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"scummvm.ini",
 "conf":CP/"examples"/"OpenZork-dosbox-fidelity-seed.conf",
 "conf_x":CP/"examples"/"OpenZork-dosboxx-autotype-oracle-seed.conf",
 "fixture_ini":R/"work"/"OpenRemaster"/"fidelity_fixture"/"scummvm-fixture.ini",
}
assert registry()["target_count"]==4

def reject(reason,fun):
 try:fun()
 except IsolationError as e:
  assert e.reason==reason,(reason,e.reason)
  return {"status":"BLOCKED","reason":reason}
 raise AssertionError("FAIL_OPEN_EXPECTED "+reason)

original=validate_registered_target("OpenZork","dosbox",roots["dosbox"])
interp=validate_registered_target("OpenZork","scummvm",roots["scummvm"])
legacy=validate_registered_target("OpenZork","dosbox",roots["dosboxx"])
fixture=validate_registered_target("OpenRemaster","scummvm",roots["fixture"])
assert original["classification"]=="BUNDLED_ORIGINAL_DOSBOX"
assert interp["classification"]=="SCUMMVM_CROSS_VALIDATION_NOT_NATIVE_DOS"
assert legacy["classification"]=="DOSBOX_X_REUSED_HASH_PINNED_PRIOR_ART"
assert fixture["classification"]=="SYNTHETIC_WIN32_CANARY_ONLY"

assert validate_game_config_binding(original,roots["conf"])["status"]=="PASS_SOURCE_BOUND"
assert validate_game_config_binding(legacy,roots["conf_x"])["status"]=="PASS_SOURCE_BOUND"
assert validate_game_config_binding(interp,roots["ini"])["status"]=="PASS_SOURCE_BOUND"
assert validate_game_config_binding(fixture,roots["fixture_ini"])["status"]=="PASS_SYNTHETIC_NO_GAME_AUTHORITY"

neg=[]
neg.append(reject("RUNTIME_PROJECT_KIND_NOT_COMMISSIONED",
 lambda:validate_registered_target("OpenROTH","dosbox",roots["dosbox"])))
neg.append(reject("RUNTIME_EXECUTABLE_NOT_REGISTERED_FOR_PROJECT",
 lambda:validate_registered_target("OpenZork","scummvm",roots["fixture"])))
neg.append(reject("RUNTIME_EXECUTABLE_NOT_REGISTERED_FOR_PROJECT",
 lambda:validate_registered_target("OpenRemaster","scummvm",roots["scummvm"])))
neg.append(reject("RUNTIME_PROJECT_KIND_NOT_COMMISSIONED",
 lambda:validate_registered_target("OpenZork","godot",roots["scummvm"])))
with tempfile.TemporaryDirectory(prefix="source-binding-negative-",dir=R/"runtime-test"/"results") as temp:
 dest=Path(temp)
 cfg=dest/"foreign.conf"
 cfg.write_text('[autoexec]\nmount C "'+str(roots["other"])+'" -ro\n')
 neg.append(reject("DOSBOX_FOREIGN_SOURCE_MOUNT",
  lambda:validate_game_config_binding(original,cfg)))
 cfg.write_text('[autoexec]\nmount C "'+str(roots["source"])+'"\n')
 neg.append(reject("DOSBOX_SOURCE_MOUNT_NOT_READ_ONLY",
  lambda:validate_game_config_binding(original,cfg)))
 cfg.write_text("[autoexec]\n@echo off\n")
 neg.append(reject("DOSBOX_EXPECTED_ORIGINAL_GAME_NOT_MOUNTED",
  lambda:validate_game_config_binding(original,cfg)))
 ini=dest/"foreign.ini"
 ini.write_text('[scummvm]\nupdates_check=0\n[znemesis]\ngameid=zvision\npath='+str(roots["other"])+'\n',encoding="utf-8")
 neg.append(reject("SCUMMVM_TARGET_PATH_DIFFERENT_GAME",
  lambda:validate_game_config_binding(interp,ini)))
 ini.write_text('[scummvm]\nupdates_check=0\n[znemesis]\ngameid=foo\npath='+str(roots["source"])+'\n',encoding="utf-8")
 neg.append(reject("SCUMMVM_TARGET_ENGINE_DIFFERENT",
  lambda:validate_game_config_binding(interp,ini)))
report={
 "schema":"OpenRemaster.VerifiedInteractiveTargetBindingCanary.v1",
 "status":"PASS",
 "registered_original_runtimes":3,
 "registered_synthetic_test_runtimes":1,
 "positive_game_config_source_tests":4,
 "negative_rejection_tests":len(neg),
 "negative_cases":neg,
 "original_Zork_corpus_source_readonly":True,
 "uncommissioned_game_profiles":"BLOCKED",
 "original_game_processes_launched":0}
out=R/"runtime-test"/"results"/"fidelity-runtime-target-binding-v7-canary.json"
if out.exists():
 existing=json.loads(out.read_text(encoding="utf-8-sig"))
 if existing!=report:
  raise AssertionError("HISTORICAL_BINDING_CANARY_EVIDENCE_DRIFT")
else:
 out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"status":"PASS","positive":report["positive_game_config_source_tests"],
 "negatives":len(neg),"game_launches":0,"evidence":str(out)},ensure_ascii=False))
