"""Scope all direct U8 DS:88F6 references and pinned USECODE source mask."""
from pathlib import Path
import struct,json,hashlib,sys
from capstone import Cs,CS_ARCH_X86,CS_MODE_16
sys.path.insert(0,r"F:\Remaster Framework\output\projects\OpenUltima8\evidence\20261008-135657__AUTONOMOUS-4H-R2__cycle01")
from ne_glob_candidates import load
u8,ne,segments=load()
assert hashlib.sha256(u8).hexdigest()=="1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f"
assert struct.unpack_from("<H",u8,ne+14)[0]==148
asset=Path(r"F:\Remaster Framework\source\Ultima 8\ENGLISH\USECODE\EUSECODE.FLX")
flx=asset.read_bytes()
assert hashlib.sha256(flx).hexdigest()=="5eceb14286f06f6bb07c35d0c83c0670d500474cd9a7390ad533c0f0f93f4e38"
count=struct.unpack_from("<I",flx,0x54)[0]
assert count==1433
off,n=struct.unpack_from("<II",flx,0x88)
assert (off,n)==(0x12ce79,1431*13)
body=flx[off:off+n]
assert hashlib.sha256(body).hexdigest()=="90ff19c6191c75562cad773c01608d31a908a8157de05e7a21cd9e5ed5f9e6f6"
mask=0x000f8000
def rec(i):
    r=body[13*i:13*(i+1)]
    assert len(r)==13
    return {"shape":i,"flags":struct.unpack_from("<I",r)[0],
            "name":r[4:].split(b"\0",1)[0].decode("latin1"),
            "hex":r.hex()}
r128=rec(128);r347=rec(347);pos=rec(59)
assert r128["flags"]==0 and r347["flags"]==0x40 and r347["name"]=="CLRWATER"
assert (r347["flags"]&mask)==0
positive=[i for i in range(1431) if rec(i)["flags"]&mask]
assert len(positive)==103 and rec(positive[0])["flags"]&mask
matches=[]
for segment in segments:
    if segment["data_segment"] or segment["iterated"]:continue
    data=u8[segment["offset"]:segment["offset"]+segment["size"]]
    start=0
    while True:
        i=data.find(bytes.fromhex("f688"),start)
        if i<0:break
        matches.append({"segment":segment["index"],"operand_byte_offset":hex(i),
                        "near_hex":data[max(0,i-4):i+8].hex()})
        start=i+1
assert len(matches)==10
assert {x["segment"] for x in matches}=={9,55,125,126}
assert sum(x["segment"]==126 for x in matches)==6
assert sum(x["segment"]==125 for x in matches)==1
# Exact original instruction-bound sites in the only two source modules that
# legitimately dereference this absolute DS slot in known control flow.
md=Cs(CS_ARCH_X86,CS_MODE_16)
def first(segment,addr):
    s=segments[segment-1]
    return next(md.disasm(u8[s["offset"]+addr:s["offset"]+addr+14],addr))
real_sites=[
 (126,0xbb2,"mov","[0x88f6]","POINTER_WRITE_INITIALIZATION"),
 (126,0xbb5,"cmp","[0x88f6]","POINTER_NULL_CHECK"),
 (126,0xbd2,"push","[0x88f6]","POINTER_PASS_RESOURCE_METHOD"),
 (126,0xc73,"cmp","[0x88f6]","POINTER_NULL_CHECK"),
 (126,0xc82,"les","[0x88f6]","TABLE_ENTRY_READ"),
 (126,0xda2,"mov","[0x88f6]","TABLE_NAME_POINTER_CALCULATION"),
 (125,0x3bc,"mov","[0x88f6]","TABLE_NAME_POINTER_READ")
]
site_rows=[]
for seg,a,m,n,label in real_sites:
    q=first(seg,a)
    assert q.address==a and q.mnemonic==m and n in q.op_str,(seg,hex(a),q.mnemonic,q.op_str)
    site_rows.append({"segment":seg,"instruction":hex(a),"opcode":q.mnemonic+" "+q.op_str,
                      "type":label})
assert sum(x["type"]=="POINTER_WRITE_INITIALIZATION" for x in site_rows)==1
# Byte matches in NE9 and NE55 arise around BP-local F6 bytes; do NOT
# promote an arbitrary two-byte substring into an aligned DS reference.
result={
 "schema":"OpenUltima8.UsecodeTableDirectReferenceScope.v1",
 "source_exe_sha256":hashlib.sha256(u8).hexdigest(),
 "source_flx_sha256":hashlib.sha256(flx).hexdigest(),
 "source_flx_entry1_sha256":hashlib.sha256(body).hexdigest(),
 "source_flx_records":1431,
 "source_flx_positive_mask_controls":103,
 "shape128":r128,"shape347":r347,"positive_control":pos,
 "callback_gate_mask":hex(mask),"shape347_mask_result":hex(r347["flags"]&mask),
 "source_DS_pointer":"0x88f6","source_auto_data_segment":148,
 "all_literal_byte_matches":matches,"byte_match_count":10,
 "aligned_known_direct_use_sites":site_rows,"aligned_known_use_count":7,
 "aligned_direct_pointer_writes":1,
 "unpromoted_substrings_in_segments":[9,55],
 "limitations":"Byte-substring scan is not full x86 CFG/alias analysis. Indirect writes through the loaded pointer, vtable methods, VM action side-effects or runtime table replacement remain unverified.",
 "original_game_instruction_tests":0,
 "live_memory_readback":False,
 "runtime_fidelity_verified":False
}
out=Path(__file__).with_name("U8_USECODE_DIRECT_XREF_SCOPE.json")
blob=json.dumps(result,indent=2,sort_keys=True)+"\n"
if out.exists():assert out.read_text(encoding="utf-8")==blob
else:out.write_text(blob,encoding="utf-8")
print(json.dumps({"status":"PASS_SOURCE_DEFAULT_CAPABILITY_AND_DIRECT_XREF_SCOPE",
  "literal_hits":len(matches),"aligned_direct_uses":len(site_rows),
  "pointer_writes":1,"shape347_mask_result":0,
  "positive_controls":103,"source_sha256":hashlib.sha256(out.read_bytes()).hexdigest()},sort_keys=True))
