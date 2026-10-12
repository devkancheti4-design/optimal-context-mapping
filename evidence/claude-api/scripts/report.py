"""PROTOCOL_VALUE report: python report.py [m3params]  ->  report_value.json (or m3_params.json)."""
import json, os, sys
import numpy as np

V = os.path.dirname(os.path.abspath(__file__)); H = os.path.dirname(V)
PHI = 0.57


def rows(f):
    return [json.loads(l) for l in open(f"{V}/{f}")] if os.path.exists(f"{V}/{f}") else []


def paired(a_rows, d_rows):
    A = {r["id"]: r for r in a_rows if not r["error"]}; D = {r["id"]: r for r in d_rows if not r["error"]}
    ids = [i for i in A if i in D]
    return ids, A, D


def factor(ids, A, D, key):
    a = np.array([A[i][key] for i in ids], float); d = np.array([D[i][key] for i in ids], float)
    if not len(ids) or d.mean() == 0:
        return None
    rng = np.random.default_rng(20261008); k = rng.integers(0, len(ids), (20000, len(ids)))
    boot = a[k].mean(1) / d[k].mean(1)
    return {"factor": round(a.mean() / d.mean(), 3), "ci95": [round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)],
            "alone mean": round(float(a.mean()), 5), "modeld mean": round(float(d.mean()), 5)}


def arm_stats(ids, R):
    rs = [R[i] for i in ids]
    if not rs:
        return {"n": 0}
    return {"n": len(rs), "right": sum(bool(r["right"]) for r in rs), "requests": round(float(np.mean([r["requests"] for r in rs])), 3),
            "tokens": round(float(np.mean([r["tokens"] for r in rs]))), "usd per issue": round(float(np.mean([r["usd"] for r in rs])), 5),
            "usd total": round(float(sum(r["usd"] for r in rs)), 4), "read path": sum(r.get("path") == "read" for r in rs)}


def compare(a_file, d_file, filt=None):
    a, d = rows(a_file), rows(d_file)
    if filt:
        a, d = [r for r in a if filt(r)], [r for r in d if filt(r)]
    ids, A, D = paired(a, d)
    return ids, A, D, {"alone": arm_stats(ids, A), "modeld": arm_stats(ids, D), "requests": factor(ids, A, D, "requests"),
                       "tokens": factor(ids, A, D, "tokens"), "usd": factor(ids, A, D, "usd"),
                       "errors": {"alone": sum(1 for r in a if r["error"]), "modeld": sum(1 for r in d if r["error"])}}


def turn_law(cmp):
    r_a, r_d = cmp["alone"]["requests"], cmp["modeld"]["requests"]
    pred = 1 + (1 - PHI) * (r_a - 1)
    return {"r_A": r_a, "r_D measured": r_d, "r_D predicted": round(pred, 3), "error": round(pred / r_d - 1, 3), "holds": abs(pred / r_d - 1) <= 0.20}


def session_law(ids, A, D):
    xs, ys = [], []
    for i in ids:
        t = np.array(A[i]["per request tokens"], float)
        if len(t) >= 2:
            j = np.arange(len(t), dtype=float); xs.append(j - j.mean()); ys.append(t - t.mean())
    X, Y = np.concatenate(xs), np.concatenate(ys); g = float(X @ Y / (X @ X))
    Pa = float(np.mean([A[i]["first tokens"] for i in ids])); Pd = float(np.mean([D[i]["first tokens"] for i in ids]))
    ra = float(np.mean([A[i]["requests"] for i in ids])); rd = float(np.mean([D[i]["requests"] for i in ids]))
    T = lambda r, P: r * P + g * r * (r - 1) / 2
    Sp = T(ra, Pa) / T(rd, Pd)
    St = float(np.mean([A[i]["tokens"] for i in ids]) / np.mean([D[i]["tokens"] for i in ids]))
    return {"g": round(g), "P_A": round(Pa), "P_D": round(Pd), "r_A": round(ra, 3), "r_D": round(rd, 3), "S_pred": round(Sp, 3),
            "S_T measured": round(St, 3), "error": round(Sp / St - 1, 3), "holds": abs(Sp / St - 1) <= 0.20}


