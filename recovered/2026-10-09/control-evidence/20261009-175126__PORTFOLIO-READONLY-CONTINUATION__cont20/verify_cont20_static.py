"""CONT20 read-only source-static verification.

Creates self-contained evidence inside a newly allocated report directory.
No original game instructions executed or emulated. No writes to source,
project worktrees, shared orchestration journal, owners, tickets or leases.
"""
from pathlib import Path
from collections import Counter
from capstone import Cs,CS_ARCH_X86,CS_MODE_16,CS_MODE_32
import json,hashlib,struct,sys

ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PINS={
 "registry":("orchestrator/control-plane/portfolio-lanes-20261008-v3.json","42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"),
 "prev":("output/projects/OpenRemasterOrchestrator/reports/20261009-173113__PORTFOLIO-READONLY-CONTINUATION__cont19/READ_ONLY_HANDOFF.json","33d24661d1b1df885677aeaa4fbe3bc42e3bfcea6cefc64b72408cf32858202e"),
 "MDK95":("source/MDK/MDK95.EXE","e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788"),
 "LEVEL3":("source/MDK/TRAVERSE/LEVEL3/LEVEL3O.MTO","6f33536701f57a404f8b25aa5580502cd68389de9ae591b53b018f415f7193ff"),
 "MDK_audit":("output/projects/OpenRemasterOrchestrator/reports/20261009-151734__PORTFOLIO-READONLY-CONTINUATION__cont17/MDK_LEVEL3_PLANE_TRIANGLE_DUAL_RANGES.json","d0ceace9b390922a1773cfff5226e6af4fc479e2e74e83b1a4e5da761fed18df"),
 "SK_EXE":("source/Stonekeep/SK.EXE","5517ddeb49c7087d6b2449182020200c58084feb4cae55e31ac8acc6cdbdddd2"),
 "LEVEL01A":("source/Stonekeep/CD/DATA/START/SAVEGAME/GAME00/LEVEL01A.SAV","3d1753ca8a4ca49b3ccf9da0fc15bb08ac242301eff40586049379ceba635dc9"),
 "U8_EXE":("source/Ultima 8/ENGLISH/U8.EXE","1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f"),
 "EUSECODE":("source/Ultima 8/ENGLISH/USECODE/EUSECODE.FLX","5eceb14286f06f6bb07c35d0c83c0670d500474cd9a7390ad533c0f0f93f4e38"),
}
sha=lambda b:hashlib.sha256(b).hexdigest()
inputs={}
for k,(rel,pin) in PINS.items():
    data=(ROOT/rel).read_bytes()
    assert sha(data)==pin,("SOURCE_PIN_CHANGED",k,sha(data))
    inputs[k]=data
previous=json.loads(inputs["prev"].decode("utf-8-sig"))
assert previous["operation_id"]=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
assert len(previous["portfolio"])==23 and len({p["project"] for p in previous["portfolio"]})==23
assert {p["project"] for p in previous["portfolio"] if p["lane"]=="FOCUS_READ_ONLY"}=={"OpenMDK1","OpenStonekeep","OpenUltima8"}

