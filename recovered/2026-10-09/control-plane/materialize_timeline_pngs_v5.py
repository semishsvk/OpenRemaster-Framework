from pathlib import Path
from PIL import Image
import json
root=Path(__file__).resolve().parents[2]
base=root/"runtime-test"/"results"/"openzork-dosboxx-threepoint-c0b9fda589"/"fidelity-isolated"/"capture"
m=json.loads((base/"capture-attestation.json").read_text())
paths=[]
for row in m["frames"]:
 p=base/row["path"]
 o=p.with_suffix(".png")
 with Image.open(p) as im:im.save(o)
 paths.append(str(o))
print(json.dumps({"status":"DIAGNOSTIC_PNG_COPIES","paths":paths}))
