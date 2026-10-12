"""PROTOCOL_REPLAY.md: ten years of Django fixes through one shared kit, offline.
    ~/.venvs/cmlm-live/bin/python replay.py stream                         -> stream.json
    ~/.venvs/cmlm-live/bin/python replay.py run <raw|masked> <frozen|learning>   -> rows_<form>_<mode>.jsonl"""
import json, os, re, shutil, subprocess, sys, tempfile, time, warnings
warnings.filterwarnings("ignore"); os.environ["OCM_OFFLINE"] = "1"; os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_VERBOSITY"] = "error"
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
FILES = json.load(open(f"{B}/swe/files.json"))
TAUGHT = "(readout: the code a taught question"
STOP = set("the and for with that this from into when are was were not but has have had its use used uses using make made makes "
           "add added adds fix fixed fixes allow allowed allows can could should would will than then also only more less "
           "new old all any each other some such via per your you our them they their there here what which who how why".split())
PREFIX = re.compile(r"^Fixed #\d+(?:\s*,\s*#\d+)*(?:\s*(?:and|,)\s*#\d+)*\s*--\s*")
CODEY = re.compile(r"[._()\[\]`'\"=<>/]|::|^[A-Z]{2,}$|[a-z][A-Z]|^[A-Z][a-z]+[A-Z]")


def mask(q):
    return " ".join(t for t in q.split() if not CODEY.search(t))


def words(s):
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", s.lower()) if w not in STOP}


def stream():
    log = subprocess.run(["git", "-C", f"{B}/histories/django", "log", "--no-merges", "--reverse", "--since=2013-01-01", "4a72da7",
                          "--format=%x1e%H%x1f%ad%x1f%s", "--date=short", "--name-only"], capture_output=True, text=True).stdout
    out = []
    for b in log.split("\x1e")[1:]:
        lines = b.strip("\n").split("\n"); h, d, s = lines[0].split("\x1f", 2)
        if not re.match(r"^Fixed #\d+", s): continue
        code = [l for l in lines[1:] if l.endswith(".py") and l.startswith("django/")]
        gold = [c for c in code if "corpus/" + c in FILES]
        if not gold or len(code) > 20: continue
        raw = PREFIX.sub("", s).strip()
        out.append({"k": len(out), "hash": h, "date": d, "raw": raw, "masked": mask(raw), "gold": gold})
    json.dump(out, open(f"{H}/stream.json", "w"), indent=0)
    print(len(out), "questions;", sum(1 for q in out if not q["masked"].strip()), "masked to empty")


def place(q):
    """The line the engineer's work points to: max word overlap with the RAW subject, across the gold files."""
    want = words(q["raw"]); best = (-1, 0, 0)
    for fi, g in enumerate(q["gold"]):
        try: lines = open(FILES["corpus/" + g], encoding="utf-8").read().split("\n")
        except (OSError, UnicodeDecodeError): continue
        for li, line in enumerate(lines, 1):
            o = len(want & words(line))
            if o > best[0] or (o == best[0] and (fi, li) < (best[1], best[2]) and best[0] > 0): best = (o, fi, li)
    if best[0] <= 0: return q["gold"][0], 1
    return q["gold"][best[1]], best[2]


def run(form, mode):
    sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
    from ocm.server import Workspace
    from ocm.loop import readout
    S = json.load(open(f"{H}/stream.json"))
    d = os.path.join(tempfile.mkdtemp(), "ws"); shutil.copytree(f"{B}/swe/ws_base", d); w = Workspace(d)
    out = open(f"{H}/rows_{form}_{mode}.jsonl", "w"); t0 = time.time()
    for q in S:
        text = q[form] if q[form].strip() else "(empty)"
        r = readout(lambda p, **kw: w.handle(p, kw), text)
        paths = re.findall(r"corpus/(django/[\w/]+\.py)", r)
        seen = []; [seen.append(p) for p in paths if p not in seen]
        lane = r.startswith(TAUGHT)
        row = {"k": q["k"], "hit": any(g in seen for g in q["gold"]), "lane": lane,
               "lane right": bool(lane and paths and paths[0] in q["gold"]), "paths": seen[:12]}
        if mode == "learning":
            f, line = place(q); placed = None
            for off in [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8, -8]:
                if line + off < 1: continue
                t = str(w.handle("teach", {"pairs": [{"question": text, "at": f"corpus/{f}:{line + off}"}]}))
                if re.search(r"taught [1-9]\d* question vectors", t): placed = f"{f}:{line + off}"; break
            row["taught at"] = placed
        out.write(json.dumps(row) + "\n"); out.flush()
        if q["k"] % 500 == 0: print(form, mode, q["k"], round(time.time() - t0), "s", flush=True)
    shutil.rmtree(os.path.dirname(d)); print(form, mode, "done", round(time.time() - t0), "s")


if __name__ == "__main__":
    if sys.argv[1] == "stream": stream()
    else: run(sys.argv[2], sys.argv[3])
