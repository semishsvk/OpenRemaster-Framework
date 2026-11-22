"""Synthetic 127.0.0.1 TCP connection client process PID verified via Windows table.
No DOSBox, no original game process or cursor/keyboard touched.
"""
import ast,socket,subprocess,sys,time,json
from pathlib import Path
from fidelity_mcp_peer_attestation_v8 import owning_pid_for_loopback_client
from fidelity_runtime_isolation_v1 import IsolationError,process_identity
CP=Path(__file__).resolve().parent
ast.parse((CP/"fidelity_mcp_peer_attestation_v8.py").read_text(encoding="utf-8"))
server=socket.socket()
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
server.bind(("127.0.0.1",0));server.listen(1);server.settimeout(5)
port=server.getsockname()[1]
client=None
try:
 script=("import socket,time;"
         f"s=socket.socket();s.connect(('127.0.0.1',{port}));"
         "time.sleep(12);s.close()")
 client=subprocess.Popen([sys.executable,"-B","-c",script],
    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 connected,peer=server.accept()
 actual=owning_pid_for_loopback_client(peer[1],port)
 assert actual==client.pid,(actual,client.pid)
 identity=process_identity(actual)
 assert identity and identity["pid"]==client.pid
 connected.close()
 print(json.dumps({"status":"PASS","port":port,"reported_owner_pid":actual,
     "actual_test_client_pid":client.pid,"owner_creation_ticks_100ns":identity["creation_ticks_100ns"],
     "new_original_game_processes":0}))
finally:
 server.close()
 if client and client.poll() is None:
  client.terminate()
  client.wait(timeout=4)
