"""Real fix commits of a repository in one year, against the code as it stood at the start of that year: subject,
and the non-test .py files each changed that exist at the snapshot.
    python3 fixes.py <name> <since YYYY-MM-DD> <until YYYY-MM-DD> -> questions/<name>_<year>.json"""
import json, os, re, subprocess, sys
FIX = re.compile(r"^(fix(es|ed)?\b|bug ?fix|hotfix)|\bfix(es|ed)? #\d+", re.I)        # oss-claude/history.py
SKIP = re.compile(r"(^|/)(tests?|__tests__|spec|specs|docs?|examples?|fixtures?)/|(^|/)test_[^/]*\.py$|(^|/)conftest\.py$")
name, since, until = sys.argv[1], sys.argv[2], sys.argv[3]; repo = f"hist/{name}"
git = lambda *a: subprocess.check_output(["git", "-C", repo, *a], text=True)
snap = git("rev-list", "-1", f"--before={since}", "HEAD").strip()
at_snap = set(git("ls-tree", "-r", "--name-only", snap).split("\n"))
log = git("log", "--no-merges", "--reverse", "--no-renames", f"--since={since}", f"--until={until}", "--format=@@%H%x09%ad%x09%s", "--date=short", "--name-only")
out, cur = [], None
for line in log.split("\n"):
    if line.startswith("@@"):
        h, d, s = line[2:].split("\t", 2); cur = {"id": h[:10], "date": d, "subject": s, "files": []}
        if FIX.search(s): out.append(cur)
        else: cur = None
    elif line.strip() and cur is not None and line.endswith(".py") and not SKIP.search(line):
        cur["files"].append(line.strip())
qs = []
for c in out:
    gold = [f for f in c["files"] if f in at_snap]
    if gold:
        qs.append({"id": c["id"], "date": c["date"], "queries": {"q": f"Where is the code behind this change: {c['subject']}", "raw": c["subject"]}, "gold": gold})
os.makedirs("questions", exist_ok=True)
json.dump({"repo": name, "snapshot": snap, "since": since, "until": until, "questions": qs}, open(f"questions/{name}_{since[:4]}.json", "w"), indent=0)
print(f"{name}: snapshot {snap[:10]} (before {since}); fix commits {len(out)}; with a changed source file at the snapshot {len(qs)}")
