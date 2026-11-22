"""CONT14 original-source static contracts: U8 callback, MDK profile, Stonekeep h415 input callback.

Runs deterministic, read-only source checks and pure Python negative/positive
fixtures. Does not execute game machine instructions or start any native
runtime/build/capture. Report files created ONLY inside this unique run folder.
"""
from pathlib import Path
import json,hashlib,collections,sys
from capstone import Cs,CS_ARCH_X86,CS_MODE_16,CS_MODE_32

ROOT=Path(r"F:\Remaster Framework")
RUN=Path(__file__).resolve().parent
PINS={
 "registry":("orchestrator/control-plane/portfolio-lanes-20261008-v3.json","42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"),
 "predecessor":("output/projects/OpenRemasterOrchestrator/reports/20261009-132559__PORTFOLIO-READONLY-CONTINUATION__cont13/READ_ONLY_HANDOFF.json","cc0240f6b2a2948d30a8ffa7fc3b74835a98dc15bb6fc57b71b4fad02cd5f302"),
 "MDK1":("source/MDK/MDK95.EXE","e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788"),
 "Stonekeep":("source/Stonekeep/SK.EXE","5517ddeb49c7087d6b2449182020200c58084feb4cae55e31ac8acc6cdbdddd2"),
 "Ultima8":("source/Ultima 8/ENGLISH/U8.EXE","1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f"),
 "TYPEFLAG":("source/Ultima 8/ENGLISH/STATIC/TYPEFLAG.DAT","2b07f4a6acc5504d9d07c47d3686f74107cac7b594ccb18251e01249fadebc62"),
 "MAP5_IR":("output/projects/OpenUltima8/evidence/20261008-094213__AUTONOMOUS-4H__cycle01/map5-materialization-sourceir-v3.json","a5c8c9aa9e9da9ceecd41c1cecd18e7f20c18f2822ba38b878b07f613b8a5638")
}
sha=lambda b:hashlib.sha256(b).hexdigest()
raws={}
for key,(name,digest) in PINS.items():
    p=ROOT/name;raw=p.read_bytes();assert sha(raw)==digest,("SOURCE_PIN_DRIFT",key,sha(raw))
    raws[key]=raw
prev=json.loads(raws["predecessor"].decode("utf-8-sig"))
assert prev["operation_id"]=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
assert len(prev["portfolio"])==23 and len({p["project"] for p in prev["portfolio"]})==23
assert {p["project"] for p in prev["portfolio"] if p["lane"]=="FOCUS_READ_ONLY"}=={"OpenMDK1","OpenStonekeep","OpenUltima8"}

