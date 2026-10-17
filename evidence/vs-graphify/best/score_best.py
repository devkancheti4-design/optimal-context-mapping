"""Both readings side by side (METHOD_BEST.md): as pre-registered, and with Graphify at its best. Standard library.
    python3 best/score_best.py"""
import json, math, os, re
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); B = f"{H}/best"; GI = f"{H}/four-repos"          # published layout
DOC = re.compile(r"\.(md|mdx|rst|txt|adoc)$", re.I)
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_tests?\.py$|(^|/)conftest\.py$")
load = lambda p: json.load(open(p)) if os.path.exists(p) else None


def mcnemar(a, b):
    n10 = sum(x and not y for x, y in zip(a, b)); n01 = sum(y and not x for x, y in zip(a, b)); n = n10 + n01; k = min(n10, n01)
    return n10, n01, (1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n))


def datasets():
    dj = load(f"{H}/questions/django2022.json")
    yield "Django 2022 (288 fixes)", [(dj, {"md_cold": load(f"{H}/results/dj_md_cold.json"), "md_cover": load(f"{H}/results/dj_md_cover.json"),
                                           "gf_printed": load(f"{H}/results/dj_gf.json"), "gf_best": load(f"{B}/dj_gf_best.json")})], ("q", "raw")
    lite = []
    for n in sorted(p[5:-5] for p in os.listdir(f"{H}/questions") if p.startswith("lite_")):
        lite.append((load(f"{H}/questions/lite_{n}.json"), {"md_cold": load(f"{H}/results/lite_md_cold_{n}.json"), "md_cover": load(f"{H}/results/lite_md_cover_{n}.json"),
                                                            "gf_printed": load(f"{H}/results/lite_gf_{n}.json"), "gf_best": load(f"{B}/lite_gf_best_{n}.json")}))
    yield "SWE-bench Lite (285 issues, 12 repos)", lite, ("title", "q400")
    four = []
    for p in sorted(os.listdir(f"{GI}/questions")):
        if p.endswith(".list.json"):
            b = p[:-10]; four.append((load(f"{GI}/questions/{p}"), {"md_cold": load(f"{GI}/vs_results/md_{b}.json"), "gf_printed": load(f"{GI}/vs_results/gf_{b}.json"),
                                                                    "gf_best": load(f"{B}/four_gf_best_{b}.json")}))
    yield "Four Python repos (requests, itsdangerous, httpx, click; 172 fixes)", four, ("q", "raw")


def lists(res, arm, i, q):
    """The arm's file list for one question, by reading; docs dropped in every reading except 'as pre-registered'."""
    if arm == "md_cold_notests":
        return [f for f in res["md_cold"][i][q]["files"] if not TEST.search(f)]
    if arm in ("gf_seeds", "gf_byfile"):
        return [f for f in res["gf_best"][i][q]["seeds" if arm == "gf_seeds" else "by file"] if not DOC.search(f)]
    if arm == "gf_printed_nodocs":
        return [f for f in res["gf_printed"][i][q]["files"] if not DOC.search(f)]
    return res[arm][i][q]["files"]


out = {}
for title, sets, queries in datasets():
    sets = [(qs, r) for qs, r in sets if qs and all(v is not None for v in r.values())]
    if not sets:
        continue
    arms = ["md_cover"] if "md_cover" in sets[0][1] else []
    arms += ["md_cold", "md_cold_notests", "gf_printed", "gf_printed_nodocs", "gf_seeds", "gf_byfile"]
    rep = {"n": sum(len(qs) for qs, _ in sets)}
    for q in queries:
        hits = {a: {k: [] for k in (1, 3, 5)} for a in arms}
        for qs, res in sets:
            for it in qs:
                i = str(it["id"])
                for a in arms:
                    L = lists(res, a, i, q)
                    for k in (1, 3, 5):
                        hits[a][k].append(any(f in it["gold"] for f in L[:k]))
        tab = {a: [sum(hits[a][k]) for k in (1, 3, 5)] for a in arms}
        best = max(("gf_printed_nodocs", "gf_seeds", "gf_byfile"), key=lambda a: (tab[a][0], tab[a][2]))
        rep[q] = {"top1/3/5": tab, "graphify at its best": best,
                  "mcnemar top-1 md_cold vs graphify best (md only, gf only, p)": mcnemar(hits["md_cold"][1], hits[best][1]),
                  "mcnemar top-5 md_cold vs graphify best": mcnemar(hits["md_cold"][5], hits[best][5])}
        rep[q]["mcnemar top-1 md_cold_notests vs graphify best (same test filter)"] = mcnemar(hits["md_cold_notests"][1], hits[best][1])
        rep[q]["mcnemar top-5 md_cold_notests vs graphify best (same test filter)"] = mcnemar(hits["md_cold_notests"][5], hits[best][5])
        if "md_cover" in arms:
            rep[q]["mcnemar top-1 md_cover vs graphify best"] = mcnemar(hits["md_cover"][1], hits[best][1])
    out[title] = rep
print(json.dumps(out, indent=1)); json.dump(out, open(f"{B}/report_best.json", "w"), indent=1)
