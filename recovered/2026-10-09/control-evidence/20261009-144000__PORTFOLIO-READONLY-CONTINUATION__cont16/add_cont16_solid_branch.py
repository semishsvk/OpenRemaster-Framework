"""Record new source-static HMO2 material branch inside owned CONT16 report."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
mdk=json.loads((HERE/"MDK_LEVEL3_SOLID_COLOR_BRANCH.json").read_text())
assert mdk["source_rasterizer"] if "source_rasterizer" in mdk else True
assert mdk["original_solid_fill_function"]=="0x415260"
assert mdk["palette_color_index"]==16 and len(mdk["source_opcode_checks"])==19
assert not mdk["fidelity_verified"] and mdk["original_game_instructions_executed"]==0
sha=lambda name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
def dump(path,payload):
    path.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
delta_path=HERE/"SEMANTIC_DELTA.json"
hand_path=HERE/"READ_ONLY_HANDOFF.json"
manifest_path=HERE/"manifest.json"
d=json.loads(delta_path.read_text(encoding="utf-8"))
h=json.loads(hand_path.read_text(encoding="utf-8"))
m=json.loads(manifest_path.read_text(encoding="utf-8"))
assert h["semantic_delta_sha256"]==sha("SEMANTIC_DELTA.json")
assert len(h["portfolio"])==23
f=d["new_focus"]["OpenMDK1"]
f.update(
  status="AUTHENTIC_LEVEL3_TRIANGLE_F3_MINUS16_SOLID_INDEX16_SOURCE_STATIC_PASS_RUNTIME_HOLD",
  progress="Original HMO2 triangle0 has signed-f3=-16, original negative-code dispatch calls rasterizer0x415260 with palette index16; uses REP STOSD/STOSB solid-color scanline fill and bypasses profileA/B callback table on that branch.",
  next="Bind live camera/projected vertices and clipping for this precise original triangle, then compare solid-fill pixels against original runtime capture under admission.")
d["original_source_report_sha256"]["MDK_LEVEL3_SOLID_COLOR_BRANCH.json"]=sha("MDK_LEVEL3_SOLID_COLOR_BRANCH.json")
d["MDK_original_negative_branch_opcode_checks"]=19
for row in h["portfolio"]:
    if row["project"]=="OpenMDK1":row.update(f)
h["reproduce"]["mdk_solid_branch"]="python -B mdk_solid_branch.py"
h["source_evidence"]["MDK_rasterizer_source_va"]="0x415260"
h["source_evidence"]["MDK_solid_palette_index"]=16
h["source_evidence"]["MDK_source_negative_branch_opcode_checks"]=19
h["source_evidence"]["MDK_negative_branch_sha256"]=sha("MDK_LEVEL3_SOLID_COLOR_BRANCH.json")
dump(delta_path,d)
h["semantic_delta_sha256"]=sha("SEMANTIC_DELTA.json")
dump(hand_path,h)
summary_path=HERE/"CONT16_SUMMARY.md"
summary=summary_path.read_text(encoding="utf-8")
addition=("\n## Addendum: authentic MDK triangle negative material branch\n"
 "Original HMO_2 triangle0 signed-f3=-16 takes sorter negative branch\n"
 "0x40C93F → 0x40C97C, produces color index16 and calls rasterizer\n"
 "0x415260 via 0x40C90B. It duplicates 0x10 into 0x10101010 and\n"
 "uses REP STOSD/STOSB scanline fills. The 19 source opcode anchors\n"
 "are pinned in MDK_LEVEL3_SOLID_COLOR_BRANCH.json. This source route\n"
 "does not select profile A/B function pointer callbacks. Original\n"
 "camera, clipping, visibility and pixels remain NOT VERIFIED.\n")
if addition not in summary:
    summary_path.write_text(summary+addition,encoding="utf-8")
existing={x["file"]:x for x in m["outputs"]}
for file in ("mdk_solid_branch.py","MDK_LEVEL3_SOLID_COLOR_BRANCH.json","add_cont16_solid_branch.py"):
    existing[file]={"file":file,"role":"ORIGINAL_SOURCE_STATIC_RASTER_BRANCH","sha256":sha(file)}
for file in ("SEMANTIC_DELTA.json","READ_ONLY_HANDOFF.json","CONT16_SUMMARY.md"):
    existing[file]["sha256"]=sha(file)
m["outputs"]=[existing[key] for key in sorted(existing)]
dump(manifest_path,m)
assert all(sha(x["file"])==x["sha256"] for x in m["outputs"])
assert len(json.loads(hand_path.read_text(encoding="utf-8"))["portfolio"])==23
print(json.dumps({"result":"PASS_CONT16_MDK_SOURCE_BRANCH_RECORDED",
                   "mdk_raster":"0x415260","palette_index":16,
                   "artifacts":len(m["outputs"]),
                   "handoff_sha256":sha("READ_ONLY_HANDOFF.json"),
                   "manifest_sha256":sha("manifest.json")},sort_keys=True))
