"""Saleor team replay: 200 real fixes in commit order. Does Model D's lead grow as the team's lessons pile up?"""
import json, math, os

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
md = json.load(open(f"{R}/team_modeld.json"))
gf = [r for k in range(3) if os.path.exists(f"{R}/team_graphify_{k}.json") for r in json.load(open(f"{R}/team_graphify_{k}.json"))]
bl = json.load(open(f"{R}/team_baselines.json")) if os.path.exists(f"{R}/team_baselines.json") else {}
by = lambda rows: {r["hash"][:10]: r for r in rows}
G, B, P, GR = by(gf), by(bl.get("bm25", [])), by(bl.get("prior", [])), by(bl.get("grep", []))
rows = [r for r in md if r["hash"] in G and r["hash"] in B]
n = len(rows)
tools = {"Model D + memory": lambda r: r["mem"], "Model D, cold": lambda r: r["cold"], "Graphify": lambda r: G[r["hash"]],
         "BM25": lambda r: B[r["hash"]], "grep": lambda r: GR[r["hash"]], "most-fixed file": lambda r: P[r["hash"]]}


def mcnemar(a, b):
    x = sum(1 for i, j in zip(a, b) if i and not j); y = sum(1 for i, j in zip(a, b) if j and not i); m = x + y
    return (1.0 if m == 0 else min(1.0, 2 * sum(math.comb(m, k) for k in range(min(x, y) + 1)) / 2 ** m)), x, y


print(f"Saleor, {n} real fixes in commit order (May 2024 to Oct 2026), {len({r['author'] for r in rows})} authors\n")
print(f"{'':18}{'right first':>14}{'top 5':>12}")
for t, f in tools.items():
    a = sum(f(r)["top1"] for r in rows); b = sum(f(r)["top5"] for r in rows)
    print(f"{t:18}{a:>7} ({a / n:>4.0%}){b:>6} ({b / n:>4.0%})")
q = 4; size = math.ceil(n / q)
print(f"\nright file first, by quarter of the replay (lessons in the shared workspace at the start of each):")
print(f"{'':18}" + "".join(f"{f'fixes {k * size + 1}-{min(n, (k + 1) * size)}':>15}" for k in range(q)))
print(f"{'lessons so far':18}" + "".join(f"{rows[k * size]['lessons']:>15}" for k in range(q)))
for t, f in tools.items():
    cells = []
    for k in range(q):
        part = rows[k * size:(k + 1) * size]
        cells.append(f"{sum(f(r)['top1'] for r in part)}/{len(part)}")
    print(f"{t:18}" + "".join(f"{c:>15}" for c in cells))
gain = [sum(r["mem"]["top1"] for r in rows[k * size:(k + 1) * size]) - sum(r["cold"]["top1"] for r in rows[k * size:(k + 1) * size]) for k in range(q)]
print(f"{'memory gain':18}" + "".join(f"{g:>+15}" for g in gain))
led = [r for r in rows if r["mem"]["pointer_led"]]
taught_by, cross = {}, 0
for r in rows:
    if r["mem"]["pointer_led"] and r["mem"]["top1"] and (taught_by.get(r["mem"]["files"][0], set()) - {r["author"]}):
        cross += 1
    if r["taught"]:
        taught_by.setdefault(r["taught"], set()).add(r["author"])
helped = sum(1 for r in rows if r["mem"]["top1"] and not r["cold"]["top1"]); hurt = sum(1 for r in rows if r["cold"]["top1"] and not r["mem"]["top1"])
print(f"\nmemory: a lesson led {len(led)} readouts, right {sum(r['mem']['top1'] for r in led)} times, {cross} of them taught by another author")
print(f"memory turned {helped} misses into right-first, and {hurt} right-first into misses; {rows[-1]['carried']} of {rows[-1]['lessons']} lessons still placed at the end")
print("\npaired exact McNemar on right-file-first:")
for t in ("Model D, cold", "Graphify", "BM25"):
    p, x, y = mcnemar([r["mem"]["top1"] for r in rows], [tools[t](r)["top1"] for r in rows])
    print(f"  Model D + memory vs {t:14} p={p:.2g}  (memory-only {x}, {t}-only {y})")
print(f"\ntokens per answer: Model D {sum(r['mem']['tokens'] for r in rows) / n:.0f}, Graphify {sum(G[r['hash']]['tokens'] for r in rows) / n:.0f}")
