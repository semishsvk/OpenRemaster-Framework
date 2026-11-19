"""Read-only admission validation of private DOSBox configuration template."""
from pathlib import Path
import tempfile,json,sys
from fidelity_runtime_isolation_v1 import IsolationError,validate_private_runtime_config
ROOT=Path(__file__).resolve().parents[2]
cfg=Path(__file__).parent/"examples"/"OpenZork-dosbox-fidelity-seed.conf"
source=ROOT/"source"
assert cfg.exists()
with tempfile.TemporaryDirectory(dir=ROOT/"runtime-test"/"results",prefix="orf-config-canary-") as td:
    r=Path(td)
    for x in ("config","capture","overlay","saves"): (r/x).mkdir()
    dst=r/"config"/"runtime.conf"
    text=cfg.read_text(encoding="utf-8")
    for name,path in {"capture_dir":r/"capture","private_overlay":r/"overlay"}.items():
        text=text.replace("{"+name+"}",str(path))
    dst.write_text(text)
    args=["-conf",str(dst),"-noconsole"]
    validate_private_runtime_config("dosbox",args,dst,r/"saves",source)
    altered=text.replace(" -ro\n","\n")
    dst.write_text(altered)
    try:
        validate_private_runtime_config("dosbox",args,dst,r/"saves",source)
        raise AssertionError("Writable source mount was permitted")
    except IsolationError as e:
        assert e.reason=="SOURCE_MOUNT_NOT_READ_ONLY",e.reason
    dst.write_text(text.replace(str(r/"capture"),str(ROOT/"work"/"OpenZork"/"oracle"/"capture")))
    try:
        validate_private_runtime_config("dosbox",args,dst,r/"saves",source)
        raise AssertionError("Shared capture path was permitted")
    except IsolationError as e:
        assert e.reason=="DOSBOX_CAPTURE_OUTSIDE_PRIVATE_RUN",e.reason
print(json.dumps({"schema":"OpenRemaster.FidelityPrivateDOSBoxConfigCanary.v1","status":"PASS","tested":["private_overlay","read_only_source","capture_directory_isolation"]}))
