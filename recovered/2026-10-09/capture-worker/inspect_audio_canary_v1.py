from pathlib import Path
import wave,json,numpy as np
root=Path(__file__).resolve().parents[2]/"runtime-test"/"results"
ds=sorted(root.glob("process-loopback-*"),key=lambda x:x.stat().st_mtime,reverse=True)[:3]
out=[]
for d in ds:
 for p in d.glob("*.wav"):
  with wave.open(str(p),"rb") as w:
   raw=w.readframes(w.getnframes())
   a=np.frombuffer(raw,dtype="<i2")
   rms=float(np.sqrt(np.mean(a.astype(float)**2))) if len(a) else 0
   peak=int(np.max(abs(a.astype(np.int32)))) if len(a) else 0
   fft0=np.abs(np.fft.rfft(a[::2].astype(float))) if len(a)>40000 else np.array([])
   freqs=np.fft.rfftfreq(len(a[::2]),1/44100) if len(a)>40000 else np.array([])
   at440=float(np.max(fft0[(freqs>430)&(freqs<450)])) if len(fft0) else None
   out.append({"path":str(p),"frames":w.getnframes(),"rms":rms,"peak":peak,"at440":at440,"max_abs":peak})
print(json.dumps(out))
