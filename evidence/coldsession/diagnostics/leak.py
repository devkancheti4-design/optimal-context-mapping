"""Where the one-read answers leak away, and what showing more of the lesson's own code would add. No model calls.

    HF_HUB_OFFLINE=1 <modeld python> -I diagnostics/leak.py <repo>"""
import json, os, re, sys
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C
from ocm.life import Life
from ocm.loop import TAUGHT, readout
from ocm.server import Workspace
from session import built

repo = sys.argv[1]
facts = [f for f in C.rows(C.data(repo, "facts.jsonl")) if f["role"] == "taught"]
rows = {s: {r["id"]: r for r in C.rows(C.results(repo, f"modeld_S{s}.jsonl"))} for s in (2, 3, 4)}
HEAD = re.compile(r"^1\. \[([^\]:]+):?(\d*)\]", re.M)
# Each session's map as it stood before that session taught anything, so a question never finds its own lesson from the same session.
built(repo, "clean_mate", "mate", carry=C.work(repo, "maps", "modeld_first"))
built(repo, "clean_T2", "T2", carry=C.work(repo, "maps", "modeld_T1"))
totals = {}
for label, name, wording, s, snap in (("next day", "modeld_after_S1", "b", 2, "T0"), ("teammate", "clean_mate", "c", 3, "mate"), ("year later", "clean_T2", "d", 4, "T2")):
    w = Workspace(C.work(repo, "maps", name))
    call = lambda p, **kw: w.handle(p, kw)
    tally = {"lane": 0, "line in readout": 0, "line in window": 0, "right file": 0, "read": 0}
    cost, miss = [], []
    for f in facts:
        q = f["wordings"][wording]
        code = readout(call, q)
        path, line = (f["new_path"], f["new_line"]) if s == 4 else (f["path"], f["line"])
        gold = open(C.work(repo, "snap", snap, "repo", path), encoding="utf-8", errors="replace").read().split("\n")[line - 1].strip()
        r = rows[s][f["id"]]
        tally["read"] += r["path"] == "read"
        if not code.startswith(TAUGHT):
            continue
        tally["lane"] += 1
        m = HEAD.search(code)
        top, at = m.group(1), int(m.group(2) or 1)
        rel = top.split("/", 1)[1] if "/" in top else top
        tally["right file"] += rel == path
        inside = gold in code
        tally["line in readout"] += inside
        lines = open(C.work(repo, "snap", snap, "repo", rel), encoding="utf-8", errors="replace").read().split("\n") if os.path.exists(C.work(repo, "snap", snap, "repo", rel)) else []
        win = "\n".join(lines[max(0, at - 16):at + 25])
        near = rel == path and gold in win
        tally["line in window"] += inside or near
        cost.append(len(code) // 4)
        if rel == path and not inside and r["path"] != "read":
            miss.append((f["kind"], f["status"], at, line, q[:70]))
        if inside and r["path"] != "read":
            miss.append(("HELD BUT SEARCHED", f["kind"], at, line, q[:70]))
            tally["held but searched"] = tally.get("held but searched", 0) + 1
    print(f"{label}: of {len(facts)}: lesson lane opened {tally['lane']}, top lesson in the fact's file {tally['right file']}, fact's line in the readout {tally['line in readout']}, in the readout or 40 lines around the top lesson {tally['line in window']}, answered in one read {tally['read']}; had the line but searched {tally.get('held but searched', 0)}; readout tokens {sum(cost) // max(1, len(cost))}")

