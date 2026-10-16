from pathlib import Path
import subprocess
from scripts.local_preflight import collect

def g(repo: Path,*args):
    subprocess.run(["git","-C",str(repo),*args],check=True,capture_output=True,text=True)

def test_collect_is_read_only_and_detects_untracked(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir()
    g(repo,"init"); g(repo,"config","user.email","test@example.invalid"); g(repo,"config","user.name","Test")
    (repo/"tracked.txt").write_text("a",encoding="utf-8")
    g(repo,"add","tracked.txt"); g(repo,"commit","-m","baseline")
    before=g(repo,"rev-parse","HEAD").stdout.strip()
    (repo/"new.txt").write_text("wip",encoding="utf-8")
    payload=collect("p",repo,[])
    after=g(repo,"rev-parse","HEAD").stdout.strip()
    assert before==after
    assert payload["git"]["head"]==before
    assert payload["changes"]["untracked"]==["new.txt"]
    assert payload["safe_to_plan_sync"] is False

def test_collect_hashes_explicit_file_inputs(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir(); g(repo,"init")
    p=tmp_path/"input.bin"; p.write_bytes(b"abc")
    payload=collect("p",repo,[(str(p),"corpus")])
    assert payload["inputs"][0]["sha256"]=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
