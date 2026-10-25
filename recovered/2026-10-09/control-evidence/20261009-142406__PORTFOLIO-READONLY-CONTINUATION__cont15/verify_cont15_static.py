"""CONT15 deterministic original-source static contracts.

NO original game/emulator instruction execution, native runtime, build,
capture, project writer, lease, or write to canonical corpus. Creates only
unique report-local JSON evidence with immutable original SHA-256 pins.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,struct,sys,datetime
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_MODE_16

ROOT=Path(r"F:\Remaster Framework")
RUN=Path(__file__).resolve().parent
PINS={
 "registry":("orchestrator/control-plane/portfolio-lanes-20261008-v3.json","42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"),
 "predecessor":("output/projects/OpenRemasterOrchestrator/reports/20261009-140226__PORTFOLIO-READONLY-CONTINUATION__cont14/READ_ONLY_HANDOFF.json","855adba6d4aa3e70b2567741d416a872f2055e082d2dc3fc7f22c68c7c0521f7"),
 "mdk":("source/MDK/MDK95.EXE","e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788"),
 "stone":("source/Stonekeep/SK.EXE","5517ddeb49c7087d6b2449182020200c58084feb4cae55e31ac8acc6cdbdddd2"),
 "u8":("source/Ultima 8/ENGLISH/U8.EXE","1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f"),
 "typeflag":("source/Ultima 8/ENGLISH/STATIC/TYPEFLAG.DAT","2b07f4a6acc5504d9d07c47d3686f74107cac7b594ccb18251e01249fadebc62"),
 "map5":("output/projects/OpenUltima8/evidence/20261008-094213__AUTONOMOUS-4H__cycle01/map5-materialization-sourceir-v3.json","a5c8c9aa9e9da9ceecd41c1cecd18e8ab5ff0ef300304b061e50aa7214123"),
 "usecode":("source/Ultima 8/ENGLISH/USECODE/EUSECODE.FLX","5eceb14286f06f6bb07c35d0c83c0670d500474cd9a7390ad533c0f0f93f4e38"),
}
# The Map5 IR pin is set below from the last verified original evidence:
PINS["map5"]=("output/projects/OpenUltima8/evidence/20261008-094213__AUTONOMOUS-4H__cycle01/map5-materialization-sourceir-v3.json",
             "a5c8c9aa9e9da9ceecd41c1cecd18e7f20c18f2822ba38b878b07f613b8a5638")
SHA=lambda b:hashlib.sha256(b).hexdigest()
raw={}
for key,(relative,digest) in PINS.items():
    p=ROOT/relative;content=p.read_bytes()
    assert SHA(content)==digest,("IMMUTABLE_INPUT_MISMATCH",key,SHA(content))
    raw[key]=content
previous=json.loads(raw["predecessor"].decode("utf-8-sig"))
assert previous["operation_id"]=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
assert len(previous["portfolio"])==23 and len({e["project"] for e in previous["portfolio"]})==23
assert {e["project"] for e in previous["portfolio"] if e["lane"]=="FOCUS_READ_ONLY"}=={"OpenMDK1","OpenStonekeep","OpenUltima8"}

sys.path.insert(0,str(ROOT/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load as mdk_load,offset as mdk_offset
mb,mdk_secs=mdk_load();assert mb==raw["mdk"]
sys.path.insert(0,str(ROOT/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
from le_fixups import LE
sk_image=LEImage(raw["stone"]);sk_le=LE(raw["stone"])
sys.path.insert(0,str(ROOT/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load as u8_load
from ne_far_target import resolve
ub,ne_offset,segments=u8_load();assert ub==raw["u8"]
NE_DATA_AUTO_SEG=struct.unpack_from("<H",ub,ne_offset+0x0e)[0]
assert NE_DATA_AUTO_SEG==148
data_seg=segments[NE_DATA_AUTO_SEG-1]
assert data_seg["data_segment"] and not data_seg["iterated"]
# This string is not an assistant assumption, it's literally stored in original U8.EXE DS.
def ds_string(offset):
    x=ub[data_seg["offset"]+offset:data_seg["offset"]+data_seg["size"]]
    return x.split(b"\0",1)[0].decode("latin-1")
assert ds_string(0x1313)=="usecode"

checks=[]
def instr_source(project,start,end,segment=None):
    if project=="mdk":
        p=mdk_offset(mdk_secs,start,end-start);buf=mb[p:p+end-start];mode=CS_MODE_32
    elif project=="stone":
        buf=sk_image.read_va(start,end-start);mode=CS_MODE_32
    else:
        s=segments[segment-1];assert not s["data_segment"] and not s["iterated"] and end<=s["size"]
        buf=ub[s["offset"]+start:s["offset"]+end];mode=CS_MODE_16
    ops=list(Cs(CS_ARCH_X86,mode).disasm(buf,start))
    assert ops and ops[0].address==start and ops[-1].address+ops[-1].size==end,("BAD_INSTR_BOUNDARY",project,hex(start),hex(end))
    checks.append({"kind":"ORIGINAL_BYTES","project":project,"segment":segment,"start":hex(start),"end":hex(end),
                   "length":len(buf),"sha256":SHA(buf),"result":"PASS_STATIC_BYTES_ONLY"})
    return {i.address:i for i in ops}

def opcode(table,address,mnemonic,needle):
    i=table.get(address)
    assert i is not None and i.mnemonic==mnemonic and needle in i.op_str,(
       "ORIGINAL_OPCODE_CONTRACT_MISMATCH",hex(address),mnemonic,needle,None if i is None else(i.mnemonic,i.op_str))
    checks.append({"kind":"OPCODE","address":hex(address),"mnemonic":mnemonic,"operand_contains":needle,"result":"PASS_SOURCE_DISASSEMBLY"})

# SOURCE: original USECODE/FLX file archive index and literal 13-byte records.
archive=raw["usecode"]
assert archive[:0x50]==b"\x1a"*0x50
archive_count=struct.unpack_from("<I",archive,0x54)[0]
archive_version=struct.unpack_from("<I",archive,0x58)[0]
assert (archive_count,archive_version)==(1433,1)
assert 0x80+archive_count*8==0x2d48
entries=[struct.unpack_from("<II",archive,0x80+i*8) for i in range(archive_count)]
assert all((o==0 and n==0) or (o>=0x2d48 and 0<o+n<=len(archive)) for o,n in entries)
nonzero=sum(bool(o and n) for o,n in entries)
assert nonzero==518 and archive_count-nonzero==915
index1_offset,index1_size=entries[1]
assert (index1_offset,index1_size)==(0x12ce79,18603)
tab=archive[index1_offset:index1_offset+index1_size]
assert SHA(tab)=="90ff19c6191c75562cad773c01608d31a908a8157de05e7a21cd9e5ed5f9e6f6"
assert index1_size%13==0 and index1_size//13==1431
mask=0x000f8000
def table_record(shape):
    assert 0<=shape<1431
    data=tab[shape*13:shape*13+13]
    flag=struct.unpack_from("<I",data)[0]
    name=data[4:].split(b"\0",1)[0].decode("latin-1")
    return {"shape_index":shape,"record13_hex":data.hex(),"flags":flag,
            "name":name,"mask":mask,"mask_result":flag&mask}
shape347=table_record(347)
shape128=table_record(128)
assert shape347["flags"]==0x40 and shape347["name"]=="CLRWATER"
assert shape347["mask_result"]==0
assert shape128["flags"]==0 and shape128["mask_result"]==0
positive_indices=[i for i in range(1431) if table_record(i)["mask_result"]!=0]
assert len(positive_indices)==103
positive_control=table_record(positive_indices[0])
assert positive_control["mask_result"]!=0
# Original archive file index1 is consistent with NE126:0xaf4 method +0x14 length,
# then copied to DS:88f6 through +0x1c; without live state readback it's a SOURCE
# RESOURCE CORRELATION, not measured runtime bytes.
u8init=instr_source("u8",0xaf4,0xbf7,126)
u8gate=instr_source("u8",0xbf7,0xced,126)
u8call=instr_source("u8",0x2577,0x26b3,28)
u8shape=instr_source("u8",0x7f8,0x80e,28)
for addr,mn,n in [
 (0xaff,"mov","[0x1313]"),(0xb8f,"push","1"),(0xb9d,"lcall","[bx + 0x14]"),
 (0xba6,"lcall","0xffff"),(0xbb2,"mov","[0x88f6]"),(0xbb5,"cmp","[0x88f6]"),
 (0xbd2,"push","[0x88f6]"),(0xbe5,"lcall","[bx + 0x1c]"),
]: opcode(u8init,addr,mn,n)
for addr,mn,n in [
 (0xbfd,"cmp","[0x8906], 0"),(0xc73,"cmp","[0x88f6], 0"),
 (0xc7d,"mov","dx, 0xd"),(0xc80,"imul","dx"),
 (0xc82,"les","[0x88f6]"),(0xc88,"mov","[bp + 0xa]"),
 (0xc8c,"test","dword ptr es:[bx], eax"),(0xc90,"je","0xce9"),
 (0xcad,"call","0xced")
]:opcode(u8gate,addr,mn,n)
for addr,mn,n in [
 (0x2692,"push","0xf"),(0x2694,"push","0x8000"),
 (0x269e,"lcall","0xffff")
]:opcode(u8call,addr,mn,n)
for addr,mn,n in [(0x809,"mov","word ptr es:[bx]")]:opcode(u8shape,addr,mn,n)
actual=resolve(28,0x269f)
assert actual["segment"]==126 and actual["offset"]==0xbf7
actual2=resolve(126,0xc6a)
assert actual2["segment"]==28 and actual2["offset"]==0x7f8
# Corpus-limited consequence of the static source table.
map5=json.loads(raw["map5"])
glob=[q for q in map5["potential_instances"] if q["source_kind"]=="GLOB_POTENTIAL"]
assert len(glob)==17774
typeflag=raw["typeflag"]
special=[q for q in glob if typeflag[q["shape"]*8]&0x80]
assert len(special)==2360 and {q["shape"] for q in special}=={347}
assert all(table_record(q["shape"])["mask_result"]==0 for q in special)
assert Counter(q["glob_id"] for q in special)=={262:2336,218:24}
model_cases=[{
    "source_marker":r["instance_id"],
    "glob_id":r["glob_id"],"shape":r["shape"],
    "input_typeflag_bit7":bool(typeflag[8*r["shape"]]&0x80),
    "source_table_capability_mask_intersection":shape347["mask_result"],
    "secondary_allocator_eligible_given_unmodified_entry1":False,
    "runtime_instance_created":"UNKNOWN",
    "source_member_raw_offset":r["source_member_raw_offset"]
} for r in special]
assert len(model_cases)==2360 and all(not r["secondary_allocator_eligible_given_unmodified_entry1"] for r in model_cases)
u8receipt={
 "schema":"OpenUltima8.UsecodeResourceCapabilityNegative.v1",
 "original_U8_EXE_SHA256":PINS["u8"][1],
 "original_EUSECODE_FLX_SHA256":PINS["usecode"][1],
 "original_TYPEFLAG_SHA256":PINS["typeflag"][1],
 "original_Map5_SourceIR_SHA256":PINS["map5"][1],
 "loader_DS_name":"usecode","auto_data_segment":148,
 "FLX_header":{"entry_count":1433,"version":1,"directory_start":128,"directory_end":11592,
               "nonempty_entries":518,"empty_entries":915},
 "entry1":{"offset":index1_offset,"length":index1_size,"sha256":SHA(tab),
           "record_count":1431,"record_stride":13,"capability_mask":hex(mask),
           "positive_control":positive_control,"glob218_shape347":shape347,
           "glob218_shape128":shape128,"total_records_matching_mask":len(positive_indices)},
 "source_loader_static_path":"NE126:0xaf4 uses DS:0x1313 'usecode', vtable+0x14 member1 query and writes allocated buffer DS:0x88f6; vtable+0x1c resource read",
 "runtime_linkage_status":"SOURCE_CORRELATION_NOT_NATIVE_MEMORY_READBACK",
 "negative_conclusion":"For source default FLX entry1 and no dynamic mutation, shape347 flags0x40 & requested 0x000F8000 = 0, so no NE126:0xCED secondary allocation on this path.",
 "qualification":"Even if secondary record callback cannot pass the source-default mask, NE28:0x2577 has earlier state effects; live table mutations, actual handle/area gate, and runtime visual fidelity remain unobserved.",
 "potential_Map5_special_count":len(model_cases),"glob_special_counts":dict(Counter(str(r["glob_id"]) for r in model_cases)),
 "model_special_coverage_total":len(model_cases),
 "source_case_examples":model_cases[:3],
 "all_original_instruction_tests":0
}

# MDK 24-code-address callback table and actual dynamic source lookup paths.
baseA=0x49bcb4;baseB=0x49bce4
mdk_profiles={}
d=Cs(CS_ARCH_X86,CS_MODE_32)
for name,addr in (("A",baseA),("B",baseB)):
    fo=mdk_offset(mdk_secs,addr,48)
    raw_table=mb[fo:fo+48]
    assert len(raw_table)==48
    ptrs=struct.unpack("<12I",raw_table)
    items=[]
    for idx,va in enumerate(ptrs):
        pos=mdk_offset(mdk_secs,va,24)
        data=mb[pos:pos+24]
        op=list(d.disasm(data,va))
        assert op and op[0].address==va
        items.append({"slot":idx,"function_va":hex(va),"code_head_sha256":SHA(data),
                      "first_opcode":op[0].mnemonic+" "+op[0].op_str})
    mdk_profiles[name]={"source_va":hex(addr),"length":48,"sha256":SHA(raw_table),"slots":items}
assert mdk_profiles["A"]["sha256"]=="c7be12d5f5515535d2e3c0926dda9bbe8865134c7e9aa7b5db0a5037a267c3ce"
assert mdk_profiles["B"]["sha256"]=="8dc940779172c5328d7faf3131867eea8c92815c501278a99de45c19725d7907"
one=instr_source("mdk",0x46daac,0x46e52c)
two=instr_source("mdk",0x46e52c,0x46e897)
for addr,mn,part in [
 (0x46deb6,"mov","[eax + 0xc]"),
 (0x46deb9,"mov","[0x5414b8]"),
 (0x46debf,"and","eax, 3"),
 (0x46decc,"or","al, 4"),
 (0x46ded4,"mov","[eax*4 + 0x54dc00]"),
 (0x46e097,"call","ebx"),
 (0x46e250,"call","ebx"),
 (0x46e3e0,"call","ebx"),
 (0x46e4d5,"call","ebx")
]:opcode(one,addr,mn,part)
for addr,mn,part in [
 (0x46e53e,"mov","[eax + 0xc]"),(0x46e541,"and","eax, 3"),
 (0x46e544,"mov","[eax*4 + 0x54dc20]"),
 (0x46e54b,"mov","[ebp - 0x28]"),(0x46e886,"call","[ebp - 0x28]")
]:opcode(two,addr,mn,part)
mdk_model=[]
for profile in ("A","B"):
 for orientation in range(4):
  for mode in ("first_four","next_four","last_four"):
   idx=orientation+(0 if mode=="first_four" else 4 if mode=="next_four" else 8)
   mdk_model.append({"profile":profile,"orientation_bits":orientation,"source_dispatch_group":mode,
                      "table_index":idx,"original_function_va":mdk_profiles[profile]["slots"][idx]["function_va"],
                      "case":"PURE_SELECTION_MODEL_NOT_ORIGINAL_INSTRUCTION_EMULATION"})
assert len(mdk_model)==24 and len({r["original_function_va"] for r in mdk_model})==24
mdk_receipt={
 "schema":"OpenMDK1.TwoProfileTwelveCallbackDispatch.v1",
 "original_EXE_SHA256":PINS["mdk"][1],
 "table_va":{"A":"0x49bcb4","B":"0x49bce4"},
 "copy_target":"0x54dc00",
 "profile_tables":mdk_profiles,
 "first_eight_dynamic_selector":"([EAX+0x0C]&3)| (4 if [0x5414b8]!=0 else 0), @0x46deb6..0x46ded4",
 "first_eight_dynamic_call_sites":["0x46e097","0x46e250","0x46e3e0","0x46e4d5"],
 "last_four_selector":"[EAX+0x0C]&3, plus table base0x54dc20 @0x46e53e..0x46e544",
 "last_four_indirect_call":"0x46e886 call dword ptr [ebp-0x28]",
 "pure_static_selection_fixtures":mdk_model,
 "profile_B_slot4_corrected_identity":"0x470f08 (not source profileA)",
 "claim_boundary":"Original static dispatch and function-pointer code identity only. CPU profile live choice and raster pixel fidelity remain unobserved."
}

# Stonekeep 22 level callbacks called by generic h415 action0 fallback.
fixup_records=[]
for obj in sk_le.objects:
 for lp in range(obj["mapsize"]):
  for f in sk_le.parse_fixup_page(obj["mapidx"]-1+lp):
   if f["target_kind"]!=0 or f["target_object"]!=3 or f["target_offset"]!=0x1b9ddc:continue
   for source in f["sources"]:
    va=obj["base"]+lp*sk_le.page_size+source
    if sk_image.read_va(va-2,2)==bytes.fromhex("c705"):
     dest=struct.unpack("<I",sk_image.read_va(va+4,4))[0]
     fixup_records.append({"writer_va":hex(va-2),"level_callback_target_va":hex(dest),
                           "fixup_file_offset":f["record_file_offset"]})
    elif sk_image.read_va(va-2,2)==bytes.fromhex("ff15"):
     checks.append({"kind":"STONE_GLOBAL_INDIRECT_CALL","source":hex(va-2),"result":"PASS_SOURCE_FIXUP"})
    else:raise AssertionError(("UNKNOWN_GLOBAL_CALLBACK_FIXUP_KIND",hex(va)))
assert len(fixup_records)==22 and len({x["level_callback_target_va"] for x in fixup_records})==22
assert all(x["level_callback_target_va"]!="0xa2ba6" for x in fixup_records)
st=instr_source("stone",0x4fc57,0x4fca9)
wrapper=instr_source("stone",0x6a183,0x6a239)
move=instr_source("stone",0xac4aa,0xac549)
tail=instr_source("stone",0xac68c,0xac69a)
default=instr_source("stone",0x3d4f5,0x3d502)
for table,values in (
 (st,[(0x4fc9b,"movsx","eax, si"),(0x4fc9e,"call","0x6a230")]),
 (wrapper,[(0x6a230,"push","edx"),(0x6a232,"mov","edx, 1"),
           (0x6a217,"call","0x6a183"),(0x6a18a,"mov","edi, eax"),
           (0x6a18c,"mov","esi, edx"),(0x6a203,"movsx","eax, di"),(0x6a206,"call","0xac4aa")]),
 (move,[(0xac4ad,"mov","esi, eax"),(0xac4b5,"cmp","si, 0x19"),
        (0xac50f,"cmp","si, 7"),(0xac52e,"cmp","si, 1"),
        (0xac532,"jb","0xac68c")]),
 (tail,[(0xac68c,"movsx","eax, si"),(0xac68f,"call","0x3d4f5")]),
 (default,[(0x3d4f6,"call","[0x1b9ddc]"),(0x3d4fd,"jmp","0x3c36a")])
):
 for addr,mn,part in values:opcode(table,addr,mn,part)
stone_receipt={
 "schema":"OpenStonekeep.H415Action0GenericLevelCallbackChain.v1",
 "original_EXE_SHA256":PINS["stone"][1],
 "h415_input_action0_direct_chain":["0x4fc9e→0x6a230","0x6a217→0x6a183","0x6a206→0xac4aa",
                                    "0xac532→0xac68c for source action0","0xac68f→0x3d4f5",
                                    "0x3d4f6→indirect current level handler0x1b9ddc"],
 "level_callback_pointer_offset":"0x1b9ddc",
 "direct_global_level_callback_stores":fixup_records,
 "store_count":22,
 "direct_global_level_callback_dispatch_calls":1,
 "no_direct_store_target_is_staging_a2ba6":True,
 "transitive_other_callbacks":"UNVERIFIED",
 "action0_not_action2_stage":"DIRECT_BRANCH_ONLY_PASS",
 "statement":"The original h415 action0 path falls through generic movement/default processing then calls a level callback. It does not directly enqueue the h415 action2 transition; transitive effects remain unknown."
}

def emit(name,obj):
 data=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
 p=RUN/name
 if p.exists():assert p.read_bytes()==data,("REPORT_OUTPUT_DRIFT",name)
 else:
  with p.open("xb") as f:f.write(data)
 return SHA(data)
out={}
for name,obj in [
 ("U8_USECODE_FLX_NEGATIVE.json",u8receipt),
 ("MDK_RASTER_CALLBACK_DISPATCH.json",mdk_receipt),
 ("STONEKEEP_ACTION0_LEVEL_CALLBACKS.json",stone_receipt)]:
 out[name]=emit(name,obj)
status={
 "schema":"OpenRemaster.CONT15StaticVerification.v1",
 "status":"PASS_SOURCE_STATIC_AND_GROUNDED_RESOURCE_NEGATIVE_ONLY",
 "operation_id":previous["operation_id"],
 "source_pins":{k:v[1] for k,v in PINS.items()},
 "source_byte_and_disasm_check_count":sum(x["kind"]=="ORIGINAL_BYTES" for x in checks),
 "source_opcode_check_count":sum(x["kind"]=="OPCODE" for x in checks),
 "special_class_source_ir_count":2360,
 "special_class_capability_positive_count_under_base_usecode":0,
 "usecode_archive_entries":1433,
 "usecode_metadata_records":1431,
 "usecode_metadata_source_sha256":SHA(tab),
 "usecode_positive_mask_control_count":103,
 "mdk_raster_callback_pointers":24,
 "stonekeep_global_level_callback_targets":22,
 "original_game_machine_instructions_executed":0,
 "game_runtime_executed":False,
 "fidelity_or_release_verified":False,
 "production_admission_granted":False,
 "boundaries":["Source EXE and base Usecode archive correspond structurally to original loader. No actual live memory dump of DS:88f6.","Indirect writes could mutate the table before a specific callback; no live absence proof.","No game native or CPU instruction execution."] ,
 "artifacts":out,
 "original_instruction_checks":checks,
 "verified_at_utc":'2026-10-09T12:28:29.301047+00:00'
}
out["STATIC_VERIFICATION.json"]=emit("STATIC_VERIFICATION.json",status)
print(json.dumps({
 "status":status["status"],
 "source_byte_regions":status["source_byte_and_disasm_check_count"],
 "source_opcode_checks":status["source_opcode_check_count"],
 "usecode_entries":status["usecode_archive_entries"],
 "usecode_record_count":status["usecode_metadata_records"],
 "usecode_mask_positive_controls":status["usecode_positive_mask_control_count"],
 "shape347_default_mask_pass":False,
 "map5_special_potential":status["special_class_source_ir_count"],
 "default_secondary_allocation_eligible":status["special_class_capability_positive_count_under_base_usecode"],
 "mdk_callbacks":status["mdk_raster_callback_pointers"],
 "stonekeep_level_callbacks":status["stonekeep_global_level_callback_targets"],
 "original_game_runtime_tests":0,"artifacts":out
},sort_keys=True))
