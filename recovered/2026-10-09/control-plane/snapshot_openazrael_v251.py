from pathlib import Path
import hashlib,json,datetime,platform
r=Path(r"F:\Remaster Framework\work\OpenAzrael")
exclude={".godot",".tmp","build",".source"}
rows=[]
for p in sorted(r.rglob("*")):
 if not p.is_file(): continue
 rel=p.relative_to(r)
 if rel.parts and rel.parts[0] in exclude: continue
 b=p.read_bytes(); rows.append({"path":rel.as_posix(),"size":len(b),"sha256":hashlib.sha256(b).hexdigest()})
tree=hashlib.sha256()
for x in rows: tree.update(f'{x["path"]}|{x["size"]}|{x["sha256"]}\n'.encode())
out={"schema":"RehydrationContract.v1","project":"OpenAzrael","checkpoint":"candidate-v251-local-baseline","created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_baseline":"candidate-v250 + current local deltas","file_count":len(rows),"tree_sha256":tree.hexdigest(),"excluded":[".godot",".tmp","build",".source"],"inputs":rows,"tool_runtime_fingerprint":{"machine":platform.node(),"os":platform.platform(),"python":platform.python_version(),"godot":"4.7.2.stable.official.ed1daf0bf"},"restore_recipe":["restore every inputs[] path byte-for-byte into an empty workspace","verify each SHA-256 and tree_sha256","regenerate disposable .godot/import cache","run ORCH-K003 KG001 deterministic headless smoke"],"smoke_job":"ORCH-K003-OpenAzrael-KG001.json"}
q=r/"REHYDRATION_MANIFEST_V251.json";q.write_text(json.dumps(out,indent=2),encoding="utf-8");print(json.dumps({"file_count":len(rows),"tree_sha256":out["tree_sha256"],"manifest":str(q)}))
