"""Windows localhost DOSBox-X MCP socket peer -> *actual supervised GUI PID* attestation.
Cannot replace independent game-fidelity validation. Only used for experimental diagnostics.
"""
import subprocess,json,time,hashlib
from pathlib import Path
from fidelity_runtime_isolation_v1 import IsolationError,process_identity,sha256

ROOT=Path(__file__).resolve().parents[2]
OWNER=ROOT/"orchestrator"/"control-plane"/"state"/"fidelity-homepc-owner.json"

def owning_pid_for_loopback_client(peer_port,server_port):
    p=int(peer_port);s=int(server_port)
    if not 1024<=p<=65535 or not 1024<=s<=65535 or p==s:
        raise IsolationError("MCP_PEER_PORT_INVALID")
    powershell=(
        "$rows = @(Get-NetTCPConnection -State Established "
        f"-LocalPort {p} -RemotePort {s} -ErrorAction Stop | "
        "Where-Object { $_.LocalAddress -eq '127.0.0.1' -and "
        "$_.RemoteAddress -eq '127.0.0.1' }); "
        "$rows | Select-Object OwningProcess,LocalPort,RemotePort | ConvertTo-Json -Compress"
    )
    try:
        result=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",powershell],
            capture_output=True,text=True,timeout=10)
    except (subprocess.TimeoutExpired,OSError) as e:
        raise IsolationError("MCP_TCP_OWNER_QUERY_FAILED",{"type":type(e).__name__})
    if result.returncode:
        raise IsolationError("MCP_TCP_OWNER_QUERY_FAILED",{"stderr_tail":result.stderr[-600:]})
    try:rows=json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:raise IsolationError("MCP_TCP_OWNER_RESULT_NOT_JSON")
    if isinstance(rows,dict):rows=[rows]
    if len(rows)!=1:
        raise IsolationError("MCP_TCP_OWNER_NOT_UNIQUE",{"matches":len(rows)})
    pid=int(rows[0]["OwningProcess"])
    if pid<=0:raise IsolationError("MCP_TCP_OWNER_PID_INVALID")
    return pid

def assert_supervised_mcp_peer(job_id,accepted_peer_ip,accepted_peer_port,server_port,base,expected_exe_sha):
    """Fail closed before debugger guest-input injection.
    Client TCP ownership verified against exact launched process with PID/starttime and lease epoch.
    """
    if accepted_peer_ip!="127.0.0.1":
        raise IsolationError("MCP_PEER_ADDRESS_NOT_LOCAL")
    base=Path(base)
    identity_file=base/"fidelity-isolated"/"runtime-identity.json"
    if not identity_file.is_file():
        raise IsolationError("MCP_SUPERVISED_RUNTIME_NOT_BOUND")
    data=json.loads(identity_file.read_text(encoding="utf-8-sig"))
    if data.get("schema")!="FidelityRuntimeIdentity.v1":
        raise IsolationError("MCP_RUNTIME_IDENTITY_SCHEMA_INVALID")
    ident=data.get("process") or {}
    token=data.get("run_token")
    if not token or not ident.get("pid") or not ident.get("creation_ticks_100ns"):
        raise IsolationError("MCP_RUNTIME_IDENTITY_INCOMPLETE")
    if ident.get("executable_sha256")!=expected_exe_sha:
        raise IsolationError("MCP_EXECUTABLE_HASH_WRONG")
    owner_pid=owning_pid_for_loopback_client(accepted_peer_port,server_port)
    if int(ident["pid"])!=owner_pid:
        raise IsolationError("MCP_SOCKET_BELONGS_TO_FOREIGN_RUNTIME",
                             {"expected":ident["pid"],"tcp_process":owner_pid})
    live=process_identity(owner_pid)
    if not live or live["creation_ticks_100ns"]!=ident["creation_ticks_100ns"]:
        raise IsolationError("MCP_PROCESS_CREATION_IDENTITY_MISMATCH")
    if sha256(live["executable"])!=expected_exe_sha:
        raise IsolationError("MCP_RUNTIME_LIVE_EXECUTABLE_HASH_CHANGED")
    if not OWNER.is_file():
        raise IsolationError("MCP_ACTIVE_LEASE_NOT_RECORDED")
    lease=json.loads(OWNER.read_text(encoding="utf-8-sig"))
    if lease.get("status")!="RUNNING" or lease.get("epoch")!=token or lease.get("job_id")!=job_id:
        raise IsolationError("MCP_ACTIVE_GUI_LEASE_NOT_MATCHED",
                             {"lease_state":lease.get("status")})
    if lease.get("runtime_pid")!=owner_pid:
        raise IsolationError("MCP_LEASE_RUNTIME_PID_CHANGED")
    return {"schema":"OpenRemaster.MCPPeerPIDBindingAttestation.v1",
            "status":"PASS_EXACT_TCP_PID_CREATION_HASH_AND_LEASE",
            "job_id":job_id,"runtime_pid":owner_pid,
            "runtime_creation_ticks":ident["creation_ticks_100ns"],
            "executable_sha256":expected_exe_sha,
            "lease_epoch":token,"local_peer_port":int(accepted_peer_port),
            "local_server_port":int(server_port),
            "identity_provenance_sha256":sha256(identity_file),
            "global_input_used":False,
            "fidelity_verification":False}
