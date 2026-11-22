"""CONT12 strictly source-static artifact verifier.

Reads pinned original game data, decodes program instruction bytes and NE
relocation records, and tests independent *pure contract models*. Does not
execute original game instructions or dispatch/native runtime/build jobs.
Creates a single report-local JSON receipt; sources/worktrees remain unmodified.
"""
from pathlib import Path
import sys,hashlib,struct,json,datetime,collections
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_MODE_16

BASE=Path(r"F:\Remaster Framework")
RUN=Path(__file__).resolve().parent
PIN=json.loads((RUN/"SEMANTIC_DELTA.json").read_text(encoding="utf-8"))
sha=lambda b:hashlib.sha256(b).hexdigest()
def verify(path,digest):
    raw=path.read_bytes()
    assert sha(raw)==digest,("PIN_MISMATCH",str(path))
    return raw
assert sha((BASE/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json").read_bytes())==PIN["portfolio_registry"]["sha256"]
prior=BASE/"output/projects/OpenRemasterOrchestrator/reports/20261009-122230__PORTFOLIO-READONLY-CONTINUATION__cont11/READ_ONLY_HANDOFF.json"
assert sha(prior.read_bytes())==PIN["previous_handoff_sha256"]
original={}
for project,info in PIN["original_corpus"].items():
    original[project]=verify(BASE/info["path"],info["sha256"])
sys.path.insert(0,str(BASE/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load as mdload,offset as mdoffset
mb,sections=mdload()
assert original["OpenMDK1"]==mb
sys.path.insert(0,str(BASE/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
le=LEImage(original["OpenStonekeep"])
sys.path.insert(0,str(BASE/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load as uload
from glob_callers import export_entries
ub,ne,segs=uload()
assert original["OpenUltima8"]==ub

REGIONS={
 "OpenMDK1":[
  (0x40ca00,0x40cacd,"0285cc9a36c1ef6cad48600642f545c36caaff02ad29cd18b5ca3458d8a47ed6"),
  (0x40cb96,0x40cbe0,"bda1e0ac92523cb1dff95ca347a25eb833f57aa369223487e2303dc9d52cd7cd"),
  (0x40d13c,0x40d1be,"50439ed78b01af9e9cf6244d6f757bfdfaa9716db19ada30c265ae3488154b22"),
  (0x40d3e2,0x40d434,"05188ff2f4f63a0b81ed664cf280a7dbbe495db3978a09197ad6643fa2865f9f"),
  (0x40d669,0x40d6a8,"cffdcffab9bc13715a96442de24132e99dadb23f6527ac29a1f866c6924c98fc"),
  (0x40d8b5,0x40da52,"4304fdd8056916e81582c19657471b8f6193796878df452f18cfa0e4c177c2ff")
 ],
 "OpenStonekeep":[
  (0xa2c2b,0xa2ca5,"a4ebe93d4c2ec22ef4cc857288832d2a29cc9b96fd86f2863c1ed853dc737393"),
  (0x85139,0x85176,"63f0809736f50129b88d55c2ee9a95ecb4bb4fa0f6f74f3bc6c490ad11e2badd"),
  (0x851c3,0x85220,"3d2c246f260543bd33f8e4997549f9103957e98c6ba94af04cec4acb3589439b")
 ],
 "OpenUltima8":[
  (29,0x272,0x39c,"0fb167cde9162306755b8dfd87ba6c3580ab94b75accdede9be86b41478d40c8"),
  (28,0xc81,0xcc3,"d8568893622479e1d6009f0a1cb123be64f1559d46d9d2a014505bd7200446e6"),
  (28,0x2577,0x265f,"fc81972b60e9bb2a21224059ed8a1fca63a8fe35becc633c64876b0ad507044a"),
  (29,0x1d40,0x1d9c,"2466bfd96911af7c12c9653f99b076fffab1f15e5f9cc01dd3e1381f88fafb50"),
  (27,0x357,0x3ba,"6dc4dbfe5a115b3d2e4ec9ccf5dc6d1b9199aef141146d2f60bbd947c3f9341d"),
  (29,0x265f,0x284d,"e4f086430f1b855a0c71884b416f14ffb7f342dfdc5bb298482706dea984d4cf"),
  (81,0x93,0x30f,"860943434f51f0c7653458c08af3f0ddac88f06a93945b884bdcd03c1ae49f83")
 ]
}
ins={k:{} for k in REGIONS}
region_receipts=[]
def attach(project,begin,end,raw,bits,expected,segment=None):
    assert len(raw)==end-begin and sha(raw)==expected,("SLICE_CHANGED",project,begin)
    decoded=list(Cs(CS_ARCH_X86,CS_MODE_32 if bits==32 else CS_MODE_16).disasm(raw,begin))
    assert decoded and decoded[0].address==begin and decoded[-1].address+decoded[-1].size==end,("INSTRUCTION_BOUNDARY",project,hex(begin),hex(end))
    for op in decoded:
        key=(segment,op.address) if segment else op.address
        if key in ins[project]:
            assert ins[project][key].bytes==op.bytes
        ins[project][key]=op
    region_receipts.append({"project":project,"address":f"NE{segment}:{begin:#x}" if segment else hex(begin),"size":len(raw),"sha256":expected,"result":"PASS_SOURCE_BYTE_IDENTITY"})
for begin,end,digest in REGIONS["OpenMDK1"]:
    pos=mdoffset(sections,begin,end-begin)
    attach("OpenMDK1",begin,end,mb[pos:pos+end-begin],32,digest)
for begin,end,digest in REGIONS["OpenStonekeep"]:
    attach("OpenStonekeep",begin,end,le.read_va(begin,end-begin),32,digest)
for seg,begin,end,digest in REGIONS["OpenUltima8"]:
    s=segs[seg-1];assert not s.get("virtual") and not s["iterated"] and not s["data_segment"] and end<=s["size"]
    attach("OpenUltima8",begin,end,ub[s["offset"]+begin:s["offset"]+end],16,digest,seg)

op_checks=[]
def check(project,address,mnemonic,operand,segment=None):
    key=(segment,address) if segment else address
    row=ins[project].get(key)
    assert row is not None and row.mnemonic==mnemonic and operand in row.op_str,(
        "OPCODE_CONTRACT_DIFFERENCE",project,key,mnemonic,operand,None if row is None else (row.mnemonic,row.op_str))
    op_checks.append({"project":project,"address":f"NE{segment}:{address:#x}" if segment else hex(address),
                      "mnemonic":mnemonic,"operand_fragment":operand,"status":"PASS_SOURCE_OPCODE_ONLY"})

# Stonekeep original enqueue call order and branch guard:
for addr,mnemonic,part in [
 (0xa2c2b,"mov","[0x1bc404]"),(0xa2c32,"mov","[0x1bc406]"),(0xa2c39,"mov","[0x1bc414]"),
 (0xa2c4a,"call","0x85139"),(0xa2c54,"cmp","eax, 1"),(0xa2c57,"jne","0xa2c80"),
 (0xa2c66,"call","0x851c3"),(0xa2c7b,"call","0x851c3"),(0xa2c91,"call","0x851c3"),
 (0xa2c96,"mov","edx, 0x2b"),(0x85146,"cmp","edx, 0x19"),(0x85149,"je","0x85171"),
 (0x85162,"mov","eax, 1"),(0x85167,"add","[0x1bc686]"),(0x85171,"xor","eax, eax"),
 (0x851d0,"cmp","edx, 0x19"),(0x851d3,"je","0x85219"),
 (0x85208,"mov","eax, 1"),(0x8520d,"add","[0x1bc686]"),(0x85219,"xor","eax, eax")
]:check("OpenStonekeep",addr,mnemonic,part)
assert not [a for a in ins["OpenStonekeep"].values() if 0x85139<=a.address<0x85176 and a.mnemonic in ("call","lcall")]
assert not [a for a in ins["OpenStonekeep"].values() if 0x851c3<=a.address<0x85220 and a.mnemonic in ("call","lcall")]

# Source-local exact capacity model on declared [0..25] domain.
def insert(n):
    if n==25:return n,False
    return n+1,True
queue_cases=[]
for conditional in (False,True):
    for initial in range(26):
        n=initial
        trace=[]
        n,ok=insert(n);trace.append(("simple",ok,n))
        if conditional:
            for name in ("extra_a","extra_b"):
                n,ok=insert(n);trace.append((name,ok,n))
        n,accepted=insert(n);trace.append(("event8",accepted,n))
        expected=initial<=(21 if conditional else 23)
        assert accepted==expected,("H415_EVENT8_ADMISSION_MISMATCH",initial,conditional,trace)
        queue_cases.append({"initial_count":initial,"optional_branch":conditional,"event8_accepted":accepted,
                            "count_after":n,"queue_events":trace,"result":"PASS_PURE_SOURCE_PATH_MODEL_NOT_GAME_TEST"})
assert len(queue_cases)==52 and sum(x["event8_accepted"] for x in queue_cases)==46
assert sum(not x["event8_accepted"] for x in queue_cases)==6

# MDK five clipping gate identity, buffer selector and static fan bound:
for addr,mnemonic,part in [
 (0x40caba,"xor","eax, eax"),(0x40cabc,"mov","[ebp - 0x5c]"),
 (0x40cbbb,"test","cl, 0x10"),(0x40cac4,"test","bl, 8"),
 (0x40d152,"test","bl, 4"),(0x40d3fb,"test","bl, 1"),(0x40d675,"test","bl, 2"),
 (0x40d14f,"mov","[ebp - 0x5c]"),(0x40d3f8,"mov","[ebp - 0x5c]"),
 (0x40d672,"mov","[ebp - 0x5c]"),(0x40d8bf,"xor","[ebp - 0x5c]"),
 (0x40d15e,"shl","edx, 4"),(0x40d163,"shl","edx, 4"),
 (0x40d16c,"sub","edx, ebx"),(0x40d176,"lea","edx, [ebx*4]"),
 (0x40d180,"add","edx, ebx"),(0x40d188,"shl","edx, 4"),
 (0x40d8b5,"cmp","[ebp - 0x18], 3"),(0x40d8c3,"test","ebx, ebx"),
 (0x40da4f,"ret","0xc")
]:check("OpenMDK1",addr,mnemonic,part)
fan=(0x40d920,0x40d95b,0x40d993,0x40d9ce,0x40da0f,0x40da44)
for x in fan:check("OpenMDK1",x,"call","0x40c860")
actual=sorted(op.address for op in ins["OpenMDK1"].values() if 0x40d8b5<=op.address<0x40da52 and op.mnemonic=="call" and op.op_str=="0x40c860")
assert tuple(actual)==fan
assert (0xf0//0x18,0x50//8)==(10,10)
assert 3+5==8 and len(fan)==8-2
mdk_cases=[]
for vertices in range(3,9):
    model_count=vertices-2
    assert 1<=model_count<=len(fan)
    mdk_cases.append({"clipped_polygon_vertices":vertices,"expected_source_fan_triangles":model_count,
                      "result":"PASS_PURE_CONVEX_POLYGON_BOUND_NOT_GAME_TEST"})

# Ultima VIII first and second traversals, active marker and list-live semantics:
def u(addr,mnemonic,part,sn):check("OpenUltima8",addr,mnemonic,part,sn)
for segment,addr,mnemonic,part in [
 (29,0x2b6,"cmp","[0x1a26]"),(29,0x2bd,"jmp","0x352"),(29,0x2d3,"mov","word ptr es:[bx]"),
 (29,0x2ec,"lcall","0xffff"),(29,0x318,"cmp","ax, 3"),(29,0x31d,"cmp","[bp - 2], 0"),
 (29,0x333,"lcall","0xffff"),(29,0x346,"mov","word ptr es:[bx]"),
 (29,0x365,"mov","word ptr es:[bx]"),(29,0x37b,"lcall","0xffff"),
 (29,0x38e,"mov","word ptr es:[bx]"),
 (28,0xcae,"cmp","ax, 3"),(28,0xcb3,"les","[0xacd7]"),(28,0xcba,"mov","word ptr es:[bx]"),
 (28,0xcbf,"xor","ax, ax"),(28,0x258d,"or","ax, 0x2000"),
 (29,0x1d5d,"call","0x272"),(29,0x1d63,"mov","[bp - 0xa], 1"),
 (29,0x1d88,"cmp","[bp - 0xa], 0"),(29,0x1d92,"lcall","0xffff"),
 (27,0x3b2,"call","0x3ba"),(29,0x2725,"mov","word ptr es:[bx]"),
 (29,0x273e,"mov","word ptr es:[bx]"),(29,0x27d9,"lcall","0xffff")
]:u(addr,mnemonic,part,segment)

# NE 16-bit relocation corpus scan, not a complete transitive callgraph:
from glob_callers import export_entries
exports=export_entries(ub,ne)
targets={(81,0x93):"BUILDER",(81,0x30f):"PREDICATE"}
far=[]
fixcount=0
for segment in segs:
    if segment.get("virtual") or not segment["relocations"]:continue
    raw=ub[segment["offset"]:segment["offset"]+segment["size"]]
    at=segment["offset"]+segment["size"]
    n=struct.unpack_from("<H",ub,at)[0]
    assert n<=16000 and at+2+n*8<=len(ub)
    fixcount+=n
    for j in range(n):
        off=at+2+8*j
        ty,flags,q,t1,t2=struct.unpack_from("<BBHHH",ub,off)
        if flags&3 or (ty&127)!=3 or flags&4:continue
        target=exports.get(t2) if t1&255==255 else {"segment":t1,"offset":t2}
        if target is None or (target.get("segment"),target.get("offset")) not in targets:continue
        seen=set()
        while q!=0xffff:
            assert q not in seen and q+4<=len(raw)
            seen.add(q)
            assert q>0 and raw[q-1]==0x9a,("NON_CALL_DIRECT_REFERENCE",segment["index"],hex(q))
            far.append({"source_segment":segment["index"],"operand":q,
                        "target_segment":target["segment"],"target_offset":target["offset"],
                        "purpose":targets[(target["segment"],target["offset"])],
                        "relocation_file_offset":off})
            q=struct.unpack_from("<H",raw,q)[0]
            assert len(seen)<4096
assert fixcount==12274
builder=sorted((r["source_segment"],r["operand"]) for r in far if r["purpose"]=="BUILDER")
query=sorted((r["source_segment"],r["operand"]) for r in far if r["purpose"]=="PREDICATE")
assert builder==[(11,0xa3e),(29,0x1d93),(82,0xa1),(82,0x2a0d)],builder
assert query==[(29,0x27da),(82,0xb09)],query

# Independent semantic fixtures of two-pass traversal. These are NOT original
# instruction execution. A first-pass head re-read for second pass matters.
def walk(head,nextmap):
    seen=set();result=[];item=head
    while item:
        assert item not in seen, "INVALID_CYCLIC_FIXTURE"
        seen.add(item);result.append(item);item=nextmap[item]
    return result
links={10:20,20:0};first=walk(10,links)
links[30]=10;second=walk(30,links)
assert first==[10,20] and second==[30,10,20]
assert walk(10,{10:20,20:0})==[10,20]
u8_cases=[
 {"name":"first_pass_original_head","result":first},
 {"name":"second_pass_reloads_after_head_splice","result":second},
 {"name":"old_head_snapshot_misses_spawned_child","result":walk(10,links)},
 {"name":"no_spawn_both_passes_same","result":walk(10,{10:20,20:0})}
]
assert second[0]==30 and 30 not in first
assert len(REGIONS["OpenMDK1"])+len(REGIONS["OpenStonekeep"])+len(REGIONS["OpenUltima8"])==16

receipt={
 "schema":"OpenRemaster.CONT12ReadOnlyStaticVerification.v1",
 "operation_id":PIN["operation_id"],"iteration_id":"CONT12",
 "status":"PASS_SOURCE_STATIC_INSTRUCTION_AND_PURE_CONTRACT_FIXTURES_ONLY",
 "original_exe_hashes":3,"source_regions":len(region_receipts),
 "source_opcode_checks":len(op_checks),
 "stonekeep_queue_pure_fixtures":len(queue_cases),
 "stonekeep_event8_accepted_fixtures":sum(x["event8_accepted"] for x in queue_cases),
 "stonekeep_event8_rejected_fixtures":sum(not x["event8_accepted"] for x in queue_cases),
 "mdk_geometry_pure_fixtures":len(mdk_cases),
 "u8_list_pure_fixtures":len(u8_cases),
 "ne_relocations_scanned":fixcount,
 "ne_grid_direct_far_callers":far,
 "source_ranges":region_receipts,
 "source_opcode_evidence":op_checks,
 "queue_model_fixtures":queue_cases,
 "mdk_geometric_upper_bound_fixtures":mdk_cases,
 "u8_two_pass_list_fixtures":u8_cases,
 "original_game_instructions_executed":0,
 "original_game_runtime_or_capture_executed":False,
 "fidelity_verified":False,
 "native_execution_admission_granted":False,
 "source_sha256":{k:sha(v) for k,v in original.items()},
 "original_parser_hashes":{
  "static_probe.py":sha((BASE/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01/static_probe.py").read_bytes()),
  "source_manifest.py":sha((BASE/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01/source_manifest.py").read_bytes()),
  "ne_glob_candidates.py":sha((BASE/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01/ne_glob_candidates.py").read_bytes()),
  "glob_callers.py":sha((BASE/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01/glob_callers.py").read_bytes())},
 "predecessor_sha256":sha(prior.read_bytes()),
 "registry_sha256":PIN["portfolio_registry"]["sha256"],
 "delta_sha256":sha((RUN/"SEMANTIC_DELTA.json").read_bytes()),
 "time_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "scope":"Read-only original static source and pure hand-written contract models; no gameplay, sprite/renderer capture, scene occupancy, or admission PASS."
}
path=RUN/"STATIC_VERIFICATION.json"
with path.open("x",encoding="utf-8") as f:
    json.dump(receipt,f,indent=2,sort_keys=True);f.write("\n")
print(json.dumps({k:receipt[k] for k in (
    "status","source_regions","source_opcode_checks","stonekeep_queue_pure_fixtures",
    "stonekeep_event8_accepted_fixtures","stonekeep_event8_rejected_fixtures",
    "mdk_geometry_pure_fixtures","u8_list_pure_fixtures","ne_relocations_scanned",
    "original_game_instructions_executed")},sort_keys=True))
