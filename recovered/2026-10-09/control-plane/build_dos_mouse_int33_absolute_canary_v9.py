"""Build exact, small 16-bit DOS COM to test INT 33h fn3 (read) and fn4 (set)
twice under DOSBox-X. All output is to the private C overlay. No keyboard/mouse
events on Windows, no original ZORKDOS binary execution or source mutations.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_16
R=Path(__file__).resolve().parents[2]
base=R/"work"/"OpenZork"/"staging"/"dosboxx-int33-absolute-canary-20261009-v9"
if base.exists():raise RuntimeError("V9_GUEST_CANARY_ALREADY_EXISTS")
guest=base/"guest"
guest.mkdir(parents=True)
class Asm:
 def __init__(self):self.b=bytearray();self.labels={};self.fix=[];self.rel8=[]
 def add(self,s):self.b.extend(bytes.fromhex(s))
 def data(self,b):self.b.extend(b)
 def label(self,n):self.labels[n]=0x100+len(self.b)
 def ptr(self,prefix,label):
  self.add(prefix);self.fix.append((len(self.b),label));self.add("00 00")
 def jump_short(self,code,label):
  self.add(code);self.rel8.append((len(self.b),label));self.add("00")
 def patch(self):
  for pos,name in self.fix:
   struct.pack_into("<H",self.b,pos,self.labels[name])
  for pos,name in self.rel8:
   rel=self.labels[name]-(0x100+pos+1)
   if not -128<=rel<=127:raise ValueError("relative branch out of range")
   struct.pack_into("<b",self.b,pos,rel)
a=Asm()
a.add("31 C0 CD 33")            # mouse reset AX=0000
a.ptr("A3","reset_ax")
a.add("B8 03 00 CD 33")
for reg,label,enc in [("bx","before_bx","89 1E"),("cx","before_x","89 0E"),("dx","before_y","89 16")]:a.ptr(enc,label)
def set_and_sample(x,y,postfix):
 a.add("B8 04 00")
 a.add("B9 "+struct.pack("<H",x).hex(" "))
 a.add("BA "+struct.pack("<H",y).hex(" "))
 a.add("CD 33")
 a.add("B8 03 00 CD 33")
 for label,enc in [("bx_"+postfix,"89 1E"),("x_"+postfix,"89 0E"),("y_"+postfix,"89 16")]:a.ptr(enc,label)
set_and_sample(100,100,"100")
set_and_sample(300,150,"300")
# File C:\MSPOSV9.BIN created on overlaid C: private output exclusively
a.add("B4 3C 31 C9");a.ptr("BA","filename")
a.add("CD 21")
a.jump_short("72","exit")
a.add("89 C3 B4 40 B9 14 00");a.ptr("BA","reset_ax")
a.add("CD 21 B4 3E CD 21")
a.label("exit")
a.add("B8 00 4C CD 21")
a.label("filename");a.data(b"C:\\MSPOSV9.BIN\x00")
names=("reset_ax","before_bx","before_x","before_y",
       "bx_100","x_100","y_100","bx_300","x_300","y_300")
assert len(names)==10
for name in names:a.label(name);a.data(b"\x00\x00")
a.patch()
exe=guest/"MSPOSV9.COM"
exe.write_bytes(a.b)
assembly=[]
md=Cs(CS_ARCH_X86,CS_MODE_16)
for i in md.disasm(a.b[:a.labels["filename"]-0x100],0x100):
 assembly.append({"pc":hex(i.address),"mnemonic":i.mnemonic,"args":i.op_str})
assert assembly[-1]["mnemonic"]=="int" and assembly[-1]["args"]=="0x21"
record={"schema":"OpenRemaster.NativeDOSInt33MousePositionFixture.v1",
 "status":"STAGED_UNEXECUTED","captured_utc":datetime.now(timezone.utc).isoformat(),
 "binary":str(exe),"sha256":hashlib.sha256(a.b).hexdigest(),"bytes":len(a.b),
 "output":"C:\\MSPOSV9.BIN","output_bytes":20,
 "requested_absolute_mouse_positions":[[100,100],[300,150]],
 "query_before_and_after":"DOS_INT_33H_AX_0003",
 "set_operation":"DOS_INT_33H_AX_0004",
 "scope":"16_BIT_GUEST_CANARY_NOT_ORIGINAL_GAME_EXECUTION",
 "host_mouse_injection":False,"retail_fidelity":"NOT_TESTED",
 "disassembly":assembly}
receipt=base/"build-evidence.json"
receipt.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],"binary":str(exe),
 "sha256":record["sha256"],"size":len(a.b),
 "instructions":len(assembly),"output_bytes":20,"evidence":str(receipt)},ensure_ascii=False))
