import json

def accept(job, validation):
    failures=[]
    if validation.get("schema")!="ORCH-K003.ValidationResult.v1":
        failures.append("VALIDATION_SCHEMA_INVALID")
    if validation.get("status")!="PASS":
        failures.append("VALIDATION_NOT_PASS")
    required=job.get("acceptance",{}).get("require_validation_pass",True)
    if required and validation.get("status")!="PASS":
        failures.append("REQUIRED_VALIDATION_FAILED")
    return {"schema":"ORCH-K003.AcceptanceResult.v1",
            "status":"PASS" if not failures else "FAIL",
            "failures":failures,
            "validation_status":validation.get("status")}
