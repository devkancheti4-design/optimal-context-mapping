"""Packs the run for the repository, once, after the run: ~/arb-work/results/<label>/<track>_details.jsonl to results/<label>.jsonl.gz,
without the gold spans and the query provenance (they are in the benchmark's samples), adding each query's length in the embedder's
tokens and whether Model D's tests rule reads it as about tests. Copies each track's _bcy.json and _bcy.md.

    HF_HUB_OFFLINE=1 <modeld python> -I pack.py [--work ~/arb-work]"""
import argparse, gzip, json, os, shutil

from ocm.cmlm_vector.embed import DEFAULT_MODEL
from ocm.server import ABOUT_TESTS
from transformers import AutoTokenizer

ap = argparse.ArgumentParser(); ap.add_argument("--work", default=os.path.expanduser("~/arb-work")); a = ap.parse_args()
H = os.path.dirname(os.path.abspath(__file__))
TRACKS = ("v2_trace2code", "v2_edit2ripple", "v2_comment2context", "v2_code2test")
KEEP = ("sample_id", "task_type", "repo", "base_commit", "gold_files", "gold_ranks", "ranked_files", "first_readout", "first_readout_tokens",
        "gold_in_first_readout", "metrics", "build_s", "ask_s")
tok = AutoTokenizer.from_pretrained(DEFAULT_MODEL)


def strings(v):                                 # run.py's rendering of the query
    if isinstance(v, str):
        return [v] if v.strip() else []
    if isinstance(v, dict):
        return [s for x in v.values() for s in strings(x)]
    if isinstance(v, (list, tuple)):
        return [s for x in v for s in strings(x)]
    return []


queries = {}
for t in TRACKS:
    for s in map(json.loads, open(f"{a.work}/data/benchmark/{t}/samples.jsonl")):
        q = "\n\n".join(sorted(strings(s["query"]), key=len))
        queries[s["id"]] = (len(tok(q, add_special_tokens=False, truncation=False)["input_ids"]), bool(ABOUT_TESTS.search(q)))

for label in ("modeld-0.5.3", "modeld-0.5.3-trail-off"):
    os.makedirs(f"{H}/results/{label}", exist_ok=True)
    with gzip.open(f"{H}/results/{label}.jsonl.gz", "wt", compresslevel=9) as out:
        for t in TRACKS:
            for r in map(json.loads, open(f"{a.work}/results/{label}/{t}_details.jsonl")):
                n, about = queries[r["sample_id"]]
                out.write(json.dumps({**{k: r[k] for k in KEEP}, "query_tokens": n, "query_about_tests": about}) + "\n")
            for ext in ("json", "md"):
                shutil.copy(f"{a.work}/results/{label}/{t}_bcy.{ext}", f"{H}/results/{label}/")
