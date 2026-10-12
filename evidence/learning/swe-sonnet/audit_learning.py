"""Audit of S4/S5 (no new model calls): did teaching succeed, does the learning kit's readout surface the gold file more
often than a frozen (never-taught) kit's readout, and on which issues do the two readouts differ."""
import json, os, shutil, sys, tempfile, warnings, re
warnings.filterwarnings("ignore")
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
from ocm.server import Workspace
from ocm.loop import readout
ISSUES = json.load(open(f"{B}/swe/issues.json"))["issues"]; LEARN = json.load(open(f"{H}/readouts.json"))
d = os.path.join(tempfile.mkdtemp(), "ws"); shutil.copytree(f"{B}/swe/ws_base", d); w = Workspace(d)
frozen = {i["id"]: readout(lambda p, **kw: w.handle(p, kw), i["issue"][:4000]) for i in ISSUES}     # never taught
json.dump(frozen, open(f"{H}/readouts_frozen.json", "w"), indent=1)
# teaching return values, replayed on a fresh copy exactly as readouts.py did
d2 = os.path.join(tempfile.mkdtemp(), "ws"); shutil.copytree(f"{B}/swe/ws_base", d2); w2 = Workspace(d2)
teach = [w2.handle("teach", {"pairs": [{"question": i["issue"][:4000], "at": f"corpus/{i['file']}:{i['line']}"}]}) for i in ISSUES]
print("teach return examples:", [str(t)[:120] for t in teach[:2]])
bad = [k for k, t in enumerate(teach) if re.search(r"error|not found|no such|0 taught|skipped", str(t), re.I)]
print("teach calls that look failed:", len(bad), bad[:10])
seen, rows = set(), []
for k, i in enumerate(ISSUES):
    g = i["file"]; rep = g in seen; seen.add(g)
    rows.append({"k": k, "id": i["id"], "repeat": rep, "gold in learned": g in LEARN[i["id"]], "gold in frozen": g in frozen[i["id"]],
                 "differs": LEARN[i["id"]] != frozen[i["id"]], "taught lane": LEARN[i["id"]].startswith("(readout: the code a taught question")})
json.dump(rows, open(f"{H}/audit_rows.json", "w"), indent=1)
def s(sel, lab):
    n = len(sel); print(f"{lab:28s} n={n:3d}  gold in readout: learned {sum(r['gold in learned'] for r in sel):3d}  frozen {sum(r['gold in frozen'] for r in sel):3d}   readout differs {sum(r['differs'] for r in sel):3d}  taught lane {sum(r['taught lane'] for r in sel)}")
s(rows, "all"); s(rows[:57], "first half"); s(rows[57:], "second half"); s([r for r in rows if r["repeat"]], "repeat file"); s([r for r in rows if not r["repeat"]], "new file")
for q in range(4): s(rows[q * 28 + min(q, 2):(q + 1) * 28 + min(q + 1, 2)], f"quarter {q + 1}")
shutil.rmtree(os.path.dirname(d)); shutil.rmtree(os.path.dirname(d2))
