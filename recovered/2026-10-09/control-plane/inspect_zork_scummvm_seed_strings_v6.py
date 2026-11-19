"""Read-only bounded ASCII scene keyword and header probe for ScummVM save slot 000."""
from pathlib import Path
import re,json,struct,hashlib
R=Path(__file__).resolve().parents[2]
save=R/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"saves"/"znemesis.000"
b=save.read_bytes()
runs=[(m.start(),m.group().decode("latin1","replace")) for m in re.finditer(rb"[\x20-\x7E]{4,}",b)]
scene_re=re.compile(r"(?:[VT][A-Z][0-9A-Z]{2}|[A-Z]{2}[0-9]{2})",re.I)
matches=[{"offset":i,"value":x[:150]} for i,x in runs if scene_re.search(x)]
tagged=[]
for pat in (b"VB20",b"VB30",b"VJ10",b"TA30",b"TEMPLE",b"CONSERV",b"current",b"node",b"location",b"room"):
 offsets=[m.start() for m in re.finditer(re.escape(pat),b,re.I)]
 tagged.append({"needle":pat.decode(),"matches":offsets[:20],"count":len(offsets)})
print(json.dumps({"size":len(b),"sha256":hashlib.sha256(b).hexdigest(),
 "first_128_hex":b[:128].hex(),"ascii_runs":len(runs),
 "first_runs":[{"offset":i,"text":x[:120]} for i,x in runs[:28]],
 "candidate_scene_strings":matches[:80],"keyword_offsets":tagged},ensure_ascii=False))