def m3params():
    e1d = rows("e1_md.jsonl"); e1a = rows("e1_alone.jsonl")
    live = [json.loads(l) for l in open(f"{H}/claude_live/rows.jsonl")]
    reads = [r["usd"] for r in e1d if r["path"] == "read" and r["requests"] == 1] + [r["usd"] for r in live if r["path"] == "read" and r["requests"] == 1]
    p = {"A": float(np.mean([r["usd"] for r in e1a if not r["error"]])), "E": float(np.mean(reads)),
         "K": float(np.mean([r["usd"] for r in e1d if r["path"] == "teach" and not r["error"]])), "reads used for E": len(reads)}
    json.dump(p, open(f"{V}/m3_params.json", "w"), indent=1); print(p)



def batch23(R):
    """PROTOCOL_VALUE2 and PROTOCOL_VALUE3 scoring."""
    for run in (2, 3):
        ids, A, D, c = compare(f"f1_r{run}_alone.jsonl", f"f1_r{run}_md.jsonl")
        R[f"F1 run {run}"] = c
        if c["requests"]:
            R[f"P1 run {run}"] = c["requests"]["ci95"][0] > 1
            R[f"M1 F1 run {run}"] = turn_law(c); R[f"M2 F1 run {run}"] = session_law(ids, A, D)
    runs = [("e1_alone.jsonl", "e1_md.jsonl"), ("f1_r2_alone.jsonl", "f1_r2_md.jsonl"), ("f1_r3_alone.jsonl", "f1_r3_md.jsonl")]
    pa, pd = [], []
    for k, (a, d) in enumerate(runs):
        pa += [dict(r, id=f"{k}:{r['id']}") for r in rows(a)]; pd += [dict(r, id=f"{k}:{r['id']}") for r in rows(d)]
    ids, A, D = paired(pa, pd)
    if len(ids) > 114:
        R["F1 pooled"] = {"alone": arm_stats(ids, A), "modeld": arm_stats(ids, D), "requests": factor(ids, A, D, "requests"),
                          "usd": factor(ids, A, D, "usd"), "tokens": factor(ids, A, D, "tokens")}
        nr = len({i.split(":")[0] for i in ids})
        R["P2"] = R["F1 pooled"]["modeld"]["right"] / nr >= R["F1 pooled"]["alone"]["right"] / nr - 5
        R["P3"] = R["F1 pooled"]["usd"]["ci95"][0] > 1
    _, _, _, R["F2"] = compare("f2_alone.jsonl", "f2_md.jsonl")
    if R["F2"]["requests"]:
        R["P4 (V8 failure replicates)"] = R["F2"]["modeld"]["right"] < R["F2"]["alone"]["right"] - 5
    for pas in (1, 2):
        R[f"F3 pass {pas}"] = compare("f3_alone.jsonl", "f3_md.jsonl", lambda r, pas=pas: r["pass"] == pas)[3]
    if R["F3 pass 1"]["usd"]:
        R["P5"] = R["F3 pass 1"]["usd"]["factor"] >= 1.5
        R["P6"] = abs(R["F3 pass 1"]["modeld"]["right"] - R["F3 pass 1"]["alone"]["right"]) <= 3
    if R["F3 pass 2"]["usd"]:
        R["P7"] = R["F3 pass 2"]["usd"]["factor"] >= 4
    i4, A4, D4, R["F4"] = compare("f4_alone.jsonl", "f4_md.jsonl")
    if R["F4"]["requests"]:
        n = R["F4"]["alone"]["n"]
        R["P8"] = R["F4"]["requests"]["ci95"][0] > 1 and R["F4"]["modeld"]["right"] / n >= R["F4"]["alone"]["right"] / n - 0.05
        R["M1 F4"] = turn_law(R["F4"]); R["M2 F4"] = session_law(i4, A4, D4)
    for pas in (1, 2):
        R[f"G1 pass {pas}"] = compare("g1_alone.jsonl", "g1_md.jsonl", lambda r, pas=pas: r["pass"] == pas)[3]
    if R["G1 pass 1"]["usd"]:
        R["G1a"] = R["G1 pass 1"]["usd"]["factor"] >= 1.3
        R["G1b"] = abs(R["G1 pass 1"]["modeld"]["right"] - R["G1 pass 1"]["alone"]["right"]) <= 3
    if R["G1 pass 2"]["usd"]:
        R["G1c"] = R["G1 pass 2"]["usd"]["factor"] >= 4
    g2 = rows("g2.jsonl")
    if g2:
        S = {}
        for r in g2:
            S.setdefault((r["session"], r["arm"]), []).append(r)
        sess = []
        for sid in sorted({k[0] for k in S}):
            a, d = S.get((sid, "alone"), []), S.get((sid, "modeld"), [])
            sess.append({"session": sid, "alone usd": round(sum(r["usd"] for r in a), 4), "modeld usd": round(sum(r["usd"] for r in d), 4),
                         "alone requests": sum(r["requests"] for r in a), "modeld requests": sum(r["requests"] for r in d),
                         "alone right": sum(bool(r["right"]) for r in a), "modeld right": sum(bool(r["right"]) for r in d)})
        half = lambda arm, lo, hi: sum(r["usd"] for r in g2 if r["arm"] == arm and lo <= r["index"] <= hi)
        f1h, f2h = half("alone", 1, 7) / half("modeld", 1, 7), half("alone", 9, 15) / half("modeld", 9, 15)
        tok = sum(r["tokens"] for r in g2 if r["arm"] == "alone") / sum(r["tokens"] for r in g2 if r["arm"] == "modeld")
        req = sum(r["requests"] for r in g2 if r["arm"] == "alone") / sum(r["requests"] for r in g2 if r["arm"] == "modeld")
        per_index = {arm: [round(float(np.mean([r["usd"] for r in g2 if r["arm"] == arm and r["index"] == i])), 5) for i in range(1, 16)] for arm in ("alone", "modeld")}
        R["G2"] = {"sessions": sess, "cost factor reports 1-7": round(f1h, 3), "cost factor reports 9-15": round(f2h, 3),
                   "session token factor": round(tok, 3), "request factor": round(req, 3),
                   "cost factor": round(sum(x["alone usd"] for x in sess) / sum(x["modeld usd"] for x in sess), 3),
                   "mean usd by report index": per_index}
        R["G2a"] = all(x["modeld usd"] < x["alone usd"] for x in sess)
        R["G2b"] = f2h > f1h
        R["G2c"] = tok > req
    i3, A3, D3, R["G3"] = compare("g3_alone.jsonl", "g3_md.jsonl")
    if R["G3"]["requests"]:
        R["G3a"] = R["G3"]["requests"]["ci95"][0] > 1
        R["G3b"] = R["G3"]["usd"]["ci95"][0] > 1
        R["G3c"] = abs(R["G3"]["modeld"]["right"] - R["G3"]["alone"]["right"]) <= 3



