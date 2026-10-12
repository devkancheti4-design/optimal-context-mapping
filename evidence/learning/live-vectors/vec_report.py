"""PROTOCOL_LIVE_VEC.md: VEC-CMLM against VEC-ALONE, both 10 fresh sessions run one after another.

    python3 vec_report.py judge     # judge_vec/judge_items_{1,2}.json (shuffled, no arm shown) and judge_map.json
    python3 vec_report.py report    # report_vec.json and a printed summary"""
import glob, json, os, random, re, sys
B = os.path.dirname(os.path.abspath(__file__)); TR = os.path.expanduser("~/.claude/projects/-Users-kanchetidevieswar-neos")
BASE = json.load(open(f"{B}/report_team_savings.json"))["fixed part per request"]
A = json.load(open(f"{B}/agents_vec.json")); Q = json.load(open(f"{B}/questions_100.json")); IDX = {q["qid"]: i for i, q in enumerate(Q)}
REP = {q["qid"]: any(x["fact"] == q["fact"] for x in Q[:IDX[q["qid"]]]) for q in Q}
TASKS = [f"t{i:02d}" for i in range(1, 11)]; ARMS = ("cmlm", "alone"); J = f"{B}/judge_vec"


def transcript(aid):
    return glob.glob(f"{TR}/*/subagents/agent-{aid}.jsonl")[0]


def session(folder):
    """Per request usage, and per question requests, cache-weighted input and search/read/list calls."""
    qs = [q["qid"] for q in json.load(open(f"{B}/agents_vec/{folder}/questions.json"))]
    seen, reqs, cur, perq = set(), [], -1, {}
    for line in open(transcript(A[folder])):
        d = json.loads(line)
        if d.get("type") != "assistant": continue
        m = d.get("message") or {}; u = m.get("usage")
        if u and m.get("id") not in seen:
            seen.add(m["id"]); x = (u.get("input_tokens", 0), u.get("cache_creation_input_tokens", 0), u.get("cache_read_input_tokens", 0)); reqs.append(x)
            if 0 <= cur < len(qs):
                r = perq.setdefault(qs[cur], {"requests": 0, "cw": 0.0, "calls": 0}); r["requests"] += 1; r["cw"] += x[0] + 1.25 * x[1] + 0.1 * x[2]
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                c = str((b.get("input") or {}).get("command", ""))
                if 0 <= cur < len(qs):
                    perq.setdefault(qs[cur], {"requests": 0, "cw": 0.0, "calls": 0})["calls"] += sum(c.count(k) for k in ("search.sh", "read.sh", "list.sh"))
                cur += c.count("next.sh")
    return reqs, perq


def split(sessions):
    n = sum(len(r) for r in sessions); tot = sum(sum(x) for r in sessions for x in r)
    cw = sum(x[0] + 1.25 * x[1] + 0.1 * x[2] for r in sessions for x in r)
    fixed = sum(r[0][2] * 0.1 + (BASE - r[0][2]) * 1.25 + (len(r) - 1) * BASE * 0.1 for r in sessions)
    return {"sessions": len(sessions), "requests": n, "cache-weighted": round(cw), "fixed, cache-weighted": round(fixed),
            "context, cache-weighted": round(cw - fixed), "context tokens read": tot - n * BASE}


def answers(folder):
    out = {}
    for line in open(f"{B}/agents_vec/{folder}/answers.jsonl"):
        d = json.loads(line); m = re.match(r"\s*ANSWER:\s*(.*?)(?:\s*\|\s*SOURCE:\s*(.*))?$", d["answer"] or "", re.I | re.S)
        out[d["qid"]] = {"answer": m.group(1).strip() if m else "(no answer)", "source": (m.group(2) or "").strip() if m else "", "taught": d.get("taught")}
    return out


