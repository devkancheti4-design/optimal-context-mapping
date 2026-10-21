"""Aggregate the localization benchmark: per repo and overall, with paired exact McNemar tests against Model D."""
import json, math, os

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
REPOS = ["aiohttp", "fastify", "zod"]


def load(tool, repo):
    if tool in ("grep", "bm25", "prior"):
        return json.load(open(f"{R}/baselines_{repo}.json"))[tool]
    f = f"{R}/{tool}_{repo}.json"
    return json.load(open(f)) if os.path.exists(f) else []


def mcnemar(a, b):
    """Exact two-sided McNemar p for paired booleans."""
    x = sum(1 for i, j in zip(a, b) if i and not j); y = sum(1 for i, j in zip(a, b) if j and not i); n = x + y
    if n == 0:
        return 1.0, x, y
    p = sum(math.comb(n, k) for k in range(0, min(x, y) + 1)) / 2 ** n * 2
    return min(1.0, p), x, y


tools = ["modeld", "graphify", "bm25", "grep", "prior"]
summary = {}
for t in tools:
    rows = {r: load(t, r) for r in REPOS}
    summary[t] = rows
print(f"{'':10}" + "".join(f"{r:>22}" for r in REPOS) + f"{'ALL':>22}")
for metric in ("top1", "top5", "top1_notests", "top5_notests"):
    print(f"-- {metric}")
    for t in tools:
        cells, allv = [], []
        for r in REPOS:
            v = [x[metric] for x in summary[t][r]]; allv += v
            cells.append(f"{sum(v):>3}/{len(v):<3}({sum(v) / max(len(v), 1):>4.0%})")
        print(f"{t:10}" + "".join(f"{c:>22}" for c in cells) + f"{sum(allv):>9}/{len(allv):<3}({sum(allv) / max(len(allv), 1):>4.0%})")
print("-- MRR (all repos)")
for t in tools:
    v = [x["rr"] for r in REPOS for x in summary[t][r]]
    print(f"{t:10} {sum(v) / max(len(v), 1):.3f}")
print("-- first answer is a test file")
for t in ("modeld", "graphify"):
    v = [x["first_is_test"] for r in REPOS for x in summary[t][r]]
    print(f"{t:10} {sum(v)}/{len(v)}")
print("-- tokens handed to the agent per question (mean)")
for t in ("modeld", "graphify"):
    v = [x["tokens"] for r in REPOS for x in summary[t][r]]
    print(f"{t:10} {sum(v) / max(len(v), 1):.0f}")
print("-- query latency s (mean), rebuild s per commit (median)")
for t in ("modeld", "graphify"):
    q = [x["query_s"] for r in REPOS for x in summary[t][r]]; b = sorted(x["build_s"] for r in REPOS for x in summary[t][r])
    print(f"{t:10} query {sum(q) / max(len(q), 1):.2f}s   rebuild median {b[len(b) // 2] if b else 0:.1f}s  max {max(b) if b else 0:.1f}s")
print("-- paired exact McNemar, Model D vs each (top1, all repos): p, MD-only wins, other-only wins")
md = {r: {x["hash"]: x for x in summary["modeld"][r]} for r in REPOS}
for t in tools[1:]:
    a, b = [], []
    for r in REPOS:
        for x in summary[t][r]:
            if x["hash"] in md[r]:
                a.append(md[r][x["hash"]]["top1"]); b.append(x["top1"])
    p, x, y = mcnemar(a, b)
    print(f"  vs {t:9} n={len(a)}  p={p:.2g}  ModelD-only {x}  {t}-only {y}")
