"""PROTOCOL_REPLAY.md report -> report_replay.json"""
import json, os, sys
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
sys.path.insert(0, f"{B}/swe_sonnet")
import transcripts as TR
S = json.load(open(f"{H}/stream.json")); N = len(S)
rows = {f"{f}_{m}": [json.loads(l) for l in open(f"{H}/rows_{f}_{m}.jsonl")] for f in ("raw", "masked") for m in ("frozen", "learning")}
assert all(len(v) == N for v in rows.values()), {k: len(v) for k, v in rows.items()}

# ---- calibration from PROTOCOL_SWE_SONNET.md sessions (API-equivalent: task read and hand-back removed; eyes: task read removed)
P = {"input": 2.00, "write": 2.50, "read": 0.20, "output": 10.00}; PH = {"input": 0.10, "write": 0.125, "read": 0.01, "output": 0.50}
usd = lambda reqs, p: sum(r["input"] * p["input"] + r["write"] * p["write"] + r["read"] * p["read"] + r["output"] * p["output"] for r in reqs) / 1e6
ISS = json.load(open(f"{B}/swe/issues.json"))["issues"]; RO = json.load(open(f"{B}/swe_sonnet/readouts.json")); ix = TR.index()
A, Kh, Km, E = [], [], [], []
for i in ISS:
    for arm in ("alone", "kit"):
        reqs = TR.measure(ix[(arm, i["id"])][-1])["requests"]; adj = reqs[1:-1]
        v = (len(adj), usd(adj, P))
        if arm == "alone": A.append(v)
        else: (Kh if i["file"] in RO[i["id"]] else Km).append(v)
    if ("eyes", i["id"]) in ix:
        reqs = TR.measure(ix[("eyes", i["id"])][-1])["requests"]; E.append((len(reqs[1:]), usd(reqs[1:], PH)))
m = lambda L, j: float(np.mean([x[j] for x in L]))
cal = {"c_A": (m(A, 0), m(A, 1)), "c_K_hit": (m(Kh, 0), m(Kh, 1)), "c_K_miss": (m(Km, 0), m(Km, 1)), "c_E": (m(E, 0), m(E, 1)), "p_NS": 3 / 7,
       "n": {"alone": len(A), "kit hit": len(Kh), "kit miss": len(Km), "eyes": len(E)}}


def costs(form, j):
    fr, le = rows[f"{form}_frozen"], rows[f"{form}_learning"]; out = {"ALONE": [], "LAWS": [], "LAWS+LEARNING": [], "MODEL D": []}
    for a, b in zip(fr, le):
        k_f = cal["c_K_hit"][j] if a["hit"] else cal["c_K_miss"][j]; k_l = cal["c_K_hit"][j] if b["hit"] else cal["c_K_miss"][j]
        out["ALONE"].append(cal["c_A"][j]); out["LAWS"].append(k_f); out["LAWS+LEARNING"].append(k_l)
        out["MODEL D"].append(cal["c_E"][j] + cal["p_NS"] * k_l if b["lane"] else k_l)
        # exploratory, not pre-registered: the eyes fall back to search whenever the lane's first item is not a gold file
        out.setdefault("MODEL D (realistic)", []).append(cal["c_E"][j] + (0 if b["lane right"] else 1) * k_l if b["lane"] else k_l)
    return out


