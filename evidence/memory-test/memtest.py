"""The memory test: Model D 0.5.3, on questions that have nothing to do with bug fixes. No model calls, $0.

For each repository, on the code as it was a year back:
  cold     map only, nothing taught
  teach    teach every question at the line read from the code
  next     a new process: only what the disk holds
  mate     a teammate's own build, lessons carried from the first (modeld build --out --carry)
  copy     the folder copied elsewhere, with the repository moved away
  notes    a lesson with no line in the repository, on a throwaway copy
  recite   on that copy, the lessons `teach` refused, cited again with the repository's folder name; recite_ask asks them
then at the code as it is now:
  later    git checkout, modeld build . (a rebuild in place carries the lessons), then ask again
  fresh    the same code, a new map with nothing taught
Every phase is its own process, so nothing survives in memory between them. cli.json is one question through the real
command line: ask, teach, ask, ask in other words, each its own process.

    <modeld python> -I memtest.py <workdir>     -> data/memtest/<repo>.<phase>.json, <repo>.build.json, cli.json"""
import contextlib, hashlib, io, json, os, re, shutil, subprocess, sys, time
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "data", "memtest")
PLAN = json.load(open(os.path.join(H, "memtest_questions.json")))
norm = lambda s: " ".join(s.split())


def ask_all(ws, questions, key):
    """Ask every question in both wordings, in this process, against what the folder holds."""
    from ocm.router import router as RL
    from ocm.server import Workspace
    w = Workspace(ws); rows = []
    for f in questions:
        for which in ("q", "other"):
            q = f[which]; L = w.lanes
            _, obs = L.measure(q); slot, lane = RL.emit(L.byte(obs, False), 63)
            text = w.handle("ask", {"question": q}); flat = norm(text)
            rows.append({"kind": f["kind"], "wording": "same" if which == "q" else "other", "q": q, "lane": RL.LANES[lane], "opens": RL.LANES[lane] == "CERTIFIED",
                         "line_in_readout": norm(f[key]) in flat, "old_answer_shown": f["t0"] != f["t2"] and key == "t2" and norm(f["t0"]) in flat,
                         "tokens": len(text) // 4, "head": text.split("\n")[0][:160]})
        assert all(("taught question's vector" in r["head"]) == r["opens"] for r in rows[-2:]), rows[-2:]
    return rows


def phase(repo, name, work):
    spec = PLAN["repos"][repo]; qs = spec["questions"]; path = os.path.join(work, repo); ws = os.path.join(path, "modeld-out")
    save = lambda obj: json.dump(obj, open(os.path.join(OUT, f"{repo}.{name}.json"), "w"), indent=1)
    t0 = time.time()
    if name == "cold":
        save(ask_all(ws, qs, "t0"))
    elif name == "teach":
        from ocm.server import Workspace
        w = Workspace(ws); replies = []
        for f in qs:
            replies.append({"q": f["q"], "at": f["at"], "reply": w.handle("teach", {"pairs": [{"question": f["q"], "at": f["at"]}]})[:200]})
        save(replies)
    elif name == "next":
        save(ask_all(ws, qs, "t0"))
    elif name == "mate":
        save(ask_all(os.path.join(work, repo + ".mate"), qs, "t0"))
    elif name == "copy":
        save(ask_all(os.path.join(work, repo + ".copy"), qs, "t0"))
    elif name == "notes":
        from ocm.server import Workspace
        w = Workspace(os.path.join(work, repo + ".throwaway"))
        save({"reply": w.handle("teach", {"pairs": [{"question": "Why did the team choose this design?", "at": "we decided this in a meeting last March"}]})[:240]})
    elif name == "recite":
        from ocm.server import Workspace
        w = Workspace(os.path.join(work, repo + ".throwaway")); done = json.load(open(os.path.join(OUT, f"{repo}.teach.json"))); got = []
        for f, d in zip(qs, done):
            if d["reply"].startswith("taught 0"):
                at = repo + "/" + f["at"]
                got.append({"q": f["q"], "at": at, "reply": w.handle("teach", {"pairs": [{"question": f["q"], "at": at}]})[:60]})
        save(got)
    elif name == "recite_ask":
        got = {x["q"] for x in json.load(open(os.path.join(OUT, f"{repo}.recite.json")))}
        save(ask_all(os.path.join(work, repo + ".throwaway"), [f for f in qs if f["q"] in got], "t0"))
    elif name == "later":
        save(ask_all(ws, qs, "t2"))
    elif name == "fresh":
        save(ask_all(path + ".fresh", qs, "t2"))
    print(f"  {repo} {name}: {time.time() - t0:.1f} s", flush=True)


def me(repo, name, work):
    subprocess.run([sys.executable, "-I", os.path.abspath(__file__), work, repo, name], check=True)


def build(args, log):
    """modeld build, in its own process, keeping what it prints."""
    code = "import sys; from ocm.cli import main; main(sys.argv[1:])"
    t0 = time.time()
    r = subprocess.run([sys.executable, "-I", "-c", code, "build", *args], check=True, capture_output=True, text=True)
    out = r.stdout + r.stderr
    keep = [re.sub(r"/var/folders/\S+", "<tmp>", l.replace(os.path.dirname(args[0]), "<work>")) for l in out.splitlines() if re.search(r"carried|workspace ready", l)]
    print("\n".join("    " + l[:150] for l in keep), flush=True)
    log.append({"args": [a.replace(os.path.dirname(args[0]), "<work>") for a in args], "seconds": round(time.time() - t0, 1), "lines": keep})


def cli(ws, repo, f):
    """One question through the real command line, each call its own process."""
    code = "import sys; from ocm.cli import main; main(sys.argv[1:])"
    env = dict(os.environ, MODELD_WORKSPACE=ws); got = []
    for args in (["ask", f["q"]], ["teach", f["q"], f["at"]], ["ask", f["q"]], ["ask", f["other"]]):
        r = subprocess.run([sys.executable, "-I", "-c", code, *args], check=True, capture_output=True, text=True, env=env)
        got.append({"args": args, "out": r.stdout})
    json.dump({"repo": repo, "calls": got}, open(os.path.join(OUT, "cli.json"), "w"), indent=1)


def main():
    work = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        return phase(sys.argv[2], sys.argv[3], work)
    os.makedirs(OUT, exist_ok=True); os.makedirs(work, exist_ok=True)
    open(os.path.join(OUT, "questions.sha256"), "w").write(hashlib.sha256(open(os.path.join(H, "memtest_questions.json"), "rb").read()).hexdigest() + "\n")
    for repo, spec in PLAN["repos"].items():
        path = os.path.join(work, repo); ws = os.path.join(path, "modeld-out"); cache = os.path.join(work, repo + ".cache.sqlite"); log = []
        print(repo, flush=True)
        if not os.path.isdir(path):
            subprocess.run(["git", "clone", "-q", spec["url"], path], check=True)
        for d in (ws, path + ".mate", path + ".copy", path + ".throwaway", path + ".away", path + ".fresh", path + ".demo"):
            shutil.rmtree(d, ignore_errors=True)
        subprocess.run(["git", "-C", path, "checkout", "-q", spec["t0"]], check=True)
        build([path, "--cache", cache], log)
        if repo == "gin":
            shutil.copytree(ws, path + ".demo")
            cli(path + ".demo", repo, next(f for f in spec["questions"] if f["kind"] == "security"))
        me(repo, "cold", work); me(repo, "teach", work); me(repo, "next", work)
        build([path, "--out", path + ".mate", "--carry", ws, "--cache", cache], log)
        me(repo, "mate", work)
        shutil.copytree(ws, path + ".copy"); shutil.copytree(ws, path + ".throwaway")
        os.rename(path, path + ".away")                        # the copy has to stand alone
        try:
            me(repo, "copy", work)
            me(repo, "notes", work)
            me(repo, "recite", work)
            me(repo, "recite_ask", work)
        finally:
            os.rename(path + ".away", path)
        n = subprocess.run(["git", "-C", path, "rev-list", "--count", f"{spec['t0']}..{spec['t2']}"], capture_output=True, text=True).stdout.strip()
        stat = subprocess.run(["git", "-C", path, "diff", "--shortstat", spec["t0"], spec["t2"]], capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "-C", path, "checkout", "-q", spec["t2"]], check=True)
        build([path, "--cache", cache], log)
        me(repo, "later", work)
        build([path, "--out", path + ".fresh", "--cache", cache], log)
        me(repo, "fresh", work)
        json.dump({"builds": log, "commits_between": int(n), "diff": stat}, open(os.path.join(OUT, f"{repo}.build.json"), "w"), indent=1)


main()
