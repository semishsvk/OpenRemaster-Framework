"""CONT18: independently validate MDK original plane-side triangle selection.

Read only pinned MDK95.EXE, LEVEL3O.MTO and previous original source
range audit. Static x86 disassembly and pure finite float-side fixtures;
NO original instructions or renderer/run/capture executed.
"""
from pathlib import Path
import sys,struct,json,hashlib
from capstone import Cs,CS_ARCH_X86,CS_MODE_32

ROOT=Path(r"F:\Remaster Framework")
RUN=Path(__file__).resolve().parent
EXE=ROOT/"source/MDK/MDK95.EXE"
MTO=ROOT/"source/MDK/TRAVERSE/LEVEL3/LEVEL3O.MTO"
PREV=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-151734__PORTFOLIO-READONLY-CONTINUATION__cont17/MDK_LEVEL3_PLANE_TRIANGLE_DUAL_RANGES.json"
SHA=lambda b:hashlib.sha256(b).hexdigest()
exe=EXE.read_bytes();mto=MTO.read_bytes();prev=PREV.read_bytes()
assert SHA(exe)=="e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788"
assert SHA(mto)=="6f33536701f57a404f8b25aa5580502cd68389de9ae591b53b018f415f7193ff"
assert SHA(prev)=="d0ceace9b390922a1773cfff5226e6af4fc479e2e74e83b1a4e5da761fed18df"
old=json.loads(prev)
assert old["total_source_triangles"]==7205 and old["global_uncovered"]==old["global_duplicate_coverage"]==0
sys.path.insert(0,str(ROOT/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load,offset
b,sections=load();assert b==exe
cs=Cs(CS_ARCH_X86,CS_MODE_32)
regions=[
 ("PARSER",0x419ee0,0x419fdb),
 ("SIDE_TEST_AND_POSITIVE_MODE1",0x409a6c,0x409b72),
 ("NEGATIVE_MODE1",0x409b78,0x409c37),
 ("NEGATIVE_MODE0",0x409c37,0x409d04),
 ("POSITIVE_MODE0",0x409d04,0x409dc4),
 ("SPAN_CONSUMER",0x409860,0x409a1b),
 ("RUNTIME_BLOB_ENTRY",0x432376,0x4323cd)
]
ops={}
byte_regions=[]
for label,a,z in regions:
    start=offset(sections,a,z-a)
    raw=b[start:start+z-a]
    assert len(raw)==z-a
    listing=list(cs.disasm(raw,a))
    assert listing and listing[0].address==a and listing[-1].address+listing[-1].size==z,(
        "INSTRUCTION_REGION_NOT_ALIGNED",label,hex(a),hex(z))
    byte_regions.append({"name":label,"begin":hex(a),"end":hex(z),"sha256":SHA(raw)})
    for i in listing:
        if i.address in ops:
            assert ops[i.address].bytes==i.bytes
        ops[i.address]=i

checks=[]
def must(a,mnemonic,fragment):
    x=ops.get(a)
    assert x is not None and x.mnemonic==mnemonic and fragment in x.op_str,(
        "ORIGINAL_OPCODE_CONTRACT_MISMATCH",hex(a),mnemonic,fragment,
        None if x is None else(x.mnemonic,x.op_str))
    checks.append({"source_va":hex(a),"opcode":x.mnemonic+" "+x.op_str})
# HMO runtime loader original plane-count*44, triangle-count*36 and vertex-count*12.
for a,m,n in [
 (0x432376,"call","0x41ab44"),(0x4323c8,"call","0x419ee0"),
 (0x419f1f,"mov","dword ptr [eax]"),
 (0x419f21,"lea","[esi*4]"),(0x419f28,"sub","edx, esi"),
 (0x419f2a,"shl","edx, 2"),(0x419f2d,"sub","edx, esi"),
 (0x419f32,"shl","edx, 2"),
 (0x419f3a,"mov","dword ptr [eax]"),(0x419f45,"shl","edx, 3"),
 (0x419f48,"add","edx, ecx"),(0x419f4d,"shl","edx, 2"),
 (0x419f55,"mov","dword ptr [eax]"),(0x419f60,"shl","edx, 2"),
 (0x419f63,"sub","edx, ecx"),(0x419f68,"shl","edx, 2"),
 (0x419f7e,"mov","dword ptr [ebx]"),
 (0x419f80,"add","dword ptr [eax + 0x1c]"),
 (0x419f83,"mov","dword ptr [eax + 0x1c]"),
 (0x419f86,"add","eax, 0x2c"),
 (0x419f8b,"add","dword ptr [eax - 0xc]"),
 (0x419f8f,"mov","dword ptr [eax - 0xc]")
]:must(a,m,n)

# Original d = n·P + D using [0x4a2468] as three float values
# and [esi+0..0xc] as plane normal and offset.
for a,m,n in [
 (0x409a80,"mov","[0x4a2468]"),
 (0x409a86,"fld","[esi + 4]"),
 (0x409a89,"fmul","[edx + 4]"),
 (0x409a8c,"fld","[esi]"),
 (0x409a8e,"fmul","[edx]"),
 (0x409a92,"fld","[esi + 8]"),
 (0x409a95,"fmul","[edx + 8]"),
 (0x409a9a,"fadd","[esi + 0xc]"),
 (0x409a9d,"mov","[0x499f8c]"),
 (0x409aa8,"je","0x409c37"),
 (0x409aae,"fldz",""),
 (0x409ab0,"fcomp","[ebp - 0x14]"),
 (0x409ab6,"jae","0x409b78"),
 (0x409c37,"fldz",""),(0x409c39,"fcomp","[ebp - 0x14]"),
 (0x409c3f,"jb","0x409d04")
]:must(a,m,n)

# Mode flag !=0 positive primary; <=0 secondary.
for a,m,n in [
 (0x409b0a,"mov","[esi + 0x14]"),(0x409b0f,"sar","ebx, 0x10"),
 (0x409b12,"mov","word ptr [esi + 0x14]"),
 (0x409b16,"call","0x409860"),
 (0x409bc6,"mov","[esi + 0x18]"),(0x409bcb,"sar","ebx, 0x10"),
 (0x409bce,"mov","word ptr [esi + 0x18]"),
 (0x409bd2,"call","0x409860")
]:must(a,m,n)
# Mode flag ==0 positive primary, <=0 secondary.
for a,m,n in [
 (0x409c93,"mov","[esi + 0x18]"),(0x409c98,"sar","ebx, 0x10"),
 (0x409c9b,"mov","word ptr [esi + 0x18]"),
 (0x409c9f,"call","0x409860"),
 (0x409d53,"mov","[esi + 0x14]"),(0x409d58,"sar","ebx, 0x10"),
 (0x409d5b,"mov","word ptr [esi + 0x14]"),
 (0x409d5f,"call","0x409860")
]:must(a,m,n)
# Original span consumer receives EBX high16=start; EDX low16=count.
# stride=36 and skip per-triangle 0x10 filter.
for a,m,n in [
 (0x409868,"mov","[ebp - 0x1c]"),(0x40986b,"lea","[ebx*8]"),
 (0x409872,"mov","[0x4a2464]"),(0x40987b,"add","ecx, ebx"),
 (0x40987d,"add","edx, ebx"),(0x40987f,"shl","ecx, 2"),
 (0x409885,"add","esi, ecx"),(0x409887,"cmp","ebx, edx"),
 (0x40989d,"mov","[esi + 0x20]"),
 (0x4098a0,"test","ah, 0x10"),(0x4098a3,"je","0x4098da"),
 (0x409946,"call","0x40ca00")
]:must(a,m,n)

# Pure branch fixtures with actual pinned HMO2 planes, NOT original x87 execution.
hmo=next(x for x in old["hmos"] if x["hmo"]=="HMO_2")
a0=hmo["plane_start_absolute"]
def record(idx):
    raw=mto[a0+44*idx:a0+44*(idx+1)]
    norm=struct.unpack_from("<4f",raw,0)
    pc,ps,sc,ss=struct.unpack_from("<4H",raw,20)
    return {"index":idx,"normal_d":norm,"positive_count":pc,"positive_start":ps,
            "nonpositive_count":sc,"nonpositive_start":ss,
            "raw_sha256":SHA(raw)}
p0=record(0);p128=record(128)
assert p0["normal_d"]==(0.,1.,0.,-1046.)
assert [p0[k] for k in ("positive_count","positive_start","nonpositive_count","nonpositive_start")]==[6,0,0,65535]
assert p128["normal_d"]==(0.,0.,1.,-136.)
assert [p128[k] for k in ("positive_count","positive_start","nonpositive_count","nonpositive_start")]==[1,249,6,250]
tests=[]
for plane,coordinates in ((p0,[(29.,1045.,124.),(29.,1046.,124.),(29.,1047.,124.)]),
                          (p128,[(0.,0.,135.),(0.,0.,136.),(0.,0.,137.)])):
    nx,ny,nz,D=plane["normal_d"]
    for viewpoint in coordinates:
        x,y,z=viewpoint
        metric=nx*x+ny*y+nz*z+D
        sign="POSITIVE" if metric>0 else "NONPOSITIVE"
        side="positive" if metric>0 else "nonpositive"
        for mode in (0,1):
            tests.append({
                "plane_index":plane["index"],"viewpoint_xyz":viewpoint,
                "plane_dot":metric,"flag_0x499f8c_nonzero":bool(mode),
                "branch":"PRIMARY_POSITIVE" if metric>0 else "SECONDARY_NONPOSITIVE",
                "source_start":plane[f"{side}_start"],
                "source_triangle_count":plane[f"{side}_count"],
                "scope":"PURE_FINITE_BRANCH_MODEL_NOT_ORIGINAL_X87_EXECUTION"
            })
assert len(tests)==12
assert len({(t["plane_index"],t["viewpoint_xyz"],t["flag_0x499f8c_nonzero"]) for t in tests})==12
assert all(t["source_triangle_count"]==(6 if t["plane_index"]==0 and t["plane_dot"]>0 else
                                      0 if t["plane_index"]==0 else
                                      1 if t["plane_dot"]>0 else 6) for t in tests)
out={
    "schema":"OpenMDK1.OriginalPlaneFacingTriangleRangeSelection.v1",
    "original_MDk95_EXE_sha256":SHA(exe),
    "original_LEVEL3_MTO_sha256":SHA(mto),
    "prior_full_source_range_audit_sha256":SHA(prev),
    "source_code_regions":byte_regions,
    "original_opcode_checks":checks,
    "original_opcode_check_count":len(checks),
    "original_source_loader":"0x432376→0x4323c8→0x419ee0",
    "HMO_plane_stride_bytes":44,
    "HMO_triangle_stride_bytes":36,
    "HMO_vertex_stride_bytes":12,
    "plane_runtime_pointer_patches":"In original parser 0x419f80..0x419f8f, plane+0x1c and plane+0x20 dword offsets are rebased relative to parsed trailing-data base.",
    "signed_plane_distance":"plane normal XYZ dotted with three float coordinates pointed by [0x4a2468] plus plane D [esi+0x0c]",
    "two_sided_dispatch":{
     "plane_dot_positive":{"count":"u16 plane+0x14","start":"u16 plane+0x16","source_call_sites":["0x409b16","0x409d5f"]},
     "plane_dot_zero_or_negative":{"count":"u16 plane+0x18","start":"u16 plane+0x1a","source_call_sites":["0x409bd2","0x409c9f"]},
     "mode":"Global [0x499f8c] changes traversal order, but both branches select the same facing-specific source span under finite comparisons.",
     "span_consumer":"0x409860",
     "per_triangle_skip":"0x40989d..0x4098a3 checks triangle byte at +0x20 bit0x10; selection does not prove every record is drawn."
    },
    "HMO2_plane0":p0,"HMO2_plane128":p128,
    "pure_finite_side_fixtures":tests,
    "quantitative_source_scope":{
      "all_original_LEVEL3_triangles":7205,"primary_records":7089,
      "secondary_records":116,"secondary_spans":45,
      "full_index_coverage_without_duplicates":True
    },
    "semantic_conclusion":"Secondary +0x18 u16 count/start is the opposite-facing candidate triangle range consumed by original runtime code, not an ungrounded second pass.",
    "limitations":["NaN/x87 exceptional plane values excluded from finite source model",
                   "Actual view vector values and global mode not read from original runtime",
                   "Per-triangle filtering and raster visibility not verified",
                   "No original game instructions executed, no pixel/fidelity PASS"],
    "original_game_instructions_executed":0,"runtime_fidelity":False
}
file=RUN/"MDK_ORIGINAL_PLANE_SIDE_DISPATCH.json"
data=(json.dumps(out,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
if file.exists():assert file.read_bytes()==data,("CONFLICTING_OUTPUT",str(file))
else:
 with file.open("xb") as f:f.write(data)
print(json.dumps({
 "status":"PASS_ORIGINAL_SOURCE_TWO_SIDED_TRIANGLE_RANGE_DISPATCH_STATIC",
 "source_regions":len(byte_regions),"opcode_checks":len(checks),"pure_side_fixtures":len(tests),
 "HMO2_plane0":p0,"HMO2_plane128":p128,
 "game_execution":0,"artifact_sha256":SHA(data)
},sort_keys=True))
