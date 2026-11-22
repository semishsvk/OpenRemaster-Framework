"""Nonintrusive WGC diagnostic on existing windows. NEVER PROMOTE to fidelity proof:
these GUI processes were not launched/owned by FidelityRuntimeIsolation supervisor.
"""
from datetime import datetime,timezone
from pathlib import Path
import json,os,subprocess,sys,uuid
from PIL import Image,ImageStat
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"control-plane"))
from fidelity_runtime_isolation_v1 import gui_conflicts,process_identity,sha256

ROOT=Path(__file__).resolve().parents[2]
EXE=Path(__file__).with_name("capture_window_wgc.exe")
OUT=ROOT/"runtime-test"/"results"/("wgc-existing-windows-diagnostic-"+uuid.uuid4().hex[:8])
OUT.mkdir()
windows=gui_conflicts()
choices=[
 ("DOSBOX","dosbox","dosbox"),
 ("SCUMMVM_GAME","scummvm","Zork Nemesis"),
 ("GODOT_ZORK","godot","OpenZork"),
]
seen=set()
results=[]
for label,name,title in choices:
    filtered=[w for w in windows if name in Path(w["executable"]).name.lower()
              and title.lower() in w["title"].lower()]
    row={"class":label,"status":"NOT_FOUND"}
    if filtered:
        w=next((w for w in filtered if w["pid"] not in seen),filtered[0])
        seen.add(w["pid"])
        ident=process_identity(w["pid"])
        row.update({"status":"UNTESTED","pid":w["pid"],"hwnd":w["hwnd"],
                    "title":w["title"],"executable":w["executable"],
                    "creation_ticks_100ns":w["creation_ticks_100ns"]})
        if ident and ident["creation_ticks_100ns"]==w["creation_ticks_100ns"]:
            d=OUT/label
            d.mkdir()
            fn=d/"frame-0001.bmp"
            command=[str(EXE),str(w["hwnd"]),str(w["pid"]),str(w["creation_ticks_100ns"]),str(fn)]
            try:
                p=subprocess.run(command,timeout=12,text=True,capture_output=True)
                if p.returncode!=0:
                    row.update(status="CAPTURE_BLOCKED",error=p.stderr[-700:])
                elif not fn.is_file():
                    row.update(status="FRAME_MISSING")
                else:
                    with Image.open(fn) as image:
                        img=image.convert("RGB")
                        stats=ImageStat.Stat(img)
                        row.update(status="DIAGNOSTIC_LOCAL_CAPTURE",width=img.width,height=img.height,
                                   channel_stdev=[round(v,3) for v in stats.stddev],
                                   mean=[round(v,2) for v in stats.mean])
                    row["frame_path"]=str(fn)
                    row["frame_sha256"]=sha256(fn)
                    row["image_bytes"]=fn.stat().st_size
            except Exception as e:
                row.update(status="CAPTURE_ERROR",type=type(e).__name__,error=str(e))
        else:
            row.update(status="PROCESS_OWNER_CHANGED")
    results.append(row)
valid=[r for r in results if r["status"]=="DIAGNOSTIC_LOCAL_CAPTURE"]
report={"schema":"OpenRemaster.UnownedGUIWGC_Diagnostic.v1",
        "status":"DIAGNOSTIC_ONLY_NO_FIDELITY_PASS",
        "date_utc":datetime.now(timezone.utc).isoformat(),
        "known_foreign_gui_count":len(windows),
        "source":"EXISTING_UNOWNED_PROCESSES_NOT_ORIGINAL_CAPTURE_AUTHORITY",
        "rdc_stream_used":False,"native_wgc_sha256":sha256(EXE),
        "captures":results,"valid_count":len(valid),"distinct_frame_hashes":len(set(x["frame_sha256"] for x in valid)),
        "no_process_termination":True,"no_input_injection":True}
dest=OUT/"diagnostic-report.json"
dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"status":report["status"],"valid_count":len(valid),
                  "distinct_hashes":report["distinct_frame_hashes"],"items":[
                  {k:r.get(k) for k in ("class","status","pid","title","width","height","frame_sha256","error")}
                  for r in results],"output":str(dest)},ensure_ascii=False))
