"""Read original LEVEL3 MTO and prove one real triangle record."""
from pathlib import Path
import math,struct,hashlib,json
p=Path(r"F:\Remaster Framework\source\MDK\TRAVERSE\LEVEL3\LEVEL3O.MTO")
b=p.read_bytes()
assert hashlib.sha256(b).hexdigest()=="6f33536701f57a404f8b25aa5580502cd68389de9ae591b53b018f415f7193ff"
count=struct.unpack_from("<I",b,20)[0]
blocks=[]
for i in range(count):
  q=24+i*12
  name=b[q:q+8].split(b"\0",1)[0].decode("ascii")
  s=struct.unpack_from("<I",b,q+8)[0]
  e=struct.unpack_from("<I",b,24+(i+1)*12+8)[0] if i+1<count else len(b)
  blocks.append((name,s,e))
name,start,end=next(row for row in blocks if row[0]=="HMO_2")
h=b[start:end]
geom=struct.unpack_from("<I",h,12)[0]
def ok(off):
  x,y,z,d=struct.unpack_from("<4f",h,off)
  n=x*x+y*y+z*z
  return all(math.isfinite(v) for v in (x,y,z,d)) and .999<n<1.001 and abs(d)<10000
best=[]
for phase in range(44):
  found=[o for o in range(geom+phase,len(h)-44,44) if ok(o)]
  if len(found)>len(best):best=found
assert best
plane_start=best[0];nplanes=0
while plane_start+(nplanes+1)*44<len(h) and ok(plane_start+nplanes*44):
  nplanes+=1
pend=plane_start+nplanes*44
ntri=struct.unpack_from("<I",h,pend)[0]
tbase=pend+4
vpos=tbase+ntri*36
nverts=struct.unpack_from("<I",h,vpos)[0]
vbase=vpos+4
assert (ntri,nverts)==(519,295)
tri=h[tbase:tbase+36]
a,b0,c,u=struct.unpack_from("<4H",tri)
signed=u if u<0x8000 else u-0x10000
assert (a,b0,c,u)==(125,98,116,65520)
vertices=[]
for idx in (a,b0,c):
  coord=struct.unpack_from("<3f",h,vbase+idx*12)
  raw=h[vbase+idx*12:vbase+(idx+1)*12]
  vertices.append({"index":idx,"coordinates":list(coord),"original_bytes_sha256":hashlib.sha256(raw).hexdigest()})
record={
 "schema":"OpenMDK1.LEVEL3AuthenticTriangleSourceFixture.v1",
 "project":"OpenMDK1","game_source_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
 "hmo":name,"container_start":start,"container_end":end,
 "plane_start_relative":plane_start,"plane_count":nplanes,
 "triangle_count":ntri,"vertex_count":nverts,
 "triangle_index":0,
 "triangle_record_absolute_offset":start+tbase,
 "triangle_record_hex":tri.hex(),"triangle_record_sha256":hashlib.sha256(tri).hexdigest(),
 "indices":[a,b0,c],"signed_f3":signed,
 "original_source_vertices":vertices,
 "source_scope":"Authored original MTO source fields, not renderer/runtime projections or a clipped replay",
 "runtime_camera":"UNBOUND","projected_uv":"UNBOUND","clipped_polygon":"UNEXECUTED",
 "raster_profile":"UNOBSERVED","fidelity":"NOT_VERIFIED"
}
dest=Path(__file__).with_name("MDK_LEVEL3_TRIANGLE_SOURCE_FIXTURE.json")
encoded=json.dumps(record,indent=2,sort_keys=True)+"\n"
if dest.exists():assert dest.read_text(encoding="utf-8")==encoded
else:dest.write_text(encoded,encoding="utf-8")
print(json.dumps({"status":"PASS_DIRECT_ORIGINAL_MTO_TRIANGLE_BYTES",
  "hmo":name,"triangle":0,"signed_f3":signed,"triangle_sha256":record["triangle_record_sha256"],
  "offset":record["triangle_record_absolute_offset"],"vertices":record["original_source_vertices"]},sort_keys=True))
