"""Model D memory test (run with the modeld venv). Teach = Model D's own `teach` (what its Stop hook does with a TEACH line)."""
import json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import snapshot, ranked_code_files, score
from ocm.build import build
from ocm.server import Workspace

CITE = re.compile(r"(?m)^\s*\d+\.\s*\[([^\]]+?):(\d+)\]")
S = json.load(open("~/eval/bench/mem_set.json"))
work = "~/eval/bench/work/mem_m"
snap, ws = os.path.join(work, "snap", "repo"), os.path.join(work, "ws")
snapshot("~/eval/targets/fastify", "HEAD", snap)
shutil.rmtree(ws, ignore_errors=True)
build([snap], ws, log=lambda *a: None, cache="~/eval/bench/work/m_fastify/embed.sqlite")
w = Workspace(ws)


def ask(q, gold):
    text = w.handle("ask", {"question": q, "scope": "code"})
    files = ranked_code_files(p.split("/", 1)[1] if "/" in p else p for p, _ in CITE.findall(text))
    return {**score(files, gold), "files": files[:5], "tokens": len(text) // 4, "pointer": text.startswith("(readout: the code a taught")}


out = {"before_para": [ask(t["paraphrase"], t["gold"]) for t in S["taught"]],
       "before_new": [ask(u["question"], u["gold"]) for u in S["untaught"]]}
out["teach_replies"] = [w.handle("teach", {"pairs": [{"question": t["question"], "at": f"{t['file']}:{t['line']}"}]})[:80] for t in S["taught"]]
out["after_same"] = [ask(t["question"], t["gold"]) for t in S["taught"]]
out["after_para"] = [ask(t["paraphrase"], t["gold"]) for t in S["taught"]]
out["after_new"] = [ask(u["question"], u["gold"]) for u in S["untaught"]]
# A new session after a rebuild: does the memory survive?
ws2 = ws + "2"; shutil.rmtree(ws2, ignore_errors=True)
build([snap], ws2, log=lambda *a: None, cache="~/eval/bench/work/m_fastify/embed.sqlite")
w = Workspace(ws2); carried = w.carry(ws)
out["carried"] = carried
out["rebuilt_para"] = [ask(t["paraphrase"], t["gold"]) for t in S["taught"]]
json.dump(out, open("~/eval/bench/results/mem_modeld.json", "w"), indent=1)
for k in ("before_para", "after_same", "after_para", "rebuilt_para", "before_new", "after_new"):
    v = out[k]; print(f"{k:13} top1 {sum(r['top1'] for r in v):>2}/{len(v)}  top5 {sum(r['top5'] for r in v):>2}  pointer-led {sum(r['pointer'] for r in v)}")
print("teach:", out["teach_replies"][:3], "carried:", carried)
