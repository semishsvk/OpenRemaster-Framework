extends Node

func _ready():
    var evidence = {
        "schema": "RuntimeSmokeEvidence.v1",
        "status": "PASS",
        "engine": Engine.get_version_info(),
        "os_name": OS.get_name(),
        "processor_count": OS.get_processor_count(),
        "capture_authority": "LOCAL_RUNTIME_FILE_OUTPUT_ONLY"
    }
    var f = FileAccess.open("user://runtime-smoke.json", FileAccess.WRITE)
    f.store_string(JSON.stringify(evidence, "  "))
    f.close()
    print("OPENREMASTER_RUNTIME_SMOKE_PASS")
    get_tree().quit(0)
