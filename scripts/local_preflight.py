from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

def _git(repo: Path, *args: str, check: bool = True) -> str:
    cp = subprocess.run(["git","-C",str(repo),*args], text=True, capture_output=True)
    if check and cp.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout.strip()

def _lines(value: str) -> list[str]:
    return [x for x in value.splitlines() if x]

def _sha256_file(path: Path) -> str:
    h=sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def collect(project_id: str, repo: Path, inputs: list[tuple[str,str]]) -> dict:
    repo=repo.resolve()
    if not (repo/".git").exists() and not _git(repo,"rev-parse","--is-inside-work-tree",check=False):
        raise ValueError(f"not a git worktree: {repo}")
    head=_git(repo,"rev-parse","HEAD",check=False) or None
    branch=_git(repo,"branch","--show-current",check=False) or None
    upstream=_git(repo,"rev-parse","--abbrev-ref","--symbolic-full-name","@{u}",check=False) or None
    remotes=_lines(_git(repo,"remote","-v",check=False))
    worktrees=_lines(_git(repo,"worktree","list","--porcelain",check=False))
    staged=_lines(_git(repo,"diff","--cached","--name-only","--",check=False))
    unstaged=_lines(_git(repo,"diff","--name-only","--",check=False))
    untracked=_lines(_git(repo,"ls-files","--others","--exclude-standard",check=False))
    input_records=[]
    for raw,role in inputs:
        p=Path(raw).expanduser().resolve()
        input_records.append({"path":str(p),"role":role,"sha256":_sha256_file(p) if p.is_file() else None})
    return {
      "schema_version":"1.0","project_id":project_id,
      "captured_at":datetime.now(timezone.utc).isoformat(),
      "git":{"repo_path":str(repo),"branch":branch,"head":head,"upstream":upstream,"remotes":remotes},
      "worktrees":worktrees,
      "changes":{"staged":staged,"unstaged":unstaged,"untracked":untracked},
      "inputs":input_records,
      "safe_to_plan_sync": bool(head) and not staged and not unstaged
    }

def main() -> int:
    ap=argparse.ArgumentParser(description="Read-only OpenRemaster local preflight collector")
    ap.add_argument("--project-id",required=True)
    ap.add_argument("--repo",required=True,type=Path)
    ap.add_argument("--input",action="append",default=[],metavar="ROLE=PATH")
    ap.add_argument("--output",type=Path)
    ns=ap.parse_args()
    parsed=[]
    for item in ns.input:
        if "=" not in item: raise SystemExit("--input must be ROLE=PATH")
        role,path=item.split("=",1); parsed.append((path,role))
    payload=collect(ns.project_id,ns.repo,parsed)
    encoded=json.dumps(payload,sort_keys=True,indent=2)+"\n"
    if ns.output:
        ns.output.parent.mkdir(parents=True,exist_ok=True)
        ns.output.write_text(encoded,encoding="utf-8")
    else:
        print(encoded,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
