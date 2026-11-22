"""Read-only pixel evidence for r10 safe cursor-position-blocked input.
No game launch or input. Converts registered bound native WGC BMP to viewable PNG.
"""
from pathlib import Path
from PIL import Image
import numpy as np,json
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-native-dosboxx-cursor-feedback-newgame-20261009-r10"
inputp=run/"fidelity-isolated"/"input-observations"/"calibration-01"/"frame-0001.bmp"
assert inputp.is_file()
with Image.open(inputp) as im:
 rgb=im.convert("RGB")
 png=inputp.with_suffix(".png")
 rgb.save(png)
 a=np.asarray(rgb,dtype=np.uint8)
roi=a[75:540,:,:]
# Threshold emphasizes white/yellow extracted cursor on black title border.
bright=((roi[:,:,0]>130)&(roi[:,:,1]>100)&(roi[:,:,2]>60))
left=bright[:,0:30]
right=bright[:,614:644]
top=bright[:75,:]
out={"schema":"OpenZork.NativeMouseCursorMissingInputEvidence.v1",
"status":"READ_ONLY_PIXEL_VIEWPORT_INVESTIGATION",
"frame_path":str(inputp),"preview_png":str(png),
"shape":list(a.shape),
"bright_left_30_pixels":int(left.sum()),
"bright_right_30_pixels":int(right.sum()),
"bright_near_top_window_pixels":int(top.sum()),
"original_newgame_clicked":False,
"source_guest_cursor_status":"UNLOCATABLE_FAIL_CLOSED"}
path=run/"cursor-missing-frame-diagnostic.json"
if path.exists():raise RuntimeError("CURSOR_MISSING_INSPECTION_EXISTS")
path.write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,ensure_ascii=False))
