"""Verify actual relocated Stonekeep level callbacks; correct prior offset-only list."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys,struct
sys.path.insert(0,r"F:\Remaster Framework\output\projects\OpenStonekeep\evidence\20261008-094213__AUTONOMOUS-4H__cycle01")
from le_fixups import LE
from source_manifest import LEImage
b=Path(r"F:\Remaster Framework\source\Stonekeep\SK.EXE").read_bytes()
assert hashlib.sha256(b).hexdigest()=="5517ddeb49c7087d6b2449182020200c58084feb4cae55e31ac8acc6cdbdddd2"
le=LE(b);im=LEImage(b)
old_path=Path(r"F:\Remaster Framework\output\projects\OpenRemasterOrchestrator\reports\20261009-142406__PORTFOLIO-READONLY-CONTINUATION__cont15\STONEKEEP_ACTION0_LEVEL_CALLBACKS.json")
old=json.loads(old_path.read_text(encoding="utf-8"))
assert len(old["direct_global_level_callback_stores"])==22
def get_fixup(object_index,virtual_addr):
    obj=le.objects[object_index-1]
    page,src=le.page_for_object_offset(object_index,virtual_addr-obj["base"])
    xs=[f for f in le.parse_fixup_page(page) if src in f["sources"]]
    assert len(xs)==1,("SOURCE_FIXUP",object_index,hex(virtual_addr),len(xs))
    return xs[0]
writers=[]
for row in old["direct_global_level_callback_stores"]:
    va=int(row["writer_va"],16)
    f=get_fixup(1,va+6) # imm32 operand starts six bytes into C7 05 disp32 imm32
    assert f["target_kind"]==0 and f["target_object"]==1
    assert int(row["level_callback_target_va"],16)==f["target_offset"]
    real=le.objects[f["target_object"]-1]["base"]+f["target_offset"]
    first=im.read_va(real,1)[0]
    writers.append({"writer":va,"old_unrelocated_offset":hex(f["target_offset"]),
       "actual_callback_va":hex(real),"source_reloc_record":f["record_file_offset"],
       "initial_opcode_hex":hex(first),"ret_stub":first==0xc3})
assert len(writers)==22 and len({r["actual_callback_va"] for r in writers})==22
assert Counter(x["ret_stub"] for x in writers)=={True:20,False:2}
page,source=le.page_for_object_offset(3,0xf10e)
level_map=[]
for level in range(1,23):
    fs=[f for f in le.parse_fixup_page(page) if source+level*4 in f["sources"]]
    assert len(fs)==1
    f=fs[0];init=le.objects[f["target_object"]-1]["base"]+f["target_offset"]
    ws=[x for x in writers if init<=x["writer"]<init+32]
    assert len(ws)==1,("LEVEL_INIT_CALLBACK",level,hex(init),len(ws))
    row=ws[0]
    level_map.append({"level":level,"initializer":hex(init),
       "callback_va":row["actual_callback_va"],
       "callback_first_opcode":row["initial_opcode_hex"],
       "is_one_byte_RET_stub":row["ret_stub"],
       "initializer_relocation_file_offset":f["record_file_offset"],
       "callback_relocation_file_offset":row["source_reloc_record"]})
l15=level_map[14]
assert l15["initializer"]=="0x4f69a"
assert l15["callback_va"]=="0x4f861" and l15["is_one_byte_RET_stub"]
assert [(x["level"],x["callback_va"]) for x in level_map if not x["is_one_byte_RET_stub"]]==[(3,"0x61add"),(12,"0x6662a")]
receipt={
 "schema":"OpenStonekeep.LevelCallbackRelocationsCorrected.v1",
 "original_source_sha256":hashlib.sha256(b).hexdigest(),
 "prior_CONT15_file_sha256":hashlib.sha256(old_path.read_bytes()).hexdigest(),
 "correction":"Prior CONT15 values were raw object-1 offsets, NOT linear VAs; add object1 base 0x10000 as indicated by original LE relocation.",
 "object1_va_base":hex(le.objects[0]["base"]),
 "writer_count":22,"ret_stub_count":20,"nontrivial_callback_count":2,
 "per_level_map":level_map,
 "level15":l15,
 "h415_current_cell_handler":"0x4f983",
 "level15_global_callback":"0x4f861",
 "level15_callback_original_first_byte":"0xc3",
 "h415_action0_global_level_callback_direct_stage":False,
 "limitations":"Only proves immediate global callback RET at level15, not that other pre/post-handler helpers cannot reenter transition or change state.",
 "original_game_instructions_executed":0,
 "fidelity_verified":False
}
p=Path(__file__).with_name("STONEKEEP_CORRECTED_LEVEL_CALLBACKS.json")
data=json.dumps(receipt,indent=2,sort_keys=True)+"\n"
if p.exists():assert p.read_text(encoding="utf-8")==data
else:p.write_text(data,encoding="utf-8")
print(json.dumps({"status":"PASS_ORIGINAL_LE_RELOCATION_CALLBACK_MAPPING",
    "levels":22,"ret_stub_count":20,"nontrivial":2,
    "level15":l15,"nontrivial_levels":[x["level"] for x in level_map if not x["is_one_byte_RET_stub"]],
    "output_sha256":hashlib.sha256(p.read_bytes()).hexdigest()},sort_keys=True))
