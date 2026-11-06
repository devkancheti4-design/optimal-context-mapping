"""One track's scores for each label run so far: Recall and MRR means from the details files, BCY from the benchmark's own
report_bcy_budget_curve (it needs the track's corpus, so run this before deleting it). Writes <work>/results/<label>/<release>_bcy.json.

    python3 score.py <release> [--work ~/arb-work]"""
import argparse, glob, json, os, sys
from pathlib import Path

ap = argparse.ArgumentParser(); ap.add_argument("release"); ap.add_argument("--work", default=os.path.expanduser("~/arb-work"))
a = ap.parse_args()
sys.path.insert(0, os.path.join(a.work, "agent-retrieval-bench", "src"))
os.chdir(a.work)                                                     # the manifest's chunk paths are relative to here
from agent_retrieval_bench.bcy_curve import report_bcy_budget_curve  # noqa: E402

for details in sorted(glob.glob(f"results/*/{a.release}_details.jsonl")):
    label = details.split("/")[1]
    rows = [json.loads(l) for l in open(details)]
    mean = lambda k: sum(r["metrics"][k] for r in rows) / len(rows)
    out = Path(f"results/{label}/{a.release}_bcy.json")
    rep = report_bcy_budget_curve(Path(f"data/corpus/{a.release}/corpus_manifest.jsonl"), out, out.with_suffix(".md"), (4000, 8000, 16000, 32000),
                                  [(label, "modeld", Path(details))])
    run = rep["runs"][0] if "runs" in rep else rep
    print(f"{a.release} {label}: n={len(rows)}  MRR {mean('MRR'):.4f}  R@5 {mean('Recall@5'):.4f}  R@10 {mean('Recall@10'):.4f}  R@20 {mean('Recall@20'):.4f}  "
          f"gold in first readout {sum(r['gold_in_first_readout'] for r in rows) / len(rows):.3f}  first readout tokens {sum(r['first_readout_tokens'] for r in rows) / len(rows):.0f}")
    print("   BCY:", json.dumps({k: run[k] for k in run if k not in ("samples", "per_sample", "rows", "details")})[:900])
