"""Stable ScummVM Zork scene reference from original game data and private save.
Three exact WGC bit-identical frames, no input. NOT native DOSBox fidelity.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,wave
import numpy as np
from PIL import Image,ImageStat

ROOT=Path(__file__).resolve().parents[2]
rid="openzork-scummvm-golden-scene-sequence-0e2fdd87"
base=ROOT/"runtime-test"/"results"/rid/"fidelity-isolated"/"capture"
manifest=base/"capture-attestation.json"
m=json.loads(manifest.read_text(encoding="utf-8"))
assert m["capture_schedule_schema"]=="OpenRemaster.BoundedFrameSchedule.v1"
rows=m["frames"]
assert len(rows)==3 and len({r["sha256"] for r in rows})==1,"Frame state drift across bounded capture"
sources=[base/row["path"] for row in rows]
assert all(f.is_file() for f in sources)
frames=[]
for path in sources:
 with Image.open(path) as im:
  im=im.convert("RGB")
  assert im.size==(962,768)
  frames.append(np.asarray(im).copy())
assert all(np.array_equal(frames[0],x) for x in frames[1:])
view=(96,167,864,647) # bounded observed visual content in 962x768 WGC original window
with Image.open(sources[0]) as src:
 viewport=src.convert("RGB").crop(view)
 crop=base/"golden-scene-viewport-768x480.png"
 viewport.save(crop)
 png=base/"golden-scene-full-window.png"
 src.save(png)
 x=np.asarray(viewport,dtype=np.float64)
mean=x.mean(axis=(0,1))
std=x.std(axis=(0,1))
previous=ROOT/"runtime-test"/"results"/"openzork-scummvm-seeded-scene-8938d2e819"/"fidelity-isolated"/"capture"/"frame-0001.bmp"
diff={}
if previous.is_file():
 with Image.open(previous) as prev:
  old=np.asarray(prev.convert("RGB").crop(view),dtype=np.int16)
 new=np.asarray(viewport,dtype=np.int16)
 delta=np.abs(old-new)
 diff={"previous_independent_run_sha256":hashlib.sha256(previous.read_bytes()).hexdigest(),
       "absolute_pixel_difference_sum":int(delta.sum()),
       "changed_pixel_fraction":round(float(np.mean(np.any(delta>15,axis=2))),8),
       "identical_across_independent_runs":bool(np.array_equal(old,new))}
audio=base/"process-0001.wav"
with wave.open(str(audio),"rb") as f:
 raw=f.readframes(f.getnframes())
 samples=np.frombuffer(raw,dtype="<i2").astype(np.float64)
 a={"frames":f.getnframes(),"channels":f.getnchannels(),
   "sample_rate":f.getframerate(),
   "peak":round(float(np.max(np.abs(samples))) if samples.size else 0,3),
   "rms":round(float(np.sqrt(np.mean(samples*samples))) if samples.size else 0,4)}
res={
 "schema":"OpenZork.ScummVMGoldenSceneStability.v1",
 "date_utc":datetime.now(timezone.utc).isoformat(),
 "status":"GOLDEN_SCENE_VISUAL_STABLE_TECHNICAL_PASS",
 "source_game_data":"ORIGINAL_ZORK_NEMESIS_DATA_READ_ONLY",
 "runtime_engine":"SCUMMVM_2.0.0_ZVISION",
 "native_ZORKDOS_executable_used":False,
 "save_slot_source_sha256":"3742d4e4be25561bea21ee1e63aed9029bef409f9cb56b323f8dd5ef254da5dc",
 "capture_offsets_seconds":[r["requested_at_seconds"] for r in rows],
 "three_frame_exact_byte_identity":True,
 "game_image_window_size":[962,768],
 "viewport_roi_physical_xyxy":list(view),
 "viewport_dimensions":[viewport.width,viewport.height],
 "viewport_file":str(crop),
 "viewport_sha256":hashlib.sha256(crop.read_bytes()).hexdigest(),
 "rgb_mean":list(np.round(mean,2)),
 "rgb_std":list(np.round(std,2)),
 "compared_to_independent_seeded_run":diff,
 "audio_capture_observed":a,
 "audio_wav_sha256":hashlib.sha256(audio.read_bytes()).hexdigest(),
 "owner_pid":m["pid"],"owner_hwnd":m["hwnd"],
 "manifest_sha256":hashlib.sha256(manifest.read_bytes()).hexdigest(),
 "gameplay_input_replay_verified":False,"fidelity_verified":False,
 "reconstruction_comparison_performed":False,
 "evidence_use":"SCUMMVM_SEED_SCENE_CROSSVALIDATION_REFERENCE_ONLY"
}
dest=base.parent.parent/"golden-scene-stability.json"
dest.write_text(json.dumps(res,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":res["schema"],"status":res["status"],
 "single_run_frames_identical":res["three_frame_exact_byte_identity"],
 "independent_run_identical":diff.get("identical_across_independent_runs"),
 "independent_run_changed_fraction":diff.get("changed_pixel_fraction"),
 "viewport_sha256":res["viewport_sha256"],
 "audio":a,"viewport":str(crop),"evidence":str(dest)}))
