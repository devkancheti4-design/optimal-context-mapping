"""PROTOCOL_LIFE.md: living-fused's Life as the CMLM's exact memory of what was taught, across the FastAPI template's
real code move from 36ddc1a to 13652b5 (400 commits). Phase 1 is taught at A; the code moves; phase 2 is asked at B.

    ~/.venvs/cmlm-live/bin/python life_replay.py      -> report_life.json"""
import difflib, json, os, re, shutil, subprocess, sys, tempfile, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping")); sys.path.insert(0, os.path.expanduser("~/living-fused/life"))
from life import Life                                     # living-fused's life/life.py (MIT), from the checkout
from ocm.server import Workspace
from ocm.loop import readout, teach_lines

B = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.expanduser("~/debug_tree_v8/full-stack-fastapi-postgresql")
A, HEAD = "36ddc1a", "13652b5"
Q = json.load(open(f"{B}/questions_100.json")); IDX = {q["qid"]: i for i, q in enumerate(Q)}
ITEM = re.compile(r"(?m)^\d+\. \[([^\]:]+)(?::(\d+))?\]")
TEACH = {}
for t in range(1, 11):
    for line in open(f"{B}/agents_vec/cmlm_t{t:02d}/answers.jsonl"):
        d = json.loads(line); TEACH[d["qid"]] = d.get("teach") or ""


def show(rev, path):
    r = subprocess.run(["git", "-C", REPO, "show", f"{rev}:{path}"], capture_output=True, text=True)
    return r.stdout.split("\n") if r.returncode == 0 else None


def renames():
    out = subprocess.run(["git", "-C", REPO, "diff", "--name-status", "-M", A, HEAD], capture_output=True, text=True).stdout
    a2b = {}
    for l in out.split("\n"):
        p = l.split("\t")
        if p[0].startswith("R") and len(p) == 3:
            a2b[p[1]] = p[2]
    return a2b, {v: k for k, v in a2b.items()}


def line_map(old, new):
    """{index in new: index in old} for lines the diff keeps."""
    mp = {}
    for a, b, n in difflib.SequenceMatcher(None, old, new, autojunk=False).get_matching_blocks():
        for k in range(n):
            mp[b + k] = a + k
    return mp


