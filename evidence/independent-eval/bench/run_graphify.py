"""Graphify: rebuild the AST graph (no LLM) for the code before each fix, then `graphify query` the fix's question.
Files are ranked in the order Graphify prints its nodes (seeds first, then by hop distance), its default 2,000-token budget."""
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from common import snapshot, ranked_code_files, score

GRAPHIFY = "~/eval/envs/graphify/bin/graphify"
SRC = re.compile(r"\[src=([^ \]]*)")
env = {**os.environ, "GRAPHIFY_QUERY_LOG_DISABLE": "1", "GRAPHIFY_BACKEND": "none"}

repo, qfile, out, work = sys.argv[1:5]
budget = sys.argv[5] if len(sys.argv) > 5 else "2000"
Q = json.load(open(qfile))
rows = []
for i, q in enumerate(Q, 1):
    snap = os.path.join(work, "snap")
    snapshot(repo, q["parent"], snap, keep=("graphify-out",))
    t0 = time.time()
    b = subprocess.run([GRAPHIFY, "update", ".", "--force"], cwd=snap, capture_output=True, text=True, env=env)
    bt = time.time() - t0
    t0 = time.time()
    p = subprocess.run([GRAPHIFY, "query", q["question"], "--budget", budget, "--graph", "graphify-out/graph.json"],
                       cwd=snap, capture_output=True, text=True, env=env)
    qt = time.time() - t0
    text = p.stdout
    files = ranked_code_files(SRC.findall(text))
    r = {"hash": q["hash"][:10], "question": q["question"], "gold": q["gold"], "files": files[:10], "exit": p.returncode,
         "tokens": len(text) // 4, "query_s": round(qt, 2), "build_s": round(bt, 1), "build_ok": b.returncode == 0,
         **score(files, q["gold"])}
    rows.append(r)
    print(f"{i:>3}/{len(Q)} {'HIT1' if r['top1'] else ('top5' if r['top5'] else 'miss')} exit {p.returncode} build {bt:5.1f}s  {q['question'][:70]}", flush=True)
    json.dump(rows, open(out, "w"), indent=1)
