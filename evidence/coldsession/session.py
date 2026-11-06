"""One session of one arm, as its own process: nothing comes along except what is on disk. Resumes.

    <modeld python> -I session.py <repo> <arm> <session 1-4>

    session 1  the first time, at T0: the taught facts in wording a
    session 2  the next day, at T0: the taught facts in wording b, plus new questions never asked before
    session 3  a teammate, at T0, on another checkout, with only what the first person's disk holds: the taught facts in wording c
    session 4  a year later, at T2, after a rebuild at T1 and another at T2: the taught facts in wording d, with the code as it is then
    session 5  session 2 again, with 200 more lessons on disk from what a busy team has learned: does carrying more cost more?

The arms with nothing to carry run only sessions 2 and 4: with no memory, a first time and a next day are the same, and a teammate is anyone else. Agents alone are the
expensive arm, so this keeps the benchmark's bill down."""
import json, os, shutil, sys, time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms as A  # noqa: E402
import common as C  # noqa: E402
import wordings as W  # noqa: E402
from ocm.build import build  # noqa: E402



def snap(repo, t):
    return C.work(repo, "snap", t, "repo")


def quiet(*_):
    pass


def built(repo, name, t, carry=None):
    """A map, built once. Maps of the same repository share an embedding cache, so a rebuild embeds only what changed."""
    ws = C.work(repo, "maps", name)
    assert not os.path.isdir(os.path.join(snap(repo, t), "repo")), f"{snap(repo, t)} has an extra folder level"
    if not os.path.exists(os.path.join(ws, "workspace.json")):
        if shutil.disk_usage(C.WORK).free < 1 << 30:
            print("STOP: under 1 GB of disk free", flush=True); sys.exit(4)
        shutil.rmtree(ws, ignore_errors=True)
        build([snap(repo, t)], ws, log=quiet, cache=C.work(repo, "embed.sqlite"), carry=carry)
    return ws


def background(repo, n=200):
    """Lessons a busy team already has: facts outside the benchmark's questions, each with its right answer and line, given alike to every arm that keeps lessons."""
    used = {f["id"] for f in C.rows(C.data(repo, "facts.jsonl"))}
    rows = [f for f in C.rows(C.data(repo, "pool.jsonl")) if f["id"] not in used and f["status"] == "same"][:n]
    return [(W.templated(f)["a"], W.shown(f), f"{f['path']}:{f['line']}") for f in rows]


def folder(repo, arm, session):
    """The map this arm's session runs on. What Model D carries forward lives in these folders and nowhere else."""
    plain = built(repo, "T2" if session == 4 else "T0", "T2" if session == 4 else "T0")
    if arm != "modeld":
        return plain
    first, after = C.work(repo, "maps", "modeld_first"), C.work(repo, "maps", "modeld_after_S1")
    if not os.path.exists(first):
        shutil.copytree(built(repo, "T0", "T0"), first)     # sessions 1 and 2 share it
    if session == 1:
        return first
    if not os.path.exists(after):
        shutil.copytree(first, after)                       # what the disk held after session 1, for session 5
    if session == 2:
        return first
    if session == 5:
        big = C.work(repo, "maps", "modeld_big")
        if not os.path.exists(big):
            shutil.copytree(after, big)
            from ocm.server import Workspace
            Workspace(big).handle("teach", {"pairs": [{"question": q, "at": at} for q, _, at in background(repo)]})
        return big
    mate = built(repo, "modeld_mate", "mate", carry=first)  # the teammate's own build, from the first person's lessons on disk
    if session == 3:
        return mate
    return built(repo, "modeld_T2", "T2", carry=built(repo, "modeld_T1", "T1", carry=mate))


def notes_file(repo, session):
    main_file, after, big = C.work(repo, "notes.md"), C.work(repo, "notes_after_S1.md"), C.work(repo, "notes_big.md")
    if session > 1 and os.path.exists(main_file) and not os.path.exists(after):
        shutil.copy(main_file, after)
    if session != 5:
        return main_file
    if not os.path.exists(big):
        shutil.copy(after, big)
        book = A.Notes(big)
        for q, answer, at in background(repo):
            book.add(q, answer, at)
    return big


def questions(facts, session):
    w = {1: "a", 2: "b", 3: "c", 4: "d", 5: "b"}[session]
    of = lambda *roles: [f for f in facts if f["role"] in roles]
    if session == 1:
        return [(f, "a") for f in of("taught", "named")]
    if session == 2:
        return [(f, "b") for f in of("taught", "named")] + [(f, "a") for f in of("sibling", "unrelated")]
    return [(f, w) for f in of("taught")]


def main(repo, arm, session, model=None):
    assert session in C.SESSIONS[arm]
    facts = C.rows(C.data(repo, "facts.jsonl"))
    slug = json.load(open(C.data(repo, "pins.json")))["repo"]
    out = C.results(repo, f"{arm}_S{session}.jsonl"); os.makedirs(os.path.dirname(out), exist_ok=True)
    done = {r["id"] for r in C.rows(out)}
    jobs = [(f, w) for f, w in questions(facts, session) if f["id"] not in done]
    if not jobs:
        return
    model = model or A.Model()
    kit = None if arm == "guess" else A.Kit(folder(repo, arm, session), memory=arm == "modeld")
    notes = A.Notes(notes_file(repo, session)) if arm == "notes" else None

    errors = []

    def one(job):
        f, w = job
        q = f["wordings"][w]
        model.bill.start(); t0 = time.time()
        try:
            if arm == "guess":
                r = {"path": "guess", "answer": model.guess(slug, q), "at": None}
            elif arm == "alone":
                r = A.alone(model, kit, q)
            elif arm == "notes":
                r = A.noted(model, kit, notes, q)
            else:
                r = A.modeld(model, kit, q)
        except C.OverCap:
            raise
        except Exception as e:                              # one failed call is recorded and counts as not right; many stop the run
            errors.append(e)
            print(f"ERROR on {f['id']}: {type(e).__name__}: {str(e)[:200]}", flush=True)
            if len(errors) > 5:
                raise
            r = {"path": "error", "answer": "", "at": None, "error": f"{type(e).__name__}: {str(e)[:200]}"}
        row = {"id": f["id"], "wording": w, "question": q, "path": r["path"], "answer": str(r["answer"]), "at": r.get("at"), "notes_chars": r.get("notes_chars"), "error": r.get("error"), **model.bill.tally(), "seconds": round(time.time() - t0, 1)}
        with open(out, "a") as o:
            o.write(json.dumps(row) + "\n")

    stateless = arm in ("alone", "map", "guess")            # no state moves between questions, so they can run side by side; the others must keep their order
    try:
        with ThreadPoolExecutor(4 if stateless else 1) as ex:
            list(ex.map(one, jobs))
    except C.OverCap as e:
        print("STOP:", e, flush=True); sys.exit(3)
    print(f"{repo} {arm} S{session}: {len(C.rows(out))} answers, spent ${C.spent():.3f}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
