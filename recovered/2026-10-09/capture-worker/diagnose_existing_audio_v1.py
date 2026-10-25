"""Read-only process-bound audio diagnostics on existing unowned GUI runtime.
These WAVs are not admissible fidelity evidence: no run ownership or deterministic replay.
"""
from datetime import datetime,timezone
import json,subprocess,sys,uuid,wave
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"control-plane"))
from fidelity_runtime_isolation_v1 import gui_conflicts,process_identity,sha256
ROOT=Path(__file__).resolve().parents[2]
EXE=Path(__file__).with_name("capture_process_audio.exe")
base=ROOT/"runtime-test"/"results"/("process-audio-existing-diagnostic-"+uuid.uuid4().hex[:8])
base.mkdir()
windows=gui_conflicts()
requests=[
  ("DOSBOX","dosbox","DOSBox"),
  ("SCUMMVM_GAME","scummvm","Zork Nemesis"),
]
rows=[]
for klass,exe_name,title in requests:
    entry={"class":klass,"status":"NO_MATCH"}
    matches=[x for x in windows if exe_name in Path(x["executable"]).name.lower() and title.lower() in x["title"].lower()]
    if matches:
        x=matches[0]
        ident=process_identity(x["pid"])
        entry.update(pid=x["pid"],hwnd=x["hwnd"],title=x["title"])
        if not ident or ident["creation_ticks_100ns"]!=x["creation_ticks_100ns"]:
            entry["status"]="PROCESS_IDENTITY_CHANGED"
        else:
            outfile=base/(klass+".wav")
            cmd=[str(EXE),str(x["pid"]),str(x["creation_ticks_100ns"]),"2200",str(outfile)]
            try:
                p=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
                if p.returncode or not outfile.exists():
                    entry.update(status="PROCESS_AUDIO_UNAVAILABLE",diagnostic=p.stderr[-400:])
                else:
                    with wave.open(str(outfile),"rb") as w:
                        samples=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2")
                        rms=float(np.sqrt(np.mean(samples.astype(float)**2))) if samples.size else 0
                        entry.update(status="DIAGNOSTIC_PROCESS_AUDIO",frames=w.getnframes(),sample_rate=w.getframerate(),
                                     bytes=outfile.stat().st_size,nonzero=int(np.count_nonzero(samples)),
                                     rms=round(rms,3),audio_sha256=sha256(outfile),audio_path=str(outfile))
            except Exception as e:
                entry.update(status="CAPTURE_ERROR",error=str(e),type=type(e).__name__)
    rows.append(entry)
report={"schema":"OpenRemaster.UnownedProcessAudioDiagnostic.v1","status":"DIAGNOSTIC_ONLY_NOT_FIDELITY",
        "date_utc":datetime.now(timezone.utc).isoformat(),
        "source":"UNOWNED_PREEXISTING_RUNTIME_AUDIO_STREAMS",
        "backend":"PROCESS_LOOPBACK_INCLUDE_TARGET_TREE",
        "binary_sha256":sha256(EXE),"no_process_stop":True,"rows":rows}
out=base/"diagnostic-report.json"
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],
                  "results":[{k:x.get(k) for k in ("class","status","pid","rms","nonzero","frames","audio_sha256","diagnostic")} for x in rows],
                  "report":str(out)},ensure_ascii=False))
