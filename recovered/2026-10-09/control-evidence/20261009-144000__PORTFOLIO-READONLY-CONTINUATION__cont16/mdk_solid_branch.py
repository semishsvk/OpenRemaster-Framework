"""Bind real LEVEL3 HMO2 f3=-16 triangle to original solid-palette rasterizer."""
import json,sys,hashlib
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
R=Path(__file__).resolve().parent
j=json.loads((R/"MDK_LEVEL3_TRIANGLE_SOURCE_FIXTURE.json").read_text(encoding="utf-8"))
assert j["signed_f3"]==-16 and j["indices"]==[125,98,116]
sys.path.insert(0,r"F:\Remaster Framework\output\projects\OpenMDK1\evidence\20261008-094213__AUTONOMOUS-4H__cycle01")
from static_probe import load,offset
b,sections=load()
assert hashlib.sha256(b).hexdigest()=="e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788"
cs=Cs(CS_ARCH_X86,CS_MODE_32)
def first(va):
    o=offset(sections,va,18)
    return next(cs.disasm(b[o:o+18],va))
checks=[]
for a,m,n in [
 (0x40c8be,"test","ebx, ebx"),
 (0x40c8c0,"jl","0x40c93f"),
 (0x40c93f,"cmp","ebx, 0xffffff00"),
 (0x40c945,"jg","0x40c97c"),
 (0x40c97c,"mov","eax, ebx"),
 (0x40c97e,"neg","eax"),
 (0x40c984,"jmp","0x40c90b"),
 (0x40c90b,"call","0x415260"),
 (0x415266,"mov","ah, al"),
 (0x415268,"mov","word ptr [esp + 0x10]"),
 (0x41526d,"mov","word ptr [esp + 0x12]"),
 (0x41532f,"mov","[esp + 0x10]"),
 (0x41534a,"add","ebp, 0x258"),
 (0x415358,"rep stosd",""),
 (0x415364,"rep stosb",""),
 (0x4153f9,"rep stosd",""),
 (0x415405,"rep stosb",""),
 (0x415432,"rep stosd",""),
 (0x41543e,"rep stosb","")
]:
    x=first(a)
    assert x.address==a and x.mnemonic==m and n in x.op_str,(hex(a),x.mnemonic,x.op_str,m,n)
    checks.append({"source_va":hex(a),"opcode":x.mnemonic+" "+x.op_str,"status":"SOURCE_STATIC_MATCH"})
# Pure signed ordering bound, not CPU execution.
f3=j["signed_f3"]
assert f3<0 and f3>-256 and -f3==16
color_byte=(-f3)&255
word=color_byte|(color_byte<<8)
dword=word|(word<<16)
assert (color_byte,word,dword)==(0x10,0x1010,0x10101010)
out={
 "schema":"OpenMDK1.AuthenticHMO2TriangleSolidRasterBranch.v1",
 "original_MTO_triangle_sha256":j["triangle_record_sha256"],
 "original_MDK95_EXE_SHA256":hashlib.sha256(b).hexdigest(),
 "hmo":"HMO_2","triangle_index":0,
 "signed_f3":f3,"source_vertex_indices":j["indices"],
 "original_source_vertex_coordinates":[v["coordinates"] for v in j["original_source_vertices"]],
 "negative_dispatch":"0x40c8be ->0x40c93f ->0x40c97c ->0x40c90b",
 "palette_color_index":color_byte,"replicated_color_dword":hex(dword),
 "original_solid_fill_function":"0x415260",
 "row_stride_bytes":0x258,
 "source_opcode_checks":checks,
 "this_path_selects_profile_table_callback":False,
 "negative_contract":"Do not assign a profileA/B material callback to f3=-16 on this original negative-code branch.",
 "important_limit":"Source triangle might be invisible/fully clipped in a frame; no original machine code executed or pixels compared.",
 "original_game_instructions_executed":0,"fidelity_verified":False
}
p=R/"MDK_LEVEL3_SOLID_COLOR_BRANCH.json"
data=json.dumps(out,sort_keys=True,indent=2)+"\n"
if p.exists():assert p.read_text(encoding="utf-8")==data
else:p.write_text(data,encoding="utf-8")
print(json.dumps({"status":"PASS_ORIGINAL_SOURCE_TRIANGLE_TO_SOLID_COLOR_BRANCH",
    "source_color":16,"source_rasterizer":"0x415260",
    "original_opcode_checks":len(checks),"fixture_sha256":hashlib.sha256(p.read_bytes()).hexdigest()}))
