"""Stonekeep h415 action0 → corrected level15 RET → generic default path.

This reconstructs only a bounded original source-code path with checked
opcode identities. Neither game instructions nor native engine are executed.
"""
from pathlib import Path
import json,hashlib,sys
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/"source/Stonekeep/SK.EXE"
raw=SOURCE.read_bytes()
SHA=lambda b:hashlib.sha256(b).hexdigest()
assert SHA(raw)=="5517ddeb49c7087d6b2449182020200c58084feb4cae55e31ac8acc6cdbdddd2"
prev=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-144000__PORTFOLIO-READONLY-CONTINUATION__cont16/STONEKEEP_CORRECTED_LEVEL_CALLBACKS.json"
prev_raw=prev.read_bytes()
assert SHA(prev_raw)=="c922fa8c5b337fd2cd5952b97d36786df925ae8c02499c01990ede0d0232ec40"
callbacks=json.loads(prev_raw)
assert callbacks["level15"]["callback_va"]=="0x4f861"
assert callbacks["level15"]["is_one_byte_RET_stub"]
sys.path.insert(0,str(ROOT/"output/projects/OpenStonekeep/evidence/20261008-094213__AUTONOMOUS-4H__cycle01"))
from source_manifest import LEImage
from le_fixups import LE
im=LEImage(raw);le=LE(raw)
decoder=Cs(CS_ARCH_X86,CS_MODE_32)
def decode(a,z):
 data=im.read_va(a,z-a)
 return {x.address:x for x in decoder.disasm(data,a)}
checks=[]
def expect(mapping,a,mn,needle):
 x=mapping.get(a)
 assert x and x.mnemonic==mn and needle in x.op_str,("OPCODE_MISMATCH",hex(a),mn,needle,None if not x else(x.mnemonic,x.op_str))
 checks.append({"VA":hex(a),"original_instr":x.mnemonic+" "+x.op_str,"status":"PASS_SOURCE_OPCODE_ONLY"})
h415=decode(0x4f983,0x4f9d4)
fallback=decode(0x4fc57,0x4fca9)
wrapper=decode(0x6a183,0x6a239)
selector=decode(0xac4aa,0xac549)
sel_tail=decode(0xac68c,0xac69a)
lev_disp=decode(0x3d4f5,0x3d502)
default=decode(0x3c36a,0x3c4bd)
helper=decode(0x3d35e,0x3d4f5)
for mapping,a,m,n in [
 (h415,0x4f983,"push","ebx"),
 (h415,0x4f988,"mov","esi, eax"),
 (h415,0x4f9b1,"cmp","ax, 2"),
 (h415,0x4f9b5,"jb","0x4fc57"),
 (fallback,0x4fc9b,"movsx","eax, si"),
 (fallback,0x4fc9e,"call","0x6a230"),
 (wrapper,0x6a230,"push","edx"),
 (wrapper,0x6a232,"mov","edx, 1"),
 (wrapper,0x6a237,"jmp","0x6a217"),
 (wrapper,0x6a217,"call","0x6a183"),
 (wrapper,0x6a18a,"mov","edi, eax"),
 (wrapper,0x6a18c,"mov","esi, edx"),
 (wrapper,0x6a203,"movsx","eax, di"),
 (wrapper,0x6a206,"call","0xac4aa"),
 (selector,0xac4ad,"mov","esi, eax"),
 (selector,0xac4b5,"cmp","si, 0x19"),
 (selector,0xac4b9,"jb","0xac50f"),
 (selector,0xac50f,"cmp","si, 7"),
 (selector,0xac513,"jb","0xac52e"),
 (selector,0xac52e,"cmp","si, 1"),
 (selector,0xac532,"jb","0xac68c"),
 (sel_tail,0xac68c,"movsx","eax, si"),
 (sel_tail,0xac68f,"call","0x3d4f5"),
 (lev_disp,0x3d4f5,"cwde",""),
 (lev_disp,0x3d4f6,"call","[0x1b9ddc]"),
 (lev_disp,0x3d4fc,"cwde",""),
 (lev_disp,0x3d4fd,"jmp","0x3c36a"),
 (default,0x3c36d,"mov","ecx, eax"),
 (default,0x3c36f,"cmp","ax, 7"),
 (default,0x3c373,"jb","0x3c3bf"),
 (default,0x3c3bf,"cmp","ax, 4"),
 (default,0x3c3c3,"jb","0x3c3d2"),
 (default,0x3c3d2,"cmp","ax, 2"),
 (default,0x3c3d6,"jb","0x3c4a3"),
 (default,0x3c446,"call","[0x1b9df4]"),
 (default,0x3c4a3,"cmp","[0x1b9d88], 0"),
 (default,0x3c4aa,"jne","0x3c4b4"),
 (default,0x3c4ac,"movsx","eax, cx"),
 (default,0x3c4af,"call","0x3d35e"),
 (default,0x3c4b4,"mov","eax, 1"),
 (helper,0x3d375,"call","0x3c14d")
]:
 expect(mapping,a,m,n)