def judge():
    items = []
    for arm in ARMS:
        got = {}
        for t in TASKS:
            got.update(answers(f"{arm}_{t}"))
        for q in Q:
            a = got.get(q["qid"], {"answer": "(no answer)", "source": ""})
            items.append((arm, q["qid"], {"question": q["question"], "expected": q["answer"], "expected_file": ", ".join(sorted({e["file"] for e in q["evidence"]})),
                                          "response": a["answer"], "response_file": a["source"]}))
    random.Random(20261007 + 5).shuffle(items); os.makedirs(J, exist_ok=True)
    keys = [f"i{i:03d}" for i in range(1, len(items) + 1)]
    for part in range(2):
        json.dump({k: it for k, (_, _, it) in list(zip(keys, items))[part * 100:(part + 1) * 100]}, open(f"{J}/judge_items_{part + 1}.json", "w"), indent=1)
    json.dump({k: [arm, qid] for k, (arm, qid, _) in zip(keys, items)}, open(f"{J}/judge_map.json", "w"), indent=1)
    print(len(items), "items in 2 files")


def report():
    V = {}
    for p in sorted(glob.glob(f"{J}/judge_out_*.json")):
        V.update(json.load(open(p)))
    M = json.load(open(f"{J}/judge_map.json")) if os.path.exists(f"{J}/judge_map.json") else {}
    out, PQ = {}, {}
    for arm in ARMS:
        sess, perq = [], {}
        for t in TASKS:
            if f"{arm}_{t}" not in A: continue
            r, pq = session(f"{arm}_{t}"); sess.append(r); perq.update(pq)
        PQ[arm] = perq
        s = split(sess); s["search/read/list calls"] = sum(v["calls"] for v in perq.values())
        s["right"] = sum(1 for i, v in V.items() if M.get(i, [None])[0] == arm and v == "correct") if V else None
        s["per task requests"] = [len(r) for r in sess]
        out[arm] = s
    taught = [a.get("taught") or "" for t in TASKS if f"cmlm_{t}" in A for a in answers(f"cmlm_{t}").values()]
    out["TEACH lines placed"] = sum(1 for x in taught if x.startswith("taught 1")); out["TEACH lines not placed"] = sum(1 for x in taught if "1 not placed" in x)
    both = [q for q in PQ["cmlm"] if q in PQ["alone"]]
    for kind in ("first", "asked before"):
        for half, rng in (("tasks 1-5", range(0, 50)), ("tasks 6-10", range(50, 100))):
            qs = [q for q in both if IDX[q] in rng and REP[q] == (kind == "asked before")]
            if not qs: continue
            g = lambda arm, k: sum(PQ[arm][q][k] for q in qs)
            out[f"{kind}, {half}"] = {"questions": len(qs), **{f"{arm} {k}": round(g(arm, k)) for arm in ARMS for k in ("requests", "calls", "cw")},
                                      "alone/cmlm requests": round(g("alone", "requests") / max(1, g("cmlm", "requests")), 2),
                                      "alone/cmlm cw": round(g("alone", "cw") / max(1, g("cmlm", "cw")), 2)}
    half = lambda h: [len(r) for r in []]
    req = {arm: out[arm]["per task requests"] for arm in ARMS}
    k = min(len(req["cmlm"]), len(req["alone"]))
    if k >= 10:
        out["L1"] = out["cmlm"]["requests"] < out["alone"]["requests"]
        out["L2"] = out["cmlm"]["cache-weighted"] < out["alone"]["cache-weighted"]
        r15 = sum(req["alone"][:5]) / sum(req["cmlm"][:5]); r610 = sum(req["alone"][5:]) / sum(req["cmlm"][5:])
        out["request saving tasks 1-5"], out["request saving tasks 6-10"] = round(r15, 2), round(r610, 2); out["L3"] = r610 >= r15
        out["L4"] = (out["cmlm"]["right"] >= out["alone"]["right"] - 2) if V else None
        ab = [q for q in both if REP[q]]
        out["L5"] = sum(PQ["cmlm"][q]["requests"] for q in ab) <= 0.6 * sum(PQ["alone"][q]["requests"] for q in ab)
    json.dump(out, open(f"{B}/report_vec.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"judge": judge, "report": report}[sys.argv[1]]()
