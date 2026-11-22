"""Strictly bounded original ZORKDOS native input experiment with cursor-image gate.
Only original read-only game / registered DOSBox-X and private per-run local capture.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
prior=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/"openzork-native-dosboxx-newgame-skipintro-20261009-r7.json"
old=R/"work"/"OpenZork"/"staging"/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"/"ZORKDOS_NATIVE_NEWMOVIE_SKIP.conf"
assert prior.is_file() and old.is_file()
rid="openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"
stage=R/"work"/"OpenZork"/"staging"/rid
assert not stage.exists()
stage.mkdir(parents=True)
conf=stage/"ZORKDOS_IMAGE_GUARDED_CLICK.conf"
s=old.read_text(encoding="utf-8")
assert s.count("mcp_server=59096")==1 and "debugbox" not in s.lower()
conf.write_text(s.replace("mcp_server=59096","mcp_server=59097"),encoding="utf-8")
j=json.loads(prior.read_text(encoding="utf-8"))
j["job_id"]=rid
j["task"]="NativeOriginalZORKDOSOnlyClickIfSourceCursorVerifiedAtNewGameThenSpace"
j["execution"]["config_source"]=str(conf)
j["inputs"][0]={"path":str(conf),"sha256":hashlib.sha256(conf.read_bytes()).hexdigest()}
dest=prior.with_name(rid+".json")
assert not dest.exists()
dest.write_text(json.dumps(j,indent=2,ensure_ascii=False),encoding="utf-8")
rec={
 "schema":"OpenZork.OriginalNativeImageGuardedMouseExperiment.v1",
 "status":"STAGED_NO_GAME_LAUNCHED","run":rid,"port":59097,
 "emulator_binary_sha256":j["inputs"][1]["sha256"],
 "source_game_readonly":True,
 "capture_at":[35,43,54,66,73],
 "pre_click_WGC":"LOCAL_OWNED_HWND_SEPARATE_NATIVE_CAPTURE_IN_RUN",
 "pre_click_positive_template":"assets/cursors/00idlea.png",
 "positive_fixture_runs":["r5","r6"],
 "negative_fixture_run":"r7",
 "input_gate":"POSITIVE_OR_NO_CLICK_AND_NO_SPACE",
 "native_movie_skip_only_after_image_authorized_click":True,
 "no_global_OS_mouse_or_keyboard":True,
 "original_vs_reconstruction_fidelity":"HOLD",
 "job":str(dest)
}
receipt=stage/"r8-image-guarded-plan.json"
receipt.write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":rec["status"],"run_id":rid,"port":59097,
 "job":str(dest),"preclick_gate":"MANDATORY","plan":str(receipt)}))
