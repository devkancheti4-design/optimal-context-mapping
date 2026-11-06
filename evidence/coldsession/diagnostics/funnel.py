"""Where do Model D's lessons go? For each taught fact: what session 1 taught, whether the lesson came through each rebuild, and whether a reworded question landed on it. No model calls.

    HF_HUB_OFFLINE=1 <modeld python> -I diagnostics/funnel.py <repo>"""
import json, os, re, sys
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C
from ocm.life import Life
from ocm.loop import TAUGHT
from ocm.server import Workspace

repo = sys.argv[1]
facts = {f["id"]: f for f in C.rows(C.data(repo, "facts.jsonl"))}
taught = [f for f in facts.values() if f["role"] == "taught"]
rows = {s: {r["id"]: r for r in C.rows(C.results(repo, f"modeld_S{s}.jsonl"))} for s in (1, 2, 3, 4, 5)}
mean = lambda v: sum(v) / len(v) if v else 0
norm = lambda q: " ".join(q.split())


def life(name):
    return Life(C.work(repo, "maps", name, "taught.life.json"))


print("## 1. what session 1 taught")
first = Workspace(C.work(repo, "maps", "modeld_after_S1"))
placed = cited_file = cited_near = 0
for f in taught:
    r = rows[1][f["id"]]
    key = norm(f["wordings"]["a"])
    held = key in first.life.store
    at = r["at"] or ""
    m = re.search(r"([\w./-]+):(\d+)", at)
    path_ok = bool(m) and m.group(1).endswith(f["path"])
    near = path_ok and abs(int(m.group(2)) - f["line"]) <= 3
    placed += held; cited_file += path_ok; cited_near += near
print(f"taught facts {len(taught)}; a lesson stored {placed}; the agent cited the fact's file {cited_file}; within 3 lines of the fact {cited_near}")

print("\n## 2. the lesson through each rebuild, by the Life's own count, and on identical code")
for name in ("modeld_first", "modeld_mate", "modeld_T1", "modeld_T2"):
    w = C.work(repo, "maps", name)
    mf = os.path.join(w, "carry_misses.json")
    miss = json.load(open(mf)) if os.path.exists(mf) else {}
    l = life(name)
    print(f"{name}: entries {len(l.store)}, without a place now {len(miss)}")
mate = life("modeld_mate"); mf = json.load(open(C.work(repo, "maps", "modeld_mate", "carry_misses.json")))
print("\nlost on the teammate's build, identical code:")
for k in list(mf)[:8]:
    v = json.loads(mate.recall(k))
    print("  ", repr(v.get("at")), repr((v.get("code") or "")[:70]), "|", k[:70])

print("\n## 3. does a reworded question land on its lesson? (asked again now, on each map, no model)")
for label, name, wording, s in (("next day", "modeld_after_S1", "b", 2), ("teammate", "modeld_mate", "c", 3), ("year later", "modeld_T2", "d", 4)):
    w = Workspace(C.work(repo, "maps", name))
    led = hit = 0
    detail = []
    for f in taught:
        code = w.handle("ask", {"question": f["wordings"][wording]})
        lane = code.startswith(TAUGHT)
        path = (f["new_path"] if s == 4 else f["path"])
        here = path in code
        led += lane; hit += lane and here
        detail.append((f, lane, here, rows[s][f["id"]]))
    print(f"{label}: the lesson lane opened {led} of {len(taught)}; opened and shows the fact's file {hit}; answered in one read {sum(d[3]['path'] == 'read' for d in detail)}")
    for status in ("same", "moved", "changed"):
        sub = [d for d in detail if d[0]["status"] == status]
        if sub:
            print(f"    {status}: n={len(sub)} lane opened {sum(d[1] for d in sub)}, shows file {sum(d[2] and d[1] for d in sub)}, one read {sum(d[3]['path'] == 'read' for d in sub)}")

