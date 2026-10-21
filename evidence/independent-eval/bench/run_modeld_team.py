"""Model D team replay on a fixed question list (run with the modeld venv). The loop is ocm.prove's --learn loop:
each fix is a new session with a fresh map of the code right before it; it is asked cold, then again after the shared
workspace's lessons from every earlier fix are carried over; then the fix lands and is taught where it landed (the
first line it wrote in its main file), as the Stop hook teaches a TEACH line. Nothing about a fix is taught before it
is asked."""
import json, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(__file__))
from common import ranked_code_files, score
from ocm.build import build
from ocm.server import Workspace
from ocm.prove import extract, landing, items_of

repo, qfile, out, cache = sys.argv[1:5]
repo = os.path.abspath(repo)
Q = json.load(open(qfile))
tmp = tempfile.mkdtemp(prefix="team-", dir=os.path.dirname(out))
rows, prev = [], None
try:
    for i, q in enumerate(Q, 1):
        snap, ws = os.path.join(tmp, "saleor"), os.path.join(tmp, f"ws{i % 2}")
        shutil.rmtree(snap, ignore_errors=True); shutil.rmtree(ws, ignore_errors=True); os.makedirs(snap)
        extract(repo, q["parent"], snap, os.path.join(tmp, "index"))
        t0 = time.time(); build([snap], ws, log=lambda *a: None, cache=cache); bt = time.time() - t0
        w = Workspace(ws)
        cold_text = w.handle("ask", {"question": q["question"], "scope": "code"})
        cold = ranked_code_files(f for f, _, _ in items_of(w, cold_text))
        c = w.carry(prev) if prev else {"entries": 0, "carried": 0}
        mem_text = w.handle("ask", {"question": q["question"], "scope": "code"})
        mem = ranked_code_files(f for f, _, _ in items_of(w, mem_text))
        land, taught = landing(repo, q), None
        if land:
            f, ln, after = land
            open(os.path.join(snap, f), "w", encoding="utf-8").write(after)
            if not w.handle("teach", {"pairs": [{"question": q["question"], "at": f"{f}:{ln}"}]}).startswith("taught 0 "):
                taught = f
        if prev:
            shutil.rmtree(prev, ignore_errors=True)
        prev = ws
        r = {"n": i, "hash": q["hash"][:10], "author": q["author"], "question": q["question"], "gold": q["gold"],
             "cold": {**score(cold, q["gold"]), "files": cold[:5], "tokens": len(cold_text) // 4},
             "mem": {**score(mem, q["gold"]), "files": mem[:5], "tokens": len(mem_text) // 4,
                     "pointer_led": mem_text.startswith("(readout: the code a taught")},
             "lessons": c["entries"], "carried": c["carried"], "taught": taught, "build_s": round(bt, 1)}
        rows.append(r)
        mark = lambda s: "HIT1" if s["top1"] else ("top5" if s["top5"] else "miss")
        print(f"{i:>3}/{len(Q)} cold {mark(r['cold'])}  mem {mark(r['mem'])}{' (pointer)' if r['mem']['pointer_led'] else ''}"
              f"  lessons {c['entries']:>3}  build {bt:5.1f}s  {q['question'][:55]}", flush=True)
        json.dump(rows, open(out, "w"), indent=1)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
