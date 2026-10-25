from pathlib import Path
from PIL import Image,ImageStat
import wave,json,numpy as np
root=Path(__file__).resolve().parents[2]
base=root/"runtime-test"/"results"/"openzork-supervised-oracle-passive-7de743cc8"/"fidelity-isolated"/"capture"
frame=base/"frame-0001.bmp";out=base/"frame-0001.png"
with Image.open(frame) as img:
 image=img.convert("RGB")
 image.save(out)
 stat=ImageStat.Stat(image)
 info={"width":image.width,"height":image.height,
       "channel_stdev":[round(x,2) for x in stat.stddev],
       "mean":[round(x,2) for x in stat.mean]}
with wave.open(str(base/"process-0001.wav"),"rb") as w:
 a=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype("float64")
 info["audio_samples"]=len(a)
 info["audio_peak"]=float(np.max(np.abs(a))) if a.size else 0
 info["audio_rms"]=float(np.sqrt(np.mean(a*a))) if a.size else 0
print(json.dumps({"schema":"OpenZork.SupervisedCaptureContentProbe.v1","analysis":info,"png":str(out)}))
