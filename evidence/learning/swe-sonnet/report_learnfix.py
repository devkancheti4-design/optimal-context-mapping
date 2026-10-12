"""PROTOCOL_LEARN_FIX.md report -> report_learnfix.json. Primary: the agent's own tool calls per session (calls.jsonl,
search/read/list); secondary: requests from the workflow transcripts; right from answer.json."""
import glob, json, os, re, sys
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
sys.path.insert(0, f"{B}/reports"); from common import ci
WF = os.path.expanduser("~/.claude/projects/-Users-kanchetidevieswar-neos")
ISSUES = json.load(open(f"{B}/swe/issues.json"))["issues"]; POS = {i["id"]: k for k, i in enumerate(ISSUES)}; GOLD = {i["id"]: i["file"] for i in ISSUES}
seen, REP = set(), {}
for i in ISSUES: REP[i["id"]] = i["file"] in seen; seen.add(i["file"])
plan = json.load(open(f"{H}/learnfix_jobs.json"))["plan"]


def norm(a):
    a = str(a or "").strip().strip("`'\" ").lstrip("./"); return a[len("corpus/"):] if a.startswith("corpus/") else a


tx = {}
for f in glob.glob(f"{WF}/**/agent-*.jsonl", recursive=True):
    try:
        with open(f) as fh: head = fh.read(20000)
    except OSError: continue
    m = re.search(r"swe_sonnet/agents/learnfix/([ZC])_r(\d)/(django__django-\d+)/task\.md", head)
    if m: tx.setdefault((m.group(1), int(m.group(2)), m.group(3)), []).append(f)


def requests(f):
    ids = set()
    for line in open(f):
        d = json.loads(line)
        if d.get("type") == "assistant":
            m = d.get("message") or {}
            if m.get("usage") and m.get("id"): ids.add(m["id"])
    return len(ids)


S = {}
for arm, ids in plan.items():
    for r in (1, 2, 3, 4):
        for i in ids:
            d = f"{H}/agents/learnfix/{arm}_r{r}/{i}"
            calls = [json.loads(l) for l in open(f"{d}/calls.jsonl")] if os.path.exists(f"{d}/calls.jsonl") else []
            ans = json.load(open(f"{d}/answer.json"))["file"] if os.path.exists(f"{d}/answer.json") else ""
            fs = tx.get((arm, r, i), [])
            if not calls and not ans:                                   # DL1: did not attempt the task
                S[(arm, r, i)] = {"calls": None, "right": None, "answered": False, "requests": None, "transcripts": len(fs), "attempted": False}; continue
            S[(arm, r, i)] = {"attempted": True, "calls": sum(1 for c in calls if c["cmd"] != "submit"), "right": norm(ans) == GOLD[i] or GOLD[i].endswith("/" + norm(ans)) if ans else False,
                              "answered": bool(ans), "requests": requests(fs[-1]) if fs else None, "transcripts": len(fs)}
mean = lambda arm, i, k: float(np.mean([S[(arm, r, i)][k] for r in (1, 2, 3, 4) if S[(arm, r, i)][k] is not None])) if any(S[(arm, r, i)][k] is not None for r in (1, 2, 3, 4)) else None
ZL = plan["C"]
out = {"protocol sha256": json.load(open(f"{B}/prereg_hashes.json"))["PROTOCOL_LEARN_FIX.md"]["sha256"],
       "sessions": len(S), "answered": sum(v["answered"] for v in S.values()), "transcripts found": sum(1 for v in S.values() if v["transcripts"]),
       "duplicate transcripts": sum(1 for v in S.values() if v["transcripts"] > 1)}
def comp(ids, k):
    z = [mean("Z", i, k) for i in ids]; l = [mean("C", i, k) for i in ids]
    if any(x is None for x in z + l): return None
    return {"issues": len(ids), f"Z mean {k} per issue": round(float(np.mean(z)), 3), f"L mean {k} per issue": round(float(np.mean(l)), 3),
            "factor Z/L": round(sum(z) / sum(l), 3), "factor Z/L 95% CI": ci(z, l), "saving Z-L per issue": round(float(np.mean(z) - np.mean(l)), 3)}
out["L1 tool calls, 29 issues"] = comp(ZL, "calls")
out["requests, 29 issues (secondary)"] = comp(ZL, "requests")
att = lambda a: [(r, i) for r in (1, 2, 3, 4) for i in ZL if S[(a, r, i)]["attempted"]]
zr = sum(S[("Z", r, i)]["right"] for r, i in att("Z")); lr = sum(S[("C", r, i)]["right"] for r, i in att("C"))
out["L2 right over 3 reps, 29 issues"] = {"Z": zr, "Z attempted": len(att("Z")), "C": lr, "L attempted": len(att("C")), "Z rate": round(zr / len(att("Z")), 4), "L rate": round(lr / len(att("C")), 4)}
out["not attempted (DL1)"] = sorted(f"{a}_r{r}/{i}" for (a, r, i), v in S.items() if not v["attempted"])
first = [i for i in ZL if POS[i] < 57]; second = [i for i in ZL if POS[i] >= 57]
sv = lambda ids: round(float(sum(mean("Z", i, "calls") - mean("C", i, "calls") for i in ids)), 3)
out["L3 learning saving in tool calls (Z-L summed)"] = {"first half": sv(first), "second half": sv(second), "issues": [len(first), len(second)],
    "by quarter": [sv([i for i in ZL if q * 28.5 <= POS[i] < (q + 1) * 28.5]) for q in range(4)]}
out["L4 repeat-file issues among the 29"] = comp([i for i in ZL if REP[i]], "calls")
out["new-file issues among the 29"] = comp([i for i in ZL if not REP[i]], "calls")
# the whole stream: KIT tool calls with the frozen kit vs with the learning kit (identical input on the other 86 issues)
kitcalls = {i["id"]: sum(1 for l in open(f"{H}/agents/kit/{i['id']}/calls.jsonl") if json.loads(l)["cmd"] != "submit") if os.path.exists(f"{H}/agents/kit/{i['id']}/calls.jsonl") else 0 for i in ISSUES}
out["whole stream, learning saving in KIT tool calls"] = {"note": "86 issues identical input (saving 0 by construction); 28 measured here",
    "first half saving": sv(first), "second half saving": sv(second)}
out["per issue"] = {i: {"pos": POS[i] + 1, "repeat": REP[i], "Z calls": [S[("Z", r, i)]["calls"] for r in (1, 2, 3, 4)], "L calls": [S[("C", r, i)]["calls"] for r in (1, 2, 3, 4)],
                        "Z right": sum(bool(S[("Z", r, i)]["right"]) for r in (1, 2, 3, 4)), "L right": sum(bool(S[("C", r, i)]["right"]) for r in (1, 2, 3, 4))} for i in ZL}
L1 = out["L1 tool calls, 29 issues"]; L4 = out["L4 repeat-file issues among the 29"]; L3 = out["L3 learning saving in tool calls (Z-L summed)"]
out["F1"] = bool(L1 and L1["factor Z/L 95% CI"][0] > 1.0)
out["F2"] = lr / len(att("C")) >= zr / len(att("Z"))   # rate over attempted sessions (DL1)
out["F3"] = L3["second half"] > L3["first half"]
out["F4 (point above 1.0; interval reported)"] = bool(L4 and L4["factor Z/L"] > 1.0)
json.dump(out, open(f"{H}/report_learnfix.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "per issue"}, indent=1))
