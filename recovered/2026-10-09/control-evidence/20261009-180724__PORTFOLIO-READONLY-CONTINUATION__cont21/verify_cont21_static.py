"""CONT21: original-source MDK group masks, Stonekeep level15 status and U8 alias rebase.

Immutable SHA-pinned read-only original source and pure Python state fixtures.
NO original game CPU-instruction execution, original runtime, build, capture,
writer/lease changes, or source/worktree modifications.
"""
from pathlib import Path
from collections import Counter
import json,struct,hashlib,sys
from capstone import Cs,CS_ARCH_X86,CS_MODE_16,CS_MODE_32

ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
SHA=lambda b:hashlib.sha256(b).hexdigest()
PINS={
 "registry":("orchestrator/control-plane/portfolio-lanes-20261008-v3.json","42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"),
 "prior":("output/projects/OpenRemasterOrchestrator/reports/20261009-175126__PORTFOLIO-READONLY-CONTINUATION__cont20/READ_ONLY_HANDOFF.json","7a19a2361026bb96086d648bb0b18484ca7beb1a3fd2a63ae9b01204d3bcedc4"),
 "MDK95":("source/MDK/MDK95.EXE","e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788"),
 "MDK_LEVEL3":("source/MDK/TRAVERSE/LEVEL3/LEVEL3O.MTO","6f33536701f57a404f8b25aa5580502cd68389de9ae591b53b018f415f7193ff"),
 "MDK_GROUP7":("output/projects/OpenRemasterOrchestrator/reports/20261009-175126__PORTFOLIO-READONLY-CONTINUATION__cont20/MDK_GROUP7_SOURCE_MEMBERS.json","a35bea2c78ed5f07b169db7d61ba664044fc86f12375ff7616527f5817ca1056"),
 "SK_EXE":("source/Stonekeep/SK.EXE","5517ddeb49c7087d6b2449182020200c58084feb4cae55e31ac8acc6cdbdddd2"),
 "SK_LEVEL01A":("source/Stonekeep/CD/DATA/START/SAVEGAME/GAME00/LEVEL01A.SAV","3d1753ca8a4ca49b3ccf9da0fc15bb08ac242301eff40586049379ceba635dc9"),
 "U8_EXE":("source/Ultima 8/ENGLISH/U8.EXE","1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f")
}
B={}
for key,(path,digest) in PINS.items():
    x=(ROOT/path).read_bytes()
    assert SHA(x)==digest,("SOURCE_IDENTITY_DRIFT",key)
    B[key]=x
old=json.loads(B["prior"].decode("utf-8-sig"))
assert len(old["portfolio"])==23 and len({x["project"] for x in old["portfolio"]})==23
assert old["operation_id"]=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
group7=json.loads(B["MDK_GROUP7"].decode("utf-8"))
assert len(group7["source_instances"])==186 and group7["source_member_count"]==186

