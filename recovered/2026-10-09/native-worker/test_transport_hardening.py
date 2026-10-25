import json,hmac,hashlib,time,copy,sys
from pathlib import Path
from transport_contract import validate_envelope
root=Path(__file__).resolve().parent
job=json.loads(Path(r"F:\Remaster Framework\runtime-test\jobs\ORCH-K003-OpenAzrael-KG001.json").read_text())
job["job_id"]="transport-validation-canary-20261008"
key=b"contract-only-test-key-not-for-production-123456"
def sign(e):
 e=copy.deepcopy(e)
 raw=json.dumps({k:v for k,v in e.items() if k!="mac"},sort_keys=True,separators=(",",":")).encode()
 e["mac"]=hmac.new(key,raw,hashlib.sha256).hexdigest()
 return e
base={"schema":"NativeJobEnvelope.v1","audience":"HomePC-NativeWorker","timestamp":int(time.time()),"job":job}
tests={}
tests["valid"]=validate_envelope(sign(base),key)
bad=copy.deepcopy(base);bad["job"]["execution"]["project_path"]=r"C:\Windows"
tests["path_escape"]=validate_envelope(sign(bad),key)
bad=copy.deepcopy(base);bad["job"]["execution"]["args"]=["--script","res://evil.gd"]
tests["arbitrary_script"]=validate_envelope(sign(bad),key)
bad=copy.deepcopy(base);bad["job"]["execution"]["kind"]="executable_runtime"
tests["arbitrary_executable"]=validate_envelope(sign(bad),key)
tests["bad_mac"]=validate_envelope(sign(base),b"other-test-key-not-for-production-123456")
bad=copy.deepcopy(base);bad["timestamp"]=1
tests["expired"]=validate_envelope(sign(bad),key)
expect={"valid":"PASS","path_escape":"INVALID_PROJECT_PATH","arbitrary_script":"DISALLOWED_ARGUMENTS","arbitrary_executable":"DISALLOWED_EXECUTION","bad_mac":"BAD_MAC","expired":"EXPIRED"}
ok=tests==expect
print(json.dumps({"schema":"NativeTransportHardeningCanary.v1","status":"PASS" if ok else "FAIL","tests":tests},indent=2))
sys.exit(0 if ok else 1)