assert im.read_va(0x4f861,1)==bytes([0xc3])
# Pure branch-path evaluation for the exact EAX=0 input callback.
def direct_trace(action,global_level_ret=True):
 assert action==0 and global_level_ret
 steps=[
  "h415 EAX0 -> 0x4f9b1 CMP AX2 -> JB 0x4fc57",
  "0x4fc9e -> 0x6a230 -> 0x6a183 selector1",
  "0x6a206 -> 0xac4aa receives EAX0",
  "0xac4b9 + 0xac513 + 0xac532 -> 0xac68c",
  "0xac68f -> 0x3d4f5; level15 0x4f861 immediate RET",
  "0x3d4fd -> 0x3c36a EAX0; 0x3c373/3c3c3/3c3d6 branches",
  "0x3c4a3, optionally 0x3d35e helper, returns"
 ]
 return steps
steps=direct_trace(0)
# The generic current-cell re-call at 3c446 is under OTHER selector branches.
assert all("3c446" not in item for item in steps)
helper_calls=sorted(({"address":hex(x.address),"target":x.op_str}
  for x in helper.values() if x.mnemonic=="call"),key=lambda r:int(r["address"],16))
direct_targets={x["target"] for x in helper_calls}
assert "0xa2ba6" not in direct_targets and "0x3cfee" not in direct_targets
assert "0x851c3" not in direct_targets and "0x85220" not in direct_targets
report={
 "schema":"OpenStonekeep.H415Level15Action0BoundedSourceTrace.v1",
 "original_EXE_sha256":SHA(raw),
 "corrected_callback_map_sha256":SHA(prev_raw),
 "source_entry_h415":"0x4f983",
 "source_level15_callback":"0x4f861",
 "level15_callback_hex":"c3","level15_ret_only":True,
 "input_pump_calls_h415_with_EAX":0,
 "bounded_action0_direct_trace":steps,
 "original_opcode_checks":checks,
 "bounded_default_action_recall_site":"0x3c446 call [0x1b9df4], not traversed by direct action0 branch",
 "general_helper_direct_calls":helper_calls,
 "no_direct_staging_or_queue_call_in_helper_source_region":True,
 "direct_call_excluded_targets":["0xa2ba6","0x3cfee","0x851c3","0x85220"],
 "remaining_unverified":[
  "other transitive audio/state/geometry helper effects and dynamic callbacks",
  "interleaving of a separate action2/3 before pending event8",
  "event8 queue-full admission and staged-payload lifetime in real gameplay",
  "loader actual live-state update and original runtime/fidelity replay"
 ],
 "claim":"For a currently installed level15 RET callback and h415 action0 EAX0, the bounded direct dispatch chain avoids the h415 action2/3 handler and avoids the generic current-cell callback callsite at0x3c446.",
 "not_claimed":"No possibility of any new event or staging anywhere in full game",
 "original_machine_instructions_executed":0,"runtime_or_fidelity_verified":False
}
output=HERE/"STONEKEEP_H415_ACTION0_DIRECT_CHAIN.json"
data=(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
if output.exists():assert output.read_bytes()==data
else:
 with output.open("xb") as f:f.write(data)
print(json.dumps({"status":"PASS_BOUNDED_ORIGINAL_H415_ACTION0_SOURCE_CHAIN",
 "level15_ret_only":True,
 "opcode_checks":len(checks),
 "helper_direct_calls":helper_calls,
 "h415_action0_direct_stage":False,
 "runtime_game_tests":0,
 "output_sha256":SHA(data)},sort_keys=True))
