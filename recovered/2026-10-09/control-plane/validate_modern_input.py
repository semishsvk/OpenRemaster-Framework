import json,sys
from pathlib import Path
p=Path(sys.argv[1])
d=json.loads(p.read_text(encoding="utf-8"))
fail=[]
if d.get("schema")!="ModernInputContract.v1": fail.append("SCHEMA")
acts=d.get("semantic_actions",[])
if not acts or len(acts)!=len(set(acts)): fail.append("ACTIONS")
tb=d.get("test_backend",{})
if not tb.get("deterministic"): fail.append("TEST_NOT_DETERMINISTIC")
if not tb.get("host_coordinate_independent"): fail.append("HOST_COORDINATE_DEPENDENT")
sp=d.get("semantics_policy",{})
for k in ("preserve_gameplay_timing","preserve_collision","preserve_simulation"):
    if sp.get(k) is not True: fail.append("SEMANTICS_"+k.upper())
profiles=d.get("profiles",{})
for k in ("test","modern","classic"):
    if k not in profiles: fail.append("PROFILE_"+k.upper())
out={"schema":"ModernInputValidation.v1","project":d.get("project"),"status":"PASS" if not fail else "FAIL","failures":fail}
print(json.dumps(out,indent=2))
raise SystemExit(0 if not fail else 1)
