"""PROTOCOL_LIFE_LIVE.md: phase 2 at the new code - REBUILD against LIFE (the kit's Life carried over a real code move).

    python3 life_live_report.py judge      # judge_life/judge_items.json (100 phase-2 answers, shuffled, no arm shown)
    python3 life_live_report.py report     # report_life_live.json"""
import glob, json, os, random, re, sys
B = os.path.dirname(os.path.abspath(__file__)); TR = os.path.expanduser("~/.claude/projects/-Users-kanchetidevieswar-neos")
BASE = json.load(open(f"{B}/report_team_savings.json"))["fixed part per request"]
A = json.load(open(f"{B}/agents_life.json")); AV = json.load(open(f"{B}/agents_vec.json"))
Q = json.load(open(f"{B}/questions_100.json")); IDX = {q["qid"]: i for i, q in enumerate(Q)}
CROSS = {q["qid"] for q in Q[50:] if any(x["fact"] == q["fact"] for x in Q[:50])}
TASKS = [f"t{i:02d}" for i in range(6, 11)]; J = f"{B}/judge_life"


def session(aid, folder):
    qs = [q["qid"] for q in json.load(open(f"{folder}/questions.json"))]
    seen, reqs, cur, perq = set(), [], -1, {}
    for line in open(glob.glob(f"{TR}/*/subagents/agent-{aid}.jsonl")[0]):
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


def arm_sessions(arm):
    if arm in ("rebuild", "life"):
        return [(A[f"{arm}_{t}"], f"{B}/agents_life/{arm}_{t}") for t in TASKS if f"{arm}_{t}" in A]
    key = {"vec-cmlm (no move)": "cmlm", "vec-alone": "alone"}[arm]
    return [(AV[f"{key}_{t}"], f"{B}/agents_vec/{key}_{t}") for t in TASKS]


def answers(folder):
    out = {}
    for line in open(f"{folder}/answers.jsonl"):
        d = json.loads(line); m = re.match(r"\s*ANSWER:\s*(.*?)(?:\s*\|\s*SOURCE:\s*(.*))?$", d["answer"] or "", re.I | re.S)
        out[d["qid"]] = {"answer": m.group(1).strip() if m else "(no answer)", "source": (m.group(2) or "").strip() if m else ""}
    return out


def judge():
    items = []
    for arm in ("rebuild", "life"):
        got = {}
        for _, f in arm_sessions(arm):
            got.update(answers(f))
        for q in Q[50:]:
            a = got.get(q["qid"], {"answer": "(no answer)", "source": ""})
            items.append((arm, q["qid"], {"question": q["question"], "expected": q["answer"], "expected_file": ", ".join(sorted({e["file"] for e in q["evidence"]})),
                                          "response": a["answer"], "response_file": a["source"]}))
    random.Random(20261008).shuffle(items); os.makedirs(J, exist_ok=True)
    keys = [f"i{i:03d}" for i in range(1, len(items) + 1)]
    json.dump({k: it for k, (_, _, it) in zip(keys, items)}, open(f"{J}/judge_items.json", "w"), indent=1)
    json.dump({k: [arm, qid] for k, (arm, qid, _) in zip(keys, items)}, open(f"{J}/judge_map.json", "w"), indent=1)
    print(len(items), "items")


def report():
    V = json.load(open(f"{J}/judge_out.json")) if os.path.exists(f"{J}/judge_out.json") else {}
    M = json.load(open(f"{J}/judge_map.json")) if os.path.exists(f"{J}/judge_map.json") else {}
    out = {"cross-phase repeats": sorted(CROSS)}
    for arm in ("rebuild", "life", "vec-cmlm (no move)", "vec-alone"):
        reqs, perq = [], {}
        for aid, f in arm_sessions(arm):
            r, pq = session(aid, f); reqs.append(r); perq.update(pq)
        n = sum(len(r) for r in reqs); cw = sum(x[0] + 1.25 * x[1] + 0.1 * x[2] for r in reqs for x in r)
        cr = [q for q in perq if q in CROSS]
        out[arm] = {"sessions": len(reqs), "requests": n, "cache-weighted": round(cw), "per session": [len(r) for r in reqs],
                    "search/read/list": sum(v["calls"] for v in perq.values()),
                    "cross-phase repeats: requests": sum(perq[q]["requests"] for q in cr), "cross-phase repeats: calls": sum(perq[q]["calls"] for q in cr),
                    "cross-phase repeats answered with no search": sum(1 for q in cr if perq[q]["calls"] == 0),
                    "right": sum(1 for i, v in V.items() if M.get(i, [None])[0] == arm and v == "correct") if V and arm in ("rebuild", "life") else None}
    if V and out["life"]["sessions"] == 5 and out["rebuild"]["sessions"] == 5:
        out["LL1"] = out["life"]["requests"] < out["rebuild"]["requests"]
        out["LL2"] = out["life"]["cross-phase repeats: requests"] < out["rebuild"]["cross-phase repeats: requests"]
        out["LL3"] = out["life"]["right"] >= out["rebuild"]["right"] - 2
    json.dump(out, open(f"{B}/report_life_live.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"judge": judge, "report": report}[sys.argv[1]]()
