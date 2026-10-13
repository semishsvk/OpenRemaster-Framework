"""Match original recovered OpenZork 00idlea alpha sprite to TWO original ScummVM screenshots.
Full-frame template search using NumPy FFT SSD, no image difference used in search.
Exploratory cursor localization only; no fidelity metrics/promotion.
"""
from pathlib import Path
import numpy as np,json,hashlib
from PIL import Image
R=Path(__file__).resolve().parents[2]
sprite_path=R/"work"/"OpenZork"/"runtime"/"assets"/"cursors"/"00idlea.png"
base=R/"runtime-test"/"results"
images=[
 base/"openzork-scummvm-golden-scene-sequence-0e2fdd87"/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png",
 base/"openzork-pinned-vb30-supervised-sequence-v7-r1"/"pinned-vb30-viewport-768x480.png"
]
with Image.open(sprite_path) as t:
 rgba=np.asarray(t.convert("RGBA"),dtype=np.float64)
mask=(rgba[:,:,3]>=200).astype(np.float64)
rgb=rgba[:,:,:3]
n=float(mask.sum())
assert n>70
kh,kw=mask.shape

def conv_valid(image,kernel):
 H,W=image.shape
 h,w=kernel.shape
 shape=(H+h-1,W+w-1)
 out=np.fft.irfft2(np.fft.rfft2(image,s=shape) * np.fft.rfft2(kernel[::-1,::-1],s=shape),s=shape)
 return out[h-1:H,w-1:W]

def search(raw):
 image=np.asarray(raw,dtype=np.float64)
 h,w=image.shape[:2]
 assert (h,w)==(480,768)
 sse=np.zeros((h-kh+1,w-kw+1),dtype=np.float64)
 for channel in range(3):
  I=image[:,:,channel];T=rgb[:,:,channel]
  sse += conv_valid(I*I,mask) - 2*conv_valid(I,mask*T) + float(np.sum(mask*T*T))
 sse=np.maximum(sse,0.0)
 rms=np.sqrt(sse/(n*3))
 order=np.argsort(rms.ravel())
 tops=[]
 for flat in order[:200]:
  y,x=np.unravel_index(flat,rms.shape)
  if any(abs(x-e["x"])<12 and abs(y-e["y"])<12 for e in tops):
   continue
  tops.append({"x":int(x),"y":int(y),"rgb_RMSE":round(float(rms[y,x]),5)})
  if len(tops)>=5:break
 return tops
result=[]
for path in images:
 with Image.open(path) as im:positions=search(im.convert("RGB"))
 result.append({"path":str(path),
  "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
  "top_00idlea_matches":positions})
record={
 "schema":"OpenZork.OriginalCursorTemplateLocalizationProbe.v1",
 "status":"SOURCE_TEMPLATE_BASED_CURSOR_SEARCH_EXPLORATORY",
 "source_cursor_png":str(sprite_path),
 "cursor_source_sha256":hashlib.sha256(sprite_path.read_bytes()).hexdigest(),
 "alpha_mask_threshold":200,"mask_pixels":n,
 "template_size":[kw,kh],
 "search_mechanism":"FULL_VIEWPORT_FFT_WEIGHTED_RGB_SSD_SOURCE_SPRITE",
 "source_images":result,"candidate_mask_predeclared":False,
 "fidelity_verified":False
}
dest=base/"openzork-pinned-vb30-supervised-sequence-v7-r1"/"cursor-template-localization-v7.json"
if dest.exists():raise RuntimeError("CURSOR_TEMPLATE_PROBE_EXISTS")
dest.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],"source_sprite_sha256":record["cursor_source_sha256"],
 "candidates":[{"file":Path(z["path"]).name,"top":z["top_00idlea_matches"]} for z in result],
 "evidence":str(dest)},ensure_ascii=False))
