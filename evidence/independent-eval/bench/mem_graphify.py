"""Graphify memory test. Teach = Graphify's own work-memory loop: `save-result` (question, answer, cited nodes,
outcome useful) into graphify-out/memory, then `update` (files the memory back into the graph) and `reflect`."""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import snapshot, ranked_code_files, score

G = "~/eval/envs/graphify/bin/graphify"
SRC = re.compile(r"\[src=([^ \]]*)")
env = {**os.environ, "GRAPHIFY_QUERY_LOG_DISABLE": "1", "GRAPHIFY_BACKEND": "none"}
S = json.load(open("~/eval/bench/mem_set.json"))
snap = "~/eval/bench/work/mem_g/snap"
snapshot("~/eval/targets/fastify", "HEAD", snap, keep=("graphify-out",))
run = lambda *a: subprocess.run([G, *a], cwd=snap, capture_output=True, text=True, env=env)
run("update", ".", "--force")


def ask(q, gold):
    text = run("query", q, "--graph", "graphify-out/graph.json").stdout
    files = ranked_code_files(SRC.findall(text))
    return {**score(files, gold), "files": files[:5], "tokens": len(text) // 4, "memory_hit": "memory/" in text}


def cite(f, ln):
    """The node a teacher would cite: the nearest symbol in that file at or above the line, plus the file node."""
    g = json.load(open(os.path.join(snap, "graphify-out/graph.json")))
    best = None
    for n in g["nodes"]:
        if n.get("source_file") == f:
            m = re.match(r"L(\d+)", n.get("source_location") or "")
            l = int(m.group(1)) if m else 0
            if l <= ln and (best is None or l > best[0]):
                best = (l, n["label"])
    return [best[1]] if best else [] + [os.path.basename(f)]


out = {"before_para": [ask(t["paraphrase"], t["gold"]) for t in S["taught"]],
       "before_new": [ask(u["question"], u["gold"]) for u in S["untaught"]]}
out["teach_replies"] = []
for t in S["taught"]:
    nodes = list(dict.fromkeys(cite(t["file"], t["line"]) + [os.path.basename(t["file"])]))
    r = run("save-result", "--question", t["question"], "--answer", f"The answer is in {t['file']} line {t['line']}.",
            "--nodes", *nodes, "--outcome", "useful")
    out["teach_replies"].append((nodes, r.returncode, (r.stdout + r.stderr)[:120]))
u = run("update", ".", "--force"); rf = run("reflect", "--graph", "graphify-out/graph.json")
out["update"] = (u.returncode, u.stdout[-300:]); out["reflect"] = (rf.returncode, (rf.stdout + rf.stderr)[-300:])
out["after_same"] = [ask(t["question"], t["gold"]) for t in S["taught"]]
out["after_para"] = [ask(t["paraphrase"], t["gold"]) for t in S["taught"]]
out["after_new"] = [ask(u["question"], u["gold"]) for u in S["untaught"]]
json.dump(out, open("~/eval/bench/results/mem_graphify.json", "w"), indent=1)
for k in ("before_para", "after_same", "after_para", "before_new", "after_new"):
    v = out[k]; print(f"{k:13} top1 {sum(r['top1'] for r in v):>2}/{len(v)}  top5 {sum(r['top5'] for r in v):>2}  memory-hit {sum(r['memory_hit'] for r in v)}")
print("teach:", out["teach_replies"][:3]); print("update:", out["update"]); print("reflect:", out["reflect"])
