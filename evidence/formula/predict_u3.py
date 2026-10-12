"""PROTOCOL_UNIVERSAL.md U3/U4: from each model's ALONE sessions, compute UF's token prediction and the turn law's
prediction for its KIT arm; write predictions_u3.json and its hash into prereg_hashes.json (before any KIT session)."""
import glob, hashlib, json, os, re, datetime
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
TR = os.path.expanduser("~/.claude/projects/-Users-kanchetidevieswar-neos")
U = json.load(open(f"{H}/universal.json")); phi = float(np.mean(list(U["phi per laws case"].values())))
DELTA = U["Delta per question (tokens)"]["C1 Sonnet 5.5, real bugs"]
T = lambda r, P, g: r * P + g * r * (r - 1) / 2


def sessions(model, arm):
    pat = re.compile(rf"swe_sonnet/agents/u3/{model}/{arm}/(django__django-\d+)/task\.md")
    out = {}
    for f in glob.glob(f"{TR}/**/agent-*.jsonl", recursive=True):
        try:
            with open(f) as fh: head = fh.read(20000)
        except OSError: continue
        m = pat.search(head)
        if not m: continue
        seen, reqs, models = set(), [], set()
        for line in open(f):
            d = json.loads(line)
            if d.get("type") != "assistant": continue
            mm = d.get("message") or {}; u = mm.get("usage")
            if mm.get("model"): models.add(mm["model"])
            if u and mm.get("id") not in seen:
                seen.add(mm["id"]); reqs.append(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("output_tokens", 0))
        out.setdefault(m.group(1), []).append({"tokens": reqs[1:-1] if len(reqs) > 2 else reqs[-1:], "models": sorted(models), "file": f})
    return out


def profile(S):
    xs, ys = [], []
    for s in S:
        t = np.array(s["tokens"], float); j = np.arange(len(t), dtype=float)
        if len(t) >= 2: xs.append(j - j.mean()); ys.append(t - t.mean())
    X, Y = np.concatenate(xs), np.concatenate(ys)
    return {"g": float(X @ Y / (X @ X)), "P": float(np.mean([s["tokens"][0] for s in S if s["tokens"]])),
            "r": float(np.mean([len(s["tokens"]) for s in S])), "A": float(np.mean([sum(s["tokens"]) for s in S]))}


if __name__ == "__main__":
    pred = {"phi": round(phi, 4), "Delta": DELTA, "models": {}}
    for model in ("haiku", "opus"):
        S = sessions(model, "alone"); one = [max(v, key=lambda s: os.path.getmtime(s["file"])) for v in S.values()]   # DU1: newest transcript
        p = profile(one); rK = 1 + (1 - phi) * (p["r"] - 1)
        pred["models"][model] = {"sessions": len(one), "models seen": sorted({m for s in one for m in s["models"]}),
                                 "alone profile": {k: round(v, 2) for k, v in p.items()},
                                 "UF token saving (U3)": round(p["A"] / T(rK, p["P"] + DELTA, p["g"]), 3), "U3 band (+-25%)": None,
                                 "turn law saving (U4)": round(p["r"] / rK, 3), "predicted KIT requests per issue": round(rK, 3)}
        u = pred["models"][model]; u["U3 band (+-25%)"] = [round(u["UF token saving (U3)"] / 1.25, 3), round(u["UF token saving (U3)"] * 1.25, 3)]
        u["U4 band (+-20%)"] = [round(u["turn law saving (U4)"] / 1.2, 3), round(u["turn law saving (U4)"] * 1.2, 3)]
    pred["written"] = datetime.datetime.now().isoformat(timespec="seconds")
    p = f"{H}/predictions_u3.json"; json.dump(pred, open(p, "w"), indent=1)
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    d = json.load(open(f"{B}/prereg_hashes.json")); d["universal/predictions_u3.json"] = {"sha256": h, "fixed": pred["written"]}
    json.dump(d, open(f"{B}/prereg_hashes.json", "w"), indent=1)
    print(json.dumps(pred, indent=1)); print("hash", h)
