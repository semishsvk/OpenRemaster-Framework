"""CONT10 read-only source anchor and instruction-identity checks.

Does not run game instructions, launch game/runtime, build, or touch canonical
worktrees. Writes only receipts in this one newly owned reports directory.
"""
import sys, json, hashlib, datetime
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_16, CS_MODE_32

BASE=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PIN=json.loads((HERE/"SEMANTIC_DELTA.json").read_text(encoding="utf-8"))
SHA=lambda b:hashlib.sha256(b).hexdigest()
def checked(p,digest):
    raw=p.read_bytes()
    assert SHA(raw)==digest, f"Source hash mismatch: {p}"
    return raw

md=checked(BASE/"source/MDK/MDK95.EXE",PIN["source_sha256"]["OpenMDK1"])
sk=checked(BASE/"source/Stonekeep/SK.EXE",PIN["source_sha256"]["OpenStonekeep"])
u8=checked(BASE/"source/Ultima 8/ENGLISH/U8.EXE",PIN["source_sha256"]["OpenUltima8"])
assert SHA((BASE/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json").read_bytes())==PIN["registry_sha256"]
assert SHA((BASE/"output/projects/OpenRemasterOrchestrator/reports/20261009-115123__PORTFOLIO-READONLY-CONTINUATION__cont09/READ_ONLY_HANDOFF.json").read_bytes())==PIN["previous_handoff_sha256"]

sys.path.insert(0,str(BASE/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load as mdload, offset as mdoffset
b,secs=mdload()
assert b==md
sys.path.insert(0,str(BASE/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
le=LEImage(sk)
sys.path.insert(0,str(BASE/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load as uload
from ne_far_target import resolve
bu,ne,segs=uload()
assert bu==u8

def raw_for(project,addr,n):
    if project=="OpenMDK1":
        a=int(addr,16);fo=mdoffset(secs,a,n)
        return b[fo:fo+n],a,CS_MODE_32
    if project=="OpenStonekeep":
        a=int(addr,16);return le.read_va(a,n),a,CS_MODE_32
    assert project=="OpenUltima8"
    segpart,addrpart=addr.split(":")
    sn=int(segpart[2:]);a=int(addrpart,16);s=segs[sn-1]
    assert not s.get("virtual") and not s["iterated"] and not s["data_segment"]
    assert a+n<=s["size"]
    return bu[s["offset"]+a:s["offset"]+a+n],a,CS_MODE_16

ins_by_project={}
regions=[]
for project,addr,size,expected in PIN["source_regions"]:
    raw,base,mode=raw_for(project,addr,size)
    assert SHA(raw)==expected,(project,addr,SHA(raw),expected)
    ins=list(Cs(CS_ARCH_X86,mode).disasm(raw,base))
    assert ins and ins[0].address==base,("UNALIGNED_START",project,addr)
    regions.append({"project":project,"address":addr,"length":size,"sha256":expected,"matches":True})
    byaddr=ins_by_project.setdefault(project,{})
    for row in ins:byaddr.setdefault(row.address,row)

def has(project,addr,mnemonic,operand_fragment):
    row=ins_by_project[project].get(addr)
    if not row or row.mnemonic!=mnemonic or operand_fragment not in row.op_str:
        raise AssertionError(("ORIGINAL_OPCODE_DIFFERENCE",project,hex(addr),mnemonic,operand_fragment,
                              None if row is None else (row.mnemonic,row.op_str)))
    return True
# Source-bound, instruction-level identity checks. No game instructions execute.
checks=[]
def check(name,project,addr,mnem,needle):
    has(project,addr,mnem,needle)
    checks.append({"name":name,"source_va":hex(addr),"project":project,"kind":"STATIC_OPCODE_IDENTITY_PASS"})

check("MDK_PLANE_DIVIDE","OpenMDK1",0x40cc22,"fdivrp","st(1)")
check("MDK_CLIPPED_Z_F32","OpenMDK1",0x40cc43,"mov","0x3d4ccccd")
check("MDK_CLIPPED_U","OpenMDK1",0x40cc60,"fstp","[eax]")
check("MDK_CLIPPED_V","OpenMDK1",0x40cc76,"fstp","[eax + 4]")
check("MDK_POLYGON_MIN3","OpenMDK1",0x40d13c,"cmp",", 3")
check("MDK_MIN3_REJECTION","OpenMDK1",0x40d140,"jl","0x40cb96")
check("MDK_NEXT_PLANE_BIT4","OpenMDK1",0x40d152,"test","bl, 4")

check("STONE_QUEUE_CAPACITY25","OpenStonekeep",0x851d0,"cmp","0x19")
check("STONE_QUEUE_FULL_BRANCH","OpenStonekeep",0x851d3,"je","0x85219")
check("STONE_QUEUE_SUCCESS_ONE","OpenStonekeep",0x85208,"mov","eax, 1")
check("STONE_QUEUE_INCREMENT","OpenStonekeep",0x8520d,"add","[0x1bc686]")
check("STONE_QUEUE_FULL_ZERO","OpenStonekeep",0x85219,"xor","eax, eax")
check("STONE_EVENT8_REQUEST","OpenStonekeep",0xa2c91,"call","0x851c3")
check("STONE_UNCHECKED_CALL_RETURN","OpenStonekeep",0xa2c96,"mov","edx, 0x2b")
check("STONE_FIFO_SHIFT","OpenStonekeep",0x85096,"movsd","dword ptr")
check("STONE_FIFO_DEC","OpenStonekeep",0x850b2,"mov","[0x1bc686]")
check("STONE_QUEUE_FIRST_ROW","OpenStonekeep",0x85303,"mov","0x1bc1ca")
check("STONE_EVENT8_SRC","OpenStonekeep",0x853a4,"movsx","[ecx + 2]")
check("STONE_EVENT8_DST","OpenStonekeep",0x853a0,"movsx","[ecx + 4]")
check("STONE_EVENT8_LOAD","OpenStonekeep",0x853a8,"call","0x5dc10")

check("U8_CREATE_CALL","OpenUltima8",0x684,"lcall","0xffff")
check("U8_PLACE_CALL","OpenUltima8",0x6a4,"lcall","0xffff")
check("U8_OR82_REQUEST","OpenUltima8",0x6ac,"push","0x82")
check("U8_SOURCE_COUNT_RETURN","OpenUltima8",0x6ee,"mov","[bp - 0x12]")
check("U8_ALLOC_TO_HOLDING_NEXT","OpenUltima8",0x262e,"mov","word ptr es:[bx]")
check("U8_ALLOC_TO_HOLDING_HEAD","OpenUltima8",0x2644,"mov","[0xacba]")
check("U8_HOLDING_COUNT_INC","OpenUltima8",0x2647,"inc","[0xacbc]")
check("U8_HOLDING_POP_ZERO","OpenUltima8",0x2c02,"xor","ax, ax")
check("U8_HOLDING_POP_DEC","OpenUltima8",0x2c06,"dec","[0xacbc]")
check("U8_HOLDING_POP_HEAD","OpenUltima8",0x2c0a,"mov","[0xacba]")
check("U8_SECTOR_COUNT_BEFORE_POP","OpenUltima8",0x268a,"inc","word ptr es:[bx]")
check("U8_HOLDING_POP_CALL","OpenUltima8",0x268f,"call","0x2bf5")
check("U8_EMPTY_PLACEMENT_EARLY_RETURN","OpenUltima8",0x269b,"jmp","0x284b")
check("U8_SECTOR_NEXT_SPLICE","OpenUltima8",0x2725,"mov","word ptr es:[bx]")
check("U8_SECTOR_HEAD_SPLICE","OpenUltima8",0x273e,"mov","word ptr es:[bx]")
check("U8_WORLD_FLAGS_CLEAR","OpenUltima8",0x2782,"and","0xf7f7")
check("U8_GRID_GETTER_CALL","OpenUltima8",0x27af,"lcall","0xffff")
check("U8_GRID_PREDICATE_CALL","OpenUltima8",0x27d9,"lcall","0xffff")
checks.append({"name":"U8_SECTOR_HEAD_BEFORE_GRID_QUERY","kind":"STATIC_ORDER_PASS","addresses":["0x273e","0x27d9"],"project":"OpenUltima8"})
assert 0x273e<0x27d9 and 0x2782<0x27d9
# Relocations explicitly confirm call identities across NE modules.
for segment,operand,targetseg,targetoff in [
 (27,0x685,28,0xf72),(27,0x6a5,28,0x1009),
 (27,0x6b5,28,0x1f9d),(27,0x6db,29,0x11f),
 (28,0x1017,29,0x265f),(28,0xf9b,29,0x2c2b),
 (29,0x27b0,82,0x2c09),(29,0x27da,81,0x30f)]:
    target=resolve(segment,operand)
    assert (target["segment"],target["offset"])==(targetseg,targetoff),("NE_RELOCATION_MISMATCH",segment,hex(operand),target)
    checks.append({"name":f"NE_RELOCATION_{segment}_{operand:x}","kind":"STATIC_RELOCATION_IDENTITY_PASS","project":"OpenUltima8"})

# Trace of straight-line source instructions in the splice→query interval.
s29=segs[28]
a=0x273e;stop=0x27d9
code=bu[s29["offset"]+a:s29["offset"]+stop]
rows=list(Cs(CS_ARCH_X86,CS_MODE_16).disasm(code,a))
assert rows and rows[0].address==a and rows[-1].address+rows[-1].size==stop
calls=[hex(q.address) for q in rows if q.mnemonic in ("call","lcall")]
assert calls==["0x27af"],("ADDITIONAL_GRID_REBUILD_OR_CALLBACK",calls)
checks.append({"name":"U8_SPLICE_TO_QUERY_ONLY_GETTER_CALL","kind":"STATIC_ORDER_PASS","project":"OpenUltima8","calls":calls})

receipt={"schema":"OpenRemaster.CONT10StaticSourceVerification.v1",
         "operation_id":PIN["operation_id"],"iteration_id":"CONT10",
         "status":"PASS_STATIC_SOURCE_IDENTITY_AND_DECLARED_INSTRUCTION_CONTRACTS_ONLY",
         "original_exe_pins":3,"source_region_matches":len(regions),
         "static_opcode_and_order_checks":len(checks)-8,
         "ne_far_relocation_checks":8,
         "regions":regions,"checks":checks,
         "new_game_instruction_or_runtime_tests":0,"runtime_fidelity_verified":False,
         "scope":"Checks immutable source bytes and disassembly; no executed game behavior, live membership or orchestration admission.",
         "delta_sha256":SHA((HERE/"SEMANTIC_DELTA.json").read_bytes()),
         "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
out=HERE/"STATIC_VERIFICATION.json"
assert not out.exists()
out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({k:receipt[k] for k in ("status","original_exe_pins","source_region_matches","static_opcode_and_order_checks","ne_far_relocation_checks","new_game_instruction_or_runtime_tests")},sort_keys=True))
