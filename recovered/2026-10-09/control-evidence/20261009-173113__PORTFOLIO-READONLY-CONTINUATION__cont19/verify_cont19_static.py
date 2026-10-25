"""CONT19: read-only static source-mechanism and pure-model verification.

No original machine code execution, game runtime, builds, captures, shared
journal writes, or modifications to sources/project worktrees.
Only produces deterministic JSON in this newly allocated report directory.
"""
from pathlib import Path
from collections import Counter
import sys,hashlib,struct,json
from capstone import Cs,CS_ARCH_X86,CS_MODE_16,CS_MODE_32

ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
SHA=lambda b:hashlib.sha256(b).hexdigest()
PINS={
  "registry":("orchestrator/control-plane/portfolio-lanes-20261008-v3.json","42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"),
  "prior":("output/projects/OpenRemasterOrchestrator/reports/20261009-155120__PORTFOLIO-READONLY-CONTINUATION__cont18/READ_ONLY_HANDOFF.json","bf2869e2bd8ea39e5f7f877f94bf934e25cc486cd14f41d8d023f33f7d865248"),
  "mdkexe":("source/MDK/MDK95.EXE","e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788"),
  "mdkmto":("source/MDK/TRAVERSE/LEVEL3/LEVEL3O.MTO","6f33536701f57a404f8b25aa5580502cd68389de9ae591b53b018f415f7193ff"),
  "mdkaudit":("output/projects/OpenRemasterOrchestrator/reports/20261009-151734__PORTFOLIO-READONLY-CONTINUATION__cont17/MDK_LEVEL3_PLANE_TRIANGLE_DUAL_RANGES.json","d0ceace9b390922a1773cfff5226e6af4fc479e2e74e83b1a4e5da761fed18df"),
  "stone":("source/Stonekeep/SK.EXE","5517ddeb49c7087d6b2449182020200c58084feb4cae55e31ac8acc6cdbdddd2"),
  "u8":("source/Ultima 8/ENGLISH/U8.EXE","1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f"),
  "flx":("source/Ultima 8/ENGLISH/USECODE/EUSECODE.FLX","5eceb14286f06f6bb07c35d0c83c0670d500474cd9a7390ad533c0f0f93f4e38")
}
B={}
for key,(path,digest) in PINS.items():
    raw=(ROOT/path).read_bytes()
    assert SHA(raw)==digest,("SOURCE_PIN_CHANGED",key,SHA(raw))
    B[key]=raw
old=json.loads(B["prior"].decode("utf-8-sig"))
assert old["operation_id"]=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
assert len(old["portfolio"])==23 and len({p["project"] for p in old["portfolio"]})==23

