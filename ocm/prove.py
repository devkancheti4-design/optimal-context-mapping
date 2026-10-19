"""modeld prove: check Model D on your own repository, against your own bug fixes, at zero tokens.

  modeld prove [repo] [--fixes 50] [--months 24] [--json FILE]

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
evidence/new-codebase-hono, where Model D put the right file first 26% of the time against grep's 16%."""
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
    log = git(repo, "log", "--no-merges", f"--since={since}", "--format=%H%x09%P%x09%s")
    out = []
    for line in log.strip().split("\n") if log.strip() else []:
        h, parents, s = line.split("\t", 2)
        if not FIX.search(s) or len(parents.split()) != 1:
            continue
        files = [f for f in git(repo, "diff", "--no-renames", "--name-only", parents, h).split("\n")
                 if f.endswith(CODE) and not TEST.search(f)]
        if not files:
            continue
        at_parent = set(git(repo, "ls-tree", "-r", "--name-only", parents).split("\n"))
        gold, lines = [f for f in files if f in at_parent], {}
        for f in gold:
            rng = []
            for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+", git(repo, "diff", "-U0", "--no-renames", parents, h, "--", f), re.M):
                a_, b = int(m.group(1)), int(m.group(2) or 1)
                rng.append((a_, a_ + b - 1) if b else (a_, a_ + 1))
            lines[f] = rng
        if gold:
            plain = re.sub(r"\s*\(#\d+\)", "", s).strip()
            bare = re.sub(r"^\s*fix(es|ed)?(\([^)]*\))?!?\s*:\s*", "", plain, flags=re.I).strip() or plain
            out.append({"hash": h, "parent": parents, "question": bare, "gold": gold, "lines": lines})
        if len(out) >= n:
            break
    return out[::-1]


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


def prove(repo, n=30, months=24, cache=None, log=print):
    from .build import build
    from .server import Workspace
    from .units import files as list_files, DOCS
    repo = os.path.abspath(repo)
    Q = questions(repo, n, months)
    if not Q:
        return {"repo": repo, "fixes": 0}
    cache = os.path.abspath(cache or os.environ.get("MODELD_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "modeld", "embed.sqlite"))
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="modeld-prove-"); rows = []
    try:
        for i, q in enumerate(Q, 1):
            snap, ws = os.path.join(tmp, os.path.basename(repo) or "repo"), os.path.join(tmp, "ws")
            shutil.rmtree(snap, ignore_errors=True); shutil.rmtree(ws, ignore_errors=True); os.makedirs(snap)
            subprocess.run(f"git -C '{repo}' archive {q['parent']} | tar -x -C '{snap}'", shell=True, check=True)
            t0 = time.time(); build([snap], ws, log=lambda *a: None, cache=cache); bt = time.time() - t0
            w = Workspace(ws)
            text = w.handle("ask", {"question": q["question"], "scope": "code"})
            items = []
            for p, ln in CITE.findall(text):
                pl = w.place(f"{p}:{ln}")
                span = next(((f, l) for f, l, j in w.spans.get(pl[1], []) if j == pl[0]), (int(ln), int(ln))) if pl else (int(ln), int(ln))
                items.append((p.split("/", 1)[1] if "/" in p else p, span[0], span[1]))
            files = list(dict.fromkeys(f for f, _, _ in items))
            code_files = [(rel.split("/", 1)[1] if "/" in rel else rel, path) for _, rel, path in list_files(w.meta["roots"])
                          if os.path.splitext(rel)[1].lower() not in DOCS]
            g = grep_rank(code_files, q["question"])
            line_hit = any(f == gf and a <= hi and b >= lo for f, a, b in items[:5] for gf, rngs in q["lines"].items() for lo, hi in rngs)
            rows.append({"hash": q["hash"][:10], "question": q["question"], "gold": q["gold"], "first": files[:1], "top5": files[:5],
                         "md_first": bool(files[:1]) and files[0] in q["gold"], "md_top5": any(f in q["gold"] for f in files[:5]),
                         "md_line_top5": line_hit, "grep_first": bool(g[:1]) and g[0] in q["gold"],
                         "grep_top5": any(f in q["gold"] for f in g[:5]), "tokens": len(text) // 4, "build_s": round(bt, 1)})
            r = rows[-1]
            log(f"  {i:>3}/{len(Q)}  {'right' if r['md_first'] else ('top 5' if r['md_top5'] else 'miss '):<5}  "
                f"grep {'right' if r['grep_first'] else ('top 5' if r['grep_top5'] else 'miss '):<5}  {q['question'][:70]}")
            shutil.rmtree(ws, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    k = len(rows); s = lambda key: sum(r[key] for r in rows)
    return {"repo": repo, "fixes": k, "model_d": {"right_first": s("md_first"), "top5": s("md_top5"), "lines_top5": s("md_line_top5")},
            "grep": {"right_first": s("grep_first"), "top5": s("grep_top5")},
            "tokens_per_readout": round(sum(r["tokens"] for r in rows) / k), "rows": rows}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="modeld prove", description=__doc__.split("\n\n")[0])
    ap.add_argument("repo", nargs="?", default="."); ap.add_argument("--fixes", type=int, default=50)
    ap.add_argument("--months", type=int, default=24); ap.add_argument("--cache"); ap.add_argument("--json")
    a = ap.parse_args(argv)
    if subprocess.run(["git", "-C", a.repo, "rev-parse"], capture_output=True).returncode:
        sys.exit(f"{a.repo} is not a git repository")
    print(f"Replaying up to {a.fixes} recent fix commits of {os.path.abspath(a.repo)}, each against the code right before it "
          f"(zero tokens; the first build embeds the whole repository)\n")
    r = prove(a.repo, a.fixes, a.months, a.cache)
    if not r["fixes"]:
        print("no fix commits with a changed source file in the window: try --months 60"); return
    k, m, g = r["fixes"], r["model_d"], r["grep"]
    pct = lambda x: f"{x:>3} ({x / k:.0%})"
    print(f"\n{k} real fixes, true answers from git:\n")
    print(f"  {'':<30}{'Model D':>14}{'grep-first':>14}")
    print(f"  {'right file first':<30}{pct(m['right_first']):>14}{pct(g['right_first']):>14}")
    print(f"  {'right file in the top 5':<30}{pct(m['top5']):>14}{pct(g['top5']):>14}")
    print(f"  {'changed line in the top 5':<30}{pct(m['lines_top5']):>14}{'-':>14}")
    half = round(98 / (k ** 0.5))                                     # the widest 95% half-width, at 50%
    print(f"\n  With {k} fixes these shares can move by up to about ±{half} points by chance; --fixes 200 gives a steadier read.")
    print(f"  {r['tokens_per_readout']} tokens per readout. Model D is cold here: teaching it the codebase once "
          f"(modeld cover) raised right-file-first from 111 to 142-149 of 288 on Django.")
    if a.json:
        json.dump(r, open(a.json, "w"), indent=1); print(f"  every question and answer: {a.json}")


if __name__ == "__main__":
    main()
