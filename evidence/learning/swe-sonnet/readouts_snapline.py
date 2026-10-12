"""The learning kit with each lesson at the line the real fix changed, in the snapshot's numbering: the gold line is read
at the issue's own base commit (histories/django), mapped to the 4a72da7 snapshot with a line diff, and taught at the
nearest line the workspace holds (offsets 0, +1, -1, ... +-8). Readouts before each issue, as readouts.py.
-> readouts_snapline.json, teach_snapline.json"""
import difflib, json, os, re, shutil, subprocess, sys, tempfile, warnings
warnings.filterwarnings("ignore"); os.environ["OCM_OFFLINE"] = "1"; os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_VERBOSITY"] = "error"
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
from ocm.server import Workspace
from ocm.loop import readout
ISSUES = json.load(open(f"{B}/swe/issues.json"))["issues"]; FILES = json.load(open(f"{B}/swe/files.json"))


def mapped_line(i):
    base = subprocess.run(["git", "-C", f"{B}/histories/django", "show", f"{i['base']}:{i['file']}"], capture_output=True, text=True).stdout.split("\n")
    snap = open(FILES["corpus/" + i["file"]], encoding="utf-8").read().split("\n")
    t = i["line"] - 1
    if not base or t >= len(base): return None, "no base text"
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base, snap, autojunk=False).get_opcodes():
        if i1 <= t < i2 or (tag == "insert" and i1 == t):
            return (j1 + (t - i1) + 1 if tag == "equal" else j1 + 1), tag
    return None, "unmapped"


d = os.path.join(tempfile.mkdtemp(), "ws"); shutil.copytree(f"{B}/swe/ws_base", d); w = Workspace(d)
out, log = {}, []
for i in ISSUES:
    out[i["id"]] = readout(lambda p, **kw: w.handle(p, kw), i["issue"][:4000])
    m, kind = mapped_line(i)
    target = m if m else i["line"]
    placed = None
    for off in [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8, -8]:
        t = str(w.handle("teach", {"pairs": [{"question": i["issue"][:4000], "at": f"corpus/{i['file']}:{target + off}"}]}))
        if re.search(r"taught [1-9]\d* question vectors", t): placed = target + off; break
    log.append({"id": i["id"], "gold line (base)": i["line"], "mapped": m, "kind": kind, "taught at": placed})
json.dump(out, open(f"{H}/readouts_snapline.json", "w"), indent=1); json.dump(log, open(f"{H}/teach_snapline.json", "w"), indent=1)
shutil.rmtree(os.path.dirname(d))
print("mapped", sum(1 for x in log if x["mapped"]), "placed", sum(1 for x in log if x["taught at"]), "| moved from base line:", sum(1 for x in log if x["taught at"] and x["taught at"] != x["gold line (base)"]))