def batch4(R):
    """PROTOCOL_VALUE4: the team stream on the Full Stack FastAPI Template, 3 runs pooled."""
    Q = {q["qid"]: q for q in json.load(open(f"{H}/questions_100.json"))}
    pa, pd = [], []
    for n in (1, 2, 3):
        pa += [dict(r, id=f"{n}:{r['id']}") for r in rows(f"v4_r{n}_alone.jsonl")]
        pd += [dict(r, id=f"{n}:{r['id']}") for r in rows(f"v4_r{n}_md.jsonl")]
    ids, A, D = paired(pa, pd)
    if not ids:
        return
    q = lambda i: Q[i.split(":", 1)[1]]
    rep = [i for i in ids if q(i).get("counts_as_repeat")]
    h1 = [i for i in ids if int(q(i)["qid"][1:]) <= 50]; h2 = [i for i in ids if int(q(i)["qid"][1:]) > 50]
    R["V4"] = {"alone": arm_stats(ids, A), "modeld": arm_stats(ids, D), "requests": factor(ids, A, D, "requests"),
               "usd": factor(ids, A, D, "usd"), "tokens": factor(ids, A, D, "tokens"),
               "repeats": {"n": len(rep), "usd": factor(rep, A, D, "usd"), "requests": factor(rep, A, D, "requests"),
                           "read share": round(sum(D[i]["path"] == "read" for i in rep) / len(rep), 3) if rep else None,
                           "right alone": sum(bool(A[i]["right"]) for i in rep), "right modeld": sum(bool(D[i]["right"]) for i in rep)},
               "first half usd factor": factor(h1, A, D, "usd")["factor"] if h1 else None,
               "second half usd factor": factor(h2, A, D, "usd")["factor"] if h2 else None,
               "new-question reads": sum(1 for i in ids if not q(i).get("counts_as_repeat") and D[i]["path"] == "read"),
               "runs complete": len({i.split(":")[0] for i in ids})}
    v = R["V4"]; n = v["alone"]["n"]
    R["C1"] = v["usd"]["ci95"][0] > 1
    R["C2"] = v["modeld"]["right"] / n >= v["alone"]["right"] / n - 0.05
    if rep:
        R["C3"] = v["repeats"]["usd"]["factor"] >= 3; R["C4"] = v["repeats"]["read share"] >= 0.5
    if h1 and h2:
        R["C5"] = v["second half usd factor"] > v["first half usd factor"]
    R["M1 V4"] = turn_law(v); R["M2 V4"] = session_law(ids, A, D)



