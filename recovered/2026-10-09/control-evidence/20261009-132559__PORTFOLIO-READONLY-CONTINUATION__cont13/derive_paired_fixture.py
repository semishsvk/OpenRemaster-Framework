"""Derive a fixed corpus-backed pair of Map5 GLOB218 child input classes."""
from pathlib import Path
import json,hashlib,collections
BASE=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
src=BASE/"output/projects/OpenUltima8/evidence/20261008-094213__AUTONOMOUS-4H__cycle01/map5-materialization-sourceir-v3.json"
typ=BASE/"source/Ultima 8/ENGLISH/STATIC/TYPEFLAG.DAT"
a=src.read_bytes();b=typ.read_bytes()
assert hashlib.sha256(a).hexdigest()=="a5c8c9aa9e9da9ceecd41c1cecd18e7f20c18f2822ba38b878b07f613b8a5638"
assert hashlib.sha256(b).hexdigest()=="2b07f4a6acc5504d9d07c47d3686f74107cac7b594ccb18251e01249fadebc62"
j=json.loads(a)
rows=[r for r in j["potential_instances"] if r["source_kind"]=="GLOB_POTENTIAL" and r["glob_id"]==218]
assert len(rows)==32
pairs=[]
for idx in (2378,2379):
    sub=[r for r in rows if r["definition_ordinal"]==idx]
    assert len(sub)==16 and collections.Counter(r["shape"] for r in sub)=={347:12,128:4}
    high=[r for r in sub if r["shape"]==347];low=[r for r in sub if r["shape"]==128]
    assert all(b[8*r["shape"]]&128 for r in high)
    assert all(not(b[8*r["shape"]]&128) for r in low)
    assert all((b[8*r["shape"]+1]>>4)==0 for r in sub)
    def one(r):
        return {"source_instance_id":r["instance_id"],"source_member_raw_offset":r["source_member_raw_offset"],
                "shape":r["shape"],"frame":r["frame"],"world":r["world"],
                "shape_typeflag_bytes":b[8*r["shape"]:8*r["shape"]+8].hex(),
                "runtime_instance_id":"UNBOUND","activation_verified":False}
    pairs.append({"marker_id":f"fixed:m5:r{idx}","glob_id":218,
                  "total_potential_children":16,"bit7_special_potential":12,"ordinary_potential":4,
                  "special_example":one(high[0]),"ordinary_example":one(low[0]),
                  "structural_inputs_only":True})
p={"schema":"OpenUltima8.Map5GLOB218PairedSpecialLifecycleFixture.v1",
   "source_ir_sha256":hashlib.sha256(a).hexdigest(),"typeflag_sha256":hashlib.sha256(b).hexdigest(),
   "markers":pairs,"expected_special_count":24,"expected_ordinary_count":8,
   "usage":"Pair with original handle identity and active-context state under future approved runtime replay; do not treat potential children as live instances.",
   "scope":"Pure original corpus projection, not executed gameplay or renderer fidelity"}
out=HERE/"U8_GLOB218_PAIRED_SOURCE_FIXTURE.json"
blob=(json.dumps(p,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode()
if out.exists():assert out.read_bytes()==blob
else:
    with out.open("xb") as f:f.write(blob)
print(json.dumps({"status":"PASS_SOURCE_IDENTITY_PAIRED_FIXTURE_ONLY",
                  "marker_count":len(pairs),"potential_special":24,"potential_ordinary":8,
                  "sha256":hashlib.sha256(blob).hexdigest(),
                  "example_special":pairs[0]["special_example"]["source_instance_id"],
                  "example_ordinary":pairs[0]["ordinary_example"]["source_instance_id"]},sort_keys=True))
