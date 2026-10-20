"""METHOD.md: every question asked twice of the same workspace, tests after code OFF and ON. Resumes.
    python -I run.py graphify|claude-mem|hono <repo>     builds at each fix's parent, with $CACHE as embedding cache
    python -I run.py django-cold|django-taught           the team year's 288 questions on a built Django workspace
-> results_<set>.jsonl. Run with Model D's environment (OCM_OFFLINE=1 HF_HUB_OFFLINE=1)."""
import json, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
import ocm  # noqa: E402
from ocm import server as SV  # noqa: E402
from ocm.build import build  # noqa: E402
from ocm.prove import CITE, extract, grep_rank, questions  # noqa: E402
from ocm.units import DOCS, files as list_files  # noqa: E402
assert ocm.__file__.startswith(os.path.expanduser("~/optimal-context-mapping")), ocm.__file__
H = os.path.dirname(os.path.abspath(__file__)); NAME = sys.argv[1]
REPO = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
OUT = f"{H}/results_{NAME}.jsonl"; TY = os.path.expanduser("~/neos/outreach/team-year")
done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()


def readout(w, q):
    """The readout's items as [file, first line, last line], file relative to the repository."""
    text = w.routed(q, True, "code"); items = []
    for p, ln in CITE.findall(text):
        pl = w.place(f"{p}:{ln}")
        span = next(((f, l) for f, l, j in w.spans.get(pl[1], []) if j == pl[0]), (int(ln), int(ln))) if pl else (int(ln), int(ln))
        items.append([p.split("/", 1)[1] if "/" in p else p, span[0], span[1]])
    return items


def both(w, q):
    out = {}
    for arm, on in (("off", False), ("on", True)):
        SV.TESTS_TRAIL = on; out[arm] = readout(w, q)
    return out


def write(row):
    with open(OUT, "a") as f:
        f.write(json.dumps(row) + "\n")


if NAME.startswith("django"):
    keep = set(json.load(open(f"{TY}/keep.json")))
    items = [x for x in json.load(open(f"{TY}/window_2022.json")) if x["k"] in keep]
    ws = f"{TY}/ws/base" if NAME == "django-cold" else os.path.expanduser("~/neos/outreach/vs-graphify/ws/dj_cover")
    w = SV.Workspace(ws)
    for x in items:
        if str(x["k"]) in done:
            continue
        q = f"Where is the code behind this change: {x['raw']}"
        write({"id": str(x["k"]), "gold": x["gold"], "lines": {}, "exempt": bool(SV.ABOUT_TESTS.search(q)),
               "q": {"q": {**both(w, q), "grep": None}}})
    print("RUN DONE", NAME); sys.exit()

if NAME == "hono":
    Q = [{"hash": x["id"], "parent": x["parent"], "gold": x["gold"], "lines": {f: [tuple(r) for r in v] for f, v in x["gold_lines"].items()},
          "queries": x["queries"]} for x in json.load(open(f"{H}/../new-codebase-hono/questions.json"))]
else:
    Q = [{**q, "queries": {"q": q["question"]}} for q in questions(REPO, 50, 24)]
cache = os.path.abspath(os.environ["CACHE"]); tmp = tempfile.mkdtemp(prefix="trail-")
try:
    for n, q in enumerate(Q, 1):
        if q["hash"][:10] in done:
            continue
        snap, ws = os.path.join(tmp, os.path.basename(REPO)), os.path.join(tmp, "ws")
        shutil.rmtree(snap, ignore_errors=True); shutil.rmtree(ws, ignore_errors=True); os.makedirs(snap)
        extract(REPO, q["parent"], snap, os.path.join(tmp, "index"))
        t0 = time.time(); build([snap], ws, log=lambda *a: None, cache=cache); bt = time.time() - t0
        w = SV.Workspace(ws)
        code = [(rel.split("/", 1)[1] if "/" in rel else rel, path) for _, rel, path in list_files(w.meta["roots"])
                if os.path.splitext(rel)[1].lower() not in DOCS]
        row = {"id": q["hash"][:10], "gold": q["gold"], "lines": q["lines"], "build_s": round(bt, 1), "q": {},
               "exempt": {k: bool(SV.ABOUT_TESTS.search(v)) for k, v in q["queries"].items()}}
        for k, text in q["queries"].items():
            row["q"][k] = {**both(w, text), "grep": grep_rank(code, text)}
        write(row); shutil.rmtree(ws, ignore_errors=True)
        print(f"{n}/{len(Q)} {row['id']} build {bt:.0f}s", flush=True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("RUN DONE", NAME)
