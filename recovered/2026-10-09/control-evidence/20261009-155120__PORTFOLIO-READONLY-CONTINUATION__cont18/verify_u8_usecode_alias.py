"""CONT18 U8 original USECODE name-pointer alias escape analysis.

Read-only U8.EXE, original EUSECODE.FLX, Map5 source IR. Identifies
specific aliases of record+4 names, not an absence-of-all-writes proof.
"""
from pathlib import Path
import hashlib,sys,json,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_16
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
EXE=ROOT/"source/Ultima 8/ENGLISH/U8.EXE"
FLX=ROOT/"source/Ultima 8/ENGLISH/USECODE/EUSECODE.FLX"
SOURCE_IR=ROOT/"output/projects/OpenUltima8/evidence/20261008-094213__AUTONOMOUS-4H__cycle01/map5-materialization-sourceir-v3.json"
SHA=lambda b:hashlib.sha256(b).hexdigest()
exe=EXE.read_bytes();flx=FLX.read_bytes();ir=SOURCE_IR.read_bytes()
assert SHA(exe)=="1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f"
assert SHA(flx)=="5eceb14286f06f6bb07c35d0c83c0670d500474cd9a7390ad533c0f0f93f4e38"
assert SHA(ir)=="a5c8c9aa9e9da9ceecd41c1cecd18e7f20c18f2822ba38b878b07f613b8a5638"
sys.path.insert(0,str(ROOT/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load
from ne_far_target import resolve
ub,ne,ss=load();assert ub==exe
md=Cs(CS_ARCH_X86,CS_MODE_16)
regions=[]
ops={}
for seg,a,z in ((126,0xd90,0xdcd),(125,0x3a1,0x3d6),(126,0xc73,0xced)):
 s=ss[seg-1]
 raw=exe[s["offset"]+a:s["offset"]+z]
 dec=list(md.disasm(raw,a))
 assert dec and dec[0].address==a and dec[-1].address+dec[-1].size==z,("ORIGINAL_INSTR_BOUND",seg,hex(a),hex(z))
 regions.append({"segment":seg,"begin":hex(a),"end":hex(z),"sha256":SHA(raw)})
 for q in dec:
  key=(seg,q.address)
  assert key not in ops
  ops[key]=q
checks=[]
def check(seg,a,mn,needle):
 q=ops.get((seg,a))
 assert q and q.mnemonic==mn and needle in q.op_str,("SOURCE_MISMATCH",seg,hex(a),mn,needle,None if not q else(q.mnemonic,q.op_str))
 checks.append({"location":f"NE{seg}:{a:#x}","original_instr":q.mnemonic+" "+q.op_str})
for sn,a,m,n in [
 (126,0xd90,"mov","[bx + 2]"),
 (126,0xd97,"mov","ax, si"),
 (126,0xd99,"mov","dx, 0xd"),
 (126,0xd9c,"imul","dx"),
 (126,0xd9e,"mov","[0x88f8]"),
 (126,0xda2,"mov","[0x88f6]"),
 (126,0xda6,"add","bx, ax"),
 (126,0xda8,"add","bx, 4"),
 (126,0xdab,"mov","[bp - 0x12]"),
 (126,0xdae,"mov","[bp - 0x14]"),
 (126,0xdb1,"mov","[bp - 0x10]"),
 (126,0xdb4,"shl","ax, 2"),
 (126,0xdb7,"les","[0x8c0a]"),
 (126,0xdbb,"add","bx, ax"),
 (126,0xdbd,"mov","[bp - 0x12]"),
 (126,0xdc0,"mov","[bp - 0x14]"),
 (126,0xdc3,"mov","word ptr es:[bx + 2]"),
 (126,0xdc7,"mov","word ptr es:[bx]"),
 (125,0x3b4,"mov","word ptr es:[bx]"),
 (125,0x3b7,"mov","dx, 0xd"),
 (125,0x3ba,"imul","dx"),
 (125,0x3bc,"mov","[0x88f6]"),
 (125,0x3c0,"add","dx, ax"),
 (125,0x3c2,"add","dx, 4"),
 (125,0x3c5,"push","[0x88f8]"),
 (125,0x3c9,"push","dx"),
 (125,0x3ce,"lcall","0xffff"),
 (126,0xc82,"les","[0x88f6]"),
 (126,0xc8c,"test","dword ptr es:[bx]"),
 (126,0xc90,"je","0xce9"),
 (126,0xcce,"les","[bp + 0x10]"),
 (126,0xcd1,"mov","word ptr es:[bx], 0"),
 (126,0xcdf,"les","[bp + 0x10]"),
 (126,0xce2,"mov","word ptr es:[bx], ax")
]:check(sn,a,m,n)
target=resolve(125,0x3cf)
assert target["segment"]==1 and target["offset"]==0x502e
# Confirm the flag bytes source default 13-byte metadata record.
count=struct.unpack_from("<I",flx,0x54)[0]
assert count==1433
loc,num=struct.unpack_from("<II",flx,0x88)
assert num==1431*13
source=flx[loc:loc+num]
assert SHA(source)=="90ff19c6191c75562cad773c01608d31a908a8157de05e7a21cd9e5ed5f9e6f6"
shape=347
rec=source[13*shape:13*(shape+1)]
assert struct.unpack_from("<I",rec)[0]==0x40
assert rec[4:].split(b"\0")[0]==b"CLRWATER"
assert struct.unpack_from("<I",rec)[0]&0x000f8000==0
# A resource name pointer starting at +4 is NOT itself proof of a write
# to the four flag bytes at +0; names may, however, be modified through
# escaped pointer and indirect runtime effects, which we don't rule out.
report={
 "schema":"OpenUltima8.UsecodeSourceNameAliasEscape.v1",
 "U8_EXE_SHA256":SHA(exe),
 "EUSECODE_FLX_SHA256":SHA(flx),
 "Map5_SourceIR_SHA256":SHA(ir),
 "original_code_byte_regions":regions,
 "original_opcode_checks":checks,"opcode_check_count":len(checks),
 "source_default_record":{"shape":347,"metadata13_hex":rec.hex(),
                         "flags":hex(struct.unpack_from("<I",rec)[0]),
                         "test_mask":"0x000f8000","result":0,
                         "name":rec[4:].split(b"\0")[0].decode("latin1")},
 "alias_escape":{
  "producer":"NE126:0xd97..0xdca",
  "input":"original shape index SI",
  "derived_name_pointer":"DS:0x88f6/88f8 + shape*13 + 4",
  "store_destination":"far-pointer array at DS:0x8c0a indexed by [BP-0x10]*4",
  "writes":"store segment and offset pointer into array, not into capability flag bytes",
  "source_alias_exposure":"PER_SHAPE_NAME_STRING_POINTER_MAY_ESCAPE",
  "not_proved":"No future indirect mutation of name, neighboring flags, or entire table"
 },
 "NE125_name_string_use":{
  "operation":"compute shape*13 + DS:0x88f6 +4, pass name-pointer to NE1:0x502e",
  "caller":"NE125:0x3a3..0x3d3",
  "source_far_relocation_file_offset":target["relocation_file_offset"],
  "call_behavior":"The external target direction/mutability is not asserted from caller signature alone"
 },
 "mask_branch":{
  "source":"NE126:0xc73..0xced",
  "test":"NE126:0xc8c reads dword at record+0",
  "original_zero_branch":"NE126:0xc90 JE0xCE9 returns AL0 before secondary allocation",
  "later_writes":"NE126:0xcd1/ce2 use new pointer loaded from [BP+0x10] and do not directly write flags",
  "source_default_shape347_negative":True
 },
 "qualifications":["Direct writer inventory cannot prove whole-program immutability",
  "Aliased name pointer indicates potential indirect access",
  "Shape347 source-default bytecode entry empty; other game state effects independent",
  "Runtime DS:88f6 content and real GLOB218 instantiation not observed"],
 "original_game_instructions_executed":0,
 "runtime_fidelity_verified":False
}
file=HERE/"U8_USECODE_NAME_ALIAS_ESCAPE.json"
data=(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
if file.exists():assert file.read_bytes()==data,("REPORT_OUTPUT_CONFLICT",str(file))
else:
 with file.open("xb") as f:f.write(data)
print(json.dumps({
 "status":"PASS_ORIGINAL_USECODE_RECORD_NAME_ALIAS_STATIC",
 "source_byte_regions":len(regions),"original_opcode_checks":len(checks),
 "shape347_flag_result":0,
 "per_shape_name_pointer_exported":True,
 "other_indirect_writes_excluded":False,
 "game_runtime":0,"SHA256":SHA(data)
},sort_keys=True))
