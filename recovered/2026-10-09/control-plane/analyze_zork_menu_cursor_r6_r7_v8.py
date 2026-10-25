"""Read-only original-ZORKDOS title cursor localization using the extracted game cursor.
No host mouse interaction or GUI process launch. Technical image evidence only.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2]
source=R/"work"/"OpenZork"/"runtime"/"assets"/"cursors"/"00idlea.png"
root=R/"runtime-test"/"results"
frames=[
 ("r5_newgame_pressed",root/"openzork-native-dosboxx-mcp-new-game-click-20261009-r5"/"fidelity-isolated"/"capture"/"samples"/"point-02"/"frame-0001.bmp"),
 ("r6_newgame_cursor_correct",root/"openzork-native-dosboxx-extended-newgame-20261009-r6"/"fidelity-isolated"/"capture"/"samples"/"point-02"/"frame-0001.bmp"),
 ("r7_cursor_left_edge",root/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"/"fidelity-isolated"/"capture"/"samples"/"point-02"/"frame-0001.bmp"),
 ("r7_cursor_left_still",root/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"/"fidelity-isolated"/"capture"/"samples"/"point-05"/"frame-0001.bmp"),
]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with Image.open(source) as im:
 rgba=np.asarray(im.convert("RGBA"),dtype=np.float64)
src_rgb=rgba[:,:,:3]
mask=(rgba[:,:,3]>=190).astype(np.float64)
n=mask.sum()
kh,kw=mask.shape
assert n>50
def cross(a,b):
 h,w=a.shape
 bh,bw=b.shape
 size=(h+bh-1,w+bw-1)
 temp=np.fft.irfft2(np.fft.rfft2(a,s=size)*np.fft.rfft2(b[::-1,::-1],s=size),s=size)
 return temp[bh-1:h,bw-1:w]
outputs=[]
for name,path in frames:
 assert path.is_file(),str(path)
 with Image.open(path) as im:
  frame=np.asarray(im.convert("RGB"),dtype=np.float64)
 H,W=frame.shape[:2]
 err=np.zeros((H-kh+1,W-kw+1),dtype=np.float64)
 for ch in range(3):
  A=frame[:,:,ch];T=src_rgb[:,:,ch]
  err+=cross(A*A,mask)-2*cross(A,mask*T)+np.sum(mask*T*T)
 rms=np.sqrt(np.maximum(err,0)/(n*3))
 flattened=np.argsort(rms.ravel())[:600]
 tops=[]
 for index in flattened:
  y,x=np.unravel_index(index,rms.shape)
  if any(abs(x-r["x"])<16 and abs(y-r["y"])<16 for r in tops):continue
  tops.append({"x":int(x),"y":int(y),"template_RGB_RMSE":round(float(rms[y,x]),3)})
  if len(tops)==5:break
 # Original native New Game WGC 644x557: button approx x260..385/y442..480.
 target=(250,425,394,492)
 target_scores=rms[target[1]:min(target[3],rms.shape[0]),
                   target[0]:min(target[2],rms.shape[1])]
 valid=target_scores.size>0
 outputs.append({"run":name,"WGC_file":str(path),"sha256":sha(path),
                 "src_template":source.name,"best_matches":tops,
                 "target_window_xyxy":target,
                 "target_best_RMSE":round(float(target_scores.min()),3) if valid else None,
                 "overall_best_RMSE":round(float(rms.min()),3)})
record={
 "schema":"OpenZork.NativeOriginalCursorLocalization.v1",
 "status":"EXPLORATORY_SOURCE_SPRITE_TEMPLATE_PROBE_NOT_VERIFIED_INPUT_GATE",
 "extracted_cursor_sha256":sha(source),"template_size":[kw,kh],
 "alpha_mask_pixels":int(n),"localizations":outputs,
 "game_input_pass":"NOT_TESTED","scene_transition_fidelity":"NOT_TESTED",
 "host_mouse_changed":False}
result=root/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"/"cursor-localization-v8.json"
if result.exists():raise RuntimeError("CURSOR_PROBE_RESULT_ALREADY_EXISTS")
result.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],
"positions":[{"name":x["run"],"best":x["best_matches"][:2],
 "button_score":x["target_best_RMSE"]} for x in outputs],
"evidence":str(result)},ensure_ascii=False))
