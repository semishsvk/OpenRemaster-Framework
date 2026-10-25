"""Create corrected immutable COM probe, without touching prior v8 staged build."""
from pathlib import Path
import hashlib,json,subprocess,sys
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
old=CP/"build_dosboxx_guest_integration_probe_v8.py"
new=CP/"build_dosboxx_guest_integration_probe_r2_v8.py"
if new.exists():raise RuntimeError("GENERATOR_R2_ALREADY_EXISTS")
text=old.read_text(encoding="utf-8")
assert text.count("dosboxx-integration-mouse-20261009-v8")==1
assert text.count('code.add("CD 21 72 13 89 C3 B9 0A 00")')==1
text=text.replace("dosboxx-integration-mouse-20261009-v8","dosboxx-integration-mouse-20261009-v8-r2")
text=text.replace('code.add("CD 21 72 13 89 C3 B9 0A 00")','code.add("CD 21 72 10 89 C3 B9 0A 00")')
new.write_text(text,encoding="utf-8")
p=subprocess.run([sys.executable,"-B",str(new)],capture_output=True,text=True,timeout=30)
assert p.returncode==0,(p.stdout,p.stderr)
result=json.loads(p.stdout.strip().splitlines()[-1])
guest=R/"work"/"OpenZork"/"staging"/"dosboxx-integration-mouse-20261009-v8-r2"/"guest"/"IGPROBE.COM"
assert guest.is_file()
assert result["sha256"]==hashlib.sha256(guest.read_bytes()).hexdigest()
print(json.dumps({"status":"PASS",
 "binary":str(guest),"sha256":result["sha256"],"bytes":guest.stat().st_size,
 "failure_branch":"JUMP_TO_SAFE_DOS_EXIT","old_v8_unmodified":True}))
