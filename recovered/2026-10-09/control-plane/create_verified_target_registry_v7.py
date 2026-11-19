"""Create immutable, SHA-pinned approved interactive runtime targets from live binaries.
Only actually verified corpus/runtimes; other game projects require commissioning.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
known=[
 {
  "project":"OpenZork","runtime_kind":"dosbox",
  "exe":R/"source"/"Zork Nemesis"/"DOSBOX"/"DOSBox.exe",
  "source":R/"source"/"Zork Nemesis",
  "classification":"BUNDLED_ORIGINAL_DOSBOX",
  "input_authority":"ORIGINAL_ZORKDOS_EXE_AND_GAME_DATA",
  "config_game_binding":"DOSBOX_SOURCE_MOUNT_EXACT"
 },
 {
  "project":"OpenZork","runtime_kind":"scummvm",
  "exe":R/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe",
  "source":R/"source"/"Zork Nemesis",
  "classification":"SCUMMVM_CROSS_VALIDATION_NOT_NATIVE_DOS",
  "input_authority":"ORIGINAL_ZORK_GAME_DATA_ONLY",
  "config_game_binding":"SCUMMVM_ZNEMESIS_PATH"
 },
 {
  "project":"OpenZork","runtime_kind":"dosbox",
  "exe":Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe"),
  "source":R/"source"/"Zork Nemesis",
  "classification":"DOSBOX_X_REUSED_HASH_PINNED_PRIOR_ART",
  "input_authority":"ORIGINAL_ZORKDOS_EXE_AND_GAME_DATA",
  "config_game_binding":"DOSBOX_SOURCE_MOUNT_EXACT"
 },
 {
  "project":"OpenRemaster","runtime_kind":"scummvm",
  "exe":R/"work"/"OpenRemaster"/"fidelity_fixture"/"synthetic_scummvm_oracle.exe",
  "source":None,
  "classification":"SYNTHETIC_WIN32_CANARY_ONLY",
  "input_authority":"NO_ORIGINAL_GAME_CORPUS",
  "config_game_binding":"SYNTHETIC_NO_GAME_CORPUS"
 }
]
entries=[]
for r in known:
 p=r["exe"]
 if not p.is_file():raise FileNotFoundError("MISSING_RUNTIME_TARGET:"+str(p))
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 entries.append({
  "project":r["project"],"runtime_kind":r["runtime_kind"],
  "executable":str(p.resolve()),"executable_sha256":h,
  "source_root":str(r["source"].resolve()) if r["source"] else None,
  "classification":r["classification"],
  "input_authority":r["input_authority"],
  "config_game_binding":r["config_game_binding"]
 })
registry={
 "schema":"OpenRemaster.VerifiedInteractiveRuntimeTargets.v1",
 "status":"REGISTERED_EXACT_TARGETS_ONLY",
 "purpose":"Reject wrong-game, wrong-DOSBox, stale-binary, and uncommissioned GUI fidelity launches",
 "validated_root":"F:\\Remaster Framework",
 "unknown_project_or_executable":"BLOCKED_NOT_IMPLICITLY_TRUSTED",
 "source_read_only":True,
 "target_count":len(entries),
 "entries":entries
}
out=CP/"fidelity-runtime-target-registry.v7.json"
if out.exists():raise RuntimeError("TARGET_REGISTRY_ALREADY_EXISTS")
out.write_text(json.dumps(registry,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":registry["status"],"targets":[{"project":r["project"],"kind":r["runtime_kind"],
 "sha256":r["executable_sha256"],"classification":r["classification"]} for r in entries],
 "path":str(out),"registry_sha256":hashlib.sha256(out.read_bytes()).hexdigest()},ensure_ascii=False))
