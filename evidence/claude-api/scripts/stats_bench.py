"""Results for PROTOCOL_SWEQA and PROTOCOL_SWECB (no model calls).  python stats_bench.py <qa | cb>"""
import json, os, random, sys
from statistics import mean

V = os.path.dirname(os.path.abspath(__file__))
DIMS = ("correctness", "completeness", "relevance", "clarity", "reasoning")


def rows(p):
    return [json.loads(l) for l in open(f"{V}/{p}")] if os.path.exists(f"{V}/{p}") else []


def boot(pairs, stat, n=20000, seed=20261008):
    rng = random.Random(seed); k = len(pairs); out = []
    for _ in range(n):
        s = [pairs[rng.randrange(k)] for _ in range(k)]
        out.append(stat(s))
    out.sort()
    return [round(out[int(0.025 * n)], 4), round(out[int(0.975 * n)], 4)]


def qa():
    md = {r["id"]: r for r in rows("qa_md.jsonl")}; al = {r["id"]: r for r in rows("qa_alone.jsonl")}
    jd = {j["key"]: j for j in rows("qa_judge.jsonl")}
    repos = sorted({i.rsplit("-", 1)[0] for i in md})
    done = [r for r in repos if all(f"{r}-{k:02d}" in md and f"{r}-{k:02d}" in al and f"modeld|{r}-{k:02d}" in jd
                                    and f"alone|{r}-{k:02d}" in jd for k in range(1, 49))]
    P = []
    for r in done:
        for k in range(1, 49):
            i = f"{r}-{k:02d}"; a, m = al[i], md[i]; ja, jm = jd[f"alone|{i}"], jd[f"modeld|{i}"]
            P.append({"id": i, "repo": r, "k": k, "ca": a["usd"], "cm": m["usd"], "ra": a["requests"], "rm": m["requests"],
                      "sa": ja["total"], "sm": jm["total"], "path": m["path"], "da": ja["scores"], "dm": jm["scores"],
                      "err": bool(a["error"] or m["error"])})
    scored = [p for p in P if p["sa"] is not None and p["sm"] is not None]
    ratio = lambda s: sum(p["ca"] for p in s) / max(1e-9, sum(p["cm"] for p in s))
    diff = lambda s: mean(p["sm"] - p["sa"] for p in s)
    early = [p for p in P if p["k"] <= 24]; late = [p for p in P if p["k"] > 24]
    out = {
        "repositories finished": done, "questions": len(P), "graded pairs": len(scored),
        "unparsed or missing grades": len(P) - len(scored), "errors": sum(p["err"] for p in P),
        "alone $ per question": round(mean(p["ca"] for p in P), 5), "model d $ per question": round(mean(p["cm"] for p in P), 5),
        "cost ratio alone/model d": round(ratio(P), 3), "cost ratio 95% CI": boot(P, ratio),
        "alone requests per question": round(mean(p["ra"] for p in P), 2), "model d requests per question": round(mean(p["rm"] for p in P), 2),
        "alone score /100": round(mean(p["sa"] for p in scored), 2), "model d score /100": round(mean(p["sm"] for p in scored), 2),
        "score difference (model d - alone)": round(diff(scored), 2), "score difference 95% CI": boot(scored, diff),
        "per dimension /20": {d: {"alone": round(mean(p["da"][d] for p in scored), 2), "model d": round(mean(p["dm"][d] for p in scored), 2)} for d in DIMS},
        "cost ratio questions 1-24": round(ratio(early), 3), "cost ratio questions 25-48": round(ratio(late), 3),
        "model d answers from the reader": f"{sum(p['path'] == 'read' for p in P)} of {len(P)}",
        "model d reader answers' score": round(mean([p["sm"] for p in scored if p["path"] == "read"] or [0]), 2),
        "per repository": {r: {"alone $": round(sum(p["ca"] for p in P if p["repo"] == r), 3), "model d $": round(sum(p["cm"] for p in P if p["repo"] == r), 3),
                               "alone score": round(mean([p["sa"] for p in scored if p["repo"] == r] or [0]), 1),
                               "model d score": round(mean([p["sm"] for p in scored if p["repo"] == r] or [0]), 1)} for r in done},
        "judge $": round(sum(j["usd"] for j in jd.values()), 3),
    }
    out["predictions"] = {"Q1 ratio >= 1.3": out["cost ratio alone/model d"] >= 1.3,
                          "Q2 score no more than 3 below": out["score difference (model d - alone)"] >= -3,
                          "Q3 saving grows": out["cost ratio questions 25-48"] >= out["cost ratio questions 1-24"],
                          "Q4 reader under 20%": sum(p["path"] == "read" for p in P) < 0.2 * max(1, len(P))}
    json.dump(out, open(f"{V}/report_sweqa.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


def cb():
    arms = ("alone", "cold", "exp")
    run = {a: {r["id"]: r for r in rows(f"cb_{a}.jsonl")} for a in arms}
    sc = {a: {r["id"]: r["resolved"] for r in rows(f"cb_scored_{a}.jsonl")} for a in arms}
    ids = sorted(set.intersection(*[set(sc[a]) for a in arms]))
    out = {"tasks finished in all three arms": len(ids)}
    for a in arms:
        n = sum(sc[a][i] for i in ids); usd = sum(run[a][i]["usd"] for i in ids)
        out[a] = {"resolved": n, "of": len(ids), "$ per task": round(usd / max(1, len(ids)), 4),
                  "$ per resolved": round(usd / n, 4) if n else None, "requests per task": round(mean([run[a][i]["requests"] for i in ids] or [0]), 2)}
        if a != "alone":
            out[a]["readout named a gold file"] = sum(run[a][i]["named gold"] for i in ids)
            out[a]["readout led with a learned match"] = sum(run[a][i]["learned"] for i in ids)
    out["per task"] = {i: {a: sc[a][i] for a in arms} for i in ids}
    if ids:
        out["predictions"] = {"C1 exp >= alone": out["exp"]["resolved"] >= out["alone"]["resolved"],
                              "C2 exp >= cold": out["exp"]["resolved"] >= out["cold"]["resolved"],
                              "C3 exp $/resolved < alone": bool(out["exp"]["$ per resolved"] and out["alone"]["$ per resolved"]
                                                                and out["exp"]["$ per resolved"] < out["alone"]["$ per resolved"]),
                              "C4 exp names gold more than cold": out["exp"]["readout named a gold file"] > out["cold"]["readout named a gold file"]}
    json.dump(out, open(f"{V}/report_swecb.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"qa": qa, "cb": cb}[sys.argv[1]]()
