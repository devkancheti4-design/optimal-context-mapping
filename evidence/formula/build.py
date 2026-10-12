"""Observables for every case, from existing logs -> cases.json.
Laws cases C1-C5 (= D1-D5 of PROTOCOL_FORMULA.md): ALONE and KIT sessions (tokens per request, exploration calls),
questions per session q, readout size R (kit readout characters / 4, per question).
Hybrid cases C6-C8 (Gemini 2.5 Flash, PROTOCOL_MODEL_D_E2E.md runs 1-3): per question ALONE tokens and turns, Model D's
path and tokens per question, readout size."""
import glob, json, os, sys
from collections import defaultdict
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
sys.path.insert(0, f"{B}/formula")
src = open(f"{B}/formula/formula.py").read().split("\ndef analyse")[0]      # reuse the audited loaders only
exec(src)


def rsize(paths):
    L = []
    for p in paths:
        for l in open(p):
            L.append(len(json.loads(l)["readout"]) / 4)
    return float(np.mean(L)) if L else None


cases = {}
RO_swe = json.load(open(f"{B}/swe_sonnet/readouts.json"))
R_swe = float(np.mean([len(v) / 4 for v in RO_swe.values()]))
for name, loader, q, R in (("C1 Sonnet 5.5, real bugs", d1, 1, R_swe), ("C2 Gemini 2.5 Flash, real bugs", d2, 1, R_swe),
                           ("C3 Gemini 2.5 Flash, codebase questions", d3, 10, rsize(glob.glob(f"{B}/api/runs/cmlm_r*/readouts.jsonl"))),
                           ("C4 Opus 5.5, codebase questions", lambda: large(f"{B}/large/agents.json"), 10, rsize(glob.glob(f"{B}/large/agents/cmlm_t*/readouts.jsonl"))),
                           ("C5 Sonnet 5.5, codebase questions", lambda: large(f"{B}/large/slices/agents_slices.json", "SON/"), 10, rsize(glob.glob(f"{B}/large/slices/SON/agents/cmlm_t*/readouts.jsonl")))):
    S = loader()
    cases[name] = {"kind": "laws", "q": q, "R": R, "alone": S["alone"], "kit": S["kit"]}

for r in (1, 2, 3):
    A = defaultdict(lambda: {"tokens": 0, "turns": 0})
    for l in open(f"{B}/api/runs/alone_r{r}/requests.jsonl"):
        x = json.loads(l)
        if x["qid"] is None: continue
        A[x["qid"]]["tokens"] += x["prompt"] + x["output"] + x["thoughts"]; A[x["qid"]]["turns"] += 1
    M = defaultdict(lambda: {"tokens": 0, "eyes tokens": 0, "body tokens": 0, "body turns": 0})
    for l in open(f"{B}/modeld/e2e/qa_r{r}/requests.jsonl"):
        x = json.loads(l); t = x["prompt"] + x["output"] + x["thoughts"]; m = M[x["qid"]]; m["tokens"] += t
        if x.get("path") == "eyes": m["eyes tokens"] += t
        else: m["body tokens"] += t; m["body turns"] += 1
    paths = {json.loads(l)["qid"]: json.loads(l)["path"] for l in open(f"{B}/modeld/e2e/qa_r{r}/decisions.jsonl")}
    qids = sorted(set(paths) & set(A))
    cases[f"C{5 + r} Gemini 2.5 Flash, hybrid end to end, run {r}"] = {
        "kind": "hybrid", "R": rsize([f"{B}/modeld/e2e/qa_r{r}/readouts.jsonl"]),
        "per question": [{"qid": k, "alone tokens": A[k]["tokens"], "alone turns": A[k]["turns"], "path": paths[k], **M[k]} for k in qids]}
json.dump(cases, open(f"{H}/cases.json", "w"))
for k, c in cases.items():
    if c["kind"] == "laws":
        print(f"{k:48s} q={c['q']:2d} R={c['R']:.0f} sessions {len(c['alone'])}/{len(c['kit'])}")
    else:
        pq = c["per question"]; print(f"{k:48s} R={c['R']:.0f} questions {len(pq)} paths {dict((p, sum(x['path'] == p for x in pq)) for p in ('eyes', 'eyes -> body', 'body'))}")
