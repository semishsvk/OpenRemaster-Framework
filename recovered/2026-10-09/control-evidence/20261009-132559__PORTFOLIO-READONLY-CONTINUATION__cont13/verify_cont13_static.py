"""CONT13: original-source static mechanism check and Map5 GLOB narrow scope.

Only reads canonical source and historical source IR. Creates deterministic,
isolated outputs under this newly allocated report directory; no original
game instruction emulation, renderer/runtime process, or write to a corpus.
"""
import hashlib,json,sys,collections
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_16,CS_MODE_32
BASE=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
SHA=lambda raw:hashlib.sha256(raw).hexdigest()
PINS={
 "registry":("orchestrator/control-plane/portfolio-lanes-20261008-v3.json","42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"),
 "prev":("output/projects/OpenRemasterOrchestrator/reports/20261009-124538__PORTFOLIO-READONLY-CONTINUATION__cont12/READ_ONLY_HANDOFF.json","d971bd33d5178ed5665781d03a67db766db57be0075c0025b71b9fc66a082c91"),
 "MDK1":("source/MDK/MDK95.EXE","e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788"),
 "Stonekeep":("source/Stonekeep/SK.EXE","5517ddeb49c7087d6b2449182020200c58084feb4cae55e31ac8acc6cdbdddd2"),
 "Ultima8":("source/Ultima 8/ENGLISH/U8.EXE","1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f"),
 "typeflags":("source/Ultima 8/ENGLISH/STATIC/TYPEFLAG.DAT","2b07f4a6acc5504d9d07c47d3686f74107cac7b594ccb18251e01249fadebc62"),
 "map5sourceir":("output/projects/OpenUltima8/evidence/20261008-094213__AUTONOMOUS-4H__cycle01/map5-materialization-sourceir-v3.json","a5c8c9aa9e9da9ceecd41c1cecd18e7f20c18f2822ba38b878b07f613b8a5638"),
}
inputs={}
for key,(rel,pin) in PINS.items():
    p=BASE/rel;raw=p.read_bytes()
    assert SHA(raw)==pin,("SOURCE_CHANGED",key,SHA(raw))
    inputs[key]=raw
prev=json.loads(inputs["prev"].decode("utf-8-sig"))
assert prev["operation_id"]=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
assert len(prev["portfolio"])==23 and len({e["project"] for e in prev["portfolio"]})==23
assert len([e for e in prev["portfolio"] if e["lane"]=="FOCUS_READ_ONLY"])==3
assert {e["project"] for e in prev["portfolio"] if e["lane"]=="FOCUS_READ_ONLY"}=={"OpenMDK1","OpenStonekeep","OpenUltima8"}

