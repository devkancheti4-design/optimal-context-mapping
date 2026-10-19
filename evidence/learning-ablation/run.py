"""METHOD.md. python run.py A|B <arm>  (A: on|off ; B: gate|forced)  -> results_<exp>_<arm>.json"""
import json, os, re, shutil, sys
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
import numpy as np
from ocm.cmlm_vector import lawsearch as LS
from ocm.server import Workspace
from ocm.router import lanes as L, router as RL
exp, arm = sys.argv[1], sys.argv[2]
H = os.path.dirname(os.path.abspath(__file__)); TY = os.path.expanduser("~/neos/outreach/team-year")
if arm in ("off",):
    LS.LearnedLaw.active = property(lambda self: False)
if arm in ("forced",):
    LS.LearnedLaw.active = property(lambda self: self.law != LS.BASE)
keep = set(json.load(open(f"{TY}/keep.json")))
items = [x for x in json.load(open(f"{TY}/window_2022.json")) if x["k"] in keep]
CITE = re.compile(r"^\s*\d+\.\s*\[([^\]]+?):\d+\]", re.M)
norm = lambda p: p.split("/", 1)[1] if p.startswith("django/django/") else p
hit = lambda files, gold: any(norm(f) == g or norm(f).endswith("/" + g) for f in files for g in gold)
if exp == "A":
    ws = os.path.expanduser("~/neos/outreach/vs-graphify/ws/dj_cover")
else:
    ws = f"{H}/ws_{arm}"; shutil.rmtree(ws, ignore_errors=True); shutil.copytree(f"{TY}/ws/base", ws)
    md = {json.loads(l)["k"]: json.loads(l) for l in open(f"{TY}/rows_md.jsonl")}
w = Workspace(ws); rows = []
for n, x in enumerate(items, 1):
    q = f"Where is the code behind this change: {x['raw']}"
    used = w.mem.law.active
    text = w.routed(q, True, "code"); files = list(dict.fromkeys(CITE.findall(text)))
    rows.append({"k": x["k"], "right1": hit(files[:1], x["gold"]), "right5": hit(files[:5], x["gold"]), "law_on": bool(used),
                 "law": LS.describe(w.mem.law.law), "header": text.split("\n", 1)[0][:60]})
    if exp == "B":
        r = md.get(x["k"])
        if r and r["path"] == "teach" and r.get("where"):
            pl = w.place(r["where"])
            if pl:
                w.mem.teach_at([(q, pl[0])])
                w.lanes = L.Lanes(w.mem, np.arange(w.meta["units"]), os.path.join(w.folder, "keyword.db"), RL)
    if n % 50 == 0:
        print(exp, arm, n, sum(r["right1"] for r in rows), flush=True)
json.dump({"rows": rows, "law_state": w.mem.law.state()}, open(f"{H}/results_{exp}_{arm}.json", "w"), default=str)
print(exp, arm, "done: right1", sum(r["right1"] for r in rows), "right5", sum(r["right5"] for r in rows), "law on", sum(r["law_on"] for r in rows), flush=True)
