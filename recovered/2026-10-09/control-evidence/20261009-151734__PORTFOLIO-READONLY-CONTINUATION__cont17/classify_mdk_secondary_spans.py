"""Classify original MDK LEVEL3 secondary plane-triangle ranges.

Does not assign secondary range a render-pass meaning; compares exact
signed-f3 and source record identity between the two structural ranges.
"""
from pathlib import Path
from collections import Counter
import json,struct,hashlib
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
p=ROOT/"source/MDK/TRAVERSE/LEVEL3/LEVEL3O.MTO"
b=p.read_bytes()
assert hashlib.sha256(b).hexdigest()=="6f33536701f57a404f8b25aa5580502cd68389de9ae591b53b018f415f7193ff"
audit=HERE/"MDK_LEVEL3_PLANE_TRIANGLE_DUAL_RANGES.json"
raw=audit.read_bytes();data=json.loads(raw)
assert data["total_source_triangles"]==7205 and data["global_uncovered"]==0 and data["global_duplicate_coverage"]==0
summary=[]
all_kinds=Counter()
all_secondary=Counter()
all_primary=Counter()
for h in data["hmos"]:
    count=h["triangles"];base=h["triangle_stream_absolute"]
    role={}
    # Source audit already pins HMO range and coverage.
    for alt in h["secondary_ranges"]:
       for i in range(alt["second_start"],alt["second_start"]+alt["second_count"]):
           assert i not in role
           role[i]=alt["plane_index"]
    positive=negative=zero=0
    modes=Counter()
    primary=Counter()
    alt=Counter()
    examples=[]
    for tri in range(count):
        off=base+36*tri
        packet=b[off:off+36]
        a,bidx,c,raw_f3=struct.unpack_from("<4H",packet)
        s=raw_f3 if raw_f3<32768 else raw_f3-65536
        category="NEGATIVE" if s<0 else "ZERO" if s==0 else "POSITIVE"
        modes[category]+=1
        if tri in role:
            alt[category]+=1
            all_secondary[category]+=1
            if len(examples)<12:
                examples.append({"triangle_index":tri,"signed_f3":s,"plane_index":role[tri],
                  "source_sha256":hashlib.sha256(packet).hexdigest(),"indices":[a,bidx,c]})
        else:
            primary[category]+=1
            all_primary[category]+=1
    summary.append({"hmo":h["hmo"],"secondary_planes":h["secondary_range_count"],
        "secondary_triangles":h["secondary_triangle_occurrences"],
        "primary_f3_classes":dict(primary),"secondary_f3_classes":dict(alt),
        "secondary_examples":examples})
assert sum(x["secondary_triangles"] for x in summary)==116
assert sum(all_secondary.values())==116 and sum(all_primary.values())==7089
report={
 "schema":"OpenMDK.LEVEL3SecondaryRangeSignedF3Distribution.v1",
 "MTO_sha256":"6f33536701f57a404f8b25aa5580502cd68389de9ae591b53b018f415f7193ff",
 "dual_range_audit_sha256":hashlib.sha256(raw).hexdigest(),
 "primary_total":7089,"secondary_total":116,
 "primary_signed_f3_classes":dict(all_primary),
 "secondary_signed_f3_classes":dict(all_secondary),
 "hmos":summary,
 "evidence_level":"STRUCTURAL_SOURCE_COUNTS_ONLY",
 "semantic_limitation":"No conclusion that secondary spans form a distinct renderer pass, collision group, or transparency group.",
 "original_runtime_or_instruction_replay":False
}
out=HERE/"MDK_SECONDARY_RANGE_F3_CLASSIFICATION.json"
text=(json.dumps(report,indent=2,sort_keys=True)+"\n").encode()
if out.exists():assert out.read_bytes()==text
else:
    with out.open("xb") as f:f.write(text)
print(json.dumps({"status":"PASS_SOURCE_SECONDARY_RANGE_F3_DISTRIBUTION",
 "primary":dict(all_primary),"secondary":dict(all_secondary),
 "per_hmo":[{k:x[k] for k in ("hmo","secondary_planes","secondary_triangles")} for x in summary],
 "report_sha256":hashlib.sha256(text).hexdigest()},sort_keys=True))
