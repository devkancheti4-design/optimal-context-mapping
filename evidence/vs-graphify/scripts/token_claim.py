"""Addendum A1: Graphify's token-reduction formula, run as its own code runs it, on its corpus and on Django 2022.
Run with Graphify's environment: gfvenv/bin/python scripts/token_claim.py"""
import json, os, subprocess, sys, tempfile
from pathlib import Path
from graphify.benchmark import run_benchmark, _SAMPLE_QUESTIONS
from graphify.detect import detect
H = Path(__file__).resolve().parent.parent; out = {}
GFREPO = Path.home() / "neos/outreach/graphify-pr/graphify"
with tempfile.TemporaryDirectory() as t:                                      # their worked example, from the 0.9.92 tag
    gp = Path(t) / "graph.json"; gp.write_bytes(subprocess.check_output(["git", "-C", str(GFREPO), "show", "86c57be8:worked/karpathy-repos/graph.json"]))
    readme = subprocess.check_output(["git", "-C", str(GFREPO), "show", "86c57be8:worked/karpathy-repos/GRAPH_REPORT.md"]).decode()   # its Corpus Check line: ~92,616 words
    r = run_benchmark(str(gp))                                                 # as the CLI runs it when no detect file exists
    out["karpathy, graph-estimated corpus"] = {k: r[k] for k in ("corpus_tokens", "avg_query_tokens", "reduction_ratio", "nodes")}
    words = [int(w.replace(",", "")) for w in __import__("re").findall(r"([\d,]{4,}) words", readme)]
    if words:
        r = run_benchmark(str(gp), corpus_words=max(words))
        out["karpathy, its reported corpus words"] = {"corpus_words": max(words), **{k: r[k] for k in ("corpus_tokens", "avg_query_tokens", "reduction_ratio")}}
dj_graph = str(H / "graphs/django-2022/graphify-out/graph.json")
d = detect(Path.home() / "neos/outreach/team-year/django")
qs = [x["queries"]["q"] for x in json.load(open(H / "questions/django2022.json"))]
for name, questions in (("django 2022, their 5 sample questions", _SAMPLE_QUESTIONS), ("django 2022, the 288 real questions", qs)):
    r = run_benchmark(dj_graph, corpus_words=d["total_words"], questions=questions)
    out[name] = {"corpus_words": d["total_words"], "files": d.get("total_files"), **{k: r[k] for k in ("corpus_tokens", "avg_query_tokens", "reduction_ratio")},
                 "questions answered": len(r["per_question"])}
ct = out["django 2022, the 288 real questions"]["corpus_tokens"]
for arm in ("md_cold", "md_cover", "gf"):                                      # the same formula on Part A's readouts
    R = json.load(open(H / f"results/dj_{arm}.json")); toks = [v["q"]["chars"] // 4 for v in R.values()]
    m = sum(toks) / len(toks); out[f"django 2022, formula on Part A readouts: {arm}"] = {"avg_readout_tokens": round(m), "reduction_ratio": round(ct / m, 1)}
print(json.dumps(out, indent=1)); json.dump(out, open(H / "results/token_claim.json", "w"), indent=1)
