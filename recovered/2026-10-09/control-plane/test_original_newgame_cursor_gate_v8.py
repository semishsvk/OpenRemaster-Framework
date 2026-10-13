"""Fail-closed real-image positive and negative original ZORKDOS cursor input admission.
Pure file processing only: no game/runtime launch, no input, no host focus.
"""
from pathlib import Path
import json,hashlib
from fidelity_original_cursor_gate_v1 import evaluate_original_newgame_cursor,TEMPLATE
from fidelity_runtime_isolation_v1 import IsolationError
ROOT=Path(__file__).resolve().parents[2]
R=ROOT/"runtime-test"/"results"
cases=[
 ("r5_positive",R/"openzork-native-dosboxx-mcp-new-game-click-20261009-r5"/"fidelity-isolated"/"capture"/"samples"/"point-02"/"frame-0001.bmp",True),
 ("r6_positive",R/"openzork-native-dosboxx-extended-newgame-20261009-r6"/"fidelity-isolated"/"capture"/"samples"/"point-02"/"frame-0001.bmp",True),
 ("r7_negative",R/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"/"fidelity-isolated"/"capture"/"samples"/"point-02"/"frame-0001.bmp",False),
 ("r7_negative_late",R/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"/"fidelity-isolated"/"capture"/"samples"/"point-05"/"frame-0001.bmp",False)
]
rows=[]
for name,file,allowed in cases:
 rec=evaluate_original_newgame_cursor(file)
 assert rec["authorized_single_mouse_click"] is allowed,(name,rec)
 rows.append({"name":name,"expected_allowed":allowed,
 "actual_allowed":rec["authorized_single_mouse_click"],
 "WGC_sha256":rec["original_frame_sha256"],
 "best_position":rec["best_cursor_top_left"],"RMSE":rec["best_template_RGB_RMSE"]})
record={"schema":"OpenZork.OriginalNativeNewGameCursorInputGuardCanary.v1",
 "status":"PASS_TWO_POSITIVES_TWO_NEGATIVES",
 "original_cursor_template_sha256":hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
 "cases":rows,"original_game_runtimes_launched":0,
 "original_game_source_modified":False,
 "global_host_mouse_keyboard_input":False,
 "scope":"EXPERIMENTAL_PRE_CLICK_ADMISSION_NOT_GAMEPLAY_FIDELITY",
 "fidelity_verified":False}
dest=R/"original-newgame-cursor-gate-canary-v8.json"
if dest.exists():
 existing=json.loads(dest.read_text(encoding="utf-8-sig"))
 assert existing==record,"HISTORICAL_CURSOR_GUARD_CANARY_DRIFT"
else:
 dest.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],"cases":[{"name":x["name"],"pass":x["actual_allowed"],
 "coord":x["best_position"],"RMSE":x["RMSE"]} for x in rows],
 "evidence":str(dest)},ensure_ascii=False))
