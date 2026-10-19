"""Score METHOD.md: right first / top 5 per arm, McNemar, by quarter for B, readouts the law reordered."""
import json, math
TY = "../team-year (the run used the original team-year folder)"
date = {x["k"]: x["date"] for x in json.load(open(f"{TY}/window_2022.json"))}
def mcn(a, b):
    n10 = sum(x and not y for x, y in zip(a, b)); n01 = sum(y and not x for x, y in zip(a, b)); n = n10 + n01; k = min(n10, n01)
    return n10, n01, (1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n))
for exp, arms in (("A", ("on", "off")), ("B", ("forced", "gate"))):
    R = {a: json.load(open(f"results_{exp}_{a}.json")) for a in arms}
    rows = {a: R[a]["rows"] for a in arms}
    print(f"\n{exp}: " + " | ".join(f"{a}: right first {sum(r['right1'] for r in rows[a])}, top 5 {sum(r['right5'] for r in rows[a])}, "
                                    f"law in use on {sum(r['law_on'] for r in rows[a])} readouts" for a in arms))
    a, b = arms
    print(f"   paired right first ({a} only, {b} only, p): {mcn([r['right1'] for r in rows[a]], [r['right1'] for r in rows[b]])}")
    print(f"   paired top 5: {mcn([r['right5'] for r in rows[a]], [r['right5'] for r in rows[b]])}")
    print("   final law state:", {x: R[x]['law_state'] for x in arms})
    if exp == "B":
        for Q in (1, 2, 3, 4):
            sel = [i for i, r in enumerate(rows[a]) if (int(date[r["k"]][5:7]) - 1) // 3 + 1 == Q]
            print(f"   Q{Q}: " + ", ".join(f"{x} {sum(rows[x][i]['right1'] for i in sel)}/{len(sel)}" for x in arms))
