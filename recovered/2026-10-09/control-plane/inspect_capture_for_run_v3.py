import json,sys,wave
from pathlib import Path
from PIL import Image,ImageStat
import numpy as np
root=Path(__file__).resolve().parents[2]
run=sys.argv[1]
if "/" in run or "\\" in run:raise ValueError("run id only")
capture=root/"runtime-test"/"results"/run/"fidelity-isolated"/"capture"
with Image.open(capture/"frame-0001.bmp") as im:
 a=im.convert("RGB")
 a.save(capture/"frame-0001.png")
 d=ImageStat.Stat(a)
 info={"size":[a.width,a.height],"mean":[round(x,1) for x in d.mean],"stddev":[round(x,1) for x in d.stddev]}
with wave.open(str(capture/"process-0001.wav"),"rb") as w:
 pcm=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype(np.float64)
 info["audio_rms"]=round(float(np.sqrt(np.mean(pcm*pcm))) if pcm.size else 0,2)
 info["audio_peak"]=int(np.max(np.abs(pcm))) if pcm.size else 0
print(json.dumps({"run":run,"image":str(capture/"frame-0001.png"),"stats":info}))
