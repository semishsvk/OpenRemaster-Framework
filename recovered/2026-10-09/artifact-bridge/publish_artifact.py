import argparse,hashlib,json,mimetypes,pathlib,shutil,time
ap=argparse.ArgumentParser(); ap.add_argument('file'); ap.add_argument('--project',required=True); ap.add_argument('--kind',default='artifact'); ap.add_argument('--classification',default='UNVERIFIED'); a=ap.parse_args()
src=pathlib.Path(a.file).resolve(); root=pathlib.Path(r'F:\Remaster Framework\orchestrator\artifact-bridge'); data=src.read_bytes(); sha=hashlib.sha256(data).hexdigest(); ext=src.suffix.lower(); dst=root/'store'/sha[:2]/(sha+ext); dst.parent.mkdir(parents=True,exist_ok=True)
if not dst.exists(): shutil.copy2(src,dst)
m={'schema':'OpenRemaster.ArtifactBridge.v1','project':a.project,'kind':a.kind,'classification':a.classification,'source_path':str(src),'artifact_path':str(dst),'name':src.name,'size':src.stat().st_size,'sha256':sha,'mime':mimetypes.guess_type(src.name)[0] or 'application/octet-stream','created_unix':int(time.time()),'fidelity_authority':False,'transport':'tailscale-private'}
mp=root/'manifests'/(sha+'.json'); mp.write_text(json.dumps(m,indent=2)); print(json.dumps(m))
