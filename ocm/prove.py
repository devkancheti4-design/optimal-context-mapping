"""modeld prove: check Model D on your own repository, against your own bug fixes, at zero tokens.

  modeld prove [repo] [--fixes 50] [--months 24] [--learn] [--json FILE]

It replays the repository's most recent fix commits. Each fix is asked against the code exactly as it stood one
commit before the fix (`git archive` of the parent), in the words of its commit subject with any "fix(scope):" prefix
and PR number removed. The true answer is what the fix really changed:
- the non-test source files;
- the exact changed lines (`git diff -U0`, the parent side).

For each fix it reports whether Model D's readout put a changed file first, a changed file in its top 5, and a changed
line in its top 5. The same is reported for a grep-first look (files ranked by how many of the question's words they
contain).

Model D is cold here: nothing is taught, and no model is called. The first build embeds the whole repository (minutes
on a large one); every later build reuses the embedding cache and takes seconds. This is the test of
evidence/new-codebase-hono, where Model D put the right file first 31% of the time against grep's 16% (25% before
0.5.3 put test files after code: evidence/tests-trail).

With --learn it also replays the memory, the way a team's agents build it up. The fixes run in commit order, and each
is asked a second time, after its map has carried over everything taught so far: every commit gets a fresh map, as a
new session would, and what earlier fixes taught is found again in the new code by its exact line (`build --carry`).
Then the fix lands: its main file is written as the fix left it, and the first line the fix wrote there is taught as
the answer, as the Stop hook teaches an agent's TEACH line. Lessons from every author go into one workspace, as on a
team's shared server. Nothing about a fix is taught before it is asked."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time

from .forecast import FIX

CODE = (".py", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".astro", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".c", ".h",
        ".cc", ".cpp", ".hpp", ".swift", ".scala", ".vue", ".svelte")
TEST = re.compile(r"(^|/)(tests?|__tests__|testing|spec|specs|docs?|examples?|benchmarks?|fixtures?)/|(^|/)test_[^/]*\.py$|_test\.(py|go)$"
                  r"|\.(test|spec)\.[a-z]+$|(^|/)conftest\.py$|\.d\.ts$", re.I)
STOP = set("the and for with from that this when into not are was were has have had but its use using used should "
           "would could can will fix fixes fixed bug issue make makes made allow allows add adds added".split())
CITE = re.compile(r"(?m)^\s*\d+\.\s*\[([^\]]+?):(\d+)\]")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout


def questions(repo, n, months):
    """The last n fix commits that change a non-test source file present at their parent, oldest first."""
    since = f"{months} months ago"
    log = git(repo, "log", "--no-merges", f"--since={since}", "--format=%H%x09%P%x09%an%x09%s")
    out = []
    for line in log.strip().split("\n") if log.strip() else []:
        h, parents, author, s = line.split("\t", 3)
        if not FIX.search(s) or len(parents.split()) != 1:
            continue
        files = [f for f in git(repo, "diff", "--no-renames", "--name-only", parents, h).split("\n")
                 if f.endswith(CODE) and not TEST.search(f)]
        if not files:
            continue
        at_parent = set(git(repo, "ls-tree", "-r", "--name-only", parents).split("\n"))
        gold, lines, new = [f for f in files if f in at_parent], {}, {}
        for f in gold:
            rng, wrote = [], []
            for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))?", git(repo, "diff", "-U0", "--no-renames", parents, h, "--", f), re.M):
                a_, b = int(m.group(1)), int(m.group(2) or 1)
                rng.append((a_, a_ + b - 1) if b else (a_, a_ + 1))
                wrote.append((int(m.group(3)), int(m.group(4) or 1)))
            lines[f], new[f] = rng, wrote
        if gold:
            plain = re.sub(r"\s*\(#\d+\)", "", s).strip()
            bare = re.sub(r"^\s*fix(es|ed)?(\([^)]*\))?!?\s*:\s*", "", plain, flags=re.I).strip() or plain
            out.append({"hash": h, "parent": parents, "author": author, "question": bare, "gold": gold, "lines": lines, "new": new})
        if len(out) >= n:
            break
    return out[::-1]


def extract(repo, commit, dest, index):
    """Write the files Model D would index, as they were at commit, into dest. Only those are read from git, through a
    throwaway index, so the repository's own index and working tree are untouched, and in a partial clone the blobs
    are fetched in one batch, never the repository's images, PDFs or videos."""
    from .units import wanted
    paths = [p for p in git(repo, "ls-tree", "-r", "--name-only", commit).split("\n") if p and wanted(p)]
    if not paths:
        return
    env = {**os.environ, "GIT_INDEX_FILE": index}
    subprocess.run(["git", "-C", repo, f"--work-tree={dest}", "checkout", commit, "--pathspec-from-file=-", "--pathspec-file-nul"],
                   input="\0".join(paths), text=True, env=env, check=True, capture_output=True)
    if os.path.exists(index):
        os.remove(index)


