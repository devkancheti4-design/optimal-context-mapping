"""Model D, cold: map the code as it stood before each fix, then ask the fix's question (scope code).
Run with the modeld venv's python. Uses only Model D's public build() and Workspace API, as its CLI does."""
import json, os, re, shutil, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from common import snapshot, ranked_code_files, score
from ocm.build import build
from ocm.server import Workspace

CITE = re.compile(r"(?m)^\s*\d+\.\s*\[([^\]]+?):(\d+)\]")

repo, qfile, out, work = sys.argv[1:5]
cache = os.path.join(work, "embed.sqlite")
Q = json.load(open(qfile))
rows = []
for i, q in enumerate(Q, 1):
    snap, ws = os.path.join(work, "snap", "repo"), os.path.join(work, "ws")
    snapshot(repo, q["parent"], snap)
    shutil.rmtree(ws, ignore_errors=True)
    t0 = time.time(); build([snap], ws, log=lambda *a: None, cache=cache); bt = time.time() - t0
    w = Workspace(ws)
    t0 = time.time(); text = w.handle("ask", {"question": q["question"], "scope": "code"}); qt = time.time() - t0
    files = ranked_code_files(p.split("/", 1)[1] if "/" in p else p for p, _ in CITE.findall(text))
    r = {"hash": q["hash"][:10], "question": q["question"], "gold": q["gold"], "files": files[:10],
         "tokens": len(text) // 4, "query_s": round(qt, 2), "build_s": round(bt, 1), **score(files, q["gold"])}
    rows.append(r)
    print(f"{i:>3}/{len(Q)} {'HIT1' if r['top1'] else ('top5' if r['top5'] else 'miss')} build {bt:5.1f}s  {q['question'][:70]}", flush=True)
    json.dump(rows, open(out, "w"), indent=1)