seen, rep = set(), []
for q in S: rep.append(any(g in seen for g in q["gold"])); seen.update(q["gold"])
dec = [(d * N // 10, (d + 1) * N // 10) for d in range(10)]
res = {"protocol sha256": json.load(open(f"{B}/prereg_hashes.json"))["PROTOCOL_REPLAY.md"]["sha256"], "questions": N,
       "calibration (requests, API-eq $)": cal}
for form in ("raw", "masked"):
    fr, le = rows[f"{form}_frozen"], rows[f"{form}_learning"]
    C = {j: costs(form, j) for j in (0, 1)}
    def blk(a, b):
        L = le[a:b]; F = fr[a:b]; lanes = [r for r in L if r["lane"]]
        d = {"questions": b - a, "dates": f"{S[a]['date']}..{S[b - 1]['date']}", "history repeat (gold file seen before)": round(np.mean(rep[a:b]), 3),
             "FROZEN file hit": round(np.mean([r["hit"] for r in F]), 3), "LEARNING file hit": round(np.mean([r["hit"] for r in L]), 3),
             "lane opened": round(len(lanes) / (b - a), 3), "lane right when opened": round(np.mean([r["lane right"] for r in lanes]), 3) if lanes else None}
        d["learning advantage (hit points)"] = round(d["LEARNING file hit"] - d["FROZEN file hit"], 3)
        for j, unit in ((0, "requests"), (1, "$")):
            mean = {k: float(np.mean(v[a:b])) for k, v in C[j].items()}
            d[f"projected {unit} per question"] = {k: round(v, 4 if unit == "$" else 3) for k, v in mean.items()}
            d[f"projected saving vs ALONE ({unit})"] = {k: round(mean["ALONE"] / v, 2) for k, v in mean.items() if k != "ALONE"}
        return d
    res[form] = {"overall": blk(0, N), "deciles": [blk(a, b) for a, b in dec]}
r, mk = res["raw"], res["masked"]; d0, d9 = r["deciles"][0], r["deciles"][-1]
res["R1"] = bool(r["overall"]["FROZEN file hit"] >= 0.60)
res["R2"] = bool(r["overall"]["LEARNING file hit"] > r["overall"]["FROZEN file hit"] and d9["learning advantage (hit points)"] > d0["learning advantage (hit points)"])
res["R3"] = bool(d9["lane opened"] > d0["lane opened"] and (r["overall"]["lane right when opened"] or 0) >= 0.5)
res["R4"] = bool(d9["projected requests per question"]["MODEL D"] < d0["projected requests per question"]["MODEL D"] and r["overall"]["projected saving vs ALONE (requests)"]["MODEL D"] >= 2.0)
res["R5"] = bool(mk["deciles"][-1]["learning advantage (hit points)"] > mk["deciles"][0]["learning advantage (hit points)"] and mk["deciles"][-1]["lane opened"] > mk["deciles"][0]["lane opened"])
json.dump(res, open(f"{H}/report_replay.json", "w"), indent=1)
print(json.dumps(cal, indent=1))
for form in ("raw", "masked"):
    o = res[form]["overall"]; print(f"\n== {form.upper()} overall: frozen hit {o['FROZEN file hit']}, learning hit {o['LEARNING file hit']}, lane {o['lane opened']} (right {o['lane right when opened']})")
    print("   saving vs ALONE (requests):", o["projected saving vs ALONE (requests)"], " ($):", o["projected saving vs ALONE ($)"])
    print("   decile | dates | repeat | frozen hit | learning hit | adv | lane | lane right | MODEL D req/q | MODEL D saving req | realistic saving req")
    for k, d in enumerate(res[form]["deciles"]):
        print(f"   {k + 1:2d} {d['dates']} {d['history repeat (gold file seen before)']:.2f} {d['FROZEN file hit']:.3f} {d['LEARNING file hit']:.3f} {d['learning advantage (hit points)']:+.3f} {d['lane opened']:.3f} {d['lane right when opened'] if d['lane right when opened'] is not None else '-'} {d['projected requests per question']['MODEL D']:.2f} {d['projected saving vs ALONE (requests)']['MODEL D']:.2f}x {d['projected saving vs ALONE (requests)']['MODEL D (realistic)']:.2f}x")
# exploratory sensitivity: drop the 81 questions whose ticket was fixed in an earlier commit
T = json.load(open(f"{H}/tickets.json"))["ticket repeat"]
keep = [k for k in range(N) if not T[k]]
for form in ("raw", "masked"):
    fr, le = rows[f"{form}_frozen"], rows[f"{form}_learning"]
    first, last = keep[:len(keep) // 10], keep[-(len(keep) // 10):]
    lane = lambda ks: round(np.mean([le[k]["lane"] for k in ks]), 3)
    res[form]["without repeat tickets"] = {"questions": len(keep), "lane first decile": lane(first), "lane last decile": lane(last),
        "learning hit": round(np.mean([le[k]["hit"] for k in keep]), 3), "frozen hit": round(np.mean([fr[k]["hit"] for k in keep]), 3)}
    print(form, "without repeat tickets:", res[form]["without repeat tickets"])
json.dump(res, open(f"{H}/report_replay.json", "w"), indent=1)
print({k: res[k] for k in ("R1", "R2", "R3", "R4", "R5")})
