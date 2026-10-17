"""PROTOCOL_VS_GRAPHIFY scorer. Part A: right file first, in the top 3 and top 5, readout tokens (characters / 4), exact
McNemar on paired hits. Part B: the bill, requests and right answers (PROTOCOL_TEAM_YEAR's D4 measure) per arm on the
paired fixes; exact McNemar on right. Then the predictions G1-G7. Standard library only.
    python score.py"""
import glob, json, math, os
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = f"{H}/results"; TY = os.path.expanduser("~/neos/outreach/team-year")
REPOS = ["astropy", "django", "flask", "matplotlib", "pylint", "pytest", "requests", "scikit-learn", "seaborn", "sphinx", "sympy", "xarray"]
ARMS = ("md_cold", "md_cover", "gf")


def mcnemar(a, b):
    n10 = sum(x and not y for x, y in zip(a, b)); n01 = sum(y and not x for x, y in zip(a, b)); n = n10 + n01
    k = min(n10, n01)
    return n10, n01, (1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n))


def part_a(qsets):
    """qsets: [(questions, {arm: results})] -> {query: {arm: hits}}"""
    out = {}
    for qs, res in qsets:
        for it in qs:
            for name in it["queries"]:
                for arm in ARMS:
                    r = res[arm][str(it["id"])][name]
                    d = out.setdefault(name, {}).setdefault(arm, {"h1": [], "h3": [], "h5": [], "tok": [], "taught": 0})
                    for k in (1, 3, 5):
                        d[f"h{k}"].append(any(f in it["gold"] for f in r["files"][:k]))
                    d["tok"].append(r["chars"] / 4); d["taught"] += r["taught"]
    rep = {}
    for name, arms in out.items():
        rep[name] = {arm: {"n": len(d["h1"]), "top1/3/5": [sum(d["h1"]), sum(d["h3"]), sum(d["h5"])],
                           "tokens": round(sum(d["tok"]) / len(d["tok"])), "taught-led": d["taught"]} for arm, d in arms.items()}
        for a, b in (("md_cover", "gf"), ("md_cold", "gf"), ("md_cover", "md_cold")):
            for k in (1, 5):
                rep[name][f"mcnemar top-{k} {a} vs {b} ({a} only, {b} only, p)"] = mcnemar(arms[a][f"h{k}"], arms[b][f"h{k}"])
    return rep


load = lambda p: json.load(open(p)) if os.path.exists(p) else None
rep = {}
dj = load(f"{H}/questions/django2022.json"); res = {a: load(f"{R}/dj_{a}.json") for a in ARMS}
if all(res.values()):
    rep["A django 2022 (288)"] = part_a([(dj, res)])
lite = []
for n in REPOS:
    res = {a: load(f"{R}/lite_{a}_{n}.json") for a in ARMS}
    if all(res.values()):
        lite.append((load(f"{H}/questions/lite_{n}.json"), res))
if lite:
    rep[f"A swe-bench lite ({sum(len(q) for q, _ in lite)} issues, {len(lite)} repos)"] = part_a(lite)


def rows(pattern):
    return {json.loads(l)["k"]: json.loads(l) for f in sorted(glob.glob(pattern)) for l in open(f)}


def cited(r):
    if r["path"] != "read":
        return r["right"]
    t = r.get("answer", "")
    return any(g in t or ("django/" + g) in t for g in r["gold"])


B = {"graphify": rows(f"{R}/rows_gf*.jsonl"), "md_final": rows(f"{R}/rows_final.jsonl"),
     "md_cold": rows(f"{TY}/rows_md.jsonl"), "alone": rows(f"{TY}/rows_alone*.jsonl")}
ks = sorted(set.intersection(*[set(v) for v in B.values()])) if all(B.values()) else []
if ks:
    b = {arm: {"usd": round(sum(v[k]["usd"] for k in ks), 3), "requests": sum(v[k]["requests"] for k in ks),
               "right": sum(cited(v[k]) for k in ks), "read path": sum(v[k]["path"] == "read" for k in ks)} for arm, v in B.items()}
    b["paired fixes"] = len(ks)
    b["mcnemar right md_final vs graphify (md only, graphify only, p)"] = mcnemar([cited(B["md_final"][k]) for k in ks], [cited(B["graphify"][k]) for k in ks])
    b["mcnemar right graphify vs alone (graphify only, alone only, p)"] = mcnemar([cited(B["graphify"][k]) for k in ks], [cited(B["alone"][k]) for k in ks])
    q = lambda d: (int(d[5:7]) - 1) // 3 + 1
    b["by quarter, $ graphify / md_final"] = {f"Q{Q}": round(sum(B["graphify"][k]["usd"] for k in ks if q(B["graphify"][k]["date"]) == Q) /
                                                      max(1e-9, sum(B["md_final"][k]["usd"] for k in ks if q(B["graphify"][k]["date"]) == Q)), 2) for Q in (1, 2, 3, 4)}
    rep["B end to end, Django 2022 with Claude"] = b
P = {}
A = rep.get("A django 2022 (288)"); L = next((v for k, v in rep.items() if k.startswith("A swe-bench")), None); E = rep.get("B end to end, Django 2022 with Claude")
if A:
    P["G1 django: md_cover right first > graphify"] = A["q"]["md_cover"]["top1/3/5"][0] > A["q"]["gf"]["top1/3/5"][0]
if L:
    P["G2 lite titles: md_cold top-5 > graphify"] = L["title"]["md_cold"]["top1/3/5"][2] > L["title"]["gf"]["top1/3/5"][2]
    P["G3 lite titles: md_cover right first > md_cold"] = L["title"]["md_cover"]["top1/3/5"][0] > L["title"]["md_cold"]["top1/3/5"][0]
if A and L:
    sets = [A["q"], A["raw"], L["title"], L["q400"]]
    P["G4 readout tokens: md_cold and md_cover < graphify on every query set"] = all(s[a]["tokens"] < s["gf"]["tokens"] for s in sets for a in ("md_cold", "md_cover"))
if E:
    P["G5 bill: graphify / md_final >= 1.5x"] = E["graphify"]["usd"] / E["md_final"]["usd"] >= 1.5
    P["G6 work: md_final right >= graphify right - 3% of fixes"] = E["md_final"]["right"] >= E["graphify"]["right"] - 0.03 * E["paired fixes"]
    P["G7 coverage pays: md_final $ < md_cold $"] = E["md_final"]["usd"] < E["md_cold"]["usd"]
rep["predictions"] = P
print(json.dumps(rep, indent=1))
json.dump(rep, open(f"{R}/report.json", "w"), indent=1)
