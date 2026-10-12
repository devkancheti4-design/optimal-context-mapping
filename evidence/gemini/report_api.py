"""PROTOCOL_API.md report: the kit through the Vertex API, CMLM against ALONE, 3 runs x 6 tasks, from the API's own usage.

    ~/.venvs/cmlm-live/bin/python report_api.py      -> report_api.json"""
import json, os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.expanduser("~/cmlm-bench10/reports")); sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
from common import usd, ci
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
QS = {q["qid"]: q for q in json.load(open(os.path.expanduser("~/cmlm-bench5/questions.json")))}
S = {}                                                          # (arm, run, task) -> totals
perq = defaultdict(dict)
for arm in ("cmlm", "alone"):
    for run in (1, 2, 3):
        d = f"{H}/runs/{arm}_r{run}"
        if not os.path.exists(f"{d}/requests.jsonl"): continue
        for l in open(f"{d}/requests.jsonl"):
            x = json.loads(l); k = (arm, run, x["task"])
            s = S.setdefault(k, {"requests": 0, "usd": 0.0, "prompt": 0, "cached": 0, "out": 0, "seconds": 0.0})
            s["requests"] += 1; s["usd"] += usd(x); s["prompt"] += x["prompt"]; s["cached"] += x["cached"]; s["out"] += x["output"] + x["thoughts"]; s["seconds"] += x["seconds"]
        for l in open(f"{d}/answers.jsonl"):
            a = json.loads(l); perq[(arm, run)][a["qid"]] = a
complete = [(r, t) for r in (1, 2, 3) for t in range(1, 7) if ("cmlm", r, t) in S and ("alone", r, t) in S
            and sum(1 for q in perq[("cmlm", r)] if (q.endswith("b")) == (t > 3)) >= 0]
def done(arm, r, t):
    qids = [f"c{i:02d}" + ("b" if t > 3 else "") for i in range((t - 1) % 3 * 10 + 1, (t - 1) % 3 * 10 + 11)]
    return all(q in perq[(arm, r)] for q in qids)
pairs = [(r, t) for r, t in complete if done("cmlm", r, t) and done("alone", r, t)]
rep = {"protocol sha256": json.load(open(f"{B}/prereg_hashes.json"))["PROTOCOL_API.md"]["sha256"], "model": "gemini-2.5-flash (Vertex AI)",
       "complete (run, task) pairs": len(pairs)}
def block(sel, name):
    if not sel: return
    A = [S[("alone", r, t)] for r, t in sel]; C = [S[("cmlm", r, t)] for r, t in sel]
    n = 10 * len(sel)
    rep[name] = {"sessions per arm": len(sel), "requests, alone / cmlm": [sum(x["requests"] for x in A), sum(x["requests"] for x in C)],
                 "requests per question, alone / cmlm": [round(sum(x["requests"] for x in A) / n, 2), round(sum(x["requests"] for x in C) / n, 2)],
                 "request factor": round(sum(x["requests"] for x in A) / sum(x["requests"] for x in C), 3),
                 "request factor 95% CI": ci([x["requests"] for x in A], [x["requests"] for x in C]),
                 "dollars, alone / cmlm": [round(sum(x["usd"] for x in A), 4), round(sum(x["usd"] for x in C), 4)],
                 "dollar factor": round(sum(x["usd"] for x in A) / sum(x["usd"] for x in C), 3), "dollar factor 95% CI": ci([x["usd"] for x in A], [x["usd"] for x in C]),
                 "prompt tokens, alone / cmlm": [sum(x["prompt"] for x in A), sum(x["prompt"] for x in C)],
                 "model seconds per question, alone / cmlm": [round(sum(x["seconds"] for x in A) / n, 2), round(sum(x["seconds"] for x in C) / n, 2)]}
block(pairs, "all"); block([p for p in pairs if p[1] <= 3], "untaught (tasks 1-3)"); block([p for p in pairs if p[1] > 3], "taught (tasks 4-6)")
# wall time per question from the answers (submit to submit), and the readout's hit rate
for arm in ("cmlm", "alone"):
    secs = [a["seconds"] for r in (1, 2, 3) for a in perq[(arm, r)].values()]
    rep.setdefault("wall seconds per question", {})[arm] = round(sum(secs) / max(1, len(secs)), 1)
try:
    from ocm.server import Workspace
    w = Workspace(f"{B}/large/ws_L_base"); span = {(p, a): (a, b) for p, xs in w.spans.items() for a, b, j in xs}
    ITEM = re.compile(r"(?m)^\d+\. \[([^\]:]+)(?::(\d+))?\]")
    def holds(text, f):
        for p, line in ITEM.findall(text):
            if line:
                a, b = span.get((p, int(line)), (int(line), int(line)))
                if p.endswith("/" + f["file"]) and a <= f["line"] <= b: return True
        return False
    hits = {"untaught": [0, 0], "taught": [0, 0]}
    for r in (1, 2, 3):
        p = f"{H}/runs/cmlm_r{r}/readouts.jsonl"
        for l in (open(p) if os.path.exists(p) else []):
            d = json.loads(l); f = QS[d["qid"].rstrip("b")]; k = "taught" if d["qid"].endswith("b") else "untaught"
            hits[k][0] += holds(d["readout"], f); hits[k][1] += 1
    rep["readout held the answer"] = {k: f"{v[0]}/{v[1]}" for k, v in hits.items()}
except Exception as e:
    rep["readout held the answer"] = f"not computed: {e}"
a, t = rep.get("all"), rep.get("taught (tasks 4-6)")
if a:
    rep["A1"] = a["request factor 95% CI"][0] > 1.25
    rep["A2"] = a["dollar factor 95% CI"][0] > 1.0
    rep["A3"] = bool(t) and t["request factor"] >= 1.5
    rep["A5"] = rep["wall seconds per question"]["cmlm"] <= rep["wall seconds per question"]["alone"]
json.dump(rep, open(f"{H}/report_api.json", "w"), indent=1); print(json.dumps(rep, indent=1))