def _judge(path, keyfn=lambda k: k):
    J = {}
    if os.path.exists(f"{V}/{path}"):
        for l in open(f"{V}/{path}"):
            r = json.loads(l); J[keyfn(r["key"])] = r["verdict"]
    return J


def batch567(R):
    """V5 (write the fix), V6/V6b (warm kit), V7 (reader fixes), V4 judge."""
    A = {r["id"]: r for r in rows("w_alone.jsonl")}; D = {r["id"]: r for r in rows("w_md.jsonl")}
    SA = {r["id"]: r for r in rows("w_scored_alone.jsonl")}; SD = {r["id"]: r for r in rows("w_scored_modeld.jsonl")}
    ids = [i for i in A if i in D and i in SA and i in SD]
    if ids:
        ra = sum(SA[i]["resolved"] for i in ids); rd = sum(SD[i]["resolved"] for i in ids)
        ua = sum(A[i]["usd"] for i in ids); ud = sum(D[i]["usd"] for i in ids)
        R["V5"] = {"n": len(ids), "resolved alone": ra, "resolved modeld": rd, "requests": factor(ids, A, D, "requests"),
                   "usd": factor(ids, A, D, "usd"), "tokens": factor(ids, A, D, "tokens"),
                   "usd per resolved alone": round(ua / ra, 4) if ra else None, "usd per resolved modeld": round(ud / rd, 4) if rd else None}
        R["W1"] = rd >= ra - 2; R["W2"] = R["V5"]["usd"]["ci95"][0] > 1; R["W3"] = R["V5"]["requests"]["ci95"][0] > 1
        R["W4"] = bool(ra and rd and ud / rd < ua / ra)
    order = [i["id"] for i in json.load(open(f"{H}/swe/issues.json"))["issues"]]
    load = lambda f: {r["id"]: r for r in rows(f)}
    AL = [load(f) for f in ("e1_alone.jsonl", "f1_r2_alone.jsonl", "f1_r3_alone.jsonl")]
    CO = [load(f) for f in ("e1_md.jsonl", "f1_r2_md.jsonl", "f1_r3_md.jsonl")]
    for tag, files in (("V6", ("warm_r1_md.jsonl", "warm_r2_md.jsonl")), ("V6b", ("warm_strict_r1_md.jsonl", "warm_strict_r2_md.jsonl"))):
        W = [load(f) for f in files]
        if not all(len(w) >= 114 for w in W):
            continue
        ids = [i for i in order if all(i in r and not r[i]["error"] for r in AL + CO + W)]
        m = lambda X, i, k: float(np.mean([r[i][k] for r in X]))
        def fac2(X, Y, k):
            x = np.array([m(X, i, k) for i in ids]); y = np.array([m(Y, i, k) for i in ids])
            rng = np.random.default_rng(20261008); kk = rng.integers(0, len(ids), (20000, len(ids))); b = x[kk].mean(1) / y[kk].mean(1)
            return {"factor": round(float(x.mean() / y.mean()), 3), "ci95": [round(float(np.percentile(b, 2.5)), 3), round(float(np.percentile(b, 97.5)), 3)],
                    "alone mean": round(float(x.mean()), 5), "modeld mean": round(float(y.mean()), 5)}
        rights = lambda X: float(np.mean([sum(bool(r[i]["right"]) for i in ids) for r in X]))
        R[tag] = {"n": len(ids), "vs cold usd": fac2(CO, W, "usd"), "vs alone usd": fac2(AL, W, "usd"), "vs alone requests": fac2(AL, W, "requests"),
                  "right per run": {"alone": round(rights(AL), 1), "cold": round(rights(CO), 1), "warm": round(rights(W), 1)},
                  "reads per run": [sum(r[i]["path"] == "read" for i in ids) for r in W],
                  "reads right": [sum(1 for r in W for i in ids if r[i]["path"] == "read" and r[i]["right"]), sum(1 for r in W for i in ids if r[i]["path"] == "read")]}
        v = R[tag]
        if tag == "V6":
            R["K1"] = v["vs cold usd"]["ci95"][0] > 1; R["K2"] = v["vs alone usd"]["factor"] >= 1.5
            R["K3"] = v["right per run"]["warm"] >= v["right per run"]["alone"] - 5; R["K4"] = min(v["reads per run"]) >= 10
        else:
            R["K5"] = v["right per run"]["warm"] >= v["right per run"]["alone"] - 5; R["K6"] = v["vs alone usd"]["factor"] >= 1.4
            R["K7"] = v["vs cold usd"]["factor"] > 1
    J4 = _judge("v4_judge.jsonl")
    if J4:
        md = {}
        for n in (1, 2, 3):
            for r in rows(f"v4_r{n}_md.jsonl"):
                md[f"{n}|modeld|{r['id']}"] = r["path"]
        def share(keys):
            keys = list(keys); c = [J4[k] for k in keys]
            return {"n": len(c), "right": round(c.count("RIGHT") / len(c), 3), "right or partial": round((c.count("RIGHT") + c.count("PARTIAL")) / len(c), 3), "wrong": c.count("WRONG")}
        R["V4 judge"] = {"alone": share(k for k in J4 if k.split("|")[1] == "alone"), "modeld": share(k for k in J4 if k.split("|")[1] == "modeld"),
                         "modeld teach": share(k for k in J4 if md.get(k) == "teach"), "modeld read": share(k for k in J4 if md.get(k) == "read")}
    J7 = _judge("v7_judge.jsonl")
    if J7:
        R["V7"] = {}
        for v, name in (("S", "strict Haiku reader"), ("N", "Sonnet reader"), ("NS", "Sonnet strict reader")):
            rs = rows(f"v7_{v}.jsonl"); c = [J7[f"{v}|{r['id']}"] for r in rs]; usd = sum(r["usd"] for r in rs) / len(rs)
            rd = [J7[f"{v}|{r['id']}"] for r in rs if r["path"] == "read"]
            R["V7"][v] = {"name": name, "n": len(rs), "right": round(c.count("RIGHT") / len(c), 3), "right or partial": round((c.count("RIGHT") + c.count("PARTIAL")) / len(c), 3),
                          "usd per question": round(usd, 5), "reads": len(rd), "reads right": rd.count("RIGHT")}
        alone_usd = R["V4"]["alone"]["usd per issue"]; alone_right = R["V4 judge"]["alone"]["right"]
        for v in R["V7"].values():
            v["saving vs alone"] = round(alone_usd / v["usd per question"], 2)
        R["Q1"] = any(v["right"] >= alone_right - 0.05 and v["saving vs alone"] >= 2 for v in R["V7"].values())
        R["Q2"] = R["V7"]["S"]["reads right"] / max(1, R["V7"]["S"]["reads"]) > R["V4 judge"]["modeld read"]["right"]
        R["Q3"] = R["V7"]["N"]["reads right"] / max(1, R["V7"]["N"]["reads"]) >= 0.60


