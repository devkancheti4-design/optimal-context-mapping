"""PROTOCOL_MODEL_D_E2E.md report: Model D end to end against the same-model arms.

    python3 report_e2e.py      -> report_e2e.json (and judge_e2e/ items for the blind judge of Model D's answers)"""
import json, os, random, sys
from collections import defaultdict
sys.path.insert(0, os.path.expanduser("~/cmlm-bench10/reports"))
from common import usd, ci
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
QS = {q["qid"]: q for q in json.load(open(os.path.expanduser("~/cmlm-bench5/questions.json")))}
rep = {"protocol sha256": json.load(open(f"{B}/prereg_hashes.json"))["PROTOCOL_MODEL_D_E2E.md"]["sha256"]}

# ---- questions: Model D per question (eyes rows carry "path": "eyes"; body rows carry the qid)
D = defaultdict(lambda: defaultdict(lambda: {"requests": 0, "usd": 0.0, "tokens": 0}))
paths = defaultdict(dict)
for r in (1, 2, 3):
    d = f"{H}/e2e/qa_r{r}"
    if not os.path.exists(f"{d}/decisions.jsonl"): continue
    for l in open(f"{d}/requests.jsonl"):
        x = json.loads(l); q = x["qid"]
        D[r][q]["requests"] += 1; D[r][q]["usd"] += usd(x); D[r][q]["tokens"] += x["prompt"] + x["output"] + x["thoughts"]
    for l in open(f"{d}/decisions.jsonl"):
        x = json.loads(l); paths[r][x["qid"]] = x["path"]
# the same-model arms, per question, from PROTOCOL_API.md's runs (sessions of 10; each request is charged to its question)
A = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"requests": 0, "usd": 0.0, "tokens": 0})))
for arm in ("alone", "cmlm"):
    for r in (1, 2, 3):
        p = f"{B}/api/runs/{arm}_r{r}/requests.jsonl"
        for l in (open(p) if os.path.exists(p) else []):
            x = json.loads(l); q = x["qid"]
            if q is None: continue
            A[arm][r][q]["requests"] += 1; A[arm][r][q]["usd"] += usd(x); A[arm][r][q]["tokens"] += x["prompt"] + x["output"] + x["thoughts"]
answered = lambda arm, r: {json.loads(l)["qid"] for l in open(f"{B}/api/runs/{arm}_r{r}/answers.jsonl")} if os.path.exists(f"{B}/api/runs/{arm}_r{r}/answers.jsonl") else set()
for r in (1, 2, 3):
    if r not in paths: continue
    done = set(paths[r]) & answered("alone", r) & answered("cmlm", r)
    if not done: continue
    sel = sorted(done)
    row = {"questions compared": len(sel), "paths": {p: sum(1 for q in sel if paths[r][q] == p) for p in ("eyes", "eyes -> body", "body")}}
    for k in ("requests", "usd", "tokens"):
        row[f"{k} per question, alone / cmlm / model d"] = [round(sum(A["alone"][r][q][k] for q in sel) / len(sel), 4),
                                                            round(sum(A["cmlm"][r][q][k] for q in sel) / len(sel), 4),
                                                            round(sum(D[r][q][k] for q in sel) / len(sel), 4)]
    row["request factor vs alone"] = round(sum(A["alone"][r][q]["requests"] for q in sel) / max(1, sum(D[r][q]["requests"] for q in sel)), 2)
    row["request factor vs alone, 95% CI"] = ci([A["alone"][r][q]["requests"] for q in sel], [max(1e-9, D[r][q]["requests"]) for q in sel])
    row["dollar factor vs alone"] = round(sum(A["alone"][r][q]["usd"] for q in sel) / max(1e-9, sum(D[r][q]["usd"] for q in sel)), 2)
    row["dollar factor vs alone, 95% CI"] = ci([A["alone"][r][q]["usd"] for q in sel], [max(1e-9, D[r][q]["usd"]) for q in sel])
    row["request factor vs cmlm"] = round(sum(A["cmlm"][r][q]["requests"] for q in sel) / max(1, sum(D[r][q]["requests"] for q in sel)), 2)
    for part, f in (("untaught (first wordings)", lambda q: not q.endswith("b")), ("taught (repeats)", lambda q: q.endswith("b"))):
        s2 = [q for q in sel if f(q)]
        if s2:
            row[part] = {"questions": len(s2), "requests per question, alone / cmlm / model d": [round(sum(A[a][r][q]["requests"] for q in s2) / len(s2), 2) for a in ("alone", "cmlm")] + [round(sum(D[r][q]["requests"] for q in s2) / len(s2), 2)],
                         "tokens per question, alone / cmlm / model d": [round(sum(A[a][r][q]["tokens"] for q in s2) / len(s2)) for a in ("alone", "cmlm")] + [round(sum(D[r][q]["tokens"] for q in s2) / len(s2))]}
    rep[f"questions, run {r}"] = row

# ---- bugs: Model D against the bug bash's arms, per program
for r in (1, 2, 3):
    p = f"{H}/e2e/bugs_r{r}/results.jsonl"
    if not os.path.exists(p): continue
    md = {json.loads(l)["program"]: json.loads(l) for l in open(p)}
    arms = {a: {json.loads(l)["program"]: json.loads(l) for l in open(f"{B}/fix/runs/{a}_r{r}/results.jsonl")} for a in ("alone", "neo4d")}
    sel = sorted(set(md) & set(arms["alone"]) & set(arms["neo4d"]))
    rep[f"bugs, run {r}"] = {"programs": len(sel), "kit-only fixes": sum(1 for q in sel if md[q].get("path") == "kit"),
                             "requests, alone / neo4d / model d": [sum(arms["alone"][q]["requests"] for q in sel), sum(arms["neo4d"][q]["requests"] for q in sel), sum(md[q]["requests"] for q in sel)],
                             "fixed, alone / neo4d / model d": [sum(arms["alone"][q]["fixed"] for q in sel), sum(arms["neo4d"][q]["fixed"] for q in sel), sum(md[q]["fixed"] for q in sel)]}

# ---- blind-judge items for Model D's answers
items = []
for r in (1, 2, 3):
    p = f"{H}/e2e/qa_r{r}/answers.jsonl"
    for l in (open(p) if os.path.exists(p) else []):
        a = json.loads(l); f = QS[a["qid"].rstrip("b")]; ans = a["answer"].split("|")[0].replace("ANSWER:", "").strip()
        items.append(((r, a["qid"]), {"question": f["question2"] if a["qid"].endswith("b") else f["question"], "expected": f["answer"], "expected_file": f["file"], "response": ans, "response_file": ""}))
if items:
    os.makedirs(f"{B}/judge_e2e", exist_ok=True); random.Random(20261008 + 17).shuffle(items)
    keys = [f"e{i:03d}" for i in range(1, len(items) + 1)]
    json.dump({k: it for k, (_, it) in zip(keys, items)}, open(f"{B}/judge_e2e/judge_items.json", "w"), indent=1)
    json.dump({k: list(m) for k, (m, _) in zip(keys, items)}, open(f"{B}/judge_e2e/judge_map.json", "w"), indent=1)
    rep["judge items written"] = len(items)
json.dump(rep, open(f"{H}/report_e2e.json", "w"), indent=1); print(json.dumps(rep, indent=1))
