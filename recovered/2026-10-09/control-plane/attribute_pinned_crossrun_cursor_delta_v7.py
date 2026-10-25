"""Descriptive original ScummVM 2.0 saved-state cross-run difference attribution.
This post hoc cursor masking is not an independent fidelity acceptance mask.
"""
from pathlib import Path
import numpy as np,json,hashlib
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-pinned-vb30-supervised-sequence-v7-r1"
prior=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
a=run/"pinned-vb30-viewport-768x480.png"
b=prior/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png"
with Image.open(a) as im:A=np.asarray(im.convert("RGB"),dtype=np.uint8)
with Image.open(b) as im:B=np.asarray(im.convert("RGB"),dtype=np.uint8)
assert A.shape==B.shape==(480,768,3)
diff=np.abs(A.astype(np.int16)-B.astype(np.int16))
active=np.any(diff!=0,axis=2)
ys,xs=np.where(active)
assert len(xs)>0
# Explicit conservative non-authoritative cursor regions inferred by visual inspection
# of two position-shifted ScummVM cursor sprites; NEVER use as blind acceptance mask.
rects=[(40,15,115,86),(205,97,278,171)]
mask=np.zeros(active.shape,dtype=bool)
for x0,y0,x1,y1 in rects:
 mask[y0:y1,x0:x1]=True
outside=active&~mask
inside=active&mask
report={
 "schema":"OpenZork.ScummVMGoldenCrossRunCursorDifferenceProbe.v1",
 "status":"CURSOR_RESIDUAL_ATTRIBUTED_DIAGNOSTIC_ONLY",
 "original_run":"openzork-scummvm-golden-scene-sequence-0e2fdd87",
 "new_run":run.name,
 "full_frame_pixel_identical":False,
 "raw_differing_pixel_count":int(active.sum()),
 "raw_differing_pixel_fraction":round(float(active.mean()),8),
 "raw_MAE_0_255":round(float(diff.mean()),6),
 "observed_difference_bounding_box_xyxy":[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],
 "post_hoc_cursor_regions_xyxy":rects,
 "pixels_changed_inside_post_hoc_regions":int(inside.sum()),
 "pixels_changed_outside_post_hoc_regions":int(outside.sum()),
 "outside_posthoc_region_pixels_unchanged":bool(not outside.any()),
 "masked_MAE_outside":round(float(diff[~mask].mean()),8),
 "full_mask_is_independently_predeclared":False,
 "pixel_fidelity_promoted":False,
 "source_save_sha256":"3742d4e4be25561bea21ee1e63aed9029bef409f9cb56b323f8dd5ef254da5dc"}
maskedA=A.copy();maskedB=B.copy()
maskedA[mask]=0;maskedB[mask]=0
fileA=run/"cursor-region-masked-new-original.png"
fileB=run/"cursor-region-masked-prior-original.png"
Image.fromarray(maskedA,"RGB").save(fileA)
Image.fromarray(maskedB,"RGB").save(fileB)
report["masked_hash_new"]=hashlib.sha256(fileA.read_bytes()).hexdigest()
report["masked_hash_prior"]=hashlib.sha256(fileB.read_bytes()).hexdigest()
report["masked_png_equal"]=fileA.read_bytes()==fileB.read_bytes()
result=run/"pinned-vb30-cursor-attribution.json"
if result.exists():raise RuntimeError("CURSOR_ATTRIBUTION_ALREADY_EXISTS")
result.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"raw_differing_pixels":report["raw_differing_pixel_count"],
 "raw_bbox":report["observed_difference_bounding_box_xyxy"],
 "outside_cursor_regions_changed":report["pixels_changed_outside_post_hoc_regions"],
 "masked_png_identical":report["masked_png_equal"],
 "fidelity":False,"evidence":str(result)},ensure_ascii=False))
