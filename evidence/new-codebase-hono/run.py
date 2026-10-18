"""Run METHOD.md: per fix, build Model D at the parent, ask both queries, record readouts, router trace and the
grep baseline; then delete the snapshot and workspace. Resumes. Run with Model D's environment:
    ~/ocm-eval/venvs/t021/bin/python -I run.py"""
import json, os, re, shutil, subprocess, sys, time
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
import ocm  # noqa: E402
assert ocm.__version__ == "0.5.0" and ocm.__file__.startswith(os.path.expanduser("~/optimal-context-mapping")), ocm.__file__
from ocm.build import build  # noqa: E402
from ocm.server import Workspace  # noqa: E402
from ocm.units import files as list_files, DOCS  # noqa: E402
H = os.path.dirname(os.path.abspath(__file__)); OUT = f"{H}/results.jsonl"; CACHE = f"{H}/embed_cache.sqlite"
STOP = set("the and for with from that this when into not are was were has have had but its use using used should "
           "would could can will fix fixes fixed bug issue make makes made allow allows add adds added".split())
CITE = re.compile(r"(?m)^\s*\d+\.\s*\[([^\]]+?):(\d+)\]")
Q = json.load(open(f"{H}/questions.json"))
done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()


def grep_rank(root, q):
    terms = sorted({w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) >= 3 and w not in STOP})
    scored = []
    for _, rel, path in list_files(root):
        if os.path.splitext(rel)[1].lower() in DOCS:
            continue
        try:
            t = open(path, encoding="utf-8", errors="replace").read().lower()
        except OSError:
            continue
        hits = [t.count(w) for w in terms]
        d = sum(1 for h in hits if h)
        if d:
            scored.append((-d, -sum(hits), rel.split("/", 1)[1] if "/" in rel else rel))
    return [r for _, _, r in sorted(scored)[:10]], terms


for n, it in enumerate(Q, 1):
    if it["id"] in done:
        continue
    snap, ws = f"{H}/snaps/hono", f"{H}/ws/{it['id']}"
    shutil.rmtree(snap, ignore_errors=True); os.makedirs(snap)
    subprocess.run(f"git -C {H}/hono archive {it['parent']} | tar -x -C {snap}", shell=True, check=True)
    shutil.rmtree(ws, ignore_errors=True)                       # a crashed run may leave one behind (D1)
    t0 = time.time(); build([snap], ws, log=lambda *a: None, cache=CACHE); build_s = time.time() - t0
    w = Workspace(ws); row = {"id": it["id"], "build_s": round(build_s, 1), "units": w.meta["units"], "q": {}}
    for name, q in it["queries"].items():
        t1 = time.time(); text = w.handle("ask", {"question": q, "scope": "code"}); ms = (time.time() - t1) * 1000
        items = []
        for p, ln in CITE.findall(text):
            pl = w.place(f"{p}:{ln}")
            span = next(((f, l) for f, l, j in w.spans.get(pl[1], []) if j == pl[0]), (int(ln), int(ln))) if pl else (int(ln), int(ln))
            items.append([p.split("/", 1)[1] if "/" in p else p, span[0], span[1]])
        _, obs = w.lanes.measure(q, allow=w.code)
        order, strong, weak = w.mem._rank(q)
        top = [int(j) for j in order if j < len(w.code) and w.code[j]][:5]
        vec = [{"path": w.mem.sources[w.mem.src[j]]["path"].split("/", 1)[-1], "line": int(w.mem.pos[j]), "weak": int(weak[j]),
                "strong": int(strong[j])} for j in top]
        g, terms = grep_rank(w.meta["roots"], q)
        row["q"][name] = {"header": text.split("\n", 1)[0], "items": items[:10], "chars": len(text), "ms": round(ms, 1),
                          "obs": {k: (v if isinstance(v, (int, float, bool, type(None))) else str(v)) for k, v in obs.items()},
                          "vector_top5": vec, "grep": g, "grep_terms": terms}
    with open(OUT, "a") as f:
        f.write(json.dumps(row) + "\n")
    shutil.rmtree(ws, ignore_errors=True)
    print(f"{n}/{len(Q)} {it['id']} build {build_s:.0f}s units {row['units']}", flush=True)
print("RUN DONE")
