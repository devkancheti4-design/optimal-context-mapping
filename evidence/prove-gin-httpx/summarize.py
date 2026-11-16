"""Recompute every number in RESULTS.md from the per-fix rows of the six `modeld prove` runs in this folder.

    python evidence/prove-gin-httpx/summarize.py

Standard library only. Shares carry a 95% Wilson interval; Model D against grep is an exact two-sided McNemar test
on the same fixes."""
import json, math, os

H = os.path.dirname(os.path.abspath(__file__))


def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def mcnemar(a, b):
    n10 = sum(x and not y for x, y in zip(a, b)); n01 = sum(y and not x for x, y in zip(a, b)); n = n10 + n01
    return n10, n01, (1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(n10, n01) + 1)) / 2 ** n))


def share(k, n):
    lo, hi = wilson(k, n)
    return f"{k} of {n} ({k / n:.1%}, {lo:.1%}-{hi:.1%})"


def run(name):
    d = json.load(open(f"{H}/{name}.json")); R = d["rows"]; n = len(R)
    assert n == d["fixes"]
    out = {"repo": d["repo"], "fixes": n, "tokens per readout": round(sum(r["tokens"] for r in R) / n)}
    for key, label in (("first", "right file first"), ("top5", "right file in the top 5")):
        md, gr = [r[f"md_{key}"] for r in R], [r[f"grep_{key}"] for r in R]
        n10, n01, p = mcnemar(md, gr)
        out[label] = f"Model D {share(sum(md), n)}; grep {share(sum(gr), n)}; Model D only {n10}, grep only {n01}, p = {p:.2g}"
    out["changed line in the top 5"] = share(sum(r["md_line_top5"] for r in R), n)
    if "mem_first" in R[0]:
        out["with memory: right file first"] = share(sum(r["mem_first"] for r in R), n)
        out["with memory: right file in the top 5"] = share(sum(r["mem_top5"] for r in R), n)
        led = [i for i, r in enumerate(R) if r["from_memory"]]
        mate = sum(all(R[j]["author"] != R[i]["author"] for j in range(i) if R[j]["taught"] == R[i]["mem_lead"][0]) for i in led)
        out["lessons taught"] = f"{sum(bool(r['taught']) for r in R)}; the fixes came from {len({r['author'] for r in R})} authors"
        out["lessons still found at the last fix"] = f"{R[-1]['carried']} of {R[-1]['lessons']}"
        out["a taught pointer led"] = f"{len(led)} readouts, right {sum(R[i]['mem_first'] for i in led)}, from another author's lesson {mate}"
    out["first and last fix replayed"] = f"{R[0]['hash']} ... {R[-1]['hash']}"
    return out


if __name__ == "__main__":
    for name in ("gin.long", "httpx.long", "gin.prove", "httpx.prove", "gin.learn", "httpx.learn"):
        print(name)
        for k, v in run(name).items():
            print(f"  {k:<38} {v}")
