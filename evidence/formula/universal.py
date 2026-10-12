"""PROTOCOL_UNIVERSAL.md leave-one-out test -> universal.json"""
import json, os
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
C = json.load(open(f"{H}/cases.json"))
T = lambda r, P, g: r * P + g * r * (r - 1) / 2


def profile(sessions):
    xs, ys = [], []
    for s in sessions:
        t = np.array(s["tokens"], float); j = np.arange(len(t), dtype=float)
        if len(t) >= 2: xs.append(j - j.mean()); ys.append(t - t.mean())
    X, Y = np.concatenate(xs), np.concatenate(ys)
    return {"g": float(X @ Y / (X @ X)), "P": float(np.mean([s["tokens"][0] for s in sessions if s["tokens"]])),
            "r": float(np.mean([len(s["tokens"]) for s in sessions])), "A": float(np.mean([sum(s["tokens"]) for s in sessions]))}


laws = [k for k in C if C[k]["kind"] == "laws"]; hyb = [k for k in C if C[k]["kind"] == "hybrid"]
prof = {k: (profile(C[k]["alone"]), profile(C[k]["kit"])) for k in laws}
phi = {k: (prof[k][0]["r"] - prof[k][1]["r"]) / (prof[k][0]["r"] - C[k]["q"]) for k in laws}
fam = lambda k: "gemini" if "Gemini" in k else "claude"
ref = {"claude": "C1 Sonnet 5.5, real bugs", "gemini": "C2 Gemini 2.5 Flash, real bugs"}
delta_ref = {f: prof[ref[f]][1]["P"] - prof[ref[f]][0]["P"] for f in ref}; R_ref = {f: C[ref[f]]["R"] for f in ref}
Delta = lambda k: delta_ref[fam(k)] * C[k]["R"] / R_ref[fam(k)]
out = {"phi per laws case": {k: round(v, 3) for k, v in phi.items()}, "Delta per question (tokens)": {k: round(Delta(k)) for k in C}, "cases": {}}

for k in laws:
    a, kt = prof[k]; q = C[k]["q"]
    ph = float(np.mean([phi[o] for o in laws if o != k]))
    rK = q + (1 - ph) * (a["r"] - q); PK = a["P"] + Delta(k) * (q + 1) / 2
    K = T(rK, PK, a["g"]); S_pred = a["A"] / K; S_meas = a["A"] / kt["A"]
    others = [o for o in laws if o != k]
    B1 = float(np.mean([prof[o][0]["A"] / prof[o][1]["A"] for o in others])); B2 = 1 / (1 - ph)
    out["cases"][k] = {"phi (LOO)": round(ph, 3), "r_alone": round(a["r"], 2), "r_K pred / meas": [round(rK, 2), round(kt["r"], 2)],
                       "P_alone": round(a["P"]), "P_K pred / meas": [round(PK), round(kt["P"])], "g": round(a["g"]),
                       "K pred / meas (tokens per session)": [round(K), round(kt["A"])], "S_pred": round(S_pred, 3), "S_meas": round(S_meas, 3),
                       "error": round(S_pred / S_meas - 1, 3), "B1": round(B1, 3), "B2": round(B2, 3)}

ph_h = float(np.mean([phi[o] for o in laws if not o.startswith("C3")]))
for k in hyb:
    pq = C[k]["per question"]; run = k[-1]
    # ALONE profile of the same run (C3's sessions for this run) -> single-question body session
    alone_sessions = [s for s in C["C3 Gemini 2.5 Flash, codebase questions"]["alone"]]
    rr = [json.loads(l) for l in open(f"{B}/api/runs/alone_r{run}/requests.jsonl")]
    sess = {}
    for x in rr: sess.setdefault(x["task"], []).append(x["prompt"] + x["output"] + x["thoughts"])
    a = profile([{"tokens": v} for v in sess.values()])
    r1 = float(np.mean([x["alone turns"] for x in pq]))
    rK1 = 1 + (1 - ph_h) * (r1 - 1); PK1 = a["P"] + Delta(k)
    K1 = T(rK1, PK1, a["g"])
    E = float(np.mean([x["eyes tokens"] for o in hyb if o != k for x in C[o]["per question"] if x["path"] in ("eyes", "eyes -> body")]))
    n = {p: sum(x["path"] == p for x in pq) for p in ("eyes", "eyes -> body", "body")}
    MD_pred = (n["eyes"] * E + n["eyes -> body"] * (E + K1) + n["body"] * K1) / len(pq)
    MD_meas = float(np.mean([x["tokens"] for x in pq])); A = float(np.mean([x["alone tokens"] for x in pq]))
    others = [o for o in hyb if o != k]
    B1 = float(np.mean([np.mean([x["alone tokens"] for x in C[o]["per question"]]) / np.mean([x["tokens"] for x in C[o]["per question"]]) for o in others]))
    body_meas = float(np.mean([x["body tokens"] for x in pq if x["path"] != "eyes"]))
    out["cases"][k] = {"phi (LOO, laws cases without C3)": round(ph_h, 3), "nu (body share)": round((n["body"] + n["eyes -> body"]) / len(pq), 3),
                       "alone turns per question": round(r1, 2), "P_1": round(a["P"]), "g": round(a["g"]),
                       "K1 pred / meas body tokens": [round(K1), round(body_meas)], "E (LOO)": round(E),
                       "Model D tokens per question pred / meas": [round(MD_pred), round(MD_meas)], "A tokens per question": round(A),
                       "S_pred": round(A / MD_pred, 3), "S_meas": round(A / MD_meas, 3), "error": round((A / MD_pred) / (A / MD_meas) - 1, 3), "B1": round(B1, 3), "B2": None}

E_ = lambda key: [abs(np.log(c[key] / c["S_meas"])) for c in out["cases"].values() if c.get(key)]
out["mean |log error|"] = {"UF": round(float(np.mean(E_("S_pred"))), 4), "B1": round(float(np.mean(E_("B1"))), 4),
                           "B2 (laws cases only)": round(float(np.mean(E_("B2"))), 4),
                           "UF on laws cases only": round(float(np.mean([abs(np.log(out['cases'][k]['S_pred'] / out['cases'][k]['S_meas'])) for k in laws])), 4)}
out["U1"] = all(abs(c["error"]) <= 0.25 for c in out["cases"].values())
out["U2"] = out["mean |log error|"]["UF"] < out["mean |log error|"]["B1"] and out["mean |log error|"]["UF on laws cases only"] < out["mean |log error|"]["B2 (laws cases only)"]
out["protocol sha256"] = json.load(open(f"{B}/prereg_hashes.json"))["PROTOCOL_UNIVERSAL.md"]["sha256"]
json.dump(out, open(f"{H}/universal.json", "w"), indent=1)
print("phi per laws case:", out["phi per laws case"])
print(f"{'case':50s} {'S_pred':>7s} {'S_meas':>7s} {'error':>7s} {'B1':>6s} {'B2':>6s}")
for k, c in out["cases"].items(): print(f"{k:50s} {c['S_pred']:7.2f} {c['S_meas']:7.2f} {c['error']:+7.1%} {c['B1']:6.2f} {c['B2'] if c['B2'] else '-':>6}")
print(out["mean |log error|"]); print("U1", out["U1"], "U2", out["U2"])
for k in hyb: print(k, {x: out["cases"][k][x] for x in ("K1 pred / meas body tokens", "E (LOO)", "Model D tokens per question pred / meas", "nu (body share)")})