sys.path.insert(0,str(ROOT/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load as mdload,offset as mdofs
mdk,secs=mdload()
assert mdk==B["MDK95"]
sys.path.insert(0,str(ROOT/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
from le_fixups import LE
sk=LEImage(B["SK_EXE"]);le=LE(B["SK_EXE"])
sys.path.insert(0,str(ROOT/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load as uload
u8,ne,segs=uload()
assert u8==B["U8_EXE"]

def emit(name,body):
    blob=(json.dumps(body,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    p=HERE/name
    if p.exists():
        assert p.read_bytes()==blob,("DIVERGENT_REPORT_OUTPUT",name)
    else:
        with p.open("xb") as f:f.write(blob)
    return SHA(blob)
regions=[];opcodes=[]
def decode(project,start,end,segment=None):
    assert start<end
    if project=="MDK":
        at=mdofs(secs,start,end-start);raw=mdk[at:at+(end-start)];mode=CS_MODE_32
    elif project=="Stonekeep":
        raw=sk.read_va(start,end-start);mode=CS_MODE_32
    else:
        item=segs[segment-1];assert not item["iterated"] and not item["data_segment"] and end<=item["size"]
        raw=u8[item["offset"]+start:item["offset"]+end];mode=CS_MODE_16
    seq=list(Cs(CS_ARCH_X86,mode).disasm(raw,start))
    assert seq and seq[0].address==start and seq[-1].address+seq[-1].size==end,("UNALIGNED_INSTRUCTION_BOUNDARY",project,start,end)
    regions.append({"project":project,"segment":segment,"start":hex(start),"end":hex(end),"sha256":SHA(raw)})
    return {x.address:x for x in seq}
def op(table,project,a,mn,contains,segment=None):
    q=table.get(a)
    assert q and q.mnemonic==mn and contains in q.op_str,(
        "SOURCE_INSTRUCTION_MISMATCH",project,hex(a),mn,contains,
        None if not q else(q.mnemonic,q.op_str))
    opcodes.append({"project":project,"segment":segment,"va":hex(a),"opcode":q.mnemonic+" "+q.op_str})

# MDK original mask producers and pending-state transition:
a=decode("MDK",0x40b4dc,0x40b5cf)
b=decode("MDK",0x40b5d0,0x40b722)
for va,mn,arg in [
 (0x40b4e8,"test","edx, edx"),
 (0x40b4ea,"je","0x40b582"),
 (0x40b4f0,"mov","[eax + 0x28]"),
 (0x40b4f3,"mov","[esi + 0x10]"),
 (0x40b4fc,"mov","byte ptr [eax + 0x20]"),
 (0x40b4ff,"test","dl, 2"),
 (0x40b506,"or","dh, 0x30"),
 (0x40b509,"mov","byte ptr [eax + 0x20]"),
 (0x40b521,"mov","[ebp - 0x14]"),
 (0x40b528,"mov","[esi + 0x110]"),
 (0x40b530,"test","eax, ecx"),
 (0x40b534,"mov","edx, 2"),
 (0x40b53e,"mov","[esi + 0x10c]"),
 (0x40b546,"test","eax, ebx"),
 (0x40b54f,"xor","edx, edx"),
 (0x40b55a,"call","0x40a704"),
 (0x40b574,"mov","edx, 4"),
 (0x40b582,"cmp","[eax + 0x114]"),
 (0x40b598,"mov","[esi + 0x114]"),
 (0x40b5a0,"test","edi, eax"),
 (0x40b5b2,"mov","edx, 2"),
 (0x40b5c0,"call","0x40a704"),
 (0x40b5c7,"and","[esi + 0x114]"),
 ]:op(a,"MDK",va,mn,arg)
for va,mn,arg in [
 (0x40b5e2,"mov","[edx + 0x23]"),
 (0x40b5e8,"test","ah, 0xff"),
 (0x40b5f4,"sar","eax, 0x18"),
 (0x40b5f7,"dec","eax"),
 (0x40b5fb,"cmp","eax, 0x10"),
 (0x40b60c,"mov","[eax + 0x6c]"),
 (0x40b60f,"test","edx, ecx"),
 (0x40b613,"test","dl, 0x80"),
 (0x40b61b,"inc","eax"),
 (0x40b623,"shl","edx, cl"),
 (0x40b628,"or","[ecx + 0x114]"),
 (0x40b631,"mov","edx, 3"),
 (0x40b63c,"call","0x40a704"),
 (0x40b677,"cmp","[eax + 0x8c]"),
 (0x40b702,"mov","[ebp - 0x14]"),
 (0x40b70e,"call","0x4546ac")
 ]:op(b,"MDK",va,mn,arg)

group7_records=group7["source_instances"]
tri_input=B["MDK_LEVEL3"]
assert all(int(row["original_source_flags_u32"],16)>>24==7 for row in group7_records)
assert all(not(int(row["original_source_flags_u32"],16)&0x30) for row in group7_records)
for row in group7_records:
    pos=row["original_file_offset"]
    packet=tri_input[pos:pos+36]
    assert len(packet)==36 and SHA(packet)==row["triangle_record_sha256"]
def mask_action(mask110,mask10c):
    """Exact static truth table for EDX!=0, one group bit, excluding premark bit2."""
    if not mask110 and not mask10c:return None
    if mask110:return 0  # SET0x30
    return 4             # SET0x20
truth=[]
for x in (0,1):
    for y in (0,1):
        act=mask_action(bool(x),bool(y))
        after=0 if act is None else (0x30 if act==0 else 0x20)
        truth.append({"group_id":7,"mask110_bit7":bool(x),"mask10c_bit7":bool(y),
                      "selected_group_action":act,"source_initial_flags_0x30":0,
                      "result_group7_low_flag_bits_0x30":hex(after),
                      "affected_original_group7_triangles":186 if act is not None else 0,
                      "runtime_observation":"NONE"})
assert [z["selected_group_action"] for z in truth]==[None,4,0,0]
# Conditional source producer -> pending bit: group7 (gid-1==6) indexed
# table+0x6c; bit0x80 and external mask gate must both be met.
pending_cases=[]
for enabled in (False,True):
  for field80 in (False,True):
    ready=enabled and field80
    pending_cases.append({
      "group_id":7,"original_source_gid_minus1_index":6,
      "external_mask_matches_group_table_byte":enabled,
      "group_table_byte_bit80":field80,
      "pending_group7_bit_set_if_gates":ready,
      "clear_group7_0x10_action3_if_gates":ready,
      "next_EDX0_service_will_set_group7_0x10_and_clear_pending":ready,
      "source_only_no_native_execution":True})
assert sum(p["pending_group7_bit_set_if_gates"] for p in pending_cases)==1
# Pending branch consumes groups0..31, group0 rejected by0x40a704.
assert (1<<7)==128 and group7["source_member_count"]==186
mdk_out={
 "schema":"OpenMDK1.GroupMaskProducerAndPendingLifecycle.v1",
 "MDK95_SHA256":PINS["MDK95"][1],
 "LEVEL3_SHA256":PINS["MDK_LEVEL3"][1],
 "prior_group7_fixture_sha256":PINS["MDK_GROUP7"][1],
 "source_group7_members_verified":186,
 "original_runtime_object_fields":{
    "+0x10":"triangle count","+0x28":"triangle record base",
    "+0x10c":"group mask B used by immediate update loop",
    "+0x110":"group mask A used by immediate update loop",
    "+0x114":"pending group bitset used by deferred EDX0 branch",
    "+0x6c + (group-1)":"per-group byte flags used by the triangle interaction producer"
 },
 "producer":"0x40b5d0 inspects original triangle+0x23 gid; when valid1..16, selected group-byte intersects external mask and bit0x80 is set, it adds bit1<<gid to +0x114 and calls 0x40a704 action3 to clear 0x10.",
 "immediate_group_update":"0x40b4dc EDX!=0 scans 32 group bits of +0x110 and +0x10c; under pure source initial bit2-clear conditions, truth table selects no-op, action4 or action0.",
 "deferred_group_update":"0x40b4dc EDX==0 scans +0x114 and calls action2 to SET0x10 for each pending group before clearing its pending bit.",
 "original_source_triangle_premark":"0x40b4fc..0x40b509 sets bits0x30 on per-triangle low flag bit0x02 if present; original LEVEL3 low flags do not initially contain bit0x02.",
 "group7_immediate_truth_table":truth,
 "group7_conditional_pending_examples":pending_cases,
 "warning":"Group7 source triangle flags initially clear, but live masks and stage/action ordering are unobserved. Pure models do not imply actual frame visibility or committed pending group.",
 "original_machine_instructions_executed":0,"runtime_fidelity_verified":False
}
mdk_sha=emit("MDK_GROUP7_PENDING_LIFECYCLE.json",mdk_out)

# Stonekeep original per-level status/resource identifier pair and live-unknown.
s1=decode("Stonekeep",0x3d383,0x3d3ee)
s2=decode("Stonekeep",0x81d73,0x81e45)
for va,mn,arg in [
 (0x3d383,"movsx","[0x1bc6a0]"),
 (0x3d38a,"mov","[eax*4 + 0xe9ae]"),
 (0x3d392,"mov","[eax*4 + 0xe9b0]"),
 (0x3d39d,"cmp","eax, -1"),
 (0x3d3a2,"cmp","[0x1b9d58]"),
 (0x3d3ab,"call","0x81d73"),
 (0x3d3b0,"mov","[0x1b9d58]"),
 (0x3d3ba,"cmp","eax, -1"),
 (0x3d3bf,"cmp","[0x1b9d5a]"),
 (0x3d3c8,"call","0x81d73"),
 (0x3d3cd,"mov","[0x1b9d5a]"),
 (0x3d3e0,"mov","[0x1b9d5a]"),
 ]:op(s1,"Stonekeep",va,mn,arg)
for va,mn,arg in [
 (0x81d7e,"imul","ebx, ebx, 0x52"),
 (0x81d81,"mov","[ebx + 0x10e49]"),
 (0x81dd9,"cwde",""),
 (0x81dda,"call","0x81c37"),
 (0x81e0e,"call","0x81ed2"),
 (0x81e13,"call","0x27700"),
 (0x81e37,"call","0xa7fd7"),
 (0x81e44,"ret","")
 ]:op(s2,"Stonekeep",va,mn,arg)
DS_base=le.objects[2]["base"]
assert DS_base==0xf0000
table=sk.read_va(DS_base+0xe9ae,4*23)
assert SHA(table)=="8fd24783fdc67843f9237c3f9ebea9481e64652279111473da7067282da859f2"
pairs=[]
for i in range(23):
    first,second=struct.unpack_from("<2H",table,4*i)
    pairs.append({"level_index":i,
                  "source_id_1":first if first!=65535 else -1,
                  "source_id_2":second if second!=65535 else -1})
assert (pairs[15]["source_id_1"],pairs[15]["source_id_2"])==(8,2)
levelcell=B["SK_LEVEL01A"]
off=11+(23*29+3)*21
assert (off,levelcell[off],levelcell[off+2])==(14081,1,0x8b)
assert struct.unpack_from("<h",levelcell,off+7)[0]==415
examples=[]
for p1,p2 in ((8,2),(8,1),(7,2),(-1,-1)):
    examples.append({"level_index":15,"live_prev_id_1_HYPOTHETICAL":p1,
                     "live_prev_id_2_HYPOTHETICAL":p2,
                     "source_new_ids":[8,2],
                     "conditional_resource_helper_calls":int(p1!=8)+int(p2!=2),
                     "state":"PURE_COMPARISON_ONLY"})
assert [x["conditional_resource_helper_calls"] for x in examples]==[0,1,1,2]
sk_out={
 "schema":"OpenStonekeep.Level15H415SourceResourcePairAndStatusGate.v1",
 "SK_EXE_sha256":PINS["SK_EXE"][1],
 "LEVEL01A_SAV_sha256":PINS["SK_LEVEL01A"][1],
 "source_level_index":"global[0x1bc6a0], runtime value unobserved",
 "source_level15_handler415_cell":{"row":23,"col":3,"serialized_offset":off,
    "byte0":"0x01","bit02":0,"source_callback":"level15 original global callback0x4f861 RET"},
 "source_static_id_pair_table":{"object3_base":hex(DS_base),
    "offset":"0xe9ae","sha256":SHA(table),
    "source_level_pairs":pairs},
 "source_level15_pair":[8,2],
 "previous_state_slots":["0x1b9d58","0x1b9d5a"],
 "0x3d383_branch":"If current serialized tile bit02 remains clear, source chooses status/resource-ID path; if new ID != -1 and differs from previous slot, calls0x81d73 and stores new ID.",
 "0x81d73_direct_calls":["0x81c37","0x81ed2","0x27700","0xa7fd7"],
 "0x81d73_resource_metadata":"Index AX by 0x52, source word at0x10e49; then additional object/resource helpers.",
 "pure_hypothetical_previous_pairs":examples,
 "stage_enqueue_direct_calls_seen_in_bounded_regions":0,
 "remaining_unknown":["Actual previous IDs and live level-index value",
    "transitive effects of 0x81d73 callees",
    "a separate input action2/3 and event8 queue generation/lifetime",
    "original runtime level transition and fidelity"],
 "original_machine_instructions_executed":0
}
sk_sha=emit("STONEKEEP_LEVEL15_RESOURCE_STATUS_PAIR.json",sk_out)

# U8 NE130 far-pointer array nonzero-offset DS segment rebase after source load.
ur=decode("Ultima8",0x1f67,0x1f9d,130)
for va,mn,arg in [
 (0x1f67,"mov","[bp - 2]"),
 (0x1f6a,"cmp","[0x8bde]"),
 (0x1f6e,"jae","0x1f9d"),
 (0x1f70,"les","[0x8c0a]"),
 (0x1f74,"add","[bp - 0xc]"),
 (0x1f7a,"mov","word ptr es:[bx]"),
 (0x1f80,"cmp","[bp - 6], 0"),
 (0x1f84,"je","0x1f8d"),
 (0x1f86,"mov","word ptr es:[bx + 2], ds"),
 (0x1f8a,"mov","word ptr es:[bx], ax"),
 (0x1f8d,"add","[bp - 0xc], 4"),
 (0x1f91,"inc","word ptr [bp - 2]"),
 (0x1f9b,"jb","0x1f70"),
 ]:op(ur,"Ultima8",va,mn,arg,130)
pointer_examples=[]
for offset,oldseg in ((0,0),(0,0xffff),(123,0),(123,0x1234),(4515,0x4321)):
    new=(offset,0xbeef if offset else oldseg)
    pointer_examples.append({
      "stored_offset":offset,"stored_segment":hex(oldseg),
      "DS_EXAMPLE_ONLY":"0xbeef","after_original_source_gate":(new[0],hex(new[1])),
      "condition":"Preserve slot bytes if offset zero; else rebase segment to current DS",
      "scope":"PURE_SOURCE_BRANCH_FIXTURE_NOT_GAME_CPU_EXECUTION"})
assert pointer_examples[1]["after_original_source_gate"]==(0,"0xffff")
assert pointer_examples[-1]["after_original_source_gate"]==(4515,"0xbeef")
u8_out={
 "schema":"OpenUltima8.UsecodeNameAliasPostTransferRebase.v1",
 "original_EXE_sha256":PINS["U8_EXE"][1],
 "source_name_alias_array":"DS:0x8c0a pointer, count DS:0x8bde",
 "source_rebase_loop":"NE130:0x1f67..0x1f9b",
 "normalization_condition":"Checks stored far-pointer OFFSET word for zero; when nonzero writes DS segment to slot+2 and original offset to slot+0.",
 "source_null_special_case":"OFFSET==0 skips rewrite; pre-existing segment word is not forced to zero in this bounded loop.",
 "source_sequence":"A far transfer call occurs earlier NE130:0x1f55; the rebase occurs after it, but exact archive/save semantics of that call remain unproven.",
 "indirect_mutation_scope":"This rebase mutates only the far-pointer ARRAY slots and is not a direct capability-flags write in USECODE metadata.",
 "pure_source_fixtures":pointer_examples,
 "limitations":["Current DS and real slot contents not observed",
   "Name-pointer consumers may write through aliases; no full alias/VM proof",
   "Loaded capability flags and GLOB218 runtime materialization still unobserved"],
 "original_machine_instructions_executed":0,"runtime_fidelity_verified":False
}
u8_sha=emit("U8_ALIAS_POST_TRANSFER_SEGMENT_REBASE.json",u8_out)
receipt={
 "schema":"OpenRemaster.CONT21ReadOnlySourceVerification.v1",
 "operation_id":old["operation_id"],
 "status":"PASS_SOURCE_STATIC_MASK_STATE_RESOURCE_PAIR_AND_ALIAS_REBASE_ONLY",
 "source_pins":{k:pin for k,(path,pin) in PINS.items()},
 "original_source_regions":regions,"original_opcode_checks":opcodes,
 "source_region_count":len(regions),"opcode_count":len(opcodes),
 "MDK_group7_source_members_checked":186,
 "MDK_mask_truth_table_cases":len(truth),
 "MDK_pending_pure_cases":len(pending_cases),
 "Stonekeep_level_source_table_records":len(pairs),
 "Stonekeep_hypothetical_previous_pair_cases":len(examples),
 "Ultima8_pure_pointer_cases":len(pointer_examples),
 "artifacts":{"MDK_GROUP7_PENDING_LIFECYCLE.json":mdk_sha,
              "STONEKEEP_LEVEL15_RESOURCE_STATUS_PAIR.json":sk_sha,
              "U8_ALIAS_POST_TRANSFER_SEGMENT_REBASE.json":u8_sha},
 "original_game_CPU_instructions_executed":0,"native_original_runtime":False,
 "fidelity_acceptance":False,"production_admission":False,
 "evidence_limit":"Static source and pure branch model; no native gameplay/alias memory readback/bitmap capture"
}
rec_sha=emit("STATIC_VERIFICATION.json",receipt)
print(json.dumps({"result":receipt["status"],"regions":len(regions),
    "opcode_checks":len(opcodes),"MDK_group7":186,"MDK_truth":len(truth),"MDK_pending":len(pending_cases),
    "Stonekeep_table_pairs":len(pairs),"Stonekeep_level15":[8,2],
    "U8_alias_model_cases":len(pointer_examples),"game_tests":0,
    "receipts":{**receipt["artifacts"],"STATIC_VERIFICATION.json":rec_sha}},sort_keys=True))