sys.path.insert(0,str(ROOT/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load as mdload,offset as mdofs
mb,mdsections=mdload()
assert mb==B["mdkexe"]
sys.path.insert(0,str(ROOT/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
from le_fixups import LE
sk=LEImage(B["stone"]);le=LE(B["stone"])
sys.path.insert(0,str(ROOT/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load as uload
ub,ne,segs=uload()
assert ub==B["u8"]

def emit(name,obj):
    raw=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    p=HERE/name
    if p.exists():assert p.read_bytes()==raw,("REPORT_OUTPUT_CONFLICT",name)
    else:
        with p.open("xb") as f:f.write(raw)
    return SHA(raw)

byte_regions=[];opchecks=[]
def anchored(project,start,end,seg=None):
    assert start<end
    if project=="MDK":
        fo=mdofs(mdsections,start,end-start);raw=mb[fo:fo+end-start];bits=CS_MODE_32
    elif project=="Stonekeep":
        raw=sk.read_va(start,end-start);bits=CS_MODE_32
    else:
        m=segs[seg-1]
        assert m["size"]>=end and not m["iterated"] and not m["data_segment"]
        raw=ub[m["offset"]+start:m["offset"]+end];bits=CS_MODE_16
    assert len(raw)==end-start
    instr=list(Cs(CS_ARCH_X86,bits).disasm(raw,start))
    assert instr and instr[0].address==start and instr[-1].address+instr[-1].size==end,("UNALIGNED_OPCODE_REGION",project,seg,hex(start),hex(end))
    byte_regions.append({"project":project,"segment":seg,"start":hex(start),"end":hex(end),"sha256":SHA(raw)})
    return {x.address:x for x in instr}

def ck(src,project,addr,mnemonic,text,seg=None):
    q=src.get(addr)
    assert q and q.mnemonic==mnemonic and text in q.op_str,("OPCODE_CONTRACT_DRIFT",project,hex(addr),mnemonic,text, None if not q else (q.mnemonic,q.op_str))
    opchecks.append({"project":project,"segment":seg,"address":hex(addr),"opcode":q.mnemonic+" "+q.op_str})

# ---- MDK original group selector and per-triangle runtime filter ----
mdk_entries=[
    (0x40a704,0x40a858),
    (0x409860,0x4098da),
    (0x40b4dc,0x40b5cd),
    (0x40a688,0x40a6ec),
    (0x409a6c,0x409aa8)
]
mcode={}
for a,z in mdk_entries:
    for at,ins in anchored("MDK",a,z).items():
        assert at not in mcode
        mcode[at]=ins

for a,m,n in [
 (0x40a70c,"test","eax, eax"),(0x40a70e,"jle","0x40a749"),
 (0x40a710,"cmp","eax, 0xff"),(0x40a715,"jg","0x40a749"),
 (0x40a717,"shl","eax, 0x18"),(0x40a71a,"cmp","esi, 5"),
 (0x40a723,"jmp","[esi*4 + 0x40a6ec]"),
 (0x40a733,"and","0xff000000"),(0x40a739,"cmp","esi, eax"),
 (0x40a742,"add","edx, 0x24"),
 (0x40a80b,"or","byte ptr [edx + 0x20], 0x30"),
 (0x40a846,"and","byte ptr [edx + 0x20], 0xcf"),
 (0x40a76c,"or","byte ptr [edx + 0x20], 0x10"),
 (0x40a797,"and","byte ptr [edx + 0x20], 0xef"),
 (0x40a7c2,"or","byte ptr [edx + 0x20], 0x20"),
 (0x40a7f9,"and","byte ptr [edx + 0x20], 0xdf"),
 (0x40986b,"lea","[ebx*8]"),(0x40987b,"add","ecx, ebx"),
 (0x40987f,"shl","ecx, 2"),
 (0x40989d,"mov","byte ptr [esi + 0x20]"),
 (0x4098a0,"test","ah, 0x10"),
 (0x4098a3,"je","0x4098da"),
 (0x4098b1,"add","esi, 0x24"),
 (0x4098b4,"inc","ebx"),
 (0x40b55a,"call","0x40a704"),(0x40b5c0,"call","0x40a704"),
 (0x40a69f,"mov","[0x4a2460]"),(0x40a6a5,"mov","[0x4a2464]"),
 (0x40a6ab,"mov","[0x4a2458]"),(0x40a6b1,"mov","[0x4a2468]"),
 (0x40a6de,"call","0x409a6c"),(0x409a80,"mov","[0x4a2468]")
]:
    ck(mcode,"MDK",a,m,n)

raw_table=mb[mdofs(mdsections,0x40a6ec,24):mdofs(mdsections,0x40a6ec,24)+24]
switch_targets=struct.unpack("<6I",raw_table)
assert switch_targets==(0x40a72a,0x40a821,0x40a74f,0x40a77a,0x40a7a5,0x40a7d4)
actions=[
 {"selector":0,"operation":"OR","mask":0x30,"source_write_va":"0x40a80b"},
 {"selector":1,"operation":"AND_NOT","mask":0x30,"source_write_va":"0x40a846"},
 {"selector":2,"operation":"OR","mask":0x10,"source_write_va":"0x40a76c"},
 {"selector":3,"operation":"AND_NOT","mask":0x10,"source_write_va":"0x40a797"},
 {"selector":4,"operation":"OR","mask":0x20,"source_write_va":"0x40a7c2"},
 {"selector":5,"operation":"AND_NOT","mask":0x20,"source_write_va":"0x40a7f9"}
]
groups=Counter();lowbytes=Counter();hmo_groups={};total=0;flags=[]
audit=json.loads(B["mdkaudit"])
assert audit["total_source_triangles"]==7205
for h in audit["hmos"]:
    gc=Counter();start=h["triangle_stream_absolute"]
    for i in range(h["triangles"]):
        rec=B["mdkmto"][start+i*36:start+(i+1)*36]
        assert len(rec)==36
        state=struct.unpack_from("<I",rec,0x20)[0]
        group=(state>>24)&255
        flags.append(state)
        groups[group]+=1;gc[group]+=1
        lowbytes[state&255]+=1
        assert (state&0x30)==0,("INITIAL_RUNTIME_FLAG_NOT_ZERO",h["hmo"],i,hex(state))
        total+=1
    hmo_groups[h["hmo"]]={str(k):v for k,v in sorted(gc.items())}
assert total==7205 and groups[0]==6161 and sum(v for k,v in groups.items() if k)>0
assert sum(v for k,v in groups.items() if k>0)==1044
assert max(groups)==14 and len(groups)==15
assert groups[7]==186
assert lowbytes=={0:6379,1:791,2:1,3:34},lowbytes

def apply(gid,action):
    # This is a PURE PYTHON model of the original bitwise group contract.
    if gid<1 or gid>255:return flags.copy()
    item=actions[action]
    mask=item["mask"]
    result=[]
    for state in flags:
        if ((state>>24)&255)==gid:
            if item["operation"]=="OR":state|=mask
            else:state&=(~mask)&0xffffffff
        result.append(state)
    return result

fixtures=[]
for gid in (0,7,14,15,255):
    for action in range(6):
        updated=apply(gid,action)
        changed=sum(a!=b for a,b in zip(flags,updated))
        mask=actions[action]["mask"]
        expected=groups[gid] if 1<=gid<=14 and action in (0,2,4) else 0
        assert changed==expected,(gid,action,changed,expected)
        assert all((s>>24)==(orig>>24) for s,orig in zip(updated,flags))
        fixtures.append({"group_id":gid,"selector":action,"operation":actions[action],
                         "modified_triangle_count":changed,
                         "scope":"PURE_BITWISE_SOURCE_MODEL_NOT_ORIGINAL_GAME_EXECUTION"})
seq=apply(7,2)
assert sum(bool(x&0x10) for x in seq)==186
seq=[(x&~0x10) if ((x>>24)&255)==7 else x for x in seq]
assert seq==flags
group_out={
 "schema":"OpenMDK1.LEVEL3RuntimeTriangleGroupFlags.v1",
 "original_EXE_sha256":PINS["mdkexe"][1],
 "original_MTO_sha256":PINS["mdkmto"][1],
 "source_ranges":{k:v for k,v in enumerate(mdk_entries)},
 "original_jumptable":"0x40a6ec",
 "original_jumptable_raw_sha256":SHA(raw_table),
 "original_jumptable_targets":[hex(x) for x in switch_targets],
 "group_field":"(u32 triangle[+0x20] >>24)&0xff",
 "valid_action_target_groups":"1..255; group0 excluded by EAX<=0 guard",
 "source_triangle_state_byte_offset":0x20,
 "original_group_change_actions":actions,
 "source_total_triangles":total,
 "group_counts":{str(k):v for k,v in sorted(groups.items())},
 "group_counts_by_hmo":hmo_groups,
 "group0_non_targetable_by_this_function":groups[0],
 "nonzero_group_source_triangles":1044,
 "source_low_byte_distribution":{str(k):v for k,v in sorted(lowbytes.items())},
 "initial_bit10_set":0,"initial_bit20_set":0,
 "runtime_filter":"0x40989d loads byte[triangle+0x20]; 0x4098a0 tests 0x10. Set bit skips normal processing path for that record; mutable at0x40a76c and0x40a797.",
 "batch_caller_sites":["0x40b55a","0x40b5c0"],
 "pure_bitwise_fixtures":fixtures,
 "pure_toggle_group7":"bit0x10 sets 186 source records in group7 and clearing restores original array; not executed machine instructions",
 "original_machine_instructions_executed":0,
 "visual_fidelity_verified":False
}
group_sha=emit("MDK_TRIANGLE_GROUP_RUNTIME_FILTER.json",group_out)

view={
 "schema":"OpenMDK1.OriginalViewVectorPointerSource.v1",
 "original_EXE_sha256":PINS["mdkexe"][1],
 "caller_function":"0x40a688",
 "original_global_pointer":"0x4a2468",
 "source_assignment":"0x40a6b1 MOV DWORD PTR [0x4a2468], EAX (caller view vector pointer)",
 "source_original_loader_globals":{"plane_blob":"0x4a2460","triangle_blob":"0x4a2464","vertex_blob":"0x4a2458"},
 "subsequent_view_source_use":"0x40a6de calls0x409a6c; 0x409a80 reads pointer at0x4a2468 to three float components",
 "camera_identity":"UNOBSERVED","runtime_coordinates":"UNOBSERVED",
 "source_region_sha256":[{"from":hex(a),"to":hex(z),"sha256":next(x["sha256"] for x in byte_regions if x["project"]=="MDK" and x["start"]==hex(a))} for a,z in ((0x40a688,0x40a6ec),(0x409a6c,0x409aa8))],
 "important_limit":"This binds view-vector pointer assignment to traversal, not a captured camera pose or original executable replay."
}
view_sha=emit("MDK_VIEW_VECTOR_POINTER_SOURCE.json",view)

# ---- Stonekeep original current-cell selector1: byte 0x02 ----
sregions=[
 (0x3d35e,0x3d38a),
 (0x3c14d,0x3c1a5),
 (0x3c19f,0x3c1a5),
 (0x3d3ee,0x3d454)
]
scode={}
for a,z in sregions:
    for addr,ins in anchored("Stonekeep",a,z).items():
        assert addr not in scode or scode[addr].bytes==ins.bytes
        scode[addr]=ins
for a,m,n in [
 (0x3d362,"movsx","[0x1bc69a]"),
 (0x3d369,"movsx","[0x1bc698]"),
 (0x3d370,"mov","eax, 1"),
 (0x3d375,"call","0x3c14d"),
 (0x3d37c,"and","al, 2"),
 (0x3d381,"jne","0x3d3ee"),
 (0x3c153,"mov","ecx, eax"),
 (0x3c188,"mov","ebx, ecx"),
 (0x3c18a,"dec","ebx"),
 (0x3c197,"jmp","cs:[ebx*4 + 0x2c115]"),
 (0x3c19f,"xor","edx, edx"),
 (0x3c1a1,"mov","byte ptr [eax]"),
 (0x3c1a3,"jmp","0x3c1ee"),
 (0x3d42d,"call","0x3d454"),
 (0x3d439,"call","0x3d454")
]:
    ck(scode,"Stonekeep",a,m,n)
obj1_base=le.objects[0]["base"]
assert obj1_base==0x10000
table_va=obj1_base+0x2c115
table=sk.read_va(table_va,14*4)
case_offsets=struct.unpack("<14I",table)
case_targets=[obj1_base+off for off in case_offsets]
assert case_targets[0]==0x3c19f
assert all(0x3c19f<=x<=0x3c1e9 for x in case_targets)
assert case_targets[1]==0x3c1a5 and case_targets[-1]==0x3c1e9
tile_cases=[{"tile_byte":v,"first_case":"0x3c19f","mask_0x02_set":bool(v&2),
             "subsequent_branch":"0x3d3ee (rectangular area conditions)" if v&2 else "0x3d383 (level status/audio)",
             "scope":"PURE_SOURCE_MODEL_NO_ACTUAL_LEVEL15_TILE_READBACK"} for v in (0,1,2,3,4,5,6,7,255)]
assert sum(c["mask_0x02_set"] for c in tile_cases)==5
stone_out={
 "schema":"OpenStonekeep.H415Action0TileBitAndLevelHelperContract.v1",
 "original_EXE_sha256":PINS["stone"][1],
 "original_source_jump_table_linear":hex(table_va),
 "jump_table_original_bytes_sha256":SHA(table),
 "jump_table_target_cs_offsets":[hex(x) for x in case_offsets],
 "jump_table_linear_targets":[hex(x) for x in case_targets],
 "action0_helper":"0x3d35e",
 "helper_input":"0x3d370 EAX=1 and original player row/col registers loaded from globals",
 "map_getter":"0x3c14d: selector1 → indexed CS jump target0x3c19f → original byte at computed map cell address",
 "cell_stride_source":"0x3c174..0x3c180 computes 21*(rowbase+column) into tile data[0xcd0d]",
 "branch_condition":"0x3d37c AND AL,2; 0x3d381 JNE0x3d3ee if bit0x02 set",
 "bit2_clear":"0x3d383 level status/audio-related branch",
 "bit2_set":"0x3d3ee conditional area/rectangle logic invokes0x3d454 when position inside bounds",
 "pure_tile_byte_branch_fixtures":tile_cases,
 "level15_current_tile_byte":"NOT_OBSERVED",
 "safety_note":"Neither branch has been declared transitive-effect-free; callback/input reentry and event8 staging remain unverified",
 "original_machine_instructions_executed":0,
 "fidelity_verified":False
}
stone_sha=emit("STONEKEEP_ACTION0_TILE_SELECTOR.json",stone_out)

# ---- U8 distinct lifecycle of name-alias array DS8C0A ----
uranges=[
 (130,0x1731,0x175a),
 (130,0x198b,0x19d1),
 (130,0x1d07,0x1d25),
 (126,0xd97,0xdcd)
]
ucode={}
for sn,a,z in uranges:
    for at,ins in anchored("Ultima8",a,z,sn).items():
        key=(sn,at)
        assert key not in ucode
        ucode[key]=ins
def uck(sn,addr,mn,text):
    q=ucode.get((sn,addr))
    assert q and q.mnemonic==mn and text in q.op_str,(
        "ORIGINAL_ULTIMA_INSTRUCTION_DRIFT",sn,hex(addr),mn,text,None if not q else (q.mnemonic,q.op_str))
    opchecks.append({"project":"Ultima8","segment":sn,"address":hex(addr),"opcode":q.mnemonic+" "+q.op_str})
for sn,a,m,n in [
 (130,0x1734,"shl","ax, 1"),
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
]:
    uck(sn,a,m,n)
baseflx=B["flx"];flx_count=struct.unpack_from("<I",baseflx,0x54)[0]
assert flx_count==1433
off,length=struct.unpack_from("<II",baseflx,0x88)
assert length==1431*13
record=baseflx[off+347*13:off+348*13]
flags0=struct.unpack_from("<I",record)[0]
assert flags0==0x40 and record[4:].split(b"\0")[0]==b"CLRWATER"
assert (flags0&0x000f8000)==0
name_fixture=[]
for index in (0,128,347,1430):
    name_fixture.append({"shape_index":index,
      "source_record13_name_byte_offset":index*13+4,
      "pointer_array_entry_offset":index*4,
      "source_table_shape347_flag_changed_by_this_model":False,
      "scope":"PURE_BYTE_OFFSET_MODEL_NOT_ALLOCATED_RUNTIME_ARRAY"})
assert name_fixture[2]["source_record13_name_byte_offset"]==4515
u8_out={
 "schema":"OpenUltima8.USECODENameAliasArrayLifecycle.v1",
 "source_EXE_sha256":PINS["u8"][1],
 "source_EUSECODE_FLX_sha256":PINS["flx"][1],
 "source_default_shape347_flags":hex(flags0),
 "source_default_shape347_required_mask":"0x000f8000",
 "source_default_shape347_mask_result":0,
 "original_name_pointer_array":"DS:0x8c0a/0x8c0c (far pointer)",
 "runtime_capacity_source":"u16 DS:0x8bde (table allocation size = count*4)",
 "array_allocate_and_clear":"NE130:0x198b..0x19d0; store array pointer then REP STOSW/STOSB zero slots",
 "per_slot_clear":"NE130:0x1741..0x1753; offset=index*4, write zero segment and offset into slot",
 "array_free_and_null":"NE130:0x1d07..0x1d1d; invoke allocator free and zero array pointer",
 "source_name_alias_producer":"NE126:0xd97..0xdc7; source USECODE shape*13+4 (name) stored into slot index*4",
 "direct_effect_class":"Independent alias-pointer-array allocation, clearing, per-slot writes and cleanup; none of these direct stores targets first4 capability bytes.",
 "important_unknowns":["other array consumers and aliased name writes",
       "runtime loaded USECODE metadata replacement and direct/indirect flag mutations",
       "original runtime Map5 instance handles, materialization and grid freshness"],
 "pure_name_index_fixtures":name_fixture,
 "original_machine_instructions_executed":0,
 "fidelity_verified":False
}
u8_sha=emit("U8_USECODE_ALIAS_ARRAY_LIFECYCLE.json",u8_out)
receipt={
 "schema":"OpenRemaster.CONT19SourceStaticReceipt.v1",
 "status":"PASS_ORIGINAL_SOURCE_OPCODE_AND_PURE_MODEL_FIXTURES",
 "operation_id":old["operation_id"],
 "source_pins":{k:dig for k,(rel,dig) in PINS.items()},
 "source_code_regions":byte_regions,
 "opcode_checks":opchecks,
 "region_count":len(byte_regions),"opcode_count":len(opchecks),
 "source_dynamic_group_count":1044,
 "source_dynamic_group0_count":6161,
 "source_group7_triangle_count":186,
 "pure_group_fixtures":len(fixtures),
 "pure_stone_tile_fixtures":len(tile_cases),
 "pure_U8_name_index_fixtures":len(name_fixture),
 "artifacts":{"MDK_TRIANGLE_GROUP_RUNTIME_FILTER.json":group_sha,
              "MDK_VIEW_VECTOR_POINTER_SOURCE.json":view_sha,
              "STONEKEEP_ACTION0_TILE_SELECTOR.json":stone_sha,
              "U8_USECODE_ALIAS_ARRAY_LIFECYCLE.json":u8_sha},
 "original_game_cpu_instructions_executed":0,
 "original_game_runtime":False,
 "visual_fidelity":False,
 "native_admission_granted":False,
 "limitations":"Only original-source bytes, disassembly, static corpus and pure model; no native scene replay, no runtime group bit observation or table contents."
}
receipt_sha=emit("STATIC_VERIFICATION.json",receipt)
print(json.dumps({"status":receipt["status"],"regions":receipt["region_count"],
 "opcodes":receipt["opcode_count"],"group_counts":group_out["group_counts"],
 "triangle_group0":6161,"triangles_group_positive":1044,"group7":186,
 "pure_group_cases":len(fixtures),"pure_tile_cases":len(tile_cases),"pure_name_cases":len(name_fixture),
 "real_game_runtime":0,
 "hashes":{**receipt["artifacts"],"STATIC_VERIFICATION.json":receipt_sha}},sort_keys=True))
