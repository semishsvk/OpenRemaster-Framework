"""Original MDK LEVEL3 plane→triangle dual-range audit.

Read-only original retail MTO + historical source-derived indices; independently
verify section offsets, field widths, range coverage and plane/triangle relation.
No game instruction emulation or writes to canonical corpus/worktrees.
"""
from pathlib import Path
import hashlib,json,struct,math,collections
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
MTO=ROOT/"source/MDK/TRAVERSE/LEVEL3/LEVEL3O.MTO"
MANIFEST=ROOT/"work/OpenMDK1/evidence/level3_world_manifest.json"
SHA=lambda b:hashlib.sha256(b).hexdigest()
b=MTO.read_bytes()
assert SHA(b)=="6f33536701f57a404f8b25aa5580502cd68389de9ae591b53b018f415f7193ff"
mr=MANIFEST.read_bytes()
manifest=json.loads(mr.decode("utf-16") if mr[:2] in (b"\xff\xfe",b"\xfe\xff") else mr.decode("utf-8-sig"))
assert manifest["source_sha256"]==SHA(b)
part_meta={x["hmo"]:x for x in manifest["parts"]}
count=struct.unpack_from("<I",b,20)[0]
assert count==10 and len(part_meta)==10
entries=[]
for i in range(count):
 q=24+i*12
 name=b[q:q+8].split(b"\0",1)[0].decode("ascii")
 block=struct.unpack_from("<I",b,q+8)[0]
 end=struct.unpack_from("<I",b,24+(i+1)*12+8)[0] if i+1<count else len(b)
 assert 0<=block<end<=len(b)
 entries.append((name,block,end))
out=[]
for name,base,end in entries:
 m=part_meta[name]
 h=b[base:end]
 pn=m["planes"]
 p0=m["plane_start"]
 assert pn>0 and pn*44+p0+4<len(h),("PLANE_RANGE_BOUND",name)
 def plane(k):
  q=p0+44*k
  return {
   "normal_xyz":list(struct.unpack_from("<3f",h,q)),
   "plane_d":struct.unpack_from("<f",h,q+12)[0],
   "primary_start":struct.unpack_from("<H",h,q+22)[0],
   "primary_count":struct.unpack_from("<H",h,q+20)[0],
   "second_start":struct.unpack_from("<H",h,q+26)[0],
   "second_count":struct.unpack_from("<H",h,q+24)[0],
   "raw_record_sha256":SHA(h[q:q+44]),
   "original_absolute_offset":base+q
  }
 planes=[plane(i) for i in range(pn)]
 ntri=struct.unpack_from("<I",h,p0+pn*44)[0]
 assert ntri==m["triangles"],("TRIANGLE_COUNT_NOT_PINNED",name,ntri,m["triangles"])
 tri_base=p0+pn*44+4
 assert tri_base+ntri*36+4<=len(h)
 nvert=struct.unpack_from("<I",h,tri_base+ntri*36)[0]
 assert nvert==m["vertices"],("VERTEX_COUNT_NOT_PINNED",name,nvert,m["vertices"])
 occupancy=collections.defaultdict(list)
 primary_count=secondary_count=0
 alternate=[]
 suspect=[]
 for ix,p in enumerate(planes):
  norm=p["normal_xyz"]
  length2=sum(f*f for f in norm)
  if not (math.isfinite(length2) and 0.998<length2<1.002):
   suspect.append({"plane_index":ix,"reason":"UNIT_PLANE_NORMAL_NOT_IN_EXPECTED_RANGE","length2":length2})
  for kind in ("primary","second"):
   start=p[kind+"_start"];n=p[kind+"_count"]
   if n==0:
    if kind=="second" and start!=65535:suspect.append({"plane_index":ix,"reason":"ZERO_SECOND_COUNT_NON_SENTINEL_START","start":start})
    continue
   if start+n>ntri:
    suspect.append({"plane_index":ix,"reason":"OUT_OF_TRIANGLE_STREAM_BOUNDS","range":kind,"start":start,"count":n})
    continue
   for tri in range(start,start+n):
    occupancy[tri].append((ix,kind))
   if kind=="primary":primary_count+=n
   else:secondary_count+=n
  if p["second_count"]:
   alternate.append({"plane_index":ix,**p})
 missing=[i for i in range(ntri) if i not in occupancy]
 duplicates={str(k):v for k,v in occupancy.items() if len(v)>1}
 result={
  "hmo":name,"block_start":base,"block_end":end,
  "planes":pn,"triangles":ntri,"vertices":nvert,
  "plane_start_relative":p0,"plane_start_absolute":base+p0,
  "triangle_stream_absolute":base+tri_base,
  "primary_triangle_occurrences":primary_count,
  "secondary_triangle_occurrences":secondary_count,
  "total_triangle_occurrences":primary_count+secondary_count,
  "unique_triangle_indices_covered":len(occupancy),
  "coverage_ratio":len(occupancy)/ntri,
  "missing_triangle_indices":missing,
  "duplicate_triangle_indices":duplicates,
  "secondary_range_count":len(alternate),
  "secondary_ranges":alternate,
  "possible_format_problems":suspect
 }
 if name=="HMO_2":
  p=planes[0]
  assert p["normal_xyz"]==[0.0,1.0,0.0] and p["plane_d"]==-1046.0
  assert (p["primary_start"],p["primary_count"])==(0,6)
  fi=next((q for q in alternate if q["plane_index"]==128),None)
  assert fi and (fi["primary_start"],fi["primary_count"],fi["second_start"],fi["second_count"])==(249,1,250,6)
  assert not missing and not duplicates and primary_count==513 and secondary_count==6
  # Bind all 6 exact coplanar f3=-16 triangles to the original first plane.
  vbase=tri_base+ntri*36+4
  coords=[struct.unpack_from("<3f",h,vbase+j*12) for j in range(nvert)]
  six=[]
  for tri in range(6):
   tri_off=tri_base+tri*36
   rec=h[tri_off:tri_off+36]
   ia,ib,ic,rawf3=struct.unpack_from("<4H",rec)
   vs=[coords[z] for z in (ia,ib,ic)]
   assert all(y==1046.0 for x,y,z in vs)
   s=rawf3 if rawf3<32768 else rawf3-65536
   assert s==-16
   ax,ay,az=vs[0];bx,by,bz=vs[1];cx,cy,cz=vs[2]
   e1=(bx-ax,by-ay,bz-az);e2=(cx-ax,cy-ay,cz-az)
   cross=(e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0])
   area=math.sqrt(sum(v*v for v in cross))/2
   assert area>0 and cross[0]==0 and cross[2]==0 and cross[1]<0
   six.append({"triangle_index":tri,"original_record_absolute_offset":base+tri_off,
               "indices":[ia,ib,ic],"source_signed_f3":s,
               "source_sha256":SHA(rec),"vertices":vs,
               "cross_winding":cross,"area_source_units_squared":area})
  assert [q["area_source_units_squared"] for q in six]==[248.,284.,8.,24.,10.,30.]
  result["authentic_plane0_solid_black_patch"]={
    "plane_index":0,"plane_equation":"y-1046=0",
    "source_triangle_indices":list(range(6)),
    "triangles":six,
    "total_unsigned_area":sum(q["area_source_units_squared"] for q in six),
    "shared_indexed_palette_color":16,
    "source_winding_relation_to_plane_normal":"cross product points -Y; plane source normal +Y; no runtime culling conclusion"
  }
 out.append(result)
