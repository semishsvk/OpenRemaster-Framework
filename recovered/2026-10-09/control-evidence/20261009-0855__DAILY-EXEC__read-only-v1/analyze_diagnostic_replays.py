"""Read-only replay repeatability probe for existing MDK diagnostic render outputs.
Never treats image similarity as original-runtime fidelity.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os
ROOT=Path(r"F:\Remaster Framework\work\OpenMDK1-Fidelity-Candidate-001-20261008")
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def seal(p,x):
    with p.open("xb") as f:
        f.write((json.dumps(x,sort_keys=True,indent=2)+"\n").encode());f.flush();os.fsync(f.fileno())
    return sha(p)
runs={name:ROOT/"evidence"/name for name in ["diagnostic1","render1","render2"]}
smokes={name:load(root/"smoke.json") for name,root in runs.items()}
for key,smoke in smokes.items():
    assert smoke["ticks"]==360 and smoke["status"]=="PASS"
    assert smoke["collision"]["mismatches"]==0 and not smoke["portal"]["failures"]
normalized={}
for name,smoke in smokes.items():
    normalized[name]={k:v for k,v in smoke.items() if k!="renderer"}
identical_structural=normalized["render1"]==normalized["render2"]
identical_diagnostic=normalized["diagnostic1"]==normalized["render2"]
images=[]
for frame in [1,90,180,300]:
    name=f"frame_{frame:03d}.png"
    files=[runs[r]/name for r in ("render1","render2")]
    assert all(f.is_file() for f in files)
    images.append({"frame":frame,
       "sha256":[sha(p) for p in files],
       "bytes":[p.stat().st_size for p in files],
       "byte_identical":sha(files[0])==sha(files[1])})
record={"schema":"OpenMDK1.DiagnosticRepeatabilityAudit.v1",
   "observed_at_utc":datetime.now(timezone.utc).isoformat(),
   "source_scope":"Existing locally generated diagnostic Godot frames; only runtime self-repeatability.",
   "smoke_sha256":{k:sha(v/"smoke.json") for k,v in runs.items()},
   "structural_trace_identical_repetitions":identical_structural,
   "diagnostic_vs_renderer_trace_identical":identical_diagnostic,
   "frames":images,
   "all_frame_png_byte_identical":all(x["byte_identical"] for x in images),
   "source_retail_capture_present":(ROOT/"evidence"/"retail-gameplay-001.png").is_file(),
   "capture_point_provenance_verified":False,
   "source_original_runtime_fidelity_pass":False,
   "known_blockers":smokes["render2"].get("limitations",[]),
   "verdict":"DIAGNOSTIC_REPEATABILITY_PASS" if identical_structural and all(x["byte_identical"] for x in images) else "DIAGNOSTIC_REPEATABILITY_VARIANCE",
   "fidelity_promotion":"HOLD_UNTIL_ORIGINAL_RUNTIME_CAPTURE_POINT_AND_RENDERIR_GEOMETRY"}
receipt=seal(OUT/"MDK1_DIAGNOSTIC_REPLAY_AUDIT.json",record)
print(json.dumps({"verdict":record["verdict"],"frames_identical":[x["byte_identical"] for x in images],
    "trace_identical":identical_structural,
    "sha256":receipt,"fidelity_promotion":record["fidelity_promotion"]},indent=2))
