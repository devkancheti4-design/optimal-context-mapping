"""PROTOCOL_CODEONLY scorer: Model D with scope "code" against Graphify 0.9.87 and against Model D with scope "all", on
the SWE-bench Lite issues whose fixed file exists in the snapshot. hit@k = a fixed file is among the first k files
listed. Tokens = readout characters / 4. Exact two-sided McNemar test on paired top-5 hits. Standard library only.
    python score_codeonly.py codeonly.json"""
import json, math, os, sys
from statistics import mean
L = os.path.dirname(os.path.abspath(__file__)); D = json.load(open(f"{L}/swebench_lite_by_repo.json"))
ARMS = {"code": json.load(open(f"{L}/{sys.argv[1]}")), "all": json.load(open(f"{L}/regress_all2.json")),
        "graphify": json.load(open(f"{L}/graphify_ranked_087.json"))}
QUERIES = (("query_title", "issue title"), ("query_400", "title + 400 characters"))


def mcnemar(a, b):
    """exact two-sided p for paired booleans a, b"""
    n10 = sum(x and not y for x, y in zip(a, b)); n01 = sum(y and not x for x, y in zip(a, b)); n = n10 + n01
    if n == 0:
        return n10, n01, 1.0
    k = min(n10, n01)
    return n10, n01, min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


kept = []
for slug, v in sorted(D.items()):
    repo = f"{L}/repos/{slug.split('/')[1]}"
    kept += [(slug, it) for it in v["issues"] if any(os.path.exists(os.path.join(repo, f)) for f in it["gold_files"])]
out = {"issues": len(kept)}
for key, label in QUERIES:
    hit = {arm: {k: [any(f in it["gold_files"] for f in R[s][it["instance_id"]][key]["files"][:k]) for s, it in kept] for k in (1, 3, 5)}
           for arm, R in ARMS.items()}
    tok = {arm: mean(R[s][it["instance_id"]][key]["chars"] / 4 for s, it in kept) for arm, R in ARMS.items()}
    r = {arm: {"top1/3/5": [sum(hit[arm][k]) for k in (1, 3, 5)], "tokens": round(tok[arm])} for arm in ARMS}
    r["mcnemar top-5 code vs graphify (code only, graphify only, p)"] = mcnemar(hit["code"][5], hit["graphify"][5])
    r["mcnemar top-5 code vs all (code only, all only, p)"] = mcnemar(hit["code"][5], hit["all"][5])
    per = {}
    for i, (s, it) in enumerate(kept):
        p = per.setdefault(s, {"n": 0, "code": 0, "graphify": 0, "all": 0}); p["n"] += 1
        for arm in ARMS:
            p[arm] += hit[arm][5][i]
    r["per repo top-5"] = per
    out[label] = r
t, l = out["issue title"], out["title + 400 characters"]
out["predictions"] = {
    "C1 titles: code top-5 > graphify top-5": t["code"]["top1/3/5"][2] > t["graphify"]["top1/3/5"][2],
    "C2 title+400: code top-5 > graphify top-5": l["code"]["top1/3/5"][2] > l["graphify"]["top1/3/5"][2],
    "C3 titles: code top-1 >= graphify top-1": t["code"]["top1/3/5"][0] >= t["graphify"]["top1/3/5"][0],
    "C4 both: code top-5 >= all top-5": t["code"]["top1/3/5"][2] >= t["all"]["top1/3/5"][2] and l["code"]["top1/3/5"][2] >= l["all"]["top1/3/5"][2],
    "C5 both: code tokens < graphify tokens": t["code"]["tokens"] < t["graphify"]["tokens"] and l["code"]["tokens"] < l["graphify"]["tokens"],
}
print(json.dumps(out, indent=1))
json.dump(out, open(f"{L}/report_codeonly.json", "w"), indent=1)
