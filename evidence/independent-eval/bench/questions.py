"""Pick real bug-fix commits from a repo and turn each into a localization question.

A question is the fix commit's subject (conventional-commit prefix, scope and PR number removed).
The gold answer is the set of non-test code files the fix changed that already existed at its parent.
Nothing here is borrowed from any of the tools under test.
"""
import json, re, subprocess, sys

FIX = re.compile(r"^(fix(es|ed)?\b|bug ?fix|hotfix)|\bfix(es|ed)? #\d+", re.I)
CODE = (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".jsx")
TEST = re.compile(r"(^|/)(tests?|__tests__|testing|spec|specs|docs?|examples?|benchmarks?|fixtures?|test-d)/"
                  r"|(^|/)test_[^/]*\.py$|_test\.py$|\.(test|spec|tst|bench)\.[a-z]+$|(^|/)conftest\.py$|\.d\.ts$", re.I)
TRIVIAL = re.compile(r"\b(typo|typos|lint|linting|docstring|docs?|changelog|readme|test|tests|ci|format|formatting|mypy|types? annotation|spelling)\b", re.I)


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout


def clean(subject):
    s = re.sub(r"\s*\(#\d+\)", "", subject).strip()
    s = re.sub(r"^\s*(fix(es|ed)?|bug ?fix|hotfix)(\([^)]*\))?!?\s*:\s*", "", s, flags=re.I).strip()
    s = re.sub(r"^\s*\[[^\]]*\]\s*", "", s)
    return s or subject


def pick(repo, n, months=36):
    log = git(repo, "log", "--no-merges", f"--since={months} months ago", "--format=%H%x09%P%x09%s")
    out, seen = [], set()
    for line in log.strip().split("\n"):
        h, parents, s = line.split("\t", 2)
        if len(parents.split()) != 1 or not FIX.search(s) or TRIVIAL.search(s):
            continue
        q = clean(s)
        key = q.lower()
        if key in seen or len(q.split()) < 3:
            continue
        files = [f for f in git(repo, "diff", "--no-renames", "--name-only", parents, h).split("\n")
                 if f.endswith(CODE) and not TEST.search(f)]
        if not files or len(files) > 6:
            continue
        at_parent = set(git(repo, "ls-tree", "-r", "--name-only", parents).split("\n"))
        gold = [f for f in files if f in at_parent]
        if not gold:
            continue
        seen.add(key)
        out.append({"hash": h, "parent": parents, "subject": s, "question": q, "gold": gold})
        if len(out) >= n:
            break
    return out[::-1]


if __name__ == "__main__":
    repo, n, dest = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    qs = pick(repo, n)
    json.dump(qs, open(dest, "w"), indent=1)
    print(f"{len(qs)} questions from {repo}")
    for q in qs[:5]:
        print(" ", q["question"], "->", q["gold"])
