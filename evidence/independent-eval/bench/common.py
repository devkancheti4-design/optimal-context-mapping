"""Shared by every runner: snapshots of a repo at a commit, and how a ranked answer is scored."""
import os, re, shutil, subprocess

CODE = (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".jsx")
TEST = re.compile(r"(^|/)(tests?|__tests__|testing|spec|specs|docs?|examples?|benchmarks?|fixtures?|test-d)/"
                  r"|(^|/)test_[^/]*\.py$|_test\.py$|\.(test|spec|tst|bench)\.[a-z]+$|(^|/)conftest\.py$|\.d\.ts$", re.I)


def snapshot(repo, commit, dest, keep=()):
    """Make dest hold exactly the tree of `commit`, leaving the names in `keep` (tool caches) alone."""
    os.makedirs(dest, exist_ok=True)
    for name in os.listdir(dest):
        if name in keep:
            continue
        p = os.path.join(dest, name)
        shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
    arc = subprocess.run(["git", "-C", repo, "archive", commit], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", dest], input=arc, check=True)


def ranked_code_files(paths):
    """Dedupe a tool's cited paths in order, keeping only code files (the same filter for every tool)."""
    out = []
    for p in paths:
        p = p.strip().lstrip("./")
        if p and p.endswith(CODE) and p not in out:
            out.append(p)
    return out


def score(files, gold):
    g = set(gold)
    nt = [f for f in files if not TEST.search(f)]
    rank = next((i for i, f in enumerate(files, 1) if f in g), None)
    return {"top1": bool(files[:1]) and files[0] in g, "top5": any(f in g for f in files[:5]),
            "top1_notests": bool(nt[:1]) and nt[0] in g, "top5_notests": any(f in g for f in nt[:5]),
            "rr": 1 / rank if rank else 0.0, "first_is_test": bool(files[:1]) and bool(TEST.search(files[0]))}
