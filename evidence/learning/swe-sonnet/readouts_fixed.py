"""The learning kit with every lesson placed: when the gold line is one the workspace does not hold (a blank line), the
lesson goes to the nearest held line of the same file (gold+1..+5, then gold-1..-5). Readouts before each issue, as
readouts.py. -> readouts_fixed.json, teach_fixed.json"""
import json, os, re, shutil, sys, tempfile, warnings
warnings.filterwarnings("ignore"); os.environ["OCM_OFFLINE"] = "1"; os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_VERBOSITY"] = "error"
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
from ocm.server import Workspace
from ocm.loop import readout
ISSUES = json.load(open(f"{B}/swe/issues.json"))["issues"]
d = os.path.join(tempfile.mkdtemp(), "ws"); shutil.copytree(f"{B}/swe/ws_base", d); w = Workspace(d)
out, log = {}, []
for i in ISSUES:
    out[i["id"]] = readout(lambda p, **kw: w.handle(p, kw), i["issue"][:4000])
    for off in [0, 1, 2, 3, 4, 5, -1, -2, -3, -4, -5]:
        t = str(w.handle("teach", {"pairs": [{"question": i["issue"][:4000], "at": f"corpus/{i['file']}:{i['line'] + off}"}]}))
        if re.search(r"taught [1-9]\d* question vectors", t):
            log.append({"id": i["id"], "offset": off}); break
    else:
        log.append({"id": i["id"], "offset": None})
json.dump(out, open(f"{H}/readouts_fixed.json", "w"), indent=1); json.dump(log, open(f"{H}/teach_fixed.json", "w"), indent=1)
shutil.rmtree(os.path.dirname(d))
print("placed", sum(1 for x in log if x["offset"] is not None), "moved", [x for x in log if x["offset"] not in (0, None)])