def landing(repo, q):
    """Where a fix landed: its main file (the one it changed most), the first non-blank line it wrote there, and the
    file as the fix left it; None if there is no such line."""
    f = max(q["gold"], key=lambda g: sum(hi - lo + 1 for lo, hi in q["lines"].get(g, [])) + sum(d for _, d in q["new"].get(g, [])))
    try:
        after = git(repo, "show", f"{q['hash']}:{f}")
    except subprocess.CalledProcessError:
        return None
    L = after.split("\n")
    for c, d in q["new"].get(f, []):
        for ln in range(max(1, c), max(1, c) + max(1, d)):
            if ln <= len(L) and L[ln - 1].strip():
                return f, ln, after
    return None


def items_of(w, text):
    """A readout's items as (file relative to the repository, first line, last line) of each unit."""
    items = []
    for p, ln in CITE.findall(text):
        pl = w.place(f"{p}:{ln}")
        span = next(((f, l) for f, l, j in w.spans.get(pl[1], []) if j == pl[0]), (int(ln), int(ln))) if pl else (int(ln), int(ln))
        items.append((p.split("/", 1)[1] if "/" in p else p, span[0], span[1]))
    return items


def scored(items, q):
    files = list(dict.fromkeys(f for f, _, _ in items))
    return files, (bool(files[:1]) and files[0] in q["gold"], any(f in q["gold"] for f in files[:5]),
                   any(f == gf and a <= hi and b >= lo for f, a, b in items[:5] for gf, rngs in q["lines"].items() for lo, hi in rngs))


def grep_rank(files, q):
    terms = sorted({w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) >= 3 and w not in STOP})
    scored = []
    for rel, path in files:
        try:
            t = open(path, encoding="utf-8", errors="replace").read().lower()
        except OSError:
            continue
        hits = [t.count(w) for w in terms]
        d = sum(1 for x in hits if x)
        if d:
            scored.append((-d, -sum(hits), rel))
    return [r for _, _, r in sorted(scored)[:10]]


