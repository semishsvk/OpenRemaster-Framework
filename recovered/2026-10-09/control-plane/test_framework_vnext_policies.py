import json,sys
from pathlib import Path
p=Path(__file__).with_name("framework-vnext-policies.json")
d=json.loads(p.read_text(encoding="utf-8-sig"))
assert d["schema"]=="OpenRemaster.FrameworkVNextPolicies.v1"
assert d["phase1_baseline"]=="FROZEN_UNCHANGED"
c=d["contracts"]
assert set(["OracleReadinessContract.v1","RuntimeLeaseContract.v1","SchedulerPromotionPolicy.v1","OracleEvidenceLevels.v1"]).issubset(c)
assert c["SchedulerPromotionPolicy.v1"]["max_heavy_lanes"]==3
levels=c["OracleEvidenceLevels.v1"]["ordered_levels"]
assert levels==["DIAGNOSTIC_CAPTURE","ORIGINAL_RUNTIME_OBSERVATION","ALIGNED_ORACLE","DETERMINISTIC_ORACLE","FIDELITY_ATTESTED"]
assert c["OracleEvidenceLevels.v1"]["remote_desktop_stream_max_level"]=="DIAGNOSTIC_CAPTURE"
assert c["OracleReadinessContract.v1"]["failure_policy"]=="FAIL_CLOSED_TO_WARM"
print(json.dumps({"status":"PASS","schema":d["schema"],"contracts":list(c),"phase1":d["phase1_baseline"]},indent=2))