sys.path.insert(0,str(ROOT/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load as mdload,offset as mdoffset
mb,sections=mdload();assert sha(mb)==PINS["MDK1"][1]
sys.path.insert(0,str(ROOT/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
from le_fixups import LE
le_image=LEImage(raws["Stonekeep"])
le=LE(raws["Stonekeep"])
sys.path.insert(0,str(ROOT/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load as uload
from ne_far_target import resolve
ub,ne,segs=uload();assert sha(ub)==PINS["Ultima8"][1]

addresses={}
regions=[]
def add_region(lane,begin,end,segment=None):
    assert begin<end
    if lane=="MDK1":
        o=mdoffset(sections,begin,end-begin);b=mb[o:o+end-begin];mode=CS_MODE_32
    elif lane=="Stonekeep":
        b=le_image.read_va(begin,end-begin);mode=CS_MODE_32
    else:
        item=segs[segment-1]
        assert not item["iterated"] and not item["data_segment"] and end<=item["size"]
        b=ub[item["offset"]+begin:item["offset"]+end];mode=CS_MODE_16
    assert len(b)==end-begin
    instr=list(Cs(CS_ARCH_X86,mode).disasm(b,begin))
    assert instr and instr[0].address==begin
    # Tail may include a later unrelated entry; only complete opcodes are accepted.
    for op in instr:
        key=(segment,op.address) if lane=="Ultima8" else (0,op.address)
        k=(lane,)+key
        assert k not in addresses or addresses[k].bytes==op.bytes,("OVERLAP",k)
        addresses[k]=op
    regions.append({"lane":lane,"segment":segment,"address":hex(begin),"size":len(b),
                    "source_sha256":sha(b),"decoded_instructions":len(instr),
                    "decoded_end":hex(instr[-1].address+instr[-1].size),
                    "result":"PASS_ORIGINAL_SOURCE_BYTE_IDENTITY_ONLY"})

for a,z in ((0x401b40,0x401b84),(0x401da4,0x401dab),(0x408f3c,0x408f4d),
            (0x425310,0x42540d),(0x47d1a0,0x47d1a5),(0x47f47f,0x47f49a),
            (0x481758,0x481769),(0x46da6c,0x46daac)):
    add_region("MDK1",a,z)
for a,z in ((0x4f983,0x4f9c5),(0x4fc57,0x4fca9),(0x32d24,0x32d4b),
            (0x3dfcc,0x3dfe3),(0x44f0b,0x44f15),(0xa9e0d,0xa9e17)):
    add_region("Stonekeep",a,z)
for sn,a,z in ((28,0x2577,0x26b3),(28,0x1ebc,0x1ed8),(28,0xd5e,0xd87),
               (28,0x7f8,0x80e),(126,0xbf7,0xced),(126,0xc73,0xced),
               (126,0xced,0xd33),(132,0x137,0x174)):
    add_region("Ultima8",a,z,sn)

opcode=[]
def op(lane,loc,mnemonic,part,seg=0):
    entry=addresses.get((lane,seg,loc))
    assert entry is not None and entry.mnemonic==mnemonic and part in entry.op_str,(
      "ORIGINAL_SOURCE_OPCODE_MISMATCH",lane,seg,hex(loc),mnemonic,part,
      None if entry is None else (entry.mnemonic,entry.op_str))
    opcode.append({"lane":lane,"source":f"NE{seg}:{loc:#x}" if seg else hex(loc),
                   "mnemonic":mnemonic,"operand":part,"result":"PASS_SOURCE_OPCODE"})

# MDK profile: CPU detector saves EDX, normal-return error and external wrappers restore it.
for a,m,p in (
 (0x401b40,"mov","edx, 1"),(0x401b57,"call","0x425310"),
 (0x401b68,"call","0x408f3c"),(0x401b72,"xor","ah, ah"),
 (0x401b74,"cmp","eax, 6"),(0x401b77,"jne","0x401da4"),
 (0x401b7d,"mov","eax, edx"),(0x401b7f,"call","0x46da6c"),
 (0x401da4,"xor","eax, eax"),(0x401da6,"jmp","0x401b7f"),
 (0x425315,"push","edx"),(0x425365,"pop","edx"),(0x425408,"pop","edx"),
 (0x408f44,"call","0x47d1a0"),(0x47d1a0,"jmp","0x47f47f"),
 (0x47f480,"push","edx"),(0x47f482,"call","[0x493304]"),
 (0x47f48d,"call","0x481758"),(0x47f492,"pop","edx"),
 (0x47f497,"pop","edx"),(0x481759,"push","edx"),
 (0x481761,"call","0x481707"),(0x481766,"pop","edx"),
 (0x46da72,"test","eax, eax"),(0x46da74,"je","0x46da9d"),
 (0x46da7b,"mov","esi, 0x49bcb4"),(0x46da9d,"mov","ecx, 0x30"),
 (0x46daa2,"mov","esi, 0x49bce4")
):op("MDK1",a,m,p)
profilerows=[]
profile_bytes={}
for va in (0x49bcb4,0x49bce4):
    o=mdoffset(sections,va,0x30);x=mb[o:o+0x30]
    assert len(x)==48
    profile_bytes[hex(va)]=x
    profilerows.append({"source_address":hex(va),"size":48,"sha256":sha(x)})
assert profile_bytes["0x49bcb4"]!=profile_bytes["0x49bce4"]
cpu_codes=(0,4,5,6,7,0x106,0x606,0x10006,0xffffff06)
cpu_examples=[]
for cpu in cpu_codes:
    normalized=cpu & 0xffff00ff
    first=(normalized==6)
    choice="0x49bcb4" if first else "0x49bce4"
    cpu_examples.append({"detector_dword":hex(cpu),"after_AH_clear":hex(normalized),
                         "selector_arg":int(first),"constant_profile":choice,
                         "sha256":sha(profile_bytes[choice]),
                         "evidence_class":"PURE_SOURCE_CONDITION_MODEL"})
assert sum(z["selector_arg"]==1 for z in cpu_examples)==3
# This bound assumes normal returns and an ABI-compatible system DLL call.

# Stonekeep 415 dispatch and input-pump action zero callback.
page,source=le.page_for_object_offset(3,0xf16a)
source+=415*4
fixups=[f for f in le.parse_fixup_page(page) if source in f["sources"]]
assert len(fixups)==1
h415=le.objects[fixups[0]["target_object"]-1]["base"]+fixups[0]["target_offset"]
assert h415==0x4f983
for a,m,p in (
 (0x4f988,"mov","esi, eax"),(0x4f9b1,"cmp","ax, 2"),
 (0x4f9b5,"jb","0x4fc57"),
 (0x4f9bb,"cmp","ax, 3"),(0x4f9bf,"jbe","0x4fb00"),
 (0x32d43,"xor","eax, eax"),(0x32d45,"call","[0x1b9df4]"),
 (0x3dfd5,"movsx","word ptr [eax + 7]"),
 (0x3dfd9,"mov","[eax*4 + 0xf16a]"),
 (0x3dfe0,"mov","[ebx], eax"),
 (0x44f0b,"mov","dword ptr [0xf16a]"),
 (0x44f10,"mov","dword ptr [0x1b9df4]"),
 (0xa9e0d,"mov","0x2c36a")
):op("Stonekeep",a,m,p)

# Relocated source operand xref inventory, not a transitive callgraph.
refs=[]
for obj in le.objects:
    for lp in range(obj["mapsize"]):
        for f in le.parse_fixup_page(obj["mapidx"]-1+lp):
            if f["target_kind"]==0 and f["target_object"]==3 and f["target_offset"]==0x1b9df4:
                refs.extend(obj["base"]+lp*le.page_size+src for src in f["sources"])
assert len(refs)==79 and len(set(refs))==79
classified=collections.Counter();refrows=[]
for va in sorted(refs):
    x=le_image.read_va(va-2,2)
    if x==bytes.fromhex("ff15"):cls="direct_indirect_call"
    elif x==bytes.fromhex("c705"):cls="direct_immediate_store"
    elif le_image.read_va(va-1,1)==bytes.fromhex("a3"):cls="direct_eax_store"
    elif le_image.read_va(va-1,1)==bytes.fromhex("bb"):cls="address_of_pointer"
    else:cls="unclassified"
    classified[cls]+=1
    refrows.append({"operand_address":hex(va),"type":cls})
assert classified=={"direct_indirect_call":74,"direct_immediate_store":1,
                   "direct_eax_store":1,"address_of_pointer":3},classified
assert any(x["operand_address"]=="0x32d47" and x["type"]=="direct_indirect_call" for x in refrows)
stone_examples=[]
for action in (0,1,2,3):
    branch="ACTION0_OR1_FALLBACK" if action<2 else "ACTION2_OR3_HANDLER_ENTRY"
    stone_examples.append({"action_eax":action,"direct_branch":branch,
                           "entry":hex(h415),"input_pump_callback_eax_zero":action==0,
                           "scope":"BOUNDED_DIRECT_BRANCH_ONLY_HELPER_SIDE_EFFECTS_UNOBSERVED"})
assert stone_examples[0]["direct_branch"]=="ACTION0_OR1_FALLBACK"

# U8 original high-bit candidate calls an optional capability-masked initializer.
for sn,addr,m,p in (
 (28,0x258d,"or","ax, 0x2000"),(28,0x2596,"call","0x1f70"),
 (28,0x2659,"call","0x1ebc"),(28,0x2680,"shr","ax, 7"),
 (28,0x2688,"je","0x26af"),(28,0x2692,"push","0xf"),
 (28,0x2694,"push","0x8000"),(28,0x269e,"lcall","0xffff"),
 (28,0x1ec2,"cmp","es:[bx], 0"),(28,0x1ec8,"cmp","0x100"),
 (28,0x809,"mov","word ptr es:[bx]"),
 (126,0xbfd,"cmp","[0x8906], 0"),(126,0xc02,"je","0xc08"),
 (126,0xc08,"push","dword ptr [bp + 6]"),
 (126,0xc0c,"lcall","0xffff"),(126,0xc4d,"cmp","ax, 4"),
 (126,0xc65,"push","dword ptr [bp + 6]"),
 (126,0xc69,"lcall","0xffff"),(126,0xc71,"mov","cx, ax"),
 (126,0xc73,"cmp","[0x88f6], 0"),(126,0xc79,"je","0xce9"),
 (126,0xc7d,"mov","dx, 0xd"),(126,0xc80,"imul","dx"),
 (126,0xc88,"mov","[bp + 0xa]"),(126,0xc8c,"test","dword ptr es:[bx], eax"),
 (126,0xc90,"je","0xce9"),(126,0xcad,"call","0xced"),
 (126,0xca5,"push","0"),(126,0xca8,"push","0"),
 (126,0xcff,"push","0x116"),(126,0xd02,"lcall","0xffff"),
 (126,0xd23,"les","[bp + 6]"),(126,0xd26,"mov","0x89f7"),
 (132,0x13d,"push","[bp + 6]"),(132,0x140,"lcall","0xffff")
):op("Ultima8",addr,m,p,sn)
rels=[]
for s,a,t,o in ((28,0x269f,126,0xbf7),(126,0xc0d,28,0x1ebc),
                 (126,0xc46,28,0xd5e),(126,0xc6a,28,0x7f8),
                 (126,0xd03,132,0x137),(126,0xd1c,132,0x0)):
    got=resolve(s,a)
    assert (got["segment"],got["offset"])==(t,o),("NE_CALL_TARGET_CHANGED",s,a,got)
    rels.append({"source":f"NE{s}:{a:#x}","target":f"NE{t}:{o:#x}",
                 "relocation_file_offset":got["relocation_file_offset"]})
# TYPEFLAG and Map5 paired source class:
tf=raws["TYPEFLAG"]
assert (tf[8*347]&0x80)!=0 and (tf[8*128]&0x80)==0
assert tf[8*347+1]>>4==0 and tf[8*128+1]>>4==0
ir=json.loads(raws["MAP5_IR"])
representatives=[]
for ordinal in (2378,2379):
    rows=[x for x in ir["potential_instances"]
          if x["source_kind"]=="GLOB_POTENTIAL" and x["definition_ordinal"]==ordinal and x["glob_id"]==218]
    assert len(rows)==16 and collections.Counter(x["shape"] for x in rows)=={347:12,128:4}
    for index in (0,12):
        q=next(x for x in rows if x["glob_member"]==index)
        representatives.append({"source_instance_id":q["instance_id"],"shape":q["shape"],
                                "source_byte_offset":q["source_member_raw_offset"],
                                "shape_flag_byte0":tf[8*q["shape"]],"runtime_id":"UNOBSERVED",
                                "world":q["world"],"live_activation":"UNOBSERVED"})

# Pure conditional fixture on declared normal-return, valid-handle domain.
mask_from_original_pushed_words=0x000f8000
assert (0xf<<16)|0x8000==mask_from_original_pushed_words
cases=[]
for handle in (1,255,256,300):
    for shape in (128,347):
        for area_active in (False,True):
            for ds8906_nonzero in (False,True):
                for table_present in (False,True):
                    for capability_bit_intersection in (False,True):
                        attempt=(area_active and handle>=256 and bool(tf[8*shape]&0x80))
                        reaches_cap=(attempt and not ds8906_nonzero and table_present)
                        eligible=(reaches_cap and capability_bit_intersection)
                        cases.append({
                          "handle":handle,"shape":shape,"area_active":area_active,
                          "ds8906_nonzero":ds8906_nonzero,
                          "ds88f6_table_present":table_present,
                          "record_mask_intersects_0x000f8000":capability_bit_intersection,
                          "NE126_entry_candidate":attempt,
                          "NE126_allocator_call_eligible_under_normal_returns":eligible,
                          "model_scope":"SOURCE_STATIC_PURE_CONDITIONAL_NOT_ORIGINAL_RUNTIME"
                        })
assert len(cases)==128
assert sum(x["NE126_allocator_call_eligible_under_normal_returns"] for x in cases)==2
assert not any(x["shape"]==128 and x["NE126_entry_candidate"] for x in cases)
assert not any(x["handle"]<=255 and x["NE126_entry_candidate"] for x in cases)

def output(name,obj):
    blob=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    p=RUN/name
    if p.exists():assert p.read_bytes()==blob,("NONDETERMINISTIC_OR_CONFLICT",name)
    else:
        with p.open("xb") as f:f.write(blob)
    return sha(blob)

mdk_payload={
 "schema":"OpenMDK1.RenderProfileSelectionStaticContract.v1",
 "source_exe_sha256":PINS["MDK1"][1],
 "CPU_profile_gate":"(CPU_detector_result & 0xFFFF00FF) == 6",
 "success_path":"EDX=1 from 0x401b40 preserved by0x425310 and0x408f3c→0x47d1a0→0x47f47f, including error wrapper0x481758 on normal return",
 "cpu_profile_six_material_source":"0x49bcb4",
 "other_cpu_profiles_material_source":"0x49bce4",
 "common_output":"0x54dc00","source_table_length_bytes":48,
 "table_pins":profilerows,
 "pure_cpu_branch_fixtures":cpu_examples,
 "not_claimed":"Observed live CPU detector result, actual raster profile selection, renderer fidelity"
}
callback_payload={
 "schema":"OpenStonekeep.H415InputCallbackStaticLinkage.v1",
 "source_exe_sha256":PINS["Stonekeep"][1],
 "handler415_target":"0x4f983",
 "handler_dispatch_fixup_file_offset":fixups[0]["record_file_offset"],
 "pointer_slot":"0x1b9df4",
 "pointer_xrefs":refrows,"pointer_xref_count":len(refrows),
 "pointer_access_categories":dict(classified),
 "default_direct_assignment":"0xa9e0d -> callback0x2c36a",
 "level_default_direct_assignment":"0x44f10 <- [0xf16a]",
 "dynamic_cell_assignment":"0x3dfcc uses current cell handler ID at cell+7 and writes table target from0xf16a to pointer at EBX",
 "poll_site":"0x32d43 xor eax,eax; 0x32d45 call dword ptr [0x1b9df4]",
 "action_branch":"h415 0x4f9b1 cmp AX,2; 0x4f9b5 JB0x4fc57 (actions0,1 bypass direct action2/3 path)",
 "pure_h415_action_fixtures":stone_examples,
 "negative_scope":"No transitive proof that helper callbacks cannot stage h415. Not a live interleaving witness."
}
u8_payload={
 "schema":"OpenUltima8.Map5SpecialShape347RuntimeGateModel.v1",
 "source_exe_sha256":PINS["Ultima8"][1],
 "typeflag_sha256":PINS["TYPEFLAG"][1],
 "map5_source_ir_sha256":PINS["MAP5_IR"][1],
 "original_masks":{"paired_16bit_pushes":["0x000f","0x8000"],"dword_test":hex(mask_from_original_pushed_words)},
 "table":"NE126:0xc73 DS:0x88f6 -> shape*13-byte record, test first dword against0x000f8000",
 "source_chain":["NE28:0x2577 → NE126:0xbf7","NE126:0xc65 → NE28:0x7f8 (shape getter for family0)",
                 "NE126:0xcad → NE126:0xced on matching capability","NE126:0xcff pushes0x116-byte allocation size",
                 "NE126:0xd02 → NE132:0x137 allocation helper"],
 "representatives":representatives,
 "pure_conditional_fixtures":cases,
 "scope":"A conditional source model only; actual table pointer/content and runtime handles/area state unobserved",
 "positive_model_cases":2,
 "original_game_instructions_executed":0
}
rec={
 "schema":"OpenRemaster.CONT14StaticInputAndContractReceipt.v1",
 "operation_id":prev["operation_id"],"iteration":"CONT14",
 "status":"PASS_ORIGINAL_SOURCE_OPCODE_RELOCATIONS_AND_PURE_CONTRACT_MODELS",
 "source_sha256":{key:digest for key,(_,digest) in PINS.items()},
 "source_regions":regions,"region_count":len(regions),
 "opcode_checks":opcode,"opcode_count":len(opcode),
 "NE_relocations":rels,
 "model_fixtures":{"U8":len(cases),"MDK1":len(cpu_examples),"Stonekeep":len(stone_examples)},
 "original_machine_instructions_executed":0,
 "native_runtime_or_capture_executed":False,
 "game_fidelity_verified":False,
 "production_admission_granted":False,
 "project_source_or_worktree_modified":False,
 "warning":"Source-static PASS does not infer native execution, callback reachability or visual fidelity."
}
outputs={}
for filename,obj in [
    ("MDK1_RENDER_PROFILE_CONTRACT.json",mdk_payload),
    ("STONEKEEP_H415_CALLBACK_CONTRACT.json",callback_payload),
    ("U8_SPECIAL_CALLBACK_GATE.json",u8_payload),
    ("STATIC_VERIFICATION.json",rec)
]:
    outputs[filename]=output(filename,obj)
print(json.dumps({
    "status":rec["status"],"source_regions":len(regions),
    "opcode_checks":len(opcode),"callback_pointer_xrefs":len(refrows),
    "pointer_kinds":dict(classified),
    "NE_relocations":len(rels),
    "model_cases":rec["model_fixtures"],"u8_positive_model_cases":2,
    "MDK_profiles":profilerows,"files":outputs
},sort_keys=True))
