"""CONT11 bounded source-static fidelity mechanism verifier.

Reads the immutable source inputs with SHA pins; uses disassembly and NE/LE
metadata only. No original game instructions are executed or emulated.
Writes a create-only static verification receipt in this report directory.
"""
from pathlib import Path
import sys
import json
import hashlib
import datetime
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_MODE_16

ROOT=Path(r"F:\Remaster Framework")
RUN=Path(__file__).resolve().parent
DELTA=json.loads((RUN/"SEMANTIC_DELTA.json").read_text(encoding="utf-8"))
SHA=lambda b:hashlib.sha256(b).hexdigest()
def fp(path):
    return SHA(path.read_bytes())

REG=ROOT/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
PREV=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-120436__PORTFOLIO-READONLY-CONTINUATION__cont10/READ_ONLY_HANDOFF.json"
assert fp(REG)==DELTA["registry_sha256"]
assert fp(PREV)==DELTA["previous_handoff_sha256"]
EXES={
 "MDK1":ROOT/"source/MDK/MDK95.EXE",
 "Stonekeep":ROOT/"source/Stonekeep/SK.EXE",
 "Ultima8":ROOT/"source/Ultima 8/ENGLISH/U8.EXE"
}
for project,path in EXES.items():
    dkey={"MDK1":"OpenMDK1","Stonekeep":"OpenStonekeep","Ultima8":"OpenUltima8"}[project]
    assert fp(path)==DELTA["project_source_sha256"][dkey],("CHANGED_EXE",project)

