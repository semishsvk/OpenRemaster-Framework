"""U8 source-default shape347 branch + USECODE resource metadata scope.

Proves exact original input bytes and bounded opcode paths. NO game execution,
no live memory/capture. A negative static branch cannot prove script immutability.
"""
from pathlib import Path
import struct,hashlib,json,sys,collections
from capstone import Cs,CS_ARCH_X86,CS_MODE_16
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
SHA=lambda b:hashlib.sha256(b).hexdigest()
exe=ROOT/"source/Ultima 8/ENGLISH/U8.EXE"
flxpath=ROOT/"source/Ultima 8/ENGLISH/USECODE/EUSECODE.FLX"
typepath=ROOT/"source/Ultima 8/ENGLISH/STATIC/TYPEFLAG.DAT"
mapfile=ROOT/"output/projects/OpenUltima8/evidence/20261008-094213__AUTONOMOUS-4H__cycle01/map5-materialization-sourceir-v3.json"
assert SHA(exe.read_bytes())=="1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f"
flx=flxpath.read_bytes()
assert SHA(flx)=="5eceb14286f06f6bb07c35d0c83c0670d500474cd9a7390ad533c0f0f93f4e38"
flag=typepath.read_bytes()
assert SHA(flag)=="2b07f4a6acc5504d9d07c47d3686f74107cac7b594ccb18251e01249fadebc62"
rawmap=mapfile.read_bytes()
assert SHA(rawmap)=="a5c8c9aa9e9da9ceecd41c1cecd18e7f20c18f2822ba38b878b07f613b8a5638"
sourceir=json.loads(rawmap.decode("utf-8-sig"))
sys.path.insert(0,str(ROOT/"output/projects/OpenUltima8/evidence/20261008-135657__AUTONOMOUS-4H-R2__cycle01"))
from ne_glob_candidates import load
from ne_far_target import resolve
b,ne,segments=load()
assert SHA(b)==SHA(exe.read_bytes())
bits=Cs(CS_ARCH_X86,CS_MODE_16)
s126=segments[125]
start,end=0xc73,0xced
code=b[s126["offset"]+start:s126["offset"]+end]
ops=list(bits.disasm(code,start))
assert ops and ops[0].address==start and ops[-1].address+ops[-1].size==end
byaddr={o.address:o for o in ops}
checks=[]
def op(addr,mn,needle):
 r=byaddr.get(addr)
 assert r and r.mnemonic==mn and needle in r.op_str,("OPCODE_OR_ADDRESS_DRIFT",hex(addr),mn,needle,None if not r else (r.mnemonic,r.op_str))
 checks.append({"VA":f"NE126:{addr:#x}","original_instruction":r.mnemonic+" "+r.op_str,"result":"PASS_SOURCE_OPCODE_ONLY"})
for row in [
 (0xc73,"cmp","[0x88f6]"),
 (0xc79,"je","0xce9"),
 (0xc7d,"mov","dx, 0xd"),
 (0xc80,"imul","dx"),
 (0xc82,"les","[0x88f6]"),
 (0xc86,"add","bx, ax"),
 (0xc8c,"test","dword ptr es:[bx], eax"),
 (0xc90,"je","0xce9"),
 (0xcad,"call","0xced"),
 (0xcce,"les","[bp + 0x10]"),
 (0xcd1,"mov","word ptr es:[bx], 0"),
 (0xcdf,"les","[bp + 0x10]"),
 (0xce2,"mov","word ptr es:[bx], ax"),
 (0xce9,"mov","al, 0")
]:
 op(*row)
assert resolve(28,0x269f)["segment"]==126 and resolve(28,0x269f)["offset"]==0xbf7
# After the capability-table load at 0xc82, ES:BX is reused for the
# CALLER-OUTPUT-pointer at cce/cdf before writes cd1/ce2. These are not
# direct writes into the usecode flags field.
assert byaddr[0xcce].op_str.endswith("[bp + 0x10]")
assert byaddr[0xcdf].op_str.endswith("[bp + 0x10]")

n=struct.unpack_from("<I",flx,0x54)[0]
assert n==1433
entries=[struct.unpack_from("<II",flx,0x80+8*i) for i in range(n)]
assert sum(bool(offset and length) for offset,length in entries)==518
off,length=entries[1]
assert length==1431*13
meta=flx[off:off+length]
assert SHA(meta)=="90ff19c6191c75562cad773c01608d31a908a8157de05e7a21cd9e5ed5f9e6f6"
mask=0x000f8000
def info(shape):
 r=meta[shape*13:(shape+1)*13]
 return {
  "shape":shape,
  "flags":struct.unpack_from("<I",r)[0],
  "name":r[4:].split(b"\x00")[0].decode("latin-1"),
  "own_FLX_entry_offset":entries[shape][0],
  "own_FLX_entry_length":entries[shape][1],
  "original_metadata_record_hex":r.hex(),
  "original_metadata_record_sha256":SHA(r)
 }
