"""METHOD.md measures from results_<set>.jsonl -> report.json and a table on stdout.  python score.py"""
import glob, json, math, os

H = os.path.dirname(os.path.abspath(__file__))


def hit(files, gold):
    return any(f == g or f.endswith("/" + g) for f in files for g in gold)


def line_hit(items, lines):
    return any(f == gf and a <= hi and b >= lo for f, a, b in items[:5] for gf, rngs in lines.items() for lo, hi in rngs)


def mcnemar(b, c):
    """Exact two-sided McNemar p on the b and c discordant pairs."""
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


report = {}
for path in sorted(glob.glob(f"{H}/results_*.jsonl")):
    name = os.path.basename(path)[8:-6]; R = [json.loads(l) for l in open(path)]
    for qk in R[0]["q"]:
        s = {"n": len(R)}; first = {}
        for arm in ("off", "on"):
            F = [list(dict.fromkeys(f for f, _, _ in r["q"][qk][arm])) for r in R]
            first[arm] = [hit(f[:1], r["gold"]) for f, r in zip(F, R)]
            s[arm] = {"right_first": sum(first[arm]), "top5": sum(hit(f[:5], r["gold"]) for f, r in zip(F, R))}
            if any(r["lines"] for r in R):
                s[arm]["line_top5"] = sum(line_hit(r["q"][qk][arm], r["lines"]) for r in R)
        if R[0]["q"][qk].get("grep") is not None:
            s["grep"] = {"right_first": sum(hit(r["q"][qk]["grep"][:1], r["gold"]) for r in R),
                         "top5": sum(hit(r["q"][qk]["grep"][:5], r["gold"]) for r in R)}
        b = sum(o and not n for o, n in zip(first["off"], first["on"])); c = sum(n and not o for o, n in zip(first["off"], first["on"]))
        s["paired_right_first"] = {"on_only": c, "off_only": b, "p": float(f"{mcnemar(b, c):.3g}")}
        s["changed"] = sum(r["q"][qk]["off"] != r["q"][qk]["on"] for r in R)
        s["exempt"] = sum(bool(r["exempt"][qk] if isinstance(r["exempt"], dict) else r["exempt"]) for r in R)
        report[f"{name}/{qk}"] = s

json.dump(report, open(f"{H}/report.json", "w"), indent=1)
pct = lambda x, n: f"{x} ({x / n:.0%})"
for k, s in report.items():
    n = s["n"]; g = s.get("grep")
    print(f"\n{k}  n={n}  readouts changed {s['changed']}, exempt (about tests) {s['exempt']}")
    print(f"  {'':<22}{'OFF (0.5.2)':>14}{'ON (0.5.3)':>14}{'grep-first':>14}")
    for m, label in (("right_first", "right file first"), ("top5", "right file in top 5"), ("line_top5", "changed line in top 5")):
        if m in s["off"]:
            print(f"  {label:<22}{pct(s['off'][m], n):>14}{pct(s['on'][m], n):>14}{(pct(g[m], n) if g and m in g else '-'):>14}")
    p = s["paired_right_first"]
    print(f"  paired right-first: ON only {p['on_only']}, OFF only {p['off_only']}, exact McNemar p = {p['p']}")
