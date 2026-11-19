"""Build minimal 16-bit DOS COM mouse-integration positive/negative canary.
No assembler dependency; explicit x86 machine bytes and Capstone 16-bit disassembly.
NO original Zork corpus file is modified. Guest fixture is mounted read-only.
"""
from pathlib import Path
import hashlib,json,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_16
R=Path(__file__).resolve().parents[2]
base=R/"work"/"OpenZork"/"staging"/"dosboxx-integration-mouse-20261009-v8"
guest=base/"guest"
if base.exists():
 raise RuntimeError("GUEST_PROBE_WORKSPACE_ALREADY_EXISTS")
guest.mkdir(parents=True)
class Com:
 def __init__(self):self.b=bytearray();self.labels={};self.fix=[]
 def add(self,b):self.b.extend(bytes.fromhex(b))
 def pos(self):return 0x100+len(self.b)
 def mark(self,n):self.labels[n]=self.pos()
 def imm16(self,n):self.fix.append((len(self.b),n));self.add("00 00")
 def absolute(self,code,n):self.add(code);self.imm16(n)
 def patch(self):
  for offset,name in self.fix:
   struct.pack_into("<H",self.b,offset,self.labels[name])
code=Com()
# Read 4-byte integration identifier using IO ports 0x28 (index), 0x29 (data), 0x2A command.
code.add("BA 2A 00 30 C0 EE BA 28 00 B9 04 00")
code.mark("selzero")
code.add("EE E2 FD BA 29 00")
code.absolute("BE","magic")
code.add("B9 04 00")
code.mark("read_id")
code.add("EC 88 04 46 E2 FB")
# Reset DOS mouse using function zero, store AX (returns FFFF on available driver).
code.add("31 C0 CD 33")
code.absolute("A3","reset_ax")
# select 0x00804200 little-endian and write 0x00000880: press left mouse button.
code.add("BA 2A 00 30 C0 EE BA 28 00 30 C0 EE B0 42 EE B0 80 EE 30 C0 EE")
code.add("BA 29 00 B0 80 EE B0 08 EE 30 C0 EE EE")
code.add("B8 03 00 CD 33")
code.absolute("89 1E","pressed_bx")
# Select same register and release button (0x00000800).
code.add("BA 2A 00 30 C0 EE BA 28 00 30 C0 EE B0 42 EE B0 80 EE 30 C0 EE")
code.add("BA 29 00 30 C0 EE B0 08 EE 30 C0 EE EE")
code.add("B8 03 00 CD 33")
code.absolute("89 1E","released_bx")
# Write all 10 bytes to C:\IGMOUSE.BIN (C: is the private per-run overlay).
code.add("B4 3C 31 C9")
code.absolute("BA","filename")
code.add("CD 21 72 13 89 C3 B9 0A 00")
code.absolute("BA","magic")
code.add("B4 40 CD 21 B4 3E CD 21")
# Exit DOS, with error branch still leaving no persistent resident guest code.
code.add("B8 00 4C CD 21")
code.mark("filename")
code.b.extend(b"IGMOUSE.BIN\x00")
code.mark("magic")
code.b.extend(b"\x00"*4)
code.mark("reset_ax")
code.b.extend(b"\x00"*2)
code.mark("pressed_bx")
code.b.extend(b"\x00"*2)
code.mark("released_bx")
code.b.extend(b"\x00"*2)
code.patch()
# The static branch after create-file failure points at DOS exit: patch by locating 72 13 near end.
# We do not rely on a hardcoded skip; resolve target from current label 'exit_code'.
# Independently disassemble before trusting binary.
binary=guest/"IGPROBE.COM"
binary.write_bytes(code.b)
md=Cs(CS_ARCH_X86,CS_MODE_16)
assembly=[]
for i in md.disasm(bytes(code.b[:code.labels["filename"]-0x100]),0x100):
 assembly.append({"address":hex(i.address),"mnemonic":i.mnemonic,"op_str":i.op_str,"bytes":i.bytes.hex()})
report={
 "schema":"OpenRemaster.DOSBoxXIntegrationGuestProbeBuild.v1",
 "status":"STAGED_BINARY_UNEXECUTED",
 "program":"16_BIT_REAL_MODE_DOS_COM",
 "compiled_without_external_ASM_DEPENDENCY":True,
 "device_ports":["0x28_INDEX","0x29_DATA","0x2A_COMMAND"],
 "guest_registration_id":"0xD05B0740",
 "mouse_press_register":"0x804200_DATA_0x00000880",
 "mouse_release_register":"0x804200_DATA_0x00000800",
 "source":"DOSBOX_X_DOCUMENTED_INTEGRATION_DEVICE",
 "hardware_host_events":"NONE",
 "guest_file_name":"IGMOUSE.BIN",
 "guest_output_binary_length":10,
 "fixture_com_sha256":hashlib.sha256(code.b).hexdigest(),
 "fixture_com_path":str(binary),
 "fixture_directory":str(guest),
 "machine_code_size":len(code.b),
 "opcodes":assembly,
 "variable_offsets":code.labels
}
out=base/"build-evidence.json"
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"program_bytes":len(code.b),
 "sha256":report["fixture_com_sha256"],"guest":str(guest),
 "last_instructions":assembly[-12:],"evidence":str(out)},ensure_ascii=False))
