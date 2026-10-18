"""Score METHOD.md: file hit@k and MRR for Model D and the grep baseline, line hit for Model D, McNemar, Wilson.
    python3 score.py -> report.json"""
import json, math
Q = {q["id"]: q for q in json.load(open("questions.json"))}
R = [json.loads(l) for l in open("results.jsonl")]


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]


def mcnemar(a, b):
    n10 = sum(x and not y for x, y in zip(a, b)); n01 = sum(y and not x for x, y in zip(a, b)); n = n10 + n01; k = min(n10, n01)
    return [n10, n01, 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)]


def line_hit(item, gl, tol):
    p, a, b = item
    return any(a - tol <= hi and b + tol >= lo for lo, hi in gl.get(p, []))


rep = {"fixes": len(R)}
for name in ("bare", "subject"):
    md_files = [list(dict.fromkeys(i[0] for i in r["q"][name]["items"])) for r in R]
    gr_files = [r["q"][name]["grep"] for r in R]
    gold = [Q[r["id"]]["gold"] for r in R]; gl = [Q[r["id"]]["gold_lines"] for r in R]
    hit = lambda L, g, k: any(f in g for f in L[:k])
    mrr = lambda L, g: next((1 / (i + 1) for i, f in enumerate(L[:10]) if f in g), 0.0)
    out = {}
    for arm, F in (("model_d", md_files), ("grep", gr_files)):
        h = {k: [hit(L, g, k) for L, g in zip(F, gold)] for k in (1, 3, 5)}
        out[arm] = {"file hit@1/3/5": [sum(h[k]) for k in (1, 3, 5)], "hit@1 95% CI": wilson(sum(h[1]), len(R)),
                    "MRR@10": round(sum(mrr(L, g) for L, g in zip(F, gold)) / len(R), 3), "_h": h}
    items = [r["q"][name]["items"] for r in R]
    for tol in (0, 5):
        l1 = [bool(it) and line_hit(it[0], g, tol) for it, g in zip(items, gl)]
        l5 = [any(line_hit(x, g, tol) for x in it[:5]) for it, g in zip(items, gl)]
        out["model_d"][f"line hit@1/@5 (±{tol})"] = [sum(l1), sum(l5)]
        if tol == 0:
            out["model_d"]["line hit@5 95% CI"] = wilson(sum(l5), len(R))
    out["mcnemar file hit@1 model_d vs grep"] = mcnemar(out["model_d"]["_h"][1], out["grep"]["_h"][1])
    out["mcnemar file hit@5 model_d vs grep"] = mcnemar(out["model_d"]["_h"][5], out["grep"]["_h"][5])
    out["model_d"]["tokens per readout"] = round(sum(r["q"][name]["chars"] for r in R) / len(R) / 4)
    ms = sorted(r["q"][name]["ms"] for r in R); out["model_d"]["ask latency ms (median / p90)"] = [ms[len(ms) // 2], ms[int(len(ms) * .9)]]
    lanes = {}
    for r in R:
        lanes[r["q"][name]["header"]] = lanes.get(r["q"][name]["header"], 0) + 1
    out["model_d"]["lanes used"] = lanes
    for arm in ("model_d", "grep"):
        out[arm].pop("_h")
    rep[name] = out
b = sorted(r["build_s"] for r in R); rep["build seconds (first / median of the rest)"] = [R[0]["build_s"], b[len(b) // 2]]
rep["units per build (median)"] = sorted(r["units"] for r in R)[len(R) // 2]
B = rep["bare"]; md, gr = B["model_d"], B["grep"]
rep["predictions"] = {"N1 bare: model_d file hit@1 > grep": md["file hit@1/3/5"][0] > gr["file hit@1/3/5"][0],
                      "N2 bare: model_d file hit@5 > grep": md["file hit@1/3/5"][2] > gr["file hit@1/3/5"][2],
                      "N3 bare: model_d line hit@5 >= 25%": md["line hit@1/@5 (±0)"][1] >= 0.25 * rep["fixes"]}
print(json.dumps(rep, indent=1)); json.dump(rep, open("report.json", "w"), indent=1)
