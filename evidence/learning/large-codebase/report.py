"""PROTOCOL_LARGE.md: L-CMLM against L-ALONE on transformers (10.8M tokens), and the absorbed map.

    python3 report.py judge                                       # judge/judge_items_{1,2}.json, judge/judge_map.json
    ~/.venvs/cmlm-live/bin/python report.py report                # report_large.json"""
import glob, json, os, random, re, sys
L = os.path.dirname(os.path.abspath(__file__)); TR = os.path.expanduser("~/.claude/projects/-Users-kanchetidevieswar-neos")
BASE = json.load(open(os.path.join(L, "..", "report_team_savings.json")))["fixed part per request"]
A = json.load(open(f"{L}/agents.json")); QS = json.load(open(os.path.expanduser("~/cmlm-bench5/questions.json")))
FACT = {q["qid"]: q for q in QS}; TASKS = [f"t{i:02d}" for i in range(1, 7)]; J = f"{L}/judge"
TAUGHT = "(readout: the code a taught question"


def session(arm, t):
    aid = A.get(f"{arm}_{t}")
    if not aid: return None
    folder = f"{L}/agents/{arm}_{t}"; qs = [q["qid"] for q in json.load(open(f"{folder}/questions.json"))]
    seen, reqs, cur, perq = set(), [], -1, {}
    for line in open(glob.glob(f"{TR}/*/subagents/agent-{aid}.jsonl")[0]):
        d = json.loads(line)
        if d.get("type") != "assistant": continue
        m = d.get("message") or {}; u = m.get("usage")
        if u and m.get("id") not in seen:
            seen.add(m["id"]); x = (u.get("input_tokens", 0), u.get("cache_creation_input_tokens", 0), u.get("cache_read_input_tokens", 0)); reqs.append(x)
            if 0 <= cur < len(qs):
                r = perq.setdefault(qs[cur], {"requests": 0, "calls": 0}); r["requests"] += 1
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                c = str((b.get("input") or {}).get("command", ""))
                if 0 <= cur < len(qs):
                    perq.setdefault(qs[cur], {"requests": 0, "calls": 0})["calls"] += sum(c.count(k) for k in ("search.sh", "read.sh", "list.sh"))
                cur += c.count("next.sh")
    return reqs, perq


def answers(arm):
    out = {}
    for t in TASKS:
        p = f"{L}/agents/{arm}_{t}/answers.jsonl"
        for line in (open(p) if os.path.exists(p) else []):
            d = json.loads(line); m = re.match(r"\s*ANSWER:\s*(.*?)(?:\s*\|\s*SOURCE:\s*(.*))?$", d["answer"] or "", re.I | re.S)
            out[d["qid"]] = {"answer": m.group(1).strip() if m else "(no answer)", "source": (m.group(2) or "").strip() if m else ""}
    return out


def judge():
    items = []
    for arm in ("cmlm", "alone"):
        got = answers(arm)
        for qid in [q["qid"] for q in QS] + [q["qid"] + "b" for q in QS]:
            f = FACT[qid.rstrip("b")]; a = got.get(qid, {"answer": "(no answer)", "source": ""})
            items.append((arm, qid, {"question": f["question2"] if qid.endswith("b") else f["question"], "expected": f["answer"],
                                     "expected_file": f["file"], "response": a["answer"], "response_file": a["source"]}))
    random.Random(20261008 + 7).shuffle(items); os.makedirs(J, exist_ok=True)
    keys = [f"i{i:03d}" for i in range(1, len(items) + 1)]
    for part in range(2):
        json.dump({k: it for k, (_, _, it) in list(zip(keys, items))[part * 60:(part + 1) * 60]}, open(f"{J}/judge_items_{part + 1}.json", "w"), indent=1)
    json.dump({k: [arm, qid] for k, (arm, qid, _) in zip(keys, items)}, open(f"{J}/judge_map.json", "w"), indent=1)
    print(len(items), "items")


def report():
    sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
    from ocm.server import Workspace
    w = Workspace(f"{L}/ws_L_base")
    V = {}
    for p in glob.glob(f"{J}/judge_out_*.json"):
        V.update(json.load(open(p)))
    M = json.load(open(f"{J}/judge_map.json")) if os.path.exists(f"{J}/judge_map.json") else {}
    out = {}
    for arm in ("cmlm", "alone"):
        per, first, rep, calls = [], 0, 0, 0
        for i, t in enumerate(TASKS):
            s = session(arm, t)
            if s is None: continue
            reqs, perq = s; per.append(len(reqs)); calls += sum(v["calls"] for v in perq.values())
            if i < 3: first += len(reqs)
            else: rep += len(reqs)
        allreq = [x for t in TASKS if session(arm, t) for x in session(arm, t)[0]]
        out[arm] = {"per task requests": per, "requests": sum(per), "first wordings (tasks 1-3)": first, "repeats (tasks 4-6)": rep,
                    "cache-weighted": round(sum(x[0] + 1.25 * x[1] + 0.1 * x[2] for x in allreq)), "search/read/list": calls,
                    "right": sum(1 for i, v in V.items() if M.get(i, [None])[0] == arm and v == "correct") if V else None}
    # the absorbed map: each second wording's readout against the unit holding the fact's line
    amap = {"right": 0, "junk": 0, "not absorbed": 0, "rows": []}
    for t in TASKS[3:]:
        p = f"{L}/agents/cmlm_{t}/readouts.jsonl"
        for line in (open(p) if os.path.exists(p) else []):
            d = json.loads(line); f = FACT[d["qid"].rstrip("b")]
            truth = w.unit_at(f"corpus/{f['file']}:{f['line']}")
            if d["readout"].startswith(TAUGHT):
                m = re.search(r"(?m)^1\. \[([^\]]+)\]", d["readout"]); got = w.unit_at(m.group(1)) if m else None
                kind = "right" if got is not None and got == truth else "junk"
            else:
                kind = "not absorbed"
            amap[kind] += 1; amap["rows"].append({"qid": d["qid"], "map": kind})
    out["absorbed map (second wordings)"] = amap
    c, a = out["cmlm"], out["alone"]
    if len(c["per task requests"]) == 6 and len(a["per task requests"]) == 6:
        out["saving"] = round(a["requests"] / c["requests"], 2)
        out["saving, first wordings"] = round(a["first wordings (tasks 1-3)"] / c["first wordings (tasks 1-3)"], 2)
        out["saving, repeats"] = round(a["repeats (tasks 4-6)"] / c["repeats (tasks 4-6)"], 2)
        out["G1"] = out["saving"] > 1.25; out["G2"] = out["saving, repeats"] >= 1.5
        out["G3"] = (c["right"] >= a["right"] - 2) if V else None
        out["G4"] = amap["right"] >= 24 and amap["junk"] <= 3
    json.dump(out, open(f"{L}/report_large.json", "w"), indent=1)
    print(json.dumps({k: (v if k != "absorbed map (second wordings)" else {x: v[x] for x in ("right", "junk", "not absorbed")}) for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    {"judge": judge, "report": report}[sys.argv[1]]()
