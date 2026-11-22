"""CONT18 original Stonekeep h415 action0 prehelper/stack-output scope.

Read-only source disassembly. Does not execute SK.EXE, callbacks,
runtime event queue, sound/audio or scene capture. Preserves project code.
"""
from pathlib import Path
import json,hashlib,sys
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
B=(ROOT/"source/Stonekeep/SK.EXE").read_bytes()
SHA=lambda x:hashlib.sha256(x).hexdigest()
assert SHA(B)=="5517ddeb49c7087d6b2449182020200c58084feb4cae55e31ac8acc6cdbdddd2"
MAP=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-144000__PORTFOLIO-READONLY-CONTINUATION__cont16/STONEKEEP_CORRECTED_LEVEL_CALLBACKS.json"
map_raw=MAP.read_bytes()
assert SHA(map_raw)=="c922fa8c5b337fd2cd5952b97d36786df925ae8c02499c01990ede0d0232ec40"
callbacks=json.loads(map_raw)
assert callbacks["level15"]["callback_va"]=="0x4f861"
sys.path.insert(0,str(ROOT/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
im=LEImage(B)
d=Cs(CS_ARCH_X86,CS_MODE_32)
ranges=[
 ("ACTION0_WRAPPER",0x6a183,0x6a213),
 ("FIRST_TABLE_LOOKUP",0x3daf3,0x3db08),
 ("SECOND_TABLE_LOOKUP",0x3db08,0x3db1d),
 ("LOOKUP_OUTPUT_FIELDS",0x3d9cc,0x3da53),
 ("QUERY_ORIGINAL_RECORD",0xabd3e,0xabd85),
 ("CURRENT_MAP_CELL_LOOKUP",0x3c2f4,0x3c325),
 ("LEVEL15_CALLBACK",0x4f861,0x4f862)
]
regions=[];instr={}
for name,a,z in ranges:
    b=im.read_va(a,z-a)
    ins=list(d.disasm(b,a))
    assert ins and ins[0].address==a and ins[-1].address+ins[-1].size==z,("UNALIGNED_ORIGINAL_SOURCE",name)
    regions.append({"name":name,"address":hex(a),"size":len(b),"sha256":SHA(b)})
    for q in ins:
        assert q.address not in instr or instr[q.address].bytes==q.bytes
        instr[q.address]=q
checks=[]
def opcode(a,mn,part):
    q=instr.get(a)
    assert q and q.mnemonic==mn and part in q.op_str,("OPCODE_DRIFT",hex(a),mn,part,None if not q else(q.mnemonic,q.op_str))
    checks.append({"VA":hex(a),"opcode":q.mnemonic+" "+q.op_str})
for a,m,n in [
 (0x6a18e,"lea","[esp + 8]"),
 (0x6a192,"push","eax"),
 (0x6a193,"lea","[esp + 0x10]"),
 (0x6a197,"push","eax"),
 (0x6a19d,"call","0x3daf3"),
 (0x6a1a2,"lea","[esp + 0xc]"),
 (0x6a1a6,"lea","[esp + 8]"),
 (0x6a1ac,"xor","eax, eax"),
 (0x6a1ae,"call","0x3d9cc"),
 (0x6a1c4,"call","0x3c2f4"),
 (0x6a206,"call","0xac4aa"),
 (0x3daf4,"movsx","[eax*2 + 0x13f6e]"),
 (0x3dafc,"imul","eax, eax, 0x16"),
 (0x3daff,"add","eax, 0x13ba4"),
 (0x3db04,"add","eax, 9"),
 (0x3db09,"movsx","[eax*2 + 0x13ffe]"),
 (0x3db11,"imul","eax, eax, 0x16"),
 (0x3d9e0,"call","0x3daf3"),
 (0x3d9eb,"call","0x3db08"),
 (0x3da06,"call","0xabd3e"),
 (0x3da0b,"test","ax, ax"),
 (0x3da0e,"je","0x3da4a"),
 (0x3da18,"mov","word ptr [ebp]"),
 (0x3da24,"mov","word ptr [edi]"),
 (0x3da33,"mov","word ptr [edx]"),
 (0x3da42,"mov","word ptr [edx]"),
 (0x3da50,"ret","8"),
 (0xabd4c,"call","0xabd28"),
 (0xabd5d,"call","0x1f490"),
 (0xabd6b,"call","0xa9c60"),
 (0xabd70,"test","eax, eax"),
 (0xabd7c,"mov","dword ptr [esi], eax"),
 (0x3c2fa,"movsx","[eax*2 + 0x1b9df8]"),
 (0x3c31d,"movsx","[edx + eax + 3]"),
 (0x4f861,"ret","")
]:opcode(a,m,n)
# No *direct* call to transition staging/queue in just these
# bounded original function bodies. Far/indirect helper effects remain open.
known_stage={"0xa2ba6","0xa2c2b","0x851c3","0x3cfee","0x85220"}
direct_calls=[]
for name,a,z in ranges:
  for p in range(a,z):
    q=instr.get(p)
    if q and q.mnemonic=="call":
      direct_calls.append({"name":name,"VA":hex(q.address),"target":q.op_str})
assert all(x["target"] not in known_stage for x in direct_calls)
# Source-local memory destinations in 0x3d9cc are pointers loaded from
# caller-provided stack locals, not absolute staged globals.
stage_slots=("{0x1bc404}","{0x1bc406}","{0x1bc414}")
writes=[q for q in instr.values() if q.mnemonic in ("mov","movsx","stos","stosd")
        and any(t in q.op_str for t in ("0x1bc404","0x1bc406","0x1bc414"))]
assert not writes
report={
 "schema":"OpenStonekeep.H415Action0PreHelperOutputProvenance.v1",
 "SK_EXE_sha256":SHA(B),
 "level_callback_correction_sha256":SHA(map_raw),
 "level15_callback":"0x4f861 immediate ret",
 "verified_source_regions":regions,
 "original_opcode_checks":checks,
 "original_opcode_check_count":len(checks),
 "coordinate_lookup":"0x6a183 calls0x3daf3/0x3d9cc and uses original pointers to local stack coordinate outputs;0x3d9cc query success writes to passed pointers",
 "lookup_table_shape":"0x3daf3 and0x3db08 select 22-byte indexed source table records",
 "original_query":"0x3d9cc calls0xabd3e; that routine calls0xabd28,0x1f490,0xa9c60 and returns a queried source record pointer",
 "map_tile_lookup":"0x3c2f4 returns original byte from current map lookup",
 "direct_staged_global_writes_found":0,
 "direct_h415_stage_or_event_queue_calls_found":0,
 "direct_calls":direct_calls,
 "important_limitations":[
  "0xabd3e transitive calls may have effects, so no global side-effect absence proof",
  "The generic action0 dispatcher and later0x3d35e helper remain conditionally reachable",
  "A separate input action2/3 may still enqueue before pending event8 consumption",
  "This does not verify original runtime event8, level transition or fidelity"
 ],
 "reentry_status":"NO_DIRECT_STAGE_WITHIN_BOUNDED_PREHELPERS; TRANSITIVE/INDEPENDENT_EVENTS_UNVERIFIED",
 "original_game_instructions_executed":0,"runtime_fidelity_verified":False
}
path=HERE/"STONEKEEP_H415_PREHELPER_SCOPE.json"
content=(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
if path.exists():assert path.read_bytes()==content,("CONFLICTING_REPORT_BYTES",str(path))
else:
 with path.open("xb") as f:f.write(content)
print(json.dumps({
 "status":"PASS_BOUNDED_ORIGINAL_ACTION0_PREHELPER_NO_DIRECT_STAGE",
 "source_regions":len(regions),"original_opcode_checks":len(checks),
 "direct_calls":len(direct_calls),"direct_stage_writes":0,
 "global_no_reentry_proved":False,"game_runtime":0,"sha256":SHA(content)
},sort_keys=True))