report={
 "schema":"OpenMDK1.LEVEL3DualTriangleRangeAudit.v1",
 "MTO_sha256":SHA(b),"input_historical_manifest_sha256":SHA(mr),
 "plane_record_stride_bytes":44,
 "triangle_record_stride_bytes":36,
 "source_plane_primary_fields":{"count_u16_offset":20,"start_u16_offset":22},
 "source_plane_secondary_fields":{"count_u16_offset":24,"start_u16_offset":26},
 "hmos":out,
 "total_source_triangles":sum(x["triangles"] for x in out),
 "total_source_planes":sum(x["planes"] for x in out),
 "total_covered_unique_triangles":sum(x["unique_triangle_indices_covered"] for x in out),
 "total_primary_records":sum(x["primary_triangle_occurrences"] for x in out),
 "total_secondary_records":sum(x["secondary_triangle_occurrences"] for x in out),
 "global_uncovered":sum(len(x["missing_triangle_indices"]) for x in out),
 "global_duplicate_coverage":sum(len(x["duplicate_triangle_indices"]) for x in out),
 "original_game_runtime_executed":False,
 "render_semantics_of_secondary_range":"UNVERIFIED; source structural grouping only",
 "purpose":"Normalize plane→triangle main and secondary range provenance in authentic WorldIR, without assuming renderer pass semantics"
}
p=HERE/"MDK_LEVEL3_PLANE_TRIANGLE_DUAL_RANGES.json"
data=(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
if p.exists():assert p.read_bytes()==data,("OUTPUT_CONFLICT",p)
else:
 with p.open("xb") as f:f.write(data)
print(json.dumps({
 "status":"PASS_ORIGINAL_MTO_PLANE_RANGE_STRUCTURAL_AUDIT",
 "hmos":[{k:x[k] for k in ("hmo","triangles","primary_triangle_occurrences","secondary_triangle_occurrences","unique_triangle_indices_covered","secondary_range_count")} for x in out],
 "total_source_triangles":report["total_source_triangles"],
 "uncovered":report["global_uncovered"],
 "duplicate":report["global_duplicate_coverage"],
 "alternate_ranges":sum(x["secondary_range_count"] for x in out),
 "HMO2_plane0_area":next(x for x in out if x["hmo"]=="HMO_2")["authentic_plane0_solid_black_patch"]["total_unsigned_area"],
 "report_sha256":SHA(data)
},sort_keys=True))
