"""Cross-verify HMO2 plane0 solid-index16 patch with original palette.

Sources: original LEVEL3O.MTO, MISC/mdkfont.fti, TRAVERSE/LEVEL3/LEVEL3.DTI.
No live camera, visibility or rendering is inferred or executed.
"""
from pathlib import Path
import hashlib,struct,json
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
SHA=lambda b:hashlib.sha256(b).hexdigest()
mto=(ROOT/"source/MDK/TRAVERSE/LEVEL3/LEVEL3O.MTO").read_bytes()
fti=(ROOT/"source/MDK/MISC/mdkfont.fti").read_bytes()
dti=(ROOT/"source/MDK/TRAVERSE/LEVEL3/LEVEL3.DTI").read_bytes()
assert SHA(mto)=="6f33536701f57a404f8b25aa5580502cd68389de9ae591b53b018f415f7193ff"
assert SHA(fti)=="4b821a9bc4b4fe74151543cd127061f67432b1e79dc769dab36c60ad4769ed9b"
assert SHA(dti)=="525c1cf9c13ffe78c19b167e78f9d824a4619adf30ce206b0bdba2b344809623"
r=HERE/"MDK_LEVEL3_PLANE_TRIANGLE_DUAL_RANGES.json"
j=json.loads(r.read_text(encoding="utf-8"))
h=next(x for x in j["hmos"] if x["hmo"]=="HMO_2")
patch=h["authentic_plane0_solid_black_patch"]
assert len(patch["triangles"])==6 and patch["source_triangle_indices"]==list(range(6))
assert patch["plane_equation"]=="y-1046=0" and patch["total_unsigned_area"]==604.0
assert all(x["source_signed_f3"]==-16 for x in patch["triangles"])
source_palette=fti[4:]
n=struct.unpack_from("<I",source_palette,0)[0]
index=[(source_palette[4+12*i:12+12*i].split(b"\0")[0].decode("ascii"),
        struct.unpack_from("<I",source_palette,12+12*i)[0])
        for i in range(n)]
ix=next(i for i,x in enumerate(index) if x[0]=="SYS_PAL")
sys_palette=source_palette[index[ix][1]:index[ix+1][1]]
assert len(sys_palette)==192 and SHA(sys_palette)=="145459d408e1cb8e7a9bbc6f83a5ae85d3be3390cb7a509b5c8df3160afada29"
dtiobj=dti[4:];ptr=struct.unpack_from("<I",dtiobj,0x1c)[0]
full_dti_palette=dtiobj[ptr+4:ptr+4+768]
assert len(full_dti_palette)==768
assert sys_palette==full_dti_palette[:192]
color_index=16
raw_rgb=sys_palette[color_index*3:color_index*3+3]
assert raw_rgb==bytes([0,0,0])
plane0_abs=h["plane_start_absolute"]
raw_plane0=mto[plane0_abs:plane0_abs+44]
assert tuple(struct.unpack_from("<4f",raw_plane0,0))==(0.0,1.0,0.0,-1046.0)
assert struct.unpack_from("<H",raw_plane0,20)[0]==6
assert struct.unpack_from("<H",raw_plane0,22)[0]==0
tri_base=h["triangle_stream_absolute"]
for index,tri in enumerate(patch["triangles"]):
 original=mto[tri_base+36*index:tri_base+36*(index+1)]
 assert SHA(original)==tri["source_sha256"]
 assert tri["area_source_units_squared"]>0
assert sum(t["area_source_units_squared"] for t in patch["triangles"])==604.0
report={
 "schema":"OpenMDK1.AuthenticHMO2Plane0SolidPalettePatch.v1",
 "original_sources_sha256":{
  "LEVEL3O.MTO":SHA(mto),"mdkfont.fti":SHA(fti),"LEVEL3.DTI":SHA(dti)
 },
 "plane_range_audit_sha256":SHA(r.read_bytes()),
 "hmo":"HMO_2","source_plane_index":0,"original_plane_va_file_offset":plane0_abs,
 "original_plane_record_sha256":SHA(raw_plane0),
 "source_plane_equation":"y-1046=0",
 "original_triangle_indices":[0,1,2,3,4,5],
 "original_triangle_record_SHA256":[x["source_sha256"] for x in patch["triangles"]],
 "source_all_six_signed_f3":-16,
 "source_all_six_palette_index":16,
 "source_triangle_total_unsigned_area":604.0,
 "original_palette_authority":"mdkfont.fti SYS_PAL first64, independently equals LEVEL3.DTI first64",
 "system_palette_sha256":SHA(sys_palette),
 "palette_index_16_rgb888":list(raw_rgb),
 "palette_index_16_rgb_hex":"#000000",
 "source_planar_winding":"all six source triangle cross products point -Y, source plane normal +Y; no runtime front-face conclusion",
 "unverified":["live camera and projection","view frustum and clipping","backface visibility","original 8-bit frame buffer","palette state at exact frame","runtime pixel comparison"],
 "game_instructions_executed":0,"runtime_fidelity_verified":False
}
out=HERE/"MDK_HMO2_PLANE0_SOLID_PATCH.json"
data=(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode()
if out.exists():assert out.read_bytes()==data
else:
 with out.open("xb") as f:f.write(data)
print(json.dumps({"status":"PASS_SOURCE_PLANE0_SIX_TRIANGLES_AND_SYS_PAL_COLOR",
 "source_triangles":6,"source_area":604,"palette_index":16,"RGB":[0,0,0],
 "palette_cross_check":True,"output_sha256":SHA(data)},sort_keys=True))
