from pathlib import Path
from PIL import Image,ImageStat
import json,wave,numpy as np
root=Path(__file__).resolve().parents[2]
run=root/"runtime-test"/"results"/"openzork-supervised-oracle-passive-7f3bfa845"/"fidelity-isolated"/"capture"
path=run/"frame-0001.bmp";out=run/"frame-0001.png"
with Image.open(path) as i:
 j=i.convert("RGB");j.save(out)
 stats=ImageStat.Stat(j);dims=[j.width,j.height];std=stats.stddev
with wave.open(str(run/"process-0001.wav"),"rb") as w:
 a=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2")
 rms=float(np.sqrt(np.mean(a.astype("float64")**2))) if a.size else 0
print(json.dumps({"image":str(out),"dims":dims,"stdev":std,"audio_rms":rms,"audio_peak":int(max(abs(a.astype("int32")))) if a.size else 0}))
