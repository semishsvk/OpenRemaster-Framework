"""Read-only original-image positive/negative and bounded planned motion canary.
No actual game input or Windows cursor moved.
"""
from pathlib import Path
import json
from fidelity_native_cursor_feedback_v1 import (
 detect_extracted_cursor_position,safe_positive_feedback_delta,
 guest_port_motion_value)
from fidelity_runtime_isolation_v1 import IsolationError
R=Path(__file__).resolve().parents[2]
base=R/"runtime-test"/"results"
def frame(run,part):
 return base/run/"fidelity-isolated"/part/"frame-0001.bmp"
r6=frame("openzork-native-dosboxx-extended-newgame-20261009-r6","capture/samples/point-02")
r7=frame("openzork-native-dosboxx-newgame-skipintro-20261009-r7","capture/samples/point-02")
r8=frame("openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8","input-observations/pre-click")
rows=[("r6",r6),("r7",r7),("r8",r8)]
found={}
for name,path in rows:found[name]=detect_extracted_cursor_position(path)
assert found["r6"]["NewGame_click_allowed"] is True and (found["r6"]["x"],found["r6"]["y"])==(317,421),found["r6"]
assert found["r7"]["status"]=="ORIGINAL_SPRITE_MATCHED_LEFT_CLIPPED" and (found["r7"]["x"],found["r7"]["y"])==(-2,233),found["r7"]
assert found["r8"]["status"]=="ORIGINAL_SPRITE_MATCHED_LEFT_CLIPPED" and (found["r8"]["x"],found["r8"]["y"])==(-2,71),found["r8"]
assert safe_positive_feedback_delta(found["r6"])["status"]=="ALREADY_ON_NEW_GAME"
assert safe_positive_feedback_delta(found["r7"])["x_delta"]==200
assert safe_positive_feedback_delta(found["r8"])["y_delta"]==200
assert guest_port_motion_value("x",200)=="C9000900"
assert guest_port_motion_value("y",110)=="6F000A00"
record={
 "schema":"OpenZork.NativeCursorFeedbackCalibrationCanary.v1",
 "status":"PASS_ORIGINAL_POSITIVE_AND_TWO_CLIPPED_NEGATIVE_FRAMES",
 "observed_original_runs":found,
 "allowed_guest_movement":"NONNEGATIVE_DELTA_MAX_200_PER_AXIS",
 "no_click_without_original_cursor_template_ROI":True,
 "total_original_game_launches":0,
 "global_host_pointer_or_focus_changes":0,
 "fidelity_verified":False}
p=base/"native-original-cursor-feedback-fixtures-v8.json"
if p.exists():
 existing=json.loads(p.read_text(encoding="utf-8-sig"))
 assert existing==record,"HISTORICAL_CURSOR_FEEDBACK_FIXTURE_DRIFT"
else:
 p.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],
"coordinates":{k:[v["x"],v["y"]] for k,v in found.items()},
"r8_calibration_start":safe_positive_feedback_delta(found["r8"]),
"source_game_mutation":False,"evidence":str(p)},ensure_ascii=False))
