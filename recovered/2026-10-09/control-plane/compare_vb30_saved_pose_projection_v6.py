"""Reproduce exact VB30@1058 projection using already-recovered original TGZ panorama.
CPU projection is independent reference/decoder lab, NOT a Godot runtime or fidelity gate.
"""
from pathlib import Path
import math,json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageChops,ImageStat

R=Path(__file__).resolve().parents[2]
base=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
pose=json.loads((base/"vb30-save-scene-pose-and-decoder-v6.json").read_text())
assert pose["status"]=="SAVE_LOCATION_AND_TGZ_DECODER_BYTE_MATCH_PASS"
assert (pose["location_key"],pose["view_coordinate"])==("VB30",1058)
source=R/"work"/"OpenZork"/"runtime"/"assets"/"VB30S11C.ppm"
with Image.open(source) as img:
 pano=np.asarray(img.convert("RGB"),dtype=np.uint8)
assert pano.shape==(1440,320,3),pano.shape
with Image.open(base/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png") as im:
 golden=im.convert("RGB")
 ref_nearest=np.asarray(golden.resize((512,320),Image.Resampling.NEAREST),dtype=np.uint8)
 ref_bilinear=np.asarray(golden.resize((512,320),Image.Resampling.BILINEAR),dtype=np.uint8)

width,height=512,320
ang=math.radians(24.2637)
half=height/2
hd=half/math.tan(ang)
td=math.tan(ang)/half
xx=np.arange(width,dtype=np.float64)
theta=np.arctan((xx-width/2+0.01)*td)
nx=np.trunc(0.6*hd*theta).astype(np.int32)+width//2
nx=np.clip(nx,0,width-1)
ys=np.arange(height,dtype=np.float64)
nhw=height*np.cos(theta)
sy=np.floor((height-nhw[:,None])/2+ys[None,:]*nhw[:,None]/height).astype(np.int32)
sy=np.clip(sy,0,height-1)
view=pose["view_coordinate"]
px=((view-width//2+nx)%1440).astype(np.int32)
# Source row index is horizontal panorama orientation and source column index vertical.
r=pano[px[:,None],sy,:].transpose((1,0,2))[:,:,::-1].copy()

def score(a,b,masked=False):
 a=a.astype(np.float32);b=b.astype(np.float32)
 if masked:
  # Exact captured mouse cursor lives in top-left corner; no claim that this mask
  # is full canonical alignment, only an exploratory cursor exclusion.
  a=a[55:,80:,:];b=b[55:,80:,:]
 mae=float(np.abs(a-b).mean())
 ga=a.mean(axis=2).ravel();gb=b.mean(axis=2).ravel()
 corr=float(np.corrcoef(ga,gb)[0,1]) if ga.std()>0 and gb.std()>0 else 0.0
 return {"MAE_0_255":round(mae,4),"grayscale_correlation":round(corr,6)}
out_img=base/"vb30-savepose-source-CPU-projection-512x320.png"
Image.fromarray(r,"RGB").save(out_img)
delta=np.abs(r.astype(np.int16)-ref_bilinear.astype(np.int16)).astype(np.uint8)
diff=base/"vb30-savepose-CPU-vs-ScummVM-diff.png"
Image.fromarray(delta,"RGB").save(diff)
side=Image.new("RGB",(1040,690),(20,20,20))
draw=ImageDraw.Draw(side)
side.paste(Image.fromarray(ref_nearest,"RGB"),(6,28))
side.paste(Image.fromarray(r,"RGB"),(522,28))
side.paste(Image.fromarray(delta,"RGB"),(522,367))
draw.text((6,7),"Original ScummVM VB30 saved view 1058",fill="white")
draw.text((522,7),"Source TGZ VB30 CPU projected at view 1058",fill="white")
draw.text((522,346),"Absolute RGB diff, exploratory, not aligned fidelity",fill="white")
contact=base/"vb30-savepose-source-vs-original-contact-sheet.png"
side.save(contact)
all_scores={
 "original_nearest":score(r,ref_nearest),
 "original_bilinear":score(r,ref_bilinear),
 "masked_cursor_region_nearest":score(r,ref_nearest,True),
 "masked_cursor_region_bilinear":score(r,ref_bilinear,True)
}
result={
 "schema":"OpenZork.VB30SavePoseIndependentSourceProjection.v1",
 "status":"CPU_SOURCE_REPROJECTION_COMPUTED_ALIGNMENT_EXPLORATORY",
 "scene":"VB30","game_data":"DATA2/ZASSETS/CONSERV",
 "saved_view":view,"saved_view_provenance":str(base/"vb30-save-scene-pose-and-decoder-v6.json"),
 "source_tgz_sha256":pose["location_source_sha256"],
 "source_ppm_sha256":pose["preexisting_ppm_sha256"],
 "original_scummvm_frame_sha256":hashlib.sha256((base/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png").read_bytes()).hexdigest(),
 "source_CPU_renderer":"OpenZork legacy R9 ZVision panoramic projection as reused prior-art",
 "projection_fov_half_angle_degrees":24.2637,
 "unverified_factors":["ScummVM camera projection equivalence","input state","sprites and overlays","cursor","game logic"],
 "pixel_scores":all_scores,
 "pixel_alignment_independently_verified":False,
 "godot_runtime_used":False,
 "fidelity_verified":False,
 "source_projection_png":str(out_img),
 "source_projection_sha256":hashlib.sha256(out_img.read_bytes()).hexdigest(),
 "difference_png":str(diff),
 "contact_sheet":str(contact)
}
e=base/"vb30-savepose-source-projection-evidence.json"
e.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":result["status"],"saved_scene":result["scene"],"saved_view":view,
 "scores":all_scores,"source_projection":str(out_img),"contact_sheet":str(contact),
 "evidence":str(e)},ensure_ascii=False))
