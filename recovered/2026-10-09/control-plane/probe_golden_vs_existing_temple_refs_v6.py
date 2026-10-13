"""Read-only golden scene lookup versus previous R14/R26/R29/R30 local visual evidence.
Numbers are exploratory alignment signals, NOT new fidelity acceptance.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageOps,ImageStat

R=Path(__file__).resolve().parents[2]
G=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png"
root=R/"output"/"projects"/"OpenZork"/"evidence"
checks=[
 ("golden_seeded_SCUMMVM",G),
 ("R14_original_temple_entry",root/"20261009-R10-ORACLE-TEMPLE-r14"/"ORIGINAL_TEMPLE_ENTRY_SCREEN.png"),
 ("R26_temple_state0",root/"20261009-R10-VISUAL-COMPARE-r26"/"ORACLE_TEMPLE_STATE_0.png"),
 ("R26_temple_state1",root/"20261009-R10-VISUAL-COMPARE-r26"/"ORACLE_TEMPLE_STATE_1.png"),
 ("R29_oracle_resized0",root/"20261009-R10-PIXEL-FIDELITY-r29"/"ORACLE_RESIZED_0.png"),
 ("R29_godot_matched0",root/"20261009-R10-PIXEL-FIDELITY-r29"/"GODOT_MATCHED_0_TA30_328.png"),
 ("R29_oracle_resized1",root/"20261009-R10-PIXEL-FIDELITY-r29"/"ORACLE_RESIZED_1.png"),
 ("R29_godot_matched1",root/"20261009-R10-PIXEL-FIDELITY-r29"/"GODOT_MATCHED_1_TA50_328.png"),
]
def normalized(im):
 im=im.convert("RGB")
 if im.size==(962,768):
  im=im.crop((96,167,864,647))
 elif im.width/im.height>1.6001:
  target=round(im.height*1.6);trim=(im.width-target)//2;im=im.crop((trim,0,trim+target,im.height))
 elif im.width/im.height<1.5999:
  target=round(im.width/1.6);trim=(im.height-target)//2;im=im.crop((0,trim,im.width,trim+target))
 return im.resize((512,320),Image.Resampling.BILINEAR)
with Image.open(G) as image:
 gold=normalized(image)
 goldarr=np.asarray(gold,dtype=np.float64)
 goldgray=goldarr.mean(axis=2)
report=[]
canvas=Image.new("RGB",(1070,((len(checks)+1)//2)*370),(27,27,27))
draw=ImageDraw.Draw(canvas)
for i,(name,path) in enumerate(checks):
 if not path.is_file():report.append({"name":name,"missing":True});continue
 with Image.open(path) as im:
  size=im.size
  norm=normalized(im)
  n=np.asarray(norm,dtype=np.float64)
  mae=float(np.abs(goldarr-n).mean())
  ga=goldgray.ravel();gb=n.mean(axis=2).ravel()
  corr=float(np.corrcoef(ga,gb)[0,1]) if ga.std()>0 and gb.std()>0 else 0.0
  rec={"name":name,"size":list(size),"source_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
       "normalized_mae_0_255":round(mae,3),"normalized_gray_corr":round(corr,5),
       "normalization":"center_cropped_to_16_10_and_bilinear_512x320"}
  report.append(rec)
  x=(i%2)*535+12;y=(i//2)*370+27
  draw.text((x,y-17),name,fill="white")
  canvas.paste(norm,(x,y))
out=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
comparison={
 "schema":"OpenZork.GoldenScenePriorReferenceAlignmentProbe.v1",
 "status":"EXPLORATORY_REFERENCES_ONLY_NO_FIDELITY_PASS",
 "golden_save_sha256":"3742d4e4be25561bea21ee1e63aed9029bef409f9cb56b323f8dd5ef254da5dc",
 "reference_provenance":"LOCAL_PREVIOUS_R14_R26_R29_ARTIFACTS",
 "limitations":["independent_camera_alignment_NOT_VERIFIED","different_WGC_vs_Godot_runtime_captures",
                "center_crop_and_resize_NOT_CANONICAL_VIEWPORT_ALIGNMENT",
                "no_audio_event_sync_or_replay_state_match"],
 "images":report
}
evidence=out/"existing-r30-reference-probe.json"
evidence.write_text(json.dumps(comparison,indent=2,ensure_ascii=False),encoding="utf-8")
sheet=out/"existing-r30-reference-contact-sheet.png"
canvas.save(sheet)
print(json.dumps({"status":comparison["status"],
 "comparisons":[{"name":x.get("name"),"size":x.get("size"),"mae":x.get("normalized_mae_0_255"),"corr":x.get("normalized_gray_corr")} for x in report],
 "evidence":str(evidence),"contact_sheet":str(sheet)},ensure_ascii=False))