def prove(repo, n=30, months=24, cache=None, log=print, learn=False):
    from .build import build
    from .server import Workspace
    from .units import files as list_files, DOCS
    repo = os.path.abspath(repo)
    Q = questions(repo, n, months)
    if not Q:
        return {"repo": repo, "fixes": 0}
    cache = os.path.abspath(cache or os.environ.get("MODELD_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "modeld", "embed.sqlite"))
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="modeld-prove-"); rows = []; prev = None; mark = lambda h: "right" if h[0] else ("top 5" if h[1] else "miss ")
    try:
        for i, q in enumerate(Q, 1):
            snap, ws = os.path.join(tmp, os.path.basename(repo) or "repo"), os.path.join(tmp, f"ws{i % 2}")
            shutil.rmtree(snap, ignore_errors=True); shutil.rmtree(ws, ignore_errors=True); os.makedirs(snap)
            extract(repo, q["parent"], snap, os.path.join(tmp, "index"))
            t0 = time.time(); build([snap], ws, log=lambda *a: None, cache=cache); bt = time.time() - t0
            w = Workspace(ws)
            text = w.handle("ask", {"question": q["question"], "scope": "code"})
            files, h = scored(items_of(w, text), q)
            code_files = [(rel.split("/", 1)[1] if "/" in rel else rel, path) for _, rel, path in list_files(w.meta["roots"])
                          if os.path.splitext(rel)[1].lower() not in DOCS]
            g = grep_rank(code_files, q["question"])
            rows.append({"hash": q["hash"][:10], "author": q["author"], "question": q["question"], "gold": q["gold"], "first": files[:1],
                         "top5": files[:5], "md_first": h[0], "md_top5": h[1], "md_line_top5": h[2],
                         "grep_first": bool(g[:1]) and g[0] in q["gold"], "grep_top5": any(f in q["gold"] for f in g[:5]),
                         "tokens": len(text) // 4, "build_s": round(bt, 1)})
            r = rows[-1]; extra = ""
            if learn:
                c = w.carry(prev) if prev else {"entries": 0, "carried": 0}       # the memory, carried into this commit's map
                mtext = w.handle("ask", {"question": q["question"], "scope": "code"})
                mfiles, mh = scored(items_of(w, mtext), q)
                r.update({"mem_first": mh[0], "mem_top5": mh[1], "mem_line_top5": mh[2], "mem_lead": mfiles[:1],
                          "from_memory": mtext.startswith("(readout: the code a taught"), "lessons": c["entries"], "carried": c["carried"]})
                land = landing(repo, q); r["taught"] = None
                if land:                                                          # the fix lands, and is taught where it landed
                    f, ln, after = land
                    open(os.path.join(snap, f), "w", encoding="utf-8").write(after)
                    if not w.handle("teach", {"pairs": [{"question": q["question"], "at": f"{f}:{ln}"}]}).startswith("taught 0 "):
                        r["taught"] = f
                if prev:
                    shutil.rmtree(prev, ignore_errors=True)
                prev = ws; extra = f"  memory {mark(mh)}{' (taught pointer)' if r['from_memory'] else ''}"
            log(f"  {i:>3}/{len(Q)}  {mark(h)}  grep {mark((r['grep_first'], r['grep_top5']))}{extra}  {q['question'][:60]}")
            if not learn:
                shutil.rmtree(ws, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    k = len(rows); s = lambda key: sum(r[key] for r in rows)
    out = {"repo": repo, "fixes": k, "model_d": {"right_first": s("md_first"), "top5": s("md_top5"), "lines_top5": s("md_line_top5")},
           "grep": {"right_first": s("grep_first"), "top5": s("grep_top5")},
           "tokens_per_readout": round(sum(r["tokens"] for r in rows) / k), "rows": rows}
    if learn:
        led = [r for r in rows if r["from_memory"]]
        taught_by = {}                                                            # file -> the authors whose fixes taught it, so far
        shared = 0
        for r in rows:
            if r["from_memory"] and r["mem_first"] and (taught_by.get(r["mem_lead"][0], set()) - {r["author"]}):
                shared += 1                                                       # a right pointer a teammate's fix had taught
            if r["taught"]:
                taught_by.setdefault(r["taught"], set()).add(r["author"])
        out["memory"] = {"right_first": s("mem_first"), "top5": s("mem_top5"), "lines_top5": s("mem_line_top5"),
                         "pointer_led": len(led), "pointer_right": sum(r["mem_first"] for r in led), "from_teammate": shared,
                         "taught": sum(bool(r["taught"]) for r in rows), "authors": len({r["author"] for r in rows}),
                         "lessons_at_end": rows[-1]["lessons"], "carried_at_end": rows[-1]["carried"]}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="modeld prove", description=__doc__.split("\n\n")[0])
    ap.add_argument("repo", nargs="?", default="."); ap.add_argument("--fixes", type=int, default=50)
    ap.add_argument("--months", type=int, default=24); ap.add_argument("--cache"); ap.add_argument("--json")
    ap.add_argument("--learn", action="store_true", help="also replay the memory a team's agents build up, fix by fix")
    a = ap.parse_args(argv)
    if subprocess.run(["git", "-C", a.repo, "rev-parse"], capture_output=True).returncode:
        sys.exit(f"{a.repo} is not a git repository")
    print(f"Replaying up to {a.fixes} recent fix commits of {os.path.abspath(a.repo)}, each against the code right before it "
          f"(zero tokens; the first build embeds the whole repository)\n")
    r = prove(a.repo, a.fixes, a.months, a.cache, learn=a.learn)
    if not r["fixes"]:
        print("no fix commits with a changed source file in the window: try --months 60"); return
    k, m, g = r["fixes"], r["model_d"], r["grep"]
    pct = lambda x: f"{x:>3} ({x / k:.0%})"
    M = r.get("memory")
    print(f"\n{k} real fixes, true answers from git:\n")
    print(f"  {'':<30}{'Model D':>14}" + (f"{'with memory':>14}" if M else "") + f"{'grep-first':>14}")
    for key, label in (("right_first", "right file first"), ("top5", "right file in the top 5"), ("lines_top5", "changed line in the top 5")):
        print(f"  {label:<30}{pct(m[key]):>14}" + (f"{pct(M[key]):>14}" if M else "") + f"{(pct(g[key]) if key in g else '-'):>14}")
    half = round(98 / (k ** 0.5))                                     # the widest 95% half-width, at 50%
    print(f"\n  With {k} fixes these shares can move by up to about ±{half} points by chance; --fixes 200 gives a steadier read.")
    print(f"  {r['tokens_per_readout']} tokens per readout.", end=" ")
    if M:
        print(f"With memory: every fix was asked in a new session, as after the prompt cache expires: a fresh map of its own "
              f"commit, with the context graph carried over from disk. Then it was taught where it landed ({M['taught']} lessons, "
              f"from {M['authors']} authors). At the last fix, {M['carried_at_end']} of {M['lessons_at_end']} lessons were still "
              f"found in the code. A taught pointer led {M['pointer_led']} readouts and was right {M['pointer_right']} times, "
              f"{M['from_teammate']} of them from a lesson another author's fix had taught.")
    else:
        print("Model D is cold here, nothing taught. --learn replays the memory a team's agents build up, fix by fix, at "
              "zero tokens.")
    if a.json:
        json.dump(r, open(a.json, "w"), indent=1); print(f"  every question and answer: {a.json}")


if __name__ == "__main__":
    main()