def main():
    R = {"protocol sha256": json.load(open(f"{H}/prereg_hashes.json"))["PROTOCOL_VALUE.md"]["sha256"]}
    i1, A1, D1, R["E1"] = compare("e1_alone.jsonl", "e1_md.jsonl")
    e = R["E1"]
    if e["requests"]:
        R["V1"] = e["requests"]["ci95"][0] > 1 and e["modeld"]["right"] >= e["alone"]["right"] - 5
        R["V2"] = e["usd"]["ci95"][0] > 1
        R["M1 E1"] = turn_law(e); R["M2 E1"] = session_law(i1, A1, D1)
    i2, A2, D2, R["E2"] = compare("e2_alone.jsonl", "e2_md.jsonl")
    if R["E2"]["requests"]:
        md = [D2[i] for i in i2]; reads = [r for r in md if r["path"] == "read"]
        R["E2"]["read share"] = round(len(reads) / len(md), 3); R["E2"]["read precision"] = round(sum(r["right"] for r in reads) / len(reads), 3) if reads else None
        R["V3"] = R["E2"]["read share"] >= 0.40; R["V4"] = bool(reads) and R["E2"]["read precision"] >= 0.90
        R["V5"] = R["E2"]["usd"]["factor"] >= 2
        if os.path.exists(f"{V}/m3_params.json"):
            p = json.load(open(f"{V}/m3_params.json")); nu = 1 - R["E2"]["read share"]
            Sp = p["A"] / ((1 - nu) * p["E"] + nu * p["K"]); Sm = R["E2"]["usd"]["factor"]
            R["M3 E2"] = {"params": p, "nu": round(nu, 3), "S predicted": round(Sp, 3), "S measured": Sm, "error": round(Sp / Sm - 1, 3), "holds": abs(Sp / Sm - 1) <= 0.20}
    e3 = [r for r in rows("e3_md.jsonl") if not r["error"]]
    if e3:
        al = {r["id"]: r for r in rows("e1_alone.jsonl") if not r["error"]}
        ids = [r["id"] for r in e3 if r["id"] in al]
        acc_d = sum(r["right"] for r in e3 if r["id"] in al) / len(ids); acc_a = sum(al[i]["right"] for i in ids) / len(ids)
        false_reads = sum(1 for r in e3 if r["path"] == "read" and not r["right"])
        R["E3"] = {"B issues": len(e3), "modeld right": round(acc_d, 3), "alone right (E1, same issues)": round(acc_a, 3),
                   "read path fired": sum(r["path"] == "read" for r in e3), "false reads": false_reads,
                   "modeld usd per issue": round(float(np.mean([r["usd"] for r in e3])), 5)}
        R["V6"] = acc_d >= acc_a - 0.05; R["V7"] = false_reads <= 0.10 * len(e3)
    i4, A4, D4, R["E4"] = compare("e4_alone.jsonl", "e4_md.jsonl")
    if R["E4"]["requests"]:
        R["V8"] = R["E4"]["requests"]["ci95"][0] > 1 and R["E4"]["modeld"]["right"] >= R["E4"]["alone"]["right"] - 5
        R["M1 E4"] = turn_law(R["E4"]); R["M2 E4"] = session_law(i4, A4, D4)
    i5, A5, D5, R["E5"] = compare("e5_alone.jsonl", "e5_md.jsonl")
    if R["E5"]["requests"]:
        n = R["E5"]["alone"]["n"]
        R["V9"] = R["E5"]["requests"]["ci95"][0] > 1 and R["E5"]["modeld"]["right"] / n >= R["E5"]["alone"]["right"] / n - 0.05
        R["M1 E5"] = turn_law(R["E5"]); R["M2 E5"] = session_law(i5, A5, D5)
        for repo in ("sympy", "scikit-learn", "pytest"):
            pre = {"sympy": "sympy__", "scikit-learn": "scikit-learn__", "pytest": "pytest-dev__"}[repo]
            R[f"E5 {repo}"] = compare("e5_alone.jsonl", "e5_md.jsonl", lambda r, pre=pre: r["id"].startswith(pre))[3]
    for pas in (1, 2):
        R[f"E6 pass {pas}"] = compare("e6_alone.jsonl", "e6_md.jsonl", lambda r, pas=pas: r["pass"] == pas)[3]
    if R["E6 pass 1"]["usd"]:
        R["V10"] = R["E6 pass 1"]["usd"]["factor"] >= 2
        R["V11"] = abs(R["E6 pass 1"]["modeld"]["right"] - R["E6 pass 1"]["alone"]["right"]) <= 3
    if R["E6 pass 2"]["usd"]:
        R["V12"] = R["E6 pass 2"]["usd"]["factor"] >= 5
    batch23(R)
    batch4(R)
    batch567(R)
    R["program spend usd"] = round(sum(json.loads(l)["usd"] for l in open(f"{V}/ledger.jsonl")), 4)
    json.dump(R, open(f"{V}/report_value.json", "w"), indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o))
    print(json.dumps({k: v for k, v in R.items() if isinstance(v, bool) or k == "program spend usd"}, indent=1, default=str))


if __name__ == "__main__":
    m3params() if sys.argv[1:] == ["m3params"] else main()
