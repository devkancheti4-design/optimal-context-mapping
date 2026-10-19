"""METHOD2.md.  python run2.py <arm: base|f1|f2|f12|f3|f13>  -> results2_<set>_<arm>.json for sets B, R, A"""
import json, os, re, shutil, sys
arm = sys.argv[1]
if arm in ("f2", "f12"):
    os.environ["OCM_CERT_MIN_OVER_OWN"] = "37"
if arm in ("f3", "f13"):
    os.environ["OCM_RELATION_LIMIT"] = "37"
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
import numpy as np
from ocm import server as SV
from ocm.server import Workspace, NAMES
from ocm.router import lanes as L, router as RL
assert (L.CERT_MIN_OVER_OWN == 37) == (arm in ("f2", "f12")), L.CERT_MIN_OVER_OWN
assert (L.RELATION_LIMIT == 37) == (arm in ("f3", "f13")), L.RELATION_LIMIT
H = os.path.dirname(os.path.abspath(__file__)); TY = os.path.expanduser("~/neos/outreach/team-year")
EV = os.path.expanduser("~/optimal-context-mapping/evidence/claude-api/inputs")
if arm in ("f1", "f12", "f13"):
    orig = Workspace.routed
    def routed(self, question, first, scope=None):
        text = orig(self, question, first, scope)
        if not text.startswith("(readout: " + NAMES[0]):
            return text
        allow = self.code if (scope or self.scope or "all").lower() == "code" else None
        rows, _ = self.lanes.measure(question, allow=allow)
        lead = [j for j in rows[0][:1]]
        out = list(dict.fromkeys(lead + list(rows[3]) + list(rows[1])))[:5]
        out = [j for j in out if j < len(self.mem.texts)]
        return f"(readout: {NAMES[0]})\n\n" + "\n\n".join(self.fmt(j, i) for i, j in enumerate(out, 1))
    Workspace.routed = routed
CITE = re.compile(r"^\s*\d+\.\s*\[([^\]]+?):\d+\]", re.M)
TAUGHT = "(readout: " + NAMES[0]


def score(w, q, gold, norm):
    text = w.routed(q, True, "code"); files = [norm(f) for f in dict.fromkeys(CITE.findall(text))]
    hit = lambda fs: any(f == g or f.endswith("/" + g) for f in fs for g in gold)
    return {"right1": hit(files[:1]), "right5": hit(files[:5]), "taught": text.startswith(TAUGHT)}


def relane(w):
    w.lanes = L.Lanes(w.mem, np.arange(w.meta["units"]), os.path.join(w.folder, "keyword.db"), RL)


# B: the team year replay
keep = set(json.load(open(f"{TY}/keep.json"))); items = [x for x in json.load(open(f"{TY}/window_2022.json")) if x["k"] in keep]
md = {json.loads(l)["k"]: json.loads(l) for l in open(f"{TY}/rows_md.jsonl")}
ws = f"{H}/ws2_B_{arm}"; shutil.rmtree(ws, ignore_errors=True); shutil.copytree(f"{TY}/ws/base", ws); w = Workspace(ws); rows = []
nd = lambda p: p.split("/", 1)[1] if p.startswith("django/django/") else p
for x in items:
    q = f"Where is the code behind this change: {x['raw']}"
    rows.append({"k": x["k"], **score(w, q, x["gold"], nd)})
    r = md.get(x["k"])
    if r and r["path"] == "teach" and r.get("where"):
        pl = w.place(r["where"])
        if pl:
            w.mem.teach_at([(q, pl[0])]); relane(w)
json.dump(rows, open(f"{H}/results2_B_{arm}.json", "w")); shutil.rmtree(ws, ignore_errors=True)
print(arm, "B", sum(r["right1"] for r in rows), sum(r["right5"] for r in rows), sum(r["taught"] for r in rows), flush=True)
# R: repeats in other words
iss = json.load(open(f"{EV}/issues.json"))["issues"]; para = json.load(open(f"{EV}/paraphrases.json"))
ws = f"{H}/ws2_R_{arm}"; shutil.rmtree(ws, ignore_errors=True)
shutil.copytree(os.path.expanduser("~/neos/outreach/vs-graphify/ws/lite/django"), ws); w = Workspace(ws)
pairs = []
for i in iss:
    pl = w.place(f"{i['file']}:{i['line']}")
    if pl:
        pairs.append((i["issue"], pl[0]))
w.mem.teach_at(pairs); relane(w)
nr = lambda p: p.split("/", 1)[1] if "/" in p else p
rows = [{"id": i["id"], **score(w, para[i["id"]], [i["file"]], nr)} for i in iss if i["id"] in para]
json.dump({"taught": len(pairs), "rows": rows}, open(f"{H}/results2_R_{arm}.json", "w")); shutil.rmtree(ws, ignore_errors=True)
print(arm, "R", len(pairs), sum(r["right1"] for r in rows), sum(r["right5"] for r in rows), sum(r["taught"] for r in rows), flush=True)
# A: coverage
w = Workspace(os.path.expanduser("~/neos/outreach/vs-graphify/ws/dj_cover"))
rows = [{"k": x["k"], **score(w, f"Where is the code behind this change: {x['raw']}", x["gold"], nd)} for x in items]
json.dump(rows, open(f"{H}/results2_A_{arm}.json", "w"))
print(arm, "A", sum(r["right1"] for r in rows), sum(r["right5"] for r in rows), sum(r["taught"] for r in rows), flush=True)
print(arm, "DONE")
