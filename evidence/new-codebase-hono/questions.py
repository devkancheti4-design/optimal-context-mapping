"""Real fix commits of honojs/hono since 2025-01-01, each asked against its parent commit (the code right before the
fix). True answer: the non-test source files the fix changed, and the exact parent-side line ranges of each change.
    python3 questions.py -> questions.json"""
import json, re, subprocess
FIX = re.compile(r"^(fix(es|ed)?\b|bug ?fix|hotfix)|\bfix(es|ed)? #\d+", re.I)        # oss-claude/history.py
CODE = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
TEST = re.compile(r"(^|/)(tests?|__tests__|test-d|benchmarks?|docs?|examples?)/|\.test\.(t|j)sx?$|\.spec\.(t|j)sx?$|\.d\.ts$")
git = lambda *a: subprocess.check_output(["git", "-C", "hono", *a], text=True)
log = git("log", "--no-merges", "--reverse", "--since=2025-01-01", "--format=%H%x09%P%x09%ad%x09%s", "--date=short")
qs = []
for line in log.strip().split("\n"):
    h, parents, d, s = line.split("\t", 3)
    if not FIX.search(s) or len(parents.split()) != 1:
        continue
    files = [f for f in git("diff", "--no-renames", "--name-only", parents, h).split("\n") if f.endswith(CODE) and not TEST.search(f)]
    if not files:
        continue
    at_parent = set(git("ls-tree", "-r", "--name-only", parents).split("\n"))
    gold, lines = [], {}
    for f in files:
        if f not in at_parent:
            continue
        rng = []
        for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+", git("diff", "-U0", "--no-renames", parents, h, "--", f), re.M):
            a, b = int(m.group(1)), int(m.group(2) or 1)
            rng.append([a, a + b - 1] if b else [a, a + 1])                  # a pure insertion: the lines around it
        gold.append(f); lines[f] = rng
    if not gold:
        continue
    plain = re.sub(r"\s*\(#\d+\)", "", s).strip()
    bare = re.sub(r"^\s*fix(es|ed)?(\([^)]*\))?!?\s*:\s*", "", plain, flags=re.I).strip()
    qs.append({"id": h[:10], "parent": parents, "date": d, "subject": s,
               "queries": {"subject": plain, "bare": bare}, "gold": gold, "gold_lines": lines})
json.dump(qs, open("questions.json", "w"), indent=0)
print(f"{len(qs)} questions; gold files per fix: mean {sum(len(q['gold']) for q in qs)/len(qs):.2f}; example: {qs[-1]['queries']}")
