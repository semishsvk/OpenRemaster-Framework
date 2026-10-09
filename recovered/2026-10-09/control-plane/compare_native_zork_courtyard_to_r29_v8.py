"""First independent real native ZORKDOS original exterior vs historical R29
ScummVM oracle and Godot TA30 projection. Read-only previous game/evidence sources.
Fixed explicit WGC viewport crop; metrics exploratory unless state/camera synchronized.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from fidelity_capture_sequence_v2 import verify_bounded_wgc_sequence_v2
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-native-dosboxx-cursor-feedback-newgame-20261009-r9"
r29=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-R10-PIXEL-FIDELITY-r29"
m=run/"fidelity-isolated"/"capture"/"capture-attestation.json"
proof=json.loads(m.read_text(encoding="utf-8-sig"))
assert verify_bounded_wgc_sequence_v2(m.parent,proof)["verified_frames"]==5
assert proof["frames"][3]["sha256"]==proof["frames"][4]["sha256"]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
actual_file=m.parent/proof["frames"][4]["path"]
with Image.open(actual_file) as im:
 actual=im.convert("RGB")
 assert actual.size==(644,557)
 crop_xyxy=(66,155,578,475)
 cropped=actual.crop(crop_xyxy)
 assert cropped.size==(512,320)
 crop=run/"original-native-TA30-courtyard-fixedviewport-512x320.png"
 if crop.exists():raise RuntimeError("NATIVE_COURTYARD_CROP_ALREADY_EXISTS")
 cropped.save(crop)
 native=np.asarray(cropped,dtype=np.uint8)
images={}
names={
 "prior_ScummVM_original":r29/"ORACLE_RESIZED_0.png",
 "prior_Godot_candidate":r29/"GODOT_MATCHED_0_TA30_328.png"
}
for k,path in names.items():
 with Image.open(path) as im:
  a=np.asarray(im.convert("RGB"),dtype=np.uint8)
  assert a.shape==(320,512,3),(k,a.shape)
  images[k]=a
def measure(a,b,exclude_cursor=False):
 if exclude_cursor:
  # Exploratory predeclared for THIS comparison: source cursor appears near
  # lower centre, bbox x240..315, y258..320 in 512x320 image.
  use=np.ones((320,512),dtype=bool)
  use[250:320,230:325]=False
  X=a[use].astype(np.float32);Y=b[use].astype(np.float32)
 else:
  X=a.astype(np.float32).reshape((-1,3))
  Y=b.astype(np.float32).reshape((-1,3))
 D=np.abs(X-Y)
 lumx=X.mean(axis=1);lumy=Y.mean(axis=1)
 corr=float(np.corrcoef(lumx,lumy)[0,1]) if lumx.std() and lumy.std() else 0.
 return {"MAE_0_255":round(float(D.mean()),5),
         "grayscale_correlation":round(corr,7),
         "changed_pixel_fraction_gt10":round(float((D>10).any(axis=1).mean()),7),
         "pixel_identical":bool(np.array_equal(X,Y))}
comparisons={
 "native_ZORKDOS_vs_prior_ScummVM":measure(native,images["prior_ScummVM_original"]),
 "native_ZORKDOS_vs_prior_ScummVM_cursor_excluded":measure(native,images["prior_ScummVM_original"],True),
 "native_ZORKDOS_vs_prior_Godot":measure(native,images["prior_Godot_candidate"]),
 "native_ZORKDOS_vs_prior_Godot_cursor_excluded":measure(native,images["prior_Godot_candidate"],True),
 "prior_ScummVM_vs_prior_Godot":measure(images["prior_ScummVM_original"],images["prior_Godot_candidate"])
}
sheet=Image.new("RGB",(1560,370),(15,15,15))
draw=ImageDraw.Draw(sheet)
for i,(name,img) in enumerate([("Native original ZORKDOS r9",native),
 ("Prior ScummVM oracle R29",images["prior_ScummVM_original"]),
 ("Prior Godot projected TA30 R29",images["prior_Godot_candidate"])]):
 sheet.paste(Image.fromarray(img,"RGB"),(i*520+3,29))
 draw.text((i*520+5,7),name,fill="white")
sheet_file=run/"native-vs-previous-TA30-oracle-godot.png"
sheet.save(sheet_file)
record={
 "schema":"OpenZork.NativeDOSOriginalCourtyardVsR29TechnicalComparison.v1",
 "status":"NATIVE_SOURCE_SAME_SCENE_COMPARISON_COMPUTED_ORIGINAL_GODOT_FIDELITY_HOLD",
 "run_id":run.name,
 "original_native_executable":"ZORKDOS.EXE",
 "runtime_kind":"DOSBOX_X_2026_10_01_REGISTERED_SHA256",
 "original_game_corpus_readonly":True,
 "source_scene_hypothesis":"TEMPLE/TA30_NEEDS_INDEPENDENT_ID_VERIFICATION",
 "R29_historical_scene":"TA30@328",
 "viewport_crop_xyxy":list(crop_xyxy),
 "native_original_viewport_sha256":sha(crop),
 "prior_ScummVM_oracle_sha256":sha(names["prior_ScummVM_original"]),
 "prior_Godot_candidate_sha256":sha(names["prior_Godot_candidate"]),
 "native_capture_master_manifest_sha256":sha(m),
 "comparison_metrics":comparisons,
 "retail_Godot_gameplay_fidelity":"HOLD",
 "cursor_exclusion":"EXPLORATORY_ONLY_NOT_PREDECLARED_BY_ORIGINAL_ACCEPTANCE",
 "source_game_actions_player_replay":"ONLY_NEWGAME_AND_SPACE; MOVEMENT_NOT_VERIFIED",
 "contact_sheet":str(sheet_file),
 "contact_sheet_sha256":sha(sheet_file)
}
report=run/"native-vs-R29-temple-technical-comparison.json"
if report.exists():raise RuntimeError("R29_COMPARISON_ALREADY_EXISTS")
report.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],
 "metrics":comparisons,"crop_sha256":record["native_original_viewport_sha256"],
 "contact_sheet":str(sheet_file),"evidence":str(report)},ensure_ascii=False))