def main():
    a2b, b2a = renames()
    w0 = Workspace(f"{B}/ws_vec_base")
    corpus_files = {rel[len("corpus/"):]: p for rel, p in w0.files.items()}
    # phase 1: the taught entries of questions 1-50, at their A locations
    entries = []
    for q in Q[:50]:
        pairs = teach_lines(TEACH.get(q["qid"], ""))
        m = re.search(r"(?:corpus/)?([\w./-]+):(\d+)", pairs[0][1]) if pairs else None
        if not m:
            continue
        pb, lb = m.group(1), int(m.group(2))
        hb = show(HEAD, pb); pa = b2a.get(pb, pb); ha = show(A, pa)
        if not hb or not ha or lb > len(hb):
            continue
        mp = line_map(ha, hb)
        if lb - 1 not in mp:
            continue
        la = mp[lb - 1] + 1
        entries.append({"qid": q["qid"], "key": " ".join(pairs[0][0].split()), "a": f"{pa}:{la}", "b_true": f"{pb}:{lb}",
                        "code": ha[la - 1], "moved": (pa, la) != (pb, lb)})
    tmp = tempfile.mkdtemp(); life_file = os.path.join(tmp, "taught.life.json")
    life = Life(life_file)
    for e in entries:
        life.learn(e["key"], json.dumps({"at": e["a"], "code": e["code"]}, sort_keys=True))
    sha_phase1 = life.sha()
    # the code moves to B: each entry found at B by exact identity, written as a revision, or ABSTAIN
    status = {}
    for e in entries:
        v = json.loads(life.recall(e["key"])); pa, la = v["at"].rsplit(":", 1); la = int(la); code = v["code"].rstrip()
        pb = a2b.get(pa, pa); found = None
        hb = show(HEAD, pb)
        if code.strip() and hb:
            hits = [i + 1 for i, l in enumerate(hb) if l.rstrip() == code]
            if hits:
                found = (pb, min(hits, key=lambda i: abs(i - la)))
        if found is None and code.strip():
            hits = [(rel, i + 1) for rel, p in corpus_files.items() for i, l in enumerate(open(p, encoding="utf-8", errors="replace").read().split("\n")) if l.rstrip() == code]
            if len(hits) == 1:
                found = hits[0]
        if found is None:
            status[e["key"]] = "ABSTAIN"
            continue
        newv = json.dumps({"at": f"{found[0]}:{found[1]}", "code": v["code"]}, sort_keys=True)
        if newv != life.recall(e["key"]):
            life.learn(e["key"], newv)
        status[e["key"]] = f"{found[0]}:{found[1]}"
    life.save(life_file); sha_saved = life.sha(); reloaded = Life(life_file)
    revised = [e["key"] for e in entries if len(life.history(e["key"])) >= 2]
    unit = lambda at: w0.unit_at("corpus/" + at) if at else None
    rows_c = []
    for e in entries:
        truth = unit(e["b_true"])
        life_at = status[e["key"]] if status[e["key"]] != "ABSTAIN" else None
        rows_c.append({"qid": e["qid"], "moved": e["moved"], "truth unit": truth,
                       "LIFE": "abstain" if life_at is None else ("right" if unit(life_at) == truth else "wrong"),
                       "CARRY-AS-IS": "not placed" if unit(e["a"]) is None else ("right" if unit(e["a"]) == truth else "wrong")})
    arms = {"REBUILD": [], "CARRY-AS-IS": [{"question": e["key"], "at": e["a"]} for e in entries],
            "LIFE": [{"question": e["key"], "at": status[e["key"]]} for e in entries if status[e["key"]] != "ABSTAIN"],
            "NO-MOVE": [{"question": e["key"], "at": e["b_true"]} for e in entries]}
    cross = {q["qid"] for q in Q[50:] if any(x["fact"] == q["fact"] for x in Q[:50])}
    R = {}
    for arm, pre in arms.items():
        d = os.path.join(tmp, arm); shutil.copytree(f"{B}/ws_vec_base", d); w = Workspace(d)
        if pre:
            w.handle("teach", {"pairs": [dict(p, at="corpus/" + p["at"]) for p in pre]})
        span = {(p, a): (a, b) for p, xs in w.spans.items() for a, b, j in xs}
        same = lambda p, f: p == f or p.endswith("/" + f)
        def holds(text, q):
            for p, line in ITEM.findall(text):
                if line:
                    a, b = span.get((p, int(line)), (int(line), int(line)))
                    if any(same(p, e["file"]) and a <= e["line"] <= b for e in q["evidence"]):
                        return True
            return False
        rows = []
        for q in Q[50:]:
            text = readout(lambda path, **kw: w.handle(path, kw), q["question"])
            rows.append({"qid": q["qid"], "holds": holds(text, q), "cross-phase repeat": q["qid"] in cross})
            pairs = teach_lines(TEACH.get(q["qid"], ""))
            if pairs:
                w.handle("teach", {"pairs": [{"question": a, "at": b} for a, b in pairs]})
        R[arm] = rows
        print(arm, sum(r["holds"] for r in rows), flush=True)
    from collections import Counter
    rep = {"protocol sha256": json.load(open(f"{B}/prereg_hashes.json"))["PROTOCOL_LIFE.md"]["sha256"],
           "entries taught at A": len(entries), "moved": sum(e["moved"] for e in entries),
           "carried": {a: dict(Counter(r[a] for r in rows_c)) for a in ("LIFE", "CARRY-AS-IS")},
           "carried, moved entries only": {a: dict(Counter(r[a] for r in rows_c if r["moved"])) for a in ("LIFE", "CARRY-AS-IS")},
           "life": {"sha after phase 1": sha_phase1, "sha before save": sha_saved, "sha after reload": reloaded.sha(),
                    "keys": len(life.store), "revised keys": len(revised),
                    "every revised key keeps A and B": all(len(life.history(k)) >= 2 for k in revised)},
           "cross-phase repeats": sorted(cross)}
    for arm, rows in R.items():
        rep[arm] = {"phase 2": f"{sum(r['holds'] for r in rows)}/{len(rows)}",
                    "cross-phase repeats": f"{sum(r['holds'] for r in rows if r['cross-phase repeat'])}/{sum(r['cross-phase repeat'] for r in rows)}"}
    h = lambda arm, k: sum(r["holds"] for r in R[arm] if (k == "all" or r["cross-phase repeat"]))
    life_c = rep["carried"]["LIFE"]
    placed = life_c.get("right", 0) + life_c.get("wrong", 0)
    rep["F1"] = placed > 0 and life_c.get("right", 0) / placed >= 0.9 and life_c.get("wrong", 0) == 0 and rep["carried"]["CARRY-AS-IS"].get("wrong", 0) >= 10
    rep["F2"] = h("LIFE", "all") >= h("REBUILD", "all") and h("LIFE", "all") >= h("CARRY-AS-IS", "all")
    rep["F3"] = h("LIFE", "cross") >= h("REBUILD", "cross")
    rep["F4"] = rep["life"]["sha before save"] == rep["life"]["sha after reload"] and rep["life"]["every revised key keeps A and B"]
    rep["entries"] = rows_c; rep["rows"] = R
    json.dump(rep, open(f"{B}/report_life.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("entries", "rows")}, indent=1))
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