sys.path.insert(0,str(BASE/"output/projects/OpenMDK1/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from static_probe import load as mdload,offset as mdoff
md,sections=mdload()
assert SHA(md)==PINS["MDK1"][1]
sys.path.insert(0,str(BASE/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
sk=LEImage(inputs["Stonekeep"])
sys.path.insert(0,str(BASE/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load as uload
from ne_far_target import resolve
ub,ne,segs=uload()
assert SHA(ub)==PINS["Ultima8"][1]

# Each slice must align to complete original x86 instructions.
RANGES={
 "MDK1":[
   (0,0x40d8b5,0x40da52,"4304fdd8056916e81582c19657471b8f6193796878df452f18cfa0e4c177c2ff"),
   (0,0x40c860,0x40c9ff,"9d44b7c9ad93be8d2fad2e67338a2de5338f470e35e367f1cbfe47016dbfe820")
 ],
 "Stonekeep":[
   (0,0x315ea,0x3163e,"0569a3897f675479476b6bbb2ec4c6b51d1a2be8a83a5c31a803f9cbf89705c3"),
   (0,0x32bff,0x32c43,"321fec4899f9e85b357c4b1f6308fbb09b00b5253e325a661bd04047e95b6300"),
   (0,0x85220,0x8525e,"259a0777ebe5b0b61b712a4e07adea0b28ca2139f55d67ad443ad3998f01acfa"),
   (0,0x851c3,0x85220,"3d2c246f260543bd33f8e4997549f9103957e98c6ba94af04cec4acb3589439b")
 ],
 "Ultima8":[
   (28,0x2577,0x26b3,"a69724734987ad259ec8e77d1fad7a0befb1364566ba66444d0e44c6122c9ad9"),
   (28,0x1ebc,0x1ed8,"20aa0cb9279a532e7ce723e1f828df3492f2f114cedddbd62a9fffef5863c165"),
   (28,0x1f70,0x1f9d,"fc5eb3f9fc788649eaed1a2c2fdfa1198ec471510a33814a6ce434d38bcc383c"),
   (28,0xdce,0xde4,"4bd61c34f68968be1eee5e83c61b0449b05db02c10657b3097d829c584b68f96"),
   (28,0xd5e,0xd87,"88e57b86d0df99003100ef40f2ddc033a2f19d6a20408bd5eb60e54feaa6b0f0"),
   (32,0x1ba1,0x1bd2,"cc164407a0eae795854dc81c9e938ea8b4f84592b66ec5b4f96c6ef309bfef02"),
   (32,0x1ac9,0x1ae9,"8b22ce63430d90b4b6d4823e6d926dc738dc3cf01a673640af56bc2f84db7381"),
   (126,0xbf7,0xc7b,"b704e24f07ed1c4108ba119f3bf212f6eece3846d513026ff62bc3ca93f951f9"),
   (29,0x272,0x39c,"0fb167cde9162306755b8dfd87ba6c3580ab94b75accdede9be86b41478d40c8"),
   (29,0x265f,0x284d,"e4f086430f1b855a0c71884b416f14ffb7f342dfdc5bb298482706dea984d4cf")
 ]
}
ins={k:{} for k in RANGES}
region_checks=[]
for project,rows in RANGES.items():
    for seg,a,z,pin in rows:
        if project=="MDK1":
            o=mdoff(sections,a,z-a);b=md[o:o+z-a];mode=CS_MODE_32
        elif project=="Stonekeep":
            b=sk.read_va(a,z-a);mode=CS_MODE_32
        else:
            x=segs[seg-1]
            assert not x["iterated"] and not x["data_segment"] and a<z<=x["size"]
            b=ub[x["offset"]+a:x["offset"]+z];mode=CS_MODE_16
        assert len(b)==z-a and SHA(b)==pin,("SLICE_DRIFT",project,seg,hex(a))
        ops=list(Cs(CS_ARCH_X86,mode).disasm(b,a))
        assert ops and ops[0].address==a and ops[-1].address+ops[-1].size==z,("UNALIGNED",project,hex(a))
        for op in ops:
            key=(seg,op.address) if project=="Ultima8" else op.address
            assert key not in ins[project]
            ins[project][key]=op
        region_checks.append({"project":project,"segment":seg or None,"start":hex(a),"end":hex(z),"sha256":pin,"result":"PASS_STATIC_ORIGINAL_BYTE_AND_INSTRUCTION_BOUNDARY"})
checks=[]
def source_check(project,addr,mn,operand,seg=0):
    key=(seg,addr) if project=="Ultima8" else addr
    q=ins[project].get(key)
    assert q is not None and q.mnemonic==mn and operand in q.op_str,("INSTRUCTION_MISMATCH",project,hex(addr),mn,operand, None if q is None else (q.mnemonic,q.op_str))
    checks.append({"project":project,"ref":f"NE{seg}:{addr:#x}" if seg else hex(addr),"instruction":mn+" "+operand,"result":"PASS_STATIC_OPCODE_IDENTITY"})

# Ultima8 late second-pass callback: flags update before ID test.
for seg,a,m,p in [
 (28,0x2587,"call","0xdce"),(28,0x258d,"or","ax, 0x2000"),
 (28,0x2596,"call","0x1f70"),(28,0x25a1,"call","0x1ebc"),
 (28,0x25a9,"je","0x25d1"),(28,0x25c1,"lcall","0xffff"),
 (28,0x25cb,"je","0x25d1"),(28,0x25d6,"call","0xd5e"),
 (28,0x25df,"cmp","[bp - 8], 4"),(28,0x25e5,"cmp","[bp - 8], 8"),
 (28,0x260b,"cmp","[0x1a14], 0"),(28,0x2610,"jne","0x2616"),
 (28,0x2612,"xor","ax, ax"),(28,0x261b,"call","0x1ebc"),
 (28,0x2623,"je","0x2654"),(28,0x2659,"call","0x1ebc"),
 (28,0x2661,"jne","0x268a"),(28,0x267d,"mov","byte ptr es:[bx]"),
 (28,0x2680,"shr","ax, 7"),(28,0x2688,"je","0x26af"),
 (28,0x269e,"lcall","0xffff"),(28,0x26af,"xor","ax, ax"),
 (28,0x1ec2,"cmp","es:[bx], 0"),(28,0x1ec8,"cmp","0x100"),
 (28,0x1ecd,"jae","0x1ed4"),(28,0x1ecf,"mov","ax, 1"),
 (28,0x1f95,"mov","[bp + 0xa]"),(28,0x1f98,"mov","word ptr es:[bx]"),
 (28,0xddf,"mov","word ptr es:[bx]"),(28,0xd7b,"mov","byte ptr es:[bx + 1]"),
 (126,0xbfd,"cmp","[0x8906], 0"),(126,0xc02,"je","0xc08"),
 (126,0xc04,"mov","al, 0"),(126,0xc73,"cmp","[0x88f6], 0"),
 (32,0x1ba7,"cmp","es:[bx], 0"),(32,0x1bad,"cmp","0x100"),
 (32,0x1bc2,"mov","byte ptr es:[bx + 0x2f]")
]:
    source_check("Ultima8",a,m,p,seg)
# Restrict only *direct* writes: other far/helper side effects unresolved.
direct_refs=[op for op in ins["Ultima8"].values() if  op.address>=0x2577 and op.address<0x26b3]
assert not any(("0xace3" in op.op_str or "0x1a16" in op.op_str) for op in direct_refs), "DIRECT_LIST_ACCESS_FOUND"
# Far identity from NE28->NE126 and second sector pass caller.
for src,operand,dst,off in [(28,0x269f,126,0xbf7),(29,0x37c,28,0x2577),
                            (28,0x25c2,32,0x1ba1),(28,0x263c,32,0x1ac9),(28,0x264d,32,0x2f83)]:
    f=resolve(src,operand)
    assert (f["segment"],f["offset"])==(dst,off),("FAR_CALL_DRIFT",src,hex(operand),f)
    checks.append({"project":"Ultima8","ref":f"NE{src}:{operand:#x}","target":f"NE{dst}:{off:#x}","result":"PASS_FAR_RELOCATION_TARGET"})
# Canonical Map5 corpus-level source IR + TYPEFLAG join.
materialized=json.loads(inputs["map5sourceir"])
flags=inputs["typeflags"]
all_instances=materialized["potential_instances"]
assert len(all_instances)==19693
glob=[r for r in all_instances if r["source_kind"]=="GLOB_POTENTIAL"]
direct=[r for r in all_instances if r["source_kind"]=="FIXED_DIRECT"]
assert (len(glob),len(direct))==(17774,1919)
ids=set();groups=collections.defaultdict(list)
family=collections.Counter();high=collections.Counter();low_property=collections.Counter()
for r in glob:
    shape=r["shape"]
    assert 0<=shape<2048
    assert r["instance_id"] not in ids
    ids.add(r["instance_id"])
    data=flags[8*shape:8*shape+8]
    assert len(data)==8
    family[data[1]>>4]+=1
    b7=bool(data[0]&0x80)
    high[b7]+=1
    low_property[bool(data[1]&1)]+=1
    if b7:
        assert shape==347
        groups[(r["definition_ordinal"],r["glob_id"])].append(r)
assert dict(family)=={0:17774}
assert high[True]==2360 and high[False]==15414
assert low_property[True]==2620 and low_property[False]==15154
assert flags[8*347:8*348].hex()=="8700400400010101"
by_glob=collections.Counter()
for rows in groups.values():
    for row in rows:by_glob[row["glob_id"]]+=1
assert by_glob=={262:2336,218:24}
assert len(groups)==148
g218=[r for r in glob if r["glob_id"]==218]
assert len(g218)==32 and sum(bool(flags[8*r["shape"]]&128) for r in g218)==24
assert len({r["shape"] for r in glob})==69
markers=[]
for (ordinal,glob_id),records in sorted(groups.items()):
    points=[v["world"] for v in records]
    markers.append({
        "marker_definition_id":f"fixed:m5:r{ordinal}",
        "definition_ordinal":ordinal,"glob_id":glob_id,
        "flag80_potential_children":len(records),
        "shape":347,
        "first_source_member":records[0]["instance_id"],
        "first_source_member_raw_offset":records[0]["source_member_raw_offset"],
        "bounds":{"x":[min(v[0] for v in points),max(v[0] for v in points)],
                  "y":[min(v[1] for v in points),max(v[1] for v in points)],
                  "z":[min(v[2] for v in points),max(v[2] for v in points)]},
        "runtime_instantiated":False,
        "evidence_class":"POTENTIAL_SOURCE_EXPANSION_ONLY"
    })
assert sum(x["flag80_potential_children"] for x in markers)==2360

# Pure reference fixtures; NOT original instruction emulation.
def valid_special_id(handle):
    return 0<handle<0x100
def flags_after_second_pass(current):
    return (current|0x2000)&0xffff
flag_fixtures=[]
for handle in (1,0xff,0x100,0x12c,0x7ff):
    for shape in (3,347):
        for current in (0,0x82,0x800,0x2082):
            result=flags_after_second_pass(current)
            assert result&0x2000
            potential_special=(not valid_special_id(handle)) and bool(flags[8*shape]&0x80)
            flag_fixtures.append({"handle":handle,"shape":shape,"before":current,"after_direct_flag_write":result,
              "valid_special_id_range":valid_special_id(handle),
              "later_NE126_branch_eligible_if_active":potential_special,
              "classification":"PURE_CONDITIONAL_SOURCE_MODEL_NOT_ORIGINAL_RUNTIME"})
assert len(flag_fixtures)==40
assert flags_after_second_pass(0x82)==0x2082
assert sum(x["later_NE126_branch_eligible_if_active"] for x in flag_fixtures)==12

# Stonekeep source scheduling. 0x31615 is after input-pump retry, not inline enqueue.
for a,m,p in [(0x3160b,"call","0x32bff"),(0x31610,"test","ax, ax"),
              (0x31613,"jne","0x3160b"),(0x31615,"call","0x85220"),
              (0x85238,"call","0x852f6"),(0x85243,"call","0x85079"),
              (0x85231,"cmp","eax, 0x29")]:
    source_check("Stonekeep",a,m,p)
poll_fixtures=[]
for trial in ([0],[1,0],[1,1,0],[1,1,1,0]):
    service_after=next(i+1 for i,x in enumerate(trial) if x==0)
    assert service_after==len(trial)
    poll_fixtures.append({"mock_input_pump_returns":trial,"service_after_n_returns":service_after,
        "scope":"PURE_LOCAL_LOOP_MODEL_NOT_ORIGINAL_EVENT_REENTRY"})
# No evidence that an input pump callback actually re-stages h415.
checks.append({"project":"Stonekeep","result":"FAIL_CLOSED_INTERLEAVING_UNPROVEN",
               "meaning":"Polling loop before service is static; second h415 request during loop remains unproven."})

# MDK clipped-fan material f3 unchanged for all six calls.
fan=[
 (0x40d8f5,0x40d8fa,0x40d920,"ebx"),
 (0x40d92f,0x40d932,0x40d95b,"ebx"),
 (0x40d96a,0x40d96d,0x40d993,"eax"),
 (0x40d9a2,0x40d9a5,0x40d9ce,"edx"),
 (0x40d9dd,0x40d9e0,0x40da0f,"ecx"),
 (0x40da1e,0x40da21,0x40da44,"ebx")
]
for load,push,call,reg in fan:
    source_check("MDK1",load,"mov",f"{reg}, dword ptr [ebp + 0x10]")
    source_check("MDK1",push,"push",reg)
    source_check("MDK1",call,"call","0x40c860")
source_check("MDK1",0x40c872,"mov","ebx, dword ptr [ebp + 0x18]")
source_check("MDK1",0x40c8be,"test","ebx, ebx")
source_check("MDK1",0x40c8c2,"mov","[0x4ce518]")
source_check("MDK1",0x40c8cc,"mov","dword ptr [eax]")
assert len(fan)==6 and len(set(x[2] for x in fan))==6
# This proves pointer identity, not the runtime material table contents.

def emit(name,obj):
    output=HERE/name
    data=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    if output.exists():
        assert output.read_bytes()==data,("REPORT_OUTPUT_DRIFT",name)
    else:
        with output.open("xb") as f:f.write(data)
    return SHA(data)
focus_markers={
 "schema":"OpenUltima8.Map5SpecialTypeflagMarkers.v1",
 "source_ir_sha256":PINS["map5sourceir"][1],"typeflag_sha256":PINS["typeflags"][1],
 "total_potential_glob_children":17774,
 "family0_potential_children":17774,
 "bit7_set_potential_children":2360,"bit7_unset_potential_children":15414,
 "bit7_set_shape_ids":[347],"shape347_typeflag_bytes":"8700400400010101",
 "bit7_glob_id_counts":{"262":2336,"218":24},
 "glob218_total":32,"glob218_unset_bit7_children":8,
 "unique_glob_shapes":69,"marker_definitions_with_bit7":148,
 "markers":markers,
 "source_provenance":"Potential SourceIR, not live runtime scene occupancy or observed callback invocation"
}
marker_sha=emit("U8_MAP5_SPECIAL_MARKERS.json",focus_markers)
result={
 "schema":"OpenRemaster.CONT13StaticEvidenceVerification.v1",
 "operation_id":"OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56",
 "iteration_id":"CONT13",
 "status":"PASS_SOURCE_STATIC_IDENTITY_WITH_CONDITIONAL_FLAG_BIT7_CONTRACTS",
 "source_inputs":{k:{"path":rel,"sha256":pin} for k,(rel,pin) in PINS.items()},
 "source_region_checks":region_checks,
 "opcode_and_relocation_checks":checks,
 "source_region_count":len(region_checks),
 "static_opcode_and_relocation_check_count":sum(x["result"].startswith("PASS_") for x in checks),
 "pure_u8_flag_fixtures":flag_fixtures,
 "pure_stonekeep_poll_fixtures":poll_fixtures,
 "derived_marker_manifest_sha256":marker_sha,
 "shape347_branch_blockers":{
  "two_known_glob_ids":[218,262],
  "potential_children":2360,
  "conditional_call":"NE28:0x269e -> NE126:0x0bf7",
  "requires":"normal return from earlier helpers, active current-area branch, and source-flow to high-bit test",
  "additional_NE126_gates":["DS:0x8906 byte at0xbfd","resource/context pointer DS:0x88f6 at0xc73"],
  "runtime_call_count":"UNKNOWN"
 },
 "source_cardinality":{
  "map5_fixed_direct":1919,"map5_glob_potential":17774,
  "map5_potential_static_instances":19693,
  "glob_family0":17774,"glob_byte0_bit7_set":2360,"glob_byte0_bit7_clear":15414,
  "glob_byte1_lowbit_set":2620,"glob_byte1_lowbit_clear":15154,
  "marker_definitions_for_special_bit":148
 },
 "original_game_instructions_executed":0,
 "runtime_capture_fidelity_verified":False,
 "production_admission":"NOT_REQUESTED",
 "evidence_note":"No original runtime instructions, no hardware/GUI capture, no project writer or game worktree writes"
}
rec_sha=emit("STATIC_VERIFICATION.json",result)
delta={
 "schema":"OpenRemaster.ReadOnlySemanticContinuation.v13",
 "operation_id":result["operation_id"],"iteration_id":"CONT13",
 "run_id":"20261009-132559__PORTFOLIO-READONLY-CONTINUATION__cont13",
 "predecessor_handoff_sha256":PINS["prev"][1],
 "registry_sha256":PINS["registry"][1],
 "static_verification_sha256":rec_sha,
 "map5_marker_manifest_sha256":marker_sha,
 "status":"NEW_ORIGINAL_SOURCE_STATIC_MECHANISM_PASS_RUNTIME_FIDELITY_HOLD",
 "focus":{
  "OpenUltima8":{
   "state":"SECOND_PASS_FLAGS_AND_SHAPE347_SPECIAL_CALLBACK_STATIC_BOUND_LIVE_SCENE_BLOCKED",
   "delta":"NE28:0x2577 first ORs bit0x2000 into ACD3[item] through NE28:0x1f70 (conditional on normal helper return), then NE28:0x1ebc tests handle range1..255, NOT world membership. For family0 and id>=256, TYPEFLAG byte0 bit7 controls the later NE126:0xbf7 helper if area globals permit.",
   "source_population":"17,774 Map5 potential GLOB children, 2,360 of shape347 with byte0 bit7 and 15,414 without; the special 2,360 are from 148 markers and GLOB IDs262=2336 and218=24; GLOB218 also has8 lowbit children. Potential != live.",
   "new_negative_contracts":["ID<256 is not proof of sector membership","A 0-return from 2577 may follow a completed 0x2000 flag write","No single universal family0=no-helper shortcut: shape347 has conditional special helper","Bit7/shape-specific helpers and earlier indirect calls remain unverified for live population"],
   "next":"Bound an original live-ID and area-state trace for one shape347 Map5 marker versus one low-bit family0 child; verify NE126 helper effects, second-pass object membership, and grid snapshot without eager grid rebuild under approved admission."
  },
  "OpenStonekeep":{
   "state":"EVENT8_SERVICE_POLL_LOOP_STATIC_GATE; REENTRY_UNVERIFIED",
   "delta":"Caller 0x3160b repeatedly invokes input/event poll0x32bff while AX!=0; first queue handler0x85220 is called only after a zero return at0x31615. Queue service is therefore not guaranteed immediate after event8 enqueue.",
   "new_negative_contracts":["Do not assume event8 service is inline with h415 request","Do not claim h415 restages during poll: transitive input-callback reachability unproven","Queue-full event8 failures and staged-global generation risks remain separate"],
   "next":"Trace original 0x32bff input dispatch dependencies for an actual h415 restaging witness before consuming pending event8; without it keep conditional graph BLOCKED."
  },
  "OpenMDK1":{
   "state":"CLIPPED_TRIANGLE_FAN_SIGNED_F3_MATERIAL_IDENTITY_STATIC_BOUND; RUNTIME_FIDELITY_BLOCKED",
   "delta":"All six explicit fan calls load the same signed-f3 slot [EBP+0x10] and push it to original sorter 0x40c860, which reads it from its own [EBP+0x18]. The clipped fan therefore inherits the source material selector instead of recomputing by triangle index.",
   "source_contract":"Six signed-f3 load/push/call triplets at0x40d8f5,0x40d92f,0x40d96a,0x40d9a2,0x40d9dd,0x40da1e ->0x40c860; original material table pointer via 0x4ce518, no falsified modulo mapping.",
   "next":"Bind one clipped LEVEL3 source triangle, effective live profile and original fan pixel captures before any fidelity promotion."
  }
 },
 "execution":{"new_heavy_jobs":0,"new_original_game_instruction_tests":0,"new_runtime":0,"new_builds":0,"new_captures":0,"native_admission":"NONE_GRANTED","source_writes":0,"project_writers_modified":False,"global_writer_journal_modified":False},
 "preservation":{"portfolio_entries":23,"azrael_retail":"PAUSED","azrael_demo":"CLOSED","roth":"WARM_COMPLETION","framework_phase1":"FROZEN","focus_read_only":["OpenMDK1","OpenStonekeep","OpenUltima8"]},
 "scope":"Persistent report-only source-static artifact; not a new game acceptance checkpoint or framework-general verified contract."
}
delta_sha=emit("SEMANTIC_DELTA.json",delta)
print(json.dumps({
 "status":result["status"],"source_regions":len(region_checks),
 "original_instruction_or_relocation_checks":result["static_opcode_and_relocation_check_count"],
 "pure_u8_flag_cases":len(flag_fixtures),"pure_poll_cases":len(poll_fixtures),
 "potential_special_children":2360,"markers":148,"files":{
  "U8_MAP5_SPECIAL_MARKERS.json":marker_sha,
  "STATIC_VERIFICATION.json":rec_sha,
  "SEMANTIC_DELTA.json":delta_sha
 }},sort_keys=True))