sys.path.insert(0,str(ROOT/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load as mdload,offset as mdoffset
mb,secs=mdload()
assert SHA(mb)==DELTA["project_source_sha256"]["OpenMDK1"]

sys.path.insert(0,str(ROOT/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
sk=LEImage(EXES["Stonekeep"].read_bytes())

sys.path.insert(0,str(ROOT/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load as uload
from ne_far_target import resolve
ub,ne,segs=uload()
assert SHA(ub)==DELTA["project_source_sha256"]["OpenUltima8"]

# SHA-256 pins for exact original-byte ranges independently read in CONT11.
REGIONS={
 "MDK1":[
  (0x40d13c,0x40d156,"f0466a4039493cf7912bb3eee60300f32ecdafa41accc0692354a53a770167cf"),
  (0x40d3fb,0x40d417,"7946d0de4c7145c68b6b54be6bd183b232a3255862155a79068a349ff1c96160"),
  (0x40d675,0x40d68a,"a409fa16ccab3ebdedeaa522a91d0c9f800d05e0057e7528b5fa427d5cf0ace7"),
  (0x40d8b5,0x40da52,"4304fdd8056916e81582c19657471b8f6193796878df452f18cfa0e4c177c2ff")
 ],
 "Stonekeep":[
  (0x3160b,0x3163e,"e138658f3cdd2fed46dfcb54c44968dad07df4e8a5fe769751510ceae2b0d9d8"),
  (0x85220,0x8525e,"259a0777ebe5b0b61b712a4e07adea0b28ca2139f55d67ad443ad3998f01acfa"),
  (0x852f6,0x85333,"99299d00cfbcc1e6138c1fd37d3804bdadcc6e303fe45df3ad0b70bbd1bd6f93"),
  (0x853a0,0x853b2,"1e8dd943a3aabf61f2798be3d484937759ddd1aba62e4638dbe12be32bc7d06c"),
  (0x85721,0x8572c,"2b212e2950273229967fe14aedeac87752d4114be2657c2d00bc56969c906752"),
  (0x85079,0x85106,"533a7af737cc073648953086602e163e84fb1197a10ce27eba0996dd7c41821a"),
  (0x851c3,0x8521e,"978d96391a70828a5df1c13c897ca4291afa28aca329a9c613ff3da4362ebaad"),
  (0x5dc10,0x5dd00,"179e897dfd305526e35c1e2f5a7c03d524d9a63aa3bd1c522ee341997ba7805f"),
  (0xa2c80,0xa2ca5,"dedf73643c9dce6457b5d5e7c8293eaf26ae6d5c57ba4f41254a7156c6c85918")
 ],
 "Ultima8":[
  (29,0x1ba8,0x1d9c,"a7456484028d37acd8318689aed05ec6279856db3670d21a0f15ad4f13719ba6"),
  (29,0x272,0x357,"78e16deafa832ab71f185e44226473b1842442b337de9dd47f8af853a6d8e743"),
  (27,0x357,0x3ba,"6dc4dbfe5a115b3d2e4ec9ccf5dc6d1b9199aef141146d2f60bbd947c3f9341d"),
  (27,0x3ba,0x6f3,"3a04b4933a347ae7113ff505b12fb0473c188e0a6bc4b26c9e5234b15667f808"),
  (29,0x265f,0x284d,"e4f086430f1b855a0c71884b416f14ffb7f342dfdc5bb298482706dea984d4cf"),
  (81,0x93,0x30f,"860943434f51f0c7653458c08af3f0ddac88f06a93945b884bdcd03c1ae49f83"),
  (82,0x2c09,0x2c11,"ca6c380b839e4ab8c05d540c52b8cd6db8772dcace479083c57d762bc4a6b019"),
  (82,0x29ee,0x2a20,"d7f37b7957f80c72eabcd0ed03d890d63dced192115c116d8fd86acc54540e08")
 ]
}

INS={"MDK1":{},"Stonekeep":{},"Ultima8":{}}
check_regions=[]
def decode(project,base,raw,bits,segment=None):
    md=Cs(CS_ARCH_X86,CS_MODE_16 if bits==16 else CS_MODE_32)
    instructions=list(md.disasm(raw,base))
    assert instructions and instructions[0].address==base,("FUNCTION_ALIGNMENT",project,hex(base))
    for instruction in instructions:
        k=(segment,instruction.address) if segment is not None else instruction.address
        if k in INS[project]:
            old=INS[project][k]
            assert (old.mnemonic,old.op_str,old.bytes)==(instruction.mnemonic,instruction.op_str,instruction.bytes)
        INS[project][k]=instruction

for start,end,expected in REGIONS["MDK1"]:
    raw=mb[mdoffset(secs,start,end-start):mdoffset(secs,start,end-start)+end-start]
    assert SHA(raw)==expected
    check_regions.append(dict(project="MDK1",address=hex(start),size=len(raw),sha256=expected))
    decode("MDK1",start,raw,32)
for start,end,expected in REGIONS["Stonekeep"]:
    raw=sk.read_va(start,end-start)
    assert SHA(raw)==expected
    check_regions.append(dict(project="Stonekeep",address=hex(start),size=len(raw),sha256=expected))
    decode("Stonekeep",start,raw,32)
for segment,start,end,expected in REGIONS["Ultima8"]:
    seg=segs[segment-1]
    assert not seg.get("virtual") and not seg["iterated"] and not seg["data_segment"] and start<end<=seg["size"]
    raw=ub[seg["offset"]+start:seg["offset"]+end]
    assert SHA(raw)==expected
    check_regions.append(dict(project="Ultima8",address=f"NE{segment}:{start:#x}",size=len(raw),sha256=expected))
    decode("Ultima8",start,raw,16,segment)

checks=[]
def expected(project,addr,mnemonic,needle,segment=None):
    k=(segment,addr) if segment is not None else addr
    i=INS[project].get(k)
    assert i is not None and i.mnemonic==mnemonic and needle in i.op_str,(
       "ORIGINAL_INSTRUCTION_CHANGED",project,segment,hex(addr),mnemonic,needle,
       None if i is None else (i.mnemonic,i.op_str))
    checks.append(dict(project=project,loc=f"NE{segment}:{hex(addr)}" if segment else hex(addr),
                       mnemonic=mnemonic,match=needle,result="PASS_OPCODE_IDENTITY"))

# MDK original polygon reject/ordered plane tests.
expected("MDK1",0x40d13c,"cmp","[ebp - 0x18], 3")
expected("MDK1",0x40d140,"jl","0x40cb96")
for a,bit in ((0x40d152,4),(0x40d3fb,1),(0x40d675,2)):
    expected("MDK1",a,"test",f"bl, {bit}")
expected("MDK1",0x40d8b5,"cmp","[ebp - 0x18], 3")
expected("MDK1",0x40d8b9,"jl","0x40cb96")
expected("MDK1",0x40d8c3,"test","ebx, ebx")
expected("MDK1",0x40d8c5,"jne","0x40cb96")
calls=[0x40d920,0x40d95b,0x40d993,0x40d9ce,0x40da0f,0x40da44]
stops=[(0x40d925,0x40d929,3),(0x40d960,0x40d964,4),(0x40d998,0x40d99c,5),
       (0x40d9d3,0x40d9d7,6),(0x40da14,0x40da18,7)]
for call in calls:expected("MDK1",call,"call","0x40c860")
for cmpva,brva,n in stops:
    expected("MDK1",cmpva,"cmp",f"[ebp - 0x18], {n}")
    expected("MDK1",brva,"je","0x40cb96")
for v in (0x40d91c,0x40d957,0x40d98f,0x40d9ca,0x40da0b,0x40da40):
    expected("MDK1",v,"mov","ebx, esi")
expected("MDK1",0x40da4f,"ret","0xc")
# Original body has exactly six direct calls to sorter in bounded fan exit region.
actual=sorted(i.address for i in INS["MDK1"].values() if 0x40d8b5<=i.address<0x40da50 and i.mnemonic=="call" and i.op_str=="0x40c860")
assert actual==calls,("UNEXPECTED_FAN_CALLS",actual)
# Pure reference fixture ONLY: no machine/game instructions executed.
for n in range(3,9):
    source_branch_count=next((idx+1 for idx,(_,_,stop) in enumerate(stops) if n==stop),6)
    assert source_branch_count==n-2
    checks.append({"project":"MDK1","fixture":f"count_{n}_expects_{n-2}_fan_triangles",
                   "result":"PASS_STATIC_BRANCH_COUNT_MODEL_NOT_GAME_EMULATION"})

# Stonekeep event enqueue, head service, per-event dequeue and loader scope.
for addr,kind,operand in (
    (0x31615,"call","0x85220"),(0x8522a,"movsx","[0x1bc1ca]"),
    (0x85231,"cmp","0x29"),(0x85238,"call","0x852f6"),
    (0x8523e,"cmp","eax, 1"),(0x85241,"jne","0x85248"),
    (0x85243,"call","0x85079"),(0x852fe,"mov","edi, 1"),
    (0x85303,"mov","0x1bc1ca"),(0x8532b,"jmp","0x7525e"),
    (0x853a0,"movsx","[ecx + 4]"),(0x853a4,"movsx","[ecx + 2]"),
    (0x853a8,"call","0x5dc10"),(0x853ad,"jmp","0x85721"),
    (0x85721,"mov","eax, edi"),(0x85096,"movsd","dword ptr"),
    (0x85097,"movsd","dword ptr"),(0x85098,"movsw","word ptr"),
    (0x850b2,"mov","[0x1bc686]"),(0x850d5,"mov","0x29"),
    (0x851d0,"cmp","edx, 0x19"),(0x851d3,"je","0x85219"),
    (0x851dc,"mov","0x1bc1ca"),(0x85208,"mov","eax, 1"),
    (0x8520d,"add","[0x1bc686]"),(0x85219,"xor","eax, eax"),
    (0xa2c91,"call","0x851c3"),(0xa2c96,"mov","edx, 0x2b"),
    (0x5dc14,"cmp","ax, dx"),(0x5dc17,"je","0x5dcf4"),
    (0x5dc6a,"mov","[0x1bc69a]"),(0x5dc76,"mov","[0x1bc698]"),
    (0x5dc82,"mov","[0x1bc6ae]"),(0x5dc9f,"mov","[0x1bc6a0]")
):expected("Stonekeep",addr,kind,operand)

# Negative graph promotion *policy fixtures*, not observed original gameplay.
def may_promote(enqueued,serviced,staged_matched,source,target,loader_written):
    return bool(enqueued and serviced and staged_matched and source!=target and loader_written)
for name,args in (
    ("queue_full_drop",(False,False,True,15,1,False)),
    ("queued_not_serviced",(True,False,True,15,1,False)),
    ("staged_overwritten",(True,True,False,15,1,True)),
    ("equal_level_no_transfer",(True,True,True,1,1,False)),
    ("loader_not_written",(True,True,True,15,1,False))
):
    assert not may_promote(*args)
    checks.append({"project":"Stonekeep","fixture":name,"result":"PASS_NEGATIVE_POLICY_FIXTURE_NOT_GAME_TEST"})
assert may_promote(True,True,True,15,1,True)
checks.append({"project":"Stonekeep","fixture":"structural_eligible_only",
               "result":"PASS_ELIGIBILITY_POLICY_NOT_RUNTIME_ACCEPTANCE"})

# Ultima VIII conditional caller/temporal precedence and NE relocations.
def ue(segment,addr,mnemonic,operand):
    expected("Ultima8",addr,mnemonic,operand,segment)
for s,a,m,op in (
    (29,0x1d5d,"call","0x272"),(29,0x1d63,"mov","[bp - 0xa], 1"),
    (29,0x1d88,"cmp","[bp - 0xa], 0"),(29,0x1d92,"lcall","0xffff"),
    (29,0x318,"cmp","ax, 3"),(29,0x333,"lcall","0xffff"),
    (27,0x3b2,"call","0x3ba"),(27,0x656,"cmp","[bp + 0x12], 0"),
    (27,0x65a,"je","0x6cd"),(27,0x684,"lcall","0xffff"),
    (27,0x68e,"je","0x6c0"),(27,0x6a4,"lcall","0xffff"),
    (27,0x6b4,"lcall","0xffff"),(27,0x6ee,"mov","[bp - 0x12]"),
    (29,0x268a,"inc","word ptr es:[bx]"),(29,0x268f,"call","0x2bf5"),
    (29,0x2725,"mov","word ptr es:[bx]"),(29,0x273e,"mov","word ptr es:[bx]"),
    (29,0x2782,"and","0xf7f7"),(29,0x27af,"lcall","0xffff"),
    (29,0x27d9,"lcall","0xffff"),(81,0xc8,"call","0x7d"),
    (82,0x2c0c,"mov","[0x5898]"),(82,0x2a0c,"lcall","0xffff")
):ue(s,a,m,op)

rels=[
 (29,0x334,27,0x357),(27,0x685,28,0xf72),(27,0x6a5,28,0x1009),
 (28,0x1017,29,0x265f),(27,0x6b5,28,0x1f9d),(27,0x6db,29,0x11f),
 (29,0x27b0,82,0x2c09),(29,0x27da,81,0x30f),
 (29,0x1d93,81,0x93),(82,0x2a0d,81,0x93)
]
for src,op,dst,dstoff in rels:
    target=resolve(src,op)
    assert (target["segment"],target["offset"])==(dst,dstoff),("FAR_TARGET_DRIFT",src,hex(op),target)
    checks.append({"project":"Ultima8","relocation":f"NE{src}:{op:#x}",
                   "target":f"NE{dst}:{dstoff:#x}","result":"PASS_ORIGINAL_RELOCATION_IDENTITY"})

# Source interval from completed sector-head splice to conditional grid predicate:
# getter only; no direct in-interval grid producer invocation.
s29=segs[28];a=0x273e;end=0x27d9
raw=ub[s29["offset"]+a:s29["offset"]+end]
ins=list(Cs(CS_ARCH_X86,CS_MODE_16).disasm(raw,a))
assert ins and ins[0].address==a and ins[-1].address+ins[-1].size==end
calls=[i.address for i in ins if i.mnemonic in ("call","lcall")]
assert calls==[0x27af],("UNEXPECTED_PRE_GRID_DIRECT_CALLS",calls)
assert resolve(29,0x27b0)["segment"]==82 and resolve(29,0x27b0)["offset"]==0x2c09
checks.append({"project":"Ultima8","fixture":"head_splice_before_grid_query_with_getter_only",
               "scope":"DIRECT_SOURCE_INTERVAL_NO_ASYNC_OR_INDIRECT_EFFECT_CLAIM",
               "result":"PASS_ORIGINAL_DIRECT_CALL_ORDER"})

# Pure temporal validation fixtures; stale grid is a permitted source state.
def snapshot_class(sector_gen,grid_gen):
    return "GRID_PRECEDES_CURRENT_SECTOR" if grid_gen<sector_gen else "GRID_NOT_PROVED_STALE"
assert snapshot_class(2,1)=="GRID_PRECEDES_CURRENT_SECTOR"
assert snapshot_class(2,2)=="GRID_NOT_PROVED_STALE"
checks.append({"project":"Ultima8","fixture":"membership_changed_grid_not_yet_rebuilt",
               "result":"PASS_TEMPORAL_MODEL_NEGATIVE_FIXTURE_NOT_ORIGINAL_RUNTIME"})
checks.append({"project":"Ultima8","fixture":"rebuild_completed_same_generation",
               "result":"PASS_TEMPORAL_MODEL_CONTROL_NOT_ORIGINAL_RUNTIME"})

rec={
 "schema":"OpenRemaster.CONT11StaticEvidenceVerification.v1",
 "operation_id":DELTA["operation_id"],"iteration_id":"CONT11",
 "status":"PASS_STATIC_BYTE_OPCODE_RELOCATION_AND_NEGATIVE_CONTRACT_FIXTURES_ONLY",
 "source_exes_checked":3,"source_regions_checked":len(check_regions),
 "original_instruction_and_fixture_checks":len(checks),
 "ne_relocations_checked":len(rels),
 "checks":checks,"source_regions":check_regions,
 "test_domain":"SOURCE_STATIC_DISASSEMBLY_AND_PURE_POLICY_MODELS",
 "original_game_instructions_executed":0,"game_runtime_executed":False,
 "fidelity_verified":False,"native_admission_granted":False,
 "predecessor_sha256":fp(PREV),"registry_sha256":fp(REG),
 "semantic_delta_sha256":fp(RUN/"SEMANTIC_DELTA.json"),
 "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()
}
path=RUN/"STATIC_VALIDATION.json"
with path.open("x",encoding="utf-8") as f:
    json.dump(rec,f,indent=2,sort_keys=True)
    f.write("\n")
print(json.dumps({k:rec[k] for k in ("status","source_exes_checked","source_regions_checked",
             "original_instruction_and_fixture_checks","ne_relocations_checked",
             "original_game_instructions_executed","fidelity_verified")},
             sort_keys=True))