sys.path.insert(0,str(ROOT/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load as mdload,offset as mdofs
mb,sections=mdload()
assert mb==inputs["MDK95"]
sys.path.insert(0,str(ROOT/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
im=LEImage(inputs["SK_EXE"])
sys.path.insert(0,str(ROOT/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load as uload
ub,ne,segs=uload()
assert ub==inputs["U8_EXE"]
src_regions=[];opcode_checks=[]

def first(project,va,seg=None):
    if project=="MDK":
        fo=mdofs(sections,va,20);v=mb[fo:fo+20];mode=CS_MODE_32
    elif project=="Stonekeep":
        v=im.read_va(va,20);mode=CS_MODE_32
    else:
        s=segs[seg-1]
        assert not s["iterated"] and not s["data_segment"] and va+20<=s["size"]
        v=ub[s["offset"]+va:s["offset"]+va+20];mode=CS_MODE_16
    q=next(Cs(CS_ARCH_X86,mode).disasm(v,va),None)
    assert q and q.address==va
    return q

def opcode(project,va,mn,needle,seg=None):
    q=first(project,va,seg)
    assert q.mnemonic==mn and needle in q.op_str,("ORIGINAL_OPCODE_DRIFT",project,seg,hex(va),mn,needle,(q.mnemonic,q.op_str))
    opcode_checks.append({"project":project,"segment":seg,"VA":hex(va),"original_opcode":q.mnemonic+" "+q.op_str})

def region(project,a,z,seg=None):
    if project=="MDK":
        at=mdofs(sections,a,z-a);raw=mb[at:at+z-a];mode=CS_MODE_32
    elif project=="Stonekeep":
        raw=im.read_va(a,z-a);mode=CS_MODE_32
    else:
        m=segs[seg-1];assert not m["iterated"] and not m["data_segment"] and z<=m["size"]
        raw=ub[m["offset"]+a:m["offset"]+z];mode=CS_MODE_16
    ops=list(Cs(CS_ARCH_X86,mode).disasm(raw,a))
    assert ops and ops[0].address==a and ops[-1].address+ops[-1].size==z,("UNALIGNED_SOURCE_REGION",project,hex(a),hex(z))
    src_regions.append({"project":project,"segment":seg,"start":hex(a),"end":hex(z),"original_sha256":sha(raw)})
    return ops

def emit(name,obj):
    body=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    dest=HERE/name
    if dest.exists():assert dest.read_bytes()==body,("CONFLICTING_SOURCE_REPORT",name)
    else:
        with dest.open("xb") as f:f.write(body)
    return sha(body)

# -------- MDK grouped + mutable triangle state --------
mdk_ranges=[(0x40a704,0x40a858),(0x409860,0x409a1b),
            (0x40b4dc,0x40b5cd),(0x40a688,0x40a6ec)]
for a,z in mdk_ranges:region("MDK",a,z)
for a,m,n in [
 (0x40a70c,"test","eax, eax"),(0x40a70e,"jle","0x40a749"),
 (0x40a710,"cmp","eax, 0xff"),(0x40a715,"jg","0x40a749"),
 (0x40a717,"shl","eax, 0x18"),(0x40a71a,"cmp","esi, 5"),
 (0x40a71d,"ja","0x40a821"),(0x40a723,"jmp","[esi*4 + 0x40a6ec]"),
 (0x40a733,"and","esi, 0xff000000"),(0x40a742,"add","edx, 0x24"),
 (0x40a80b,"or","byte ptr [edx + 0x20], 0x30"),
 (0x40a846,"and","byte ptr [edx + 0x20], 0xcf"),
 (0x40a76c,"or","byte ptr [edx + 0x20], 0x10"),
 (0x40a797,"and","byte ptr [edx + 0x20], 0xef"),
 (0x40a7c2,"or","byte ptr [edx + 0x20], 0x20"),
 (0x40a7f9,"and","byte ptr [edx + 0x20], 0xdf"),
 (0x40986b,"lea","[ebx*8]"),(0x40987b,"add","ecx, ebx"),
 (0x40987f,"shl","ecx, 2"),(0x40989d,"mov","byte ptr [esi + 0x20]"),
 (0x4098a0,"test","ah, 0x10"),(0x4098a3,"je","0x4098da"),
 (0x4098b1,"add","esi, 0x24"),(0x409946,"call","0x40ca00"),
 (0x40b55a,"call","0x40a704"),(0x40b5c0,"call","0x40a704"),
 (0x40a69f,"mov","[0x4a2460]"),(0x40a6a5,"mov","[0x4a2464]"),
 (0x40a6ab,"mov","[0x4a2458]"),(0x40a6b1,"mov","[0x4a2468]"),
 (0x40a6de,"call","0x409a6c")
]:opcode("MDK",a,m,n)
raw_switch=mb[mdofs(sections,0x40a6ec,24):mdofs(sections,0x40a6ec,24)+24]
switch=struct.unpack("<6I",raw_switch)
assert switch==(0x40a72a,0x40a821,0x40a74f,0x40a77a,0x40a7a5,0x40a7d4)
group_actions=[
 {"selector":0,"op":"SET","mask":0x30},
 {"selector":1,"op":"CLEAR","mask":0x30},
 {"selector":2,"op":"SET","mask":0x10},
 {"selector":3,"op":"CLEAR","mask":0x10},
 {"selector":4,"op":"SET","mask":0x20},
 {"selector":5,"op":"CLEAR","mask":0x20},
 {"selector":6,"op":"CLEAR","mask":0x30,"source_branch":"DEFAULT_UNSIGNED_ABOVE_5"}
]
mdk_audit=json.loads(inputs["MDK_audit"].decode("utf-8"))
assert mdk_audit["total_source_triangles"]==7205
triangles=[]
groups=Counter();lowbytes=Counter();members=[]
for h in mdk_audit["hmos"]:
    start=h["triangle_stream_absolute"]
    for ix in range(h["triangles"]):
        packet=inputs["LEVEL3"][start+ix*36:start+(ix+1)*36]
        assert len(packet)==36
        state=struct.unpack_from("<I",packet,0x20)[0]
        group=(state>>24)&255
        groups[group]+=1;lowbytes[state&255]+=1
        triangles.append((group,state))
        if group==7:
            members.append({
                "hmo":h["hmo"],"triangle":ix,
                "original_file_offset":start+ix*36,
                "triangle_record_sha256":sha(packet),
                "original_source_flags_u32":hex(state),
                "original_f3_signed":struct.unpack_from("<h",packet,6)[0],
                "vertex_indices":list(struct.unpack_from("<3H",packet,0)),
                "original_machine_runtime":"UNOBSERVED"
            })
assert len(triangles)==7205 and groups[0]==6161
assert sum(v for k,v in groups.items() if k)!=0 and sum(v for k,v in groups.items() if k)!=1045
assert sum(v for k,v in groups.items() if k)==1044
assert groups[7]==186 and len(members)==186
assert all((state&0x30)==0 for group,state in triangles)
assert lowbytes=={0:6379,1:791,2:1,3:34}
# Source action 6 is a default "CLEAR BOTH" -- not a new seventh specialized routine.
def action_apply(group_id,action):
    if group_id<=0 or group_id>255:return [state for _,state in triangles]
    desc=group_actions[action]
    return [((state|desc["mask"]) if desc["op"]=="SET" else (state & (~desc["mask"] & 0xffffffff))) if group==group_id else state
            for group,state in triangles]
fixtures=[]
for group in (0,7,14,15,255):
    for action in range(7):
        vals=action_apply(group,action)
        changes=sum(a!=b for a,(_,b) in zip(vals,triangles))
        expect=groups[group] if 1<=group<=14 and action in (0,2,4) else 0
        assert changes==expect,(group,action,changes,expect)
        assert all((st>>24)==(source_st>>24) for st,(_,source_st) in zip(vals,triangles))
        fixtures.append({"target_group":group,"action":action,"mask":hex(group_actions[action]["mask"]),
                         "changed_records":changes,"model":"PURE_BITWISE_MODEL_NOT_ORIGINAL_INSTRUCTION_EXECUTION"})
assert len(fixtures)==35
assert sum(1 for v in action_apply(7,2) if v&0x10)==186
assert action_apply(7,3)==[state for _,state in triangles]
group_report={
 "schema":"OpenMDK1.LEVEL3Group7VisibilityAndDefaultAction.v1",
 "original_EXE_sha256":PINS["MDK95"][1],
 "original_MTO_sha256":PINS["LEVEL3"][1],
 "source_switch_sha256":sha(raw_switch),"source_switch_targets":[hex(x) for x in switch],
 "source_group_action_semantics":group_actions,
 "operation_gt5_unsigned_fallback":"0x40a71d JA 0x40a821 → CLEAR flags0x30",
 "negative_group_conditions":"group0 rejected by EAX<=0, group>255 rejected by cmp0xff",
 "source_total_triangles":7205,"source_group0":6161,"source_nonzero_groups":1044,
 "source_group7":186,"source_group_distribution":{str(k):v for k,v in sorted(groups.items())},
 "source_initial_bit10_or20_set_count":0,
 "source_low_byte_counts":{str(k):v for k,v in sorted(lowbytes.items())},
 "renderer_filter":"0x4098a0 TEST 0x10, JE normal render at0x4098da when clear; 0x10 SET jumps over draw path into scan-next",
 "pure_negative_fixture_count":len(fixtures),"pure_fixtures":fixtures,
 "group7_pinned_instances":len(members),"original_game_runtime_held":True
}
group_sha=emit("MDK_GROUP7_VISIBILITY_CONTRACT.json",group_report)
members_sha=emit("MDK_GROUP7_SOURCE_MEMBERS.json",{
    "schema":"OpenMDK1.LEVEL3Group7OriginalMemberProvenance.v1",
    "MTO_sha256":PINS["LEVEL3"][1],"source_member_count":186,
    "source_instances":members,"source_scope_only":True})
# ---------- Stonekeep original serialized level01A h415 tile ----------
save=inputs["LEVEL01A"]
sys.path.insert(0,str(ROOT/"work/OpenStonekeep-E16/tools"))
from inspect_level_save import parse as parse_level
info=parse_level(ROOT/PINS["LEVEL01A"][0])
assert (info["row_count"],info["column_count"],info["grid_start"],info["cell_size"])==(26,29,11,21)
pos=(23,3);r,c=pos
off=11+(r*29+c)*21
cell=save[off:off+21]
assert len(cell)==21 and off==14081
assert cell[0]==1 and cell[2]==0x8b and struct.unpack_from("<h",cell,7)[0]==415
assert not (cell[0]&2)
before_cell=save[11+(22*29+3)*21:11+(22*29+4)*21]
assert struct.unpack_from("<h",before_cell,7)[0]==85
assert before_cell[0]==1
sk_ranges=[(0x3d35e,0x3d38a),(0x3d383,0x3d3ee),(0x3c14d,0x3c1b6),
           (0x3c19f,0x3c1a5),(0x3d3ee,0x3d454),(0x4f861,0x4f862)]
for a,z in sk_ranges:region("Stonekeep",a,z)
for a,m,n in [
 (0x3d362,"movsx","[0x1bc69a]"),(0x3d369,"movsx","[0x1bc698]"),
 (0x3d370,"mov","eax, 1"),(0x3d375,"call","0x3c14d"),
 (0x3d37c,"and","al, 2"),(0x3d381,"jne","0x3d3ee"),
 (0x3c153,"mov","ecx, eax"),(0x3c197,"jmp","cs:[ebx*4 + 0x2c115]"),
 (0x3c1a1,"mov","byte ptr [eax]"),
 (0x3d383,"movsx","[0x1bc6a0]"),
 (0x3d3ab,"call","0x81d73"),(0x3d3c8,"call","0x81d73"),
 (0x3d3b0,"mov","[0x1b9d58]"),(0x3d3cd,"mov","[0x1b9d5a]"),
 (0x3d3e0,"mov","[0x1b9d5a]"),(0x4f861,"ret","")
]:opcode("Stonekeep",a,m,n)
jmp_table=im.read_va(0x3c115,56)
jmp_entries=struct.unpack("<14I",jmp_table)
assert jmp_entries[0]+0x10000==0x3c19f
tile_fixtures=[]
for original_byte in (0,1,2,3,4,5,6,7,255):
    tile_fixtures.append({"byte0":original_byte,"bit02":bool(original_byte&2),
                          "source_branch":"0x3D3EE" if original_byte&2 else "0x3D383",
                          "source_only_not_live":True})
assert len(tile_fixtures)==9 and tile_fixtures[1]["source_branch"]=="0x3D383"
sk_report={
 "schema":"OpenStonekeep.H415OriginalLevel01AByteAndAction0Branch.v1",
 "original_SK_EXE_sha256":PINS["SK_EXE"][1],
 "original_LEVEL01A_SAV_sha256":PINS["LEVEL01A"][1],
 "original_serialized_grid":{"rows":26,"cols":29,"cell_stride":21,"first_cell_offset":11},
 "h415_source_cell":{"row":23,"col":3,"handler":415,"file_offset":off,
                      "raw_hex":cell.hex(),"sha256":sha(cell),
                      "byte0":cell[0],"source_test_mask0x02_result":cell[0]&2,"byte2":cell[2]},
 "arrival_h85_source_byte0":before_cell[0],
 "original_level15_callback":"0x4F861 one-byte RET",
 "original_selector1_jump_table_sha256":sha(jmp_table),
 "h415_action0_source_path":"0x3D35E invokes0x3C14D selector1, returns cell.byte0, AND AL,0x02 at0x3D37C; source initial byte0=0x01 → 0x3D383 status/audio branch",
 "source_initial_bit02_clear_followup":"0x3D383..0x3D3ED reads level status tables, invokes0x81D73 conditionally up to twice and updates globals0x1b9d58/5a, not direct h415 stage/queue calls",
 "pure_tile_fixtures":tile_fixtures,
 "must_remain_conditional":"Live cell byte0 or current player location may differ after crossing/other effects; indirect audio helper and input action2/3 still unverified",
 "source_h415_live_context":"UNOBSERVED","original_game_instruction_tests":0
}
sk_sha=emit("STONEKEEP_H415_SERIALIZED_TILE_AND_BRANCH.json",sk_report)
# -------- Ultima 8 pointer-array direct lifecycle ----------
u8_ranges=[(130,0x1731,0x175a),(130,0x198b,0x19d1),
           (130,0x1d07,0x1d25),(126,0xd97,0xdcd)]
for seg,a,z in u8_ranges:region("Ultima8",a,z,seg)
for seg,a,m,n in [
 (130,0x1744,"shl","ax, 2"),
 (130,0x1747,"les","[0x8c0a]"),
 (130,0x174d,"mov","word ptr es:[bx + 2], 0"),
 (130,0x1753,"mov","word ptr es:[bx], 0"),
 (130,0x198b,"mov","[0x8bde]"),
 (130,0x198e,"shl","ax, 2"),
 (130,0x1992,"lcall","0xffff"),
 (130,0x199e,"mov","[0x8c0a]"),
 (130,0x19bc,"les","[0x8c0a]"),
 (130,0x19c8,"rep stosw",""),
 (130,0x19cc,"rep stosb",""),
 (130,0x1d0b,"push","[0x8c0a]"),
 (130,0x1d0f,"lcall","0xffff"),
 (130,0x1d17,"mov","[0x8c0c], 0"),
 (130,0x1d1d,"mov","[0x8c0a], 0"),
 (126,0xd99,"mov","dx, 0xd"),
 (126,0xd9c,"imul","dx"),
 (126,0xda2,"mov","[0x88f6]"),
 (126,0xda8,"add","bx, 4"),
 (126,0xdb4,"shl","ax, 2"),
 (126,0xdb7,"les","[0x8c0a]"),
 (126,0xdc3,"mov","word ptr es:[bx + 2]"),
 (126,0xdc7,"mov","word ptr es:[bx]")
]:opcode("Ultima8",a,m,n,seg)
flx=inputs["EUSECODE"]
assert struct.unpack_from("<I",flx,0x54)[0]==1433
meta_offset,meta_length=struct.unpack_from("<II",flx,0x88)
assert meta_length==1431*13
record347=flx[meta_offset+347*13:meta_offset+348*13]
assert len(record347)==13 and struct.unpack_from("<I",record347)[0]==0x40
assert (struct.unpack_from("<I",record347)[0]&0x000f8000)==0
array_cases=[{"shape":i,"source_metadata_name_offset":i*13+4,
              "alias_slot_byte_offset":i*4,
              "source_flag_bytes_written_directly":False,
              "runtime_table_contents":"UNOBSERVED"}
             for i in (0,128,347,1430)]
assert array_cases[2]["source_metadata_name_offset"]==4515
u8_report={
 "schema":"OpenUltima8.UsecodeNameAliasLifecycleBoundedOriginalCode.v1",
 "original_EXE_sha256":PINS["U8_EXE"][1],"original_FLX_sha256":PINS["EUSECODE"][1],
 "metadata_shape347_original_record13_sha256":sha(record347),
 "original_shape347_default_flags":"0x40",
 "original_shape347_mask_result":0,
 "original_alias_array_far_pointer":"DS:0x8c0a",
 "array_allocation_and_clear":"NE130:0x198b..0x19d0, DS:0x8bde count*4 and REP STOSW/STOSB",
 "per_slot_clear":"NE130:0x1731..0x1759",
 "array_disposal":"NE130:0x1d07..0x1d24",
 "alias_store":"NE126:0xd97..0xdca; USECODE shape*13+4 to slot*4",
 "source_direct_write_target":"Alias pointer slot; not USECODE four capability-flag bytes",
 "pure_name_cases":array_cases,
 "indirect_table_mutation":"NOT_EXCLUDED","native_memory_observed":False
}
u8_sha=emit("U8_USECODE_NAME_POINTER_ARRAY_BOUND.json",u8_report)
receipt={
 "schema":"OpenRemaster.CONT20StaticSourceVerification.v1",
 "status":"PASS_ORIGINAL_SOURCE_BYTES_OPCODE_AND_PURE_MODEL_FIXTURES_ONLY",
 "operation_id":previous["operation_id"],"iteration_id":"CONT20",
 "source_pins":{k:pin for k,(rel,pin) in PINS.items()},
 "source_regions":src_regions,"source_region_count":len(src_regions),
 "opcode_checks":opcode_checks,"opcode_count":len(opcode_checks),
 "MDK_group0_source_triangles":6161,
 "MDK_nonzero_groups_source_triangles":1044,
 "MDK_group7_source_triangles":186,
 "MDK_pure_bitwise_cases":len(fixtures),
 "Stonekeep_h415_serialized_bit02":0,
 "Stonekeep_pure_tile_cases":len(tile_fixtures),
 "Ultima8_pure_alias_pointer_cases":len(array_cases),
 "artifacts":{
  "MDK_GROUP7_VISIBILITY_CONTRACT.json":group_sha,
  "MDK_GROUP7_SOURCE_MEMBERS.json":members_sha,
  "STONEKEEP_H415_SERIALIZED_TILE_AND_BRANCH.json":sk_sha,
  "U8_USECODE_NAME_POINTER_ARRAY_BOUND.json":u8_sha
 },
 "original_game_machine_instructions_executed":0,
 "original_game_runtime_executed":False,
 "visual_fidelity_verified":False,
 "native_production_admission_granted":False,
 "static_not_runtime_note":"Original source bytes and pure bit/tile/offset models; no live state or complete alias-analysis proof"
}
rec_sha=emit("STATIC_VERIFICATION.json",receipt)
print(json.dumps({
 "status":receipt["status"],"source_regions":len(src_regions),
 "opcode_checks":len(opcode_checks),"MDK_group7":186,"MDK_group0":6161,
 "MDK_pure_cases":len(fixtures),"Stonekeep_tile_source_mask":0,
 "Stonekeep_cases":len(tile_fixtures),"U8_cases":len(array_cases),
 "artifacts":{**receipt["artifacts"],"STATIC_VERIFICATION.json":rec_sha},
 "original_runtime_tests":0
},sort_keys=True))
