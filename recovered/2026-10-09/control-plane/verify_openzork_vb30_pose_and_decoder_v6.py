"""Original Zork save LOC scene/camera view and existing TGZ decoder integrity.
Authoritative source and save are read only; decoded bytes are compared in-memory to prior PPM.
"""
import json,struct,hashlib,re
from pathlib import Path
R=Path(__file__).resolve().parents[2]
SAVE=R/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"saves"/"znemesis.000"
SOURCE=R/"source"/"Zork Nemesis"/"DATA2"/"ZASSETS"/"CONSERV"/"VB30S11C.TGA"
PPM=R/"work"/"OpenZork"/"runtime"/"assets"/"VB30S11C.ppm"
out=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
s=SAVE.read_bytes()
assert s[:4]==b"ZNSG","BAD_SAVE_MAGIC"
major=struct.unpack_from("<I",s,4)[0]
offset=12
tag=s[offset:offset+4]
length=struct.unpack_from("<I",s,offset+4)[0]
assert tag==b"LOC " and length==8
loc=s[offset+8:offset+12].decode("ascii")
view=struct.unpack_from("<I",s,offset+12)[0]
assert re.fullmatch(r"[a-z]{2}\d{2}",loc),loc
assert 0<=view<1440,view
assert loc=="vb30" and view==1058,(loc,view)

b=SOURCE.read_bytes()
magic,opaque,w,h=struct.unpack_from("<4sIii",b,0)
assert (magic,w,h)==(b"TGZ\0",320,1440),(magic,w,h)
# Exact reuse of the previously verified ZVision TGZ LZSS + RGB555 decoder, in-memory only.
stream=b[16:];ring=bytearray(4096);pos=0xfee;cursor=0;decoded=bytearray();limit=w*h*2
while cursor<len(stream) and len(decoded)<limit:
 flags=stream[cursor];cursor+=1
 for bit in range(8):
  if cursor>=len(stream) or len(decoded)>=limit:break
  if flags&(1<<bit):
   value=stream[cursor];cursor+=1;decoded.append(value);ring[pos]=value;pos=(pos+1)&0xfff
  else:
   if cursor+1>=len(stream):break
   lo=stream[cursor];hi=stream[cursor+1];cursor+=2
   offset=lo|((hi&0xf0)<<4);count=(hi&0xf)+3
   for j in range(count):
    value=ring[(offset+j)&0xfff]
    decoded.append(value);ring[pos]=value;pos=(pos+1)&0xfff
    if len(decoded)>=limit:break
assert len(decoded)==limit,(len(decoded),limit)
rgb=bytearray(w*h*3)
for i in range(w*h):
 value=decoded[2*i]|(decoded[2*i+1]<<8)
 rgb[i*3:i*3+3]=bytes((
    (value&31)*255//31,((value>>5)&31)*255//31,
    ((value>>10)&31)*255//31))
ppm_data=("P6\n%d %d\n255\n"%(w,h)).encode()+rgb
ppm_actual=PPM.read_bytes()
match=ppm_data==ppm_actual
result={
 "schema":"OpenZork.VB30SeededScenePoseAndDecoder.v1",
 "status":"SAVE_LOCATION_AND_TGZ_DECODER_BYTE_MATCH_PASS" if match else "PPM_DECODER_MISMATCH_HOLD",
 "corpus_read_only":True,
 "save_path":str(SAVE),"save_sha256":hashlib.sha256(s).hexdigest(),
 "save_magic":"ZNSG","save_version":major,
 "location_tag":"LOC ","location_chunk_length":length,
 "location_key":loc.upper(),"view_coordinate":view,
 "panorama_period":1440,
 "location_source_path":str(SOURCE),"location_source_sha256":hashlib.sha256(b).hexdigest(),
 "source_native_magic":"TGZ", "native_TGZ_dimensions":[w,h],
 "decoded_raw_rgb555_bytes":len(decoded),
 "decoded_ppm_sha256":hashlib.sha256(ppm_data).hexdigest(),
 "preexisting_ppm_path":str(PPM),
 "preexisting_ppm_sha256":hashlib.sha256(ppm_actual).hexdigest(),
 "decoded_ppm_matches_preexisting":match,
 "source_location":"DATA2/ZASSETS/CONSERV",
 "different_from_r29_temple_TA30":True,
 "original_reconstruction_fidelity":"NOT_VERIFIED"}
p=out/"vb30-save-scene-pose-and-decoder-v6.json"
p.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":result["status"],
 "save_location":loc,"view_coordinate":view,"save_sha256":result["save_sha256"],
 "source_tgz_sha256":result["location_source_sha256"],
 "decoded_ppm_matches_preexisting":match,
 "original_runtime_scene":"CONSERV/VB30",
 "evidence":str(p)},ensure_ascii=False))
raise SystemExit(0 if match else 1)
