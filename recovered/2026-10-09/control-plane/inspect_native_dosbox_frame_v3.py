from pathlib import Path
from PIL import Image,ImageStat
import json
root=Path(__file__).resolve().parents[2]
d=root/"runtime-test"/"results"/"openzork-native-dosbox-passive-ca496ab07"/"fidelity-isolated"/"capture"
with Image.open(d/"frame-0001.bmp") as i:
 im=i.convert("RGB");out=d/"frame-0001.png";im.save(out)
 stat=ImageStat.Stat(im)
 print(json.dumps({"image":str(out),"size":[im.width,im.height],"mean":[round(x,1) for x in stat.mean],"stddev":[round(x,1) for x in stat.stddev]}))
