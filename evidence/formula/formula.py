"""PROTOCOL_FORMULA.md -> formula.json. Sessions as lists of per-request tokens, plus exploration calls, for D1-D5."""
import glob, json, os, re, sys
from collections import defaultdict
import numpy as np
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.expanduser("~/.claude/projects/-Users-kanchetidevieswar-neos")
EXPL = re.compile(r"/(search|read|list)\.sh\b")


def transcript(aid):
    fs = glob.glob(f"{TR}/*/subagents/agent-{aid}.jsonl")
    if not fs: return None
    seen, reqs, calls = set(), [], 0
    for line in open(fs[0]):
        d = json.loads(line)
        if d.get("type") != "assistant": continue
        m = d.get("message") or {}; u = m.get("usage")
        if u and m.get("id") not in seen:
            seen.add(m["id"]); reqs.append(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("output_tokens", 0))
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                calls += len(EXPL.findall(str((b.get("input") or {}).get("command", ""))))
    return {"tokens": reqs, "calls": calls}


def d1():
    sys.path.insert(0, f"{B}/swe_sonnet"); import transcripts as T
    ix = T.index(); out = {"alone": [], "kit": []}
    for i in json.load(open(f"{B}/swe/issues.json"))["issues"]:
        for arm in out:
            reqs = T.measure(ix[(arm, i["id"])][-1])["requests"][1:-1]      # API-equivalent (DS1/DS2)
            c = [json.loads(l)["cmd"] for l in open(f"{B}/swe_sonnet/agents/{arm}/{i['id']}/calls.jsonl")] if os.path.exists(f"{B}/swe_sonnet/agents/{arm}/{i['id']}/calls.jsonl") else []
            out[arm].append({"tokens": [r["input"] + r["write"] + r["read"] + r["output"] for r in reqs], "calls": sum(x != "submit" for x in c)})
    return out


def d2():
    out = {}
    for arm in ("alone", "kit"):
        S = defaultdict(list)
        for l in open(f"{B}/swe/runs/{arm}/requests.jsonl"):
            x = json.loads(l)
            if x.get("path", "agent") == "agent": S[x["id"]].append(x["prompt"] + x["output"] + x["thoughts"])
        out[arm] = [{"tokens": v, "calls": max(0, len(v) - 1)} for v in S.values()]
    return out


def d3():
    out = {}
    for arm, key in (("alone", "alone"), ("kit", "cmlm")):
        S = defaultdict(lambda: {"tokens": [], "calls": 0})
        for r in (1, 2, 3):
            for l in open(f"{B}/api/runs/{key}_r{r}/requests.jsonl"):
                x = json.loads(l); s = S[(r, x["task"])]
                s["tokens"].append(x["prompt"] + x["output"] + x["thoughts"])
                s["calls"] += sum(1 for c in x.get("calls", []) if c[0] in ("search", "read_file", "list_files"))
        out[arm] = list(S.values())
    return out


def large(agents, prefix=""):
    A = json.load(open(agents)); out = {"alone": [], "kit": []}
    for k, aid in A.items():
        if not k.startswith(prefix): continue
        arm = "alone" if "alone" in k else "kit"
        t = transcript(aid)
        if t: out[arm].append(t)
    return out


def analyse(sessions):
    a, k = sessions["alone"], sessions["kit"]
    # g: within-session slope of tokens on request index, ALONE only (fixed effects)
    xs, ys = [], []
    for s in a:
        t = np.array(s["tokens"], float); j = np.arange(len(t), dtype=float)
        if len(t) >= 2: xs.append(j - j.mean()); ys.append(t - t.mean())
    X = np.concatenate(xs); Y = np.concatenate(ys); g = float((X @ Y) / (X @ X))
    P_a = float(np.mean([s["tokens"][0] for s in a if s["tokens"]])); P_k = float(np.mean([s["tokens"][0] for s in k if s["tokens"]]))
    r_a = float(np.mean([len(s["tokens"]) for s in a])); r_k = float(np.mean([len(s["tokens"]) for s in k]))
    Tf = lambda r, P: r * P + g * r * (r - 1) / 2
    ca = sum(s["calls"] for s in a) / len(a); ck = sum(s["calls"] for s in k) / len(k)
    S_T = sum(sum(s["tokens"]) for s in a) / len(a) / (sum(sum(s["tokens"]) for s in k) / len(k))
    S_r = r_a / r_k
    per_session_pred = np.mean([Tf(len(s["tokens"]), P_a) for s in a]) / np.mean([Tf(len(s["tokens"]), P_k) for s in k])
    return {"sessions": [len(a), len(k)], "calls per session alone/kit": [round(ca, 2), round(ck, 2)], "phi": round(1 - ck / ca, 3),
            "requests per session alone/kit": [round(r_a, 2), round(r_k, 2)], "P alone/kit": [round(P_a), round(P_k)], "g": round(g),
            "S_pred": round(Tf(r_a, P_a) / Tf(r_k, P_k), 3), "S_pred (per-session r, exploratory)": round(float(per_session_pred), 3),
            "S_T measured": round(S_T, 3), "S_r measured": round(S_r, 3),
            "tokens per session alone/kit": [round(sum(sum(s["tokens"]) for s in a) / len(a)), round(sum(sum(s["tokens"]) for s in k) / len(k))]}


R = {"D1 Sonnet 5.5, 114 real issues": analyse(d1()), "D2 Gemini 2.5 Flash, 114 real issues": analyse(d2()),
     "D3 Gemini 2.5 Flash, 60-question stream": analyse(d3()),
     "D4 Opus 5.5, 60-question stream": analyse(large(f"{B}/large/agents.json")),
     "D5 Sonnet 5.5, 60-question stream": analyse(large(f"{B}/large/slices/agents_slices.json", "SON/"))}
ds = list(R.values())
R["G1"] = all(d["phi"] >= 0.5 for d in ds)
R["G2"] = all(abs(d["S_pred"] / d["S_T measured"] - 1) <= 0.20 for d in ds)
R["G3"] = all(d["S_T measured"] > d["S_r measured"] for d in ds)
R["G4"] = sum(d["S_T measured"] >= 2.0 for d in ds) >= 3
R["protocol sha256"] = json.load(open(f"{B}/prereg_hashes.json"))["PROTOCOL_FORMULA.md"]["sha256"]
json.dump(R, open(f"{os.path.dirname(os.path.abspath(__file__))}/formula.json", "w"), indent=1)
print(f"{'dataset':42s} {'phi':>6s} {'calls a/k':>12s} {'req a/k':>12s} {'P a/k':>14s} {'g':>7s} {'S_pred':>7s} {'S_T':>6s} {'S_r':>6s}")
for k, d in R.items():
    if isinstance(d, dict): print(f"{k:42s} {d['phi']:6.3f} {str(d['calls per session alone/kit']):>12s} {str(d['requests per session alone/kit']):>12s} {str(d['P alone/kit']):>14s} {d['g']:7d} {d['S_pred']:7.2f} {d['S_T measured']:6.2f} {d['S_r measured']:6.2f}")
print({k: R[k] for k in ("G1", "G2", "G3", "G4")})
