import json,hmac,hashlib,time,sys
from transport_contract import validate_envelope
key=b"test-key-not-production"
job={"schema":"ORCH-K003.Job.v1","job_id":"transport-contract-test","execution":{"kind":"godot_runtime"}}
e={"schema":"NativeJobEnvelope.v1","audience":"HomePC-NativeWorker","timestamp":int(time.time()),"job":job}
payload=json.dumps(e,sort_keys=True,separators=(",",":")).encode()
e["mac"]=hmac.new(key,payload,hashlib.sha256).hexdigest()
rows={"valid":validate_envelope(e,key),"bad_key":validate_envelope(e,b"other"),"expired":validate_envelope({**e,"timestamp":1},key),"bad_audience":validate_envelope({**e,"audience":"other"},key)}
ok=rows=={"valid":"PASS","bad_key":"BAD_MAC","expired":"EXPIRED","bad_audience":"INVALID_AUDIENCE"}
print(json.dumps({"schema":"NativeTransportContractCanary.v1","status":"PASS" if ok else "FAIL","cases":rows},indent=2))
sys.exit(0 if ok else 1)