r347=info(347);r128=info(128);r59=info(59)
assert r347["flags"]==0x40 and r347["name"]=="CLRWATER" and r347["own_FLX_entry_length"]==0
assert r128["flags"]==0 and r128["own_FLX_entry_length"]==0
assert r59["flags"]==0x18000 and r59["own_FLX_entry_length"]==180
assert (r347["flags"]&mask)==0 and (r59["flags"]&mask)!=0
assert flag[8*347]&0x80 and not (flag[8*128]&0x80)
cross=collections.Counter()
for shape in range(1431):
 flags=struct.unpack_from("<I",meta,shape*13)[0]
 cross[(bool(flags&mask),bool(entries[shape][1]))]+=1
assert cross=={(False,True):441,(False,False):887,(True,True):75,(True,False):28}
glob=[x for x in sourceir["potential_instances"] if x["source_kind"]=="GLOB_POTENTIAL"]
special=[x for x in glob if flag[x["shape"]*8]&0x80]
assert len(special)==2360 and {x["shape"] for x in special}=={347}
assert len([x for x in glob if x["glob_id"]==218 and x["shape"]==347])==24
assert all((struct.unpack_from("<I",meta,x["shape"]*13)[0]&mask)==0 for x in special)
paired=[]
for ordinal in (2378,2379):
 subset=[x for x in glob if x["glob_id"]==218 and x["definition_ordinal"]==ordinal]
 assert collections.Counter(x["shape"] for x in subset)=={347:12,128:4}
 pair=[]
 for member in (0,12):
  x=next(q for q in subset if q["glob_member"]==member)
  pair.append({
    "source_instance_id":x["instance_id"],"shape":x["shape"],
    "source_member_offset":x["source_member_raw_offset"],
    "typeflag_bit7":bool(flag[x["shape"]*8]&0x80),
    "original_USECODE_metadata_mask":hex(info(x["shape"])["flags"]&mask),
    "own_USECODE_code_length":entries[x["shape"]][1],
    "native_runtime_handle":"UNOBSERVED",
    "area_activation":"UNOBSERVED"
  })
 paired.append({"fixed_marker":f"fixed:m5:r{ordinal}","glob_id":218,"pair":pair})

report={
 "schema":"OpenUltima8.UsecodeShape347BoundedNegativeBranch.v1",
 "inputs_sha256":{
  "U8.EXE":SHA(b),"EUSECODE.FLX":SHA(flx),
  "TYPEFLAG.DAT":SHA(flag),"Map5SourceIR":SHA(rawmap)
 },
 "byte_slice_NE126_c73_ced_sha256":SHA(code),
 "source_opcode_checks":checks,
 "entry1_record_stride":13,"entry1_record_count":1431,
 "tested_mask":hex(mask),"records_with_mask_and_code_cross_tab":[
  {"flag_mask_nonzero":a,"script_entry_nonzero":b,"count":n}
  for (a,b),n in sorted(cross.items())],
 "record_shape347":r347,"record_shape128":r128,"positive_control_shape59":r59,
 "Map5_special_potential_count":2360,"matched_special_shapes":[347],
 "original_GLOB218_pair":paired,
 "source_default_negative_effect":"For shape347 and unmodified source FLX member1, test at NE126:c8c yields zero, jumps c90→ce9 returning AL0 BEFORE conditional NE126:ced secondary allocation.",
 "source_value_mutation_scope":"NE126:cd1/ce2 write to caller-provided output pointer loaded from BP+0x10, NOT into the usecode table that was previously in ES:BX. This is a specific alias correction, not a global absence-of-writes proof.",
 "qualifications":[
  "Original USECODE data may be changed/replaced indirectly at runtime; no memory readback",
  "Source FLX per-shape entry 347 absent does not prove absence of other world/VM callbacks",
  "Earlier state mutations and object placement are independent of secondary allocation",
  "No original game instructions, runtime graphics or fidelity capture executed"
 ],
 "game_instruction_tests":0,"runtime_fidelity_verified":False
}
path=HERE/"U8_SHAPE347_MASK_AND_ALIAS_GATE.json"
blob=(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
if path.exists():assert path.read_bytes()==blob,("REPORT_OUTPUT_CONFLICT",path)
else:
 with path.open("xb") as f:f.write(blob)
print(json.dumps({
 "status":"PASS_SOURCE_U8_SPECIAL_BRANCH_NEGATIVE_AND_OUTPUT_ALIAS_CORRECTION",
 "source_records":1431,"mask_positive_controls":103,
 "shape347_default_mask":0,"shape347_own_script_length":0,
 "special_map5_potential_children":2360,
 "source_opcode_checks":len(checks),
 "source_code_mask_vs_script_cross_tab":dict((str(k),v) for k,v in cross.items()),
 "output_sha256":SHA(blob),
 "original_game_tests":0
},sort_keys=True))
