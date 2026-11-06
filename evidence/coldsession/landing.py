"""Model D's mechanisms alone, with no model calls: teach each fact's first wording onto the line that holds it, then ask in other words in new sessions, on a teammate's build
and after real commits. Does the lesson land, does the code it brings hold the fact, and how many tokens does that readout cost? The lessons here are perfect, so this is
the most teaching can do; session.py measures what an agent's own lessons do.

    <modeld python> -I landing.py <repo>     -> results/<repo>/landing.jsonl"""
import json, os, shutil, sys

os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
from ocm.loop import TAUGHT, readout  # noqa: E402
from ocm.server import Workspace  # noqa: E402
from session import background, built  # noqa: E402


def line_of(repo, t, path, line):
    lines = open(C.work(repo, "snap", t, "repo", path), encoding="utf-8", errors="replace").read().split("\n")
    return lines[line - 1].strip()


def asks(repo, w, f, wording, t, session, kind, out):
    path, line = (f["path"], f["line"]) if t == "T0" else (f["new_path"], f["new_line"])
    gold = line_of(repo, t, path, line)
    call = lambda p, **kw: w.handle(p, kw)
    code = readout(call, f["wordings"][wording])
    out.write(json.dumps({"id": f["id"], "kind": f["kind"], "role": f["role"], "status": f["status"], "session": session, "map": kind, "wording": wording, "lesson_led": code.startswith(TAUGHT),
                          "fact_in_readout": gold in code, "tokens": len(code) // 4}) + "\n")


def main(repo):
    facts = C.rows(C.data(repo, "facts.jsonl"))
    taught = [f for f in facts if f["role"] in ("taught", "named")]
    os.makedirs(C.results(repo), exist_ok=True)
    first = C.work(repo, "maps", "landing_first")
    shutil.rmtree(first, ignore_errors=True)
    shutil.copytree(built(repo, "T0", "T0"), first)
    w = Workspace(first)
    said = w.handle("teach", {"pairs": [{"question": f["wordings"]["a"], "at": f"{f['path']}:{f['line']}"} for f in taught]})
    print(said[:80], flush=True)
    for name in ("landing_mate", "landing_T1", "landing_T2"):
        shutil.rmtree(C.work(repo, "maps", name), ignore_errors=True)
    with open(C.results(repo, "landing.jsonl"), "w") as out:
        new = Workspace(first)                                    # a new session: only what the disk holds
        cold = Workspace(built(repo, "T0", "T0"))
        for f in facts:
            asks(repo, new, f, "b" if f["role"] in ("taught", "named") else "a", "T0", 2, "taught", out)
            asks(repo, cold, f, "b" if f["role"] in ("taught", "named") else "a", "T0", 2, "cold", out)
        mate = Workspace(built(repo, "landing_mate", "mate", carry=first))
        big = C.work(repo, "maps", "landing_big")
        shutil.rmtree(big, ignore_errors=True); shutil.copytree(first, big)
        more = Workspace(big)
        more.handle("teach", {"pairs": [{"question": q, "at": at} for q, _, at in background(repo)]})
        for f in taught:
            asks(repo, more, f, "b", "T0", 5, f"taught, {len(more.life.store)} lessons", out)
        for f in taught:
            asks(repo, mate, f, "c", "T0", 3, "taught", out)
        later = Workspace(built(repo, "landing_T2", "T2", carry=built(repo, "landing_T1", "T1", carry=C.work(repo, "maps", "landing_mate"))))
        cold2 = Workspace(built(repo, "T2", "T2"))
        for f in taught:
            asks(repo, later, f, "d", "T2", 4, "taught", out)
            asks(repo, cold2, f, "d", "T2", 4, "cold", out)
    print(json.dumps(summary(repo), indent=1), flush=True)


def summary(repo):
    groups = {}
    for r in C.rows(C.results(repo, "landing.jsonl")):
        key = f"S{r['session']} {r['map']}" + (f" {r['status']}" if r["session"] == 4 else "") + (f" {r['role']}" if r["session"] == 2 and r["role"] != "taught" else "")
        groups.setdefault(key, []).append(r)
    mean = lambda v: round(sum(v) / len(v), 3)
    return {k: {"n": len(v), "lesson led": mean([r["lesson_led"] for r in v]), "fact in readout": mean([r["fact_in_readout"] for r in v]), "tokens": round(mean([r["tokens"] for r in v]))} for k, v in sorted(groups.items())}


if __name__ == "__main__":
    main(sys.argv[1])
