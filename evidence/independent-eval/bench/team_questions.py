"""The team-replay question set for Saleor (run with the modeld venv).
Model D's own fix selection (ocm.prove.questions: non-merge fix commits that change a non-test source file present at
their parent, gold = those files and the parent-side changed lines), then two neutral filters every tool shares:
- a repeated subject (a backport or cherry-pick of the same fix) is kept only the first time, so memory gets no free
  exact repeats;
- the 200 most recent that remain, oldest first."""
import json, sys
from ocm.prove import questions

repo, out = sys.argv[1], sys.argv[2]
Q = questions(repo, 400, 60)
seen, keep = set(), []
for q in Q:
    k = " ".join(q["question"].lower().split())
    if k in seen:
        continue
    seen.add(k); keep.append(q)
keep = keep[-200:]
json.dump(keep, open(out, "w"), indent=1)
authors = {q["author"] for q in keep}
print(f"{len(Q)} fix commits found, {len(Q) - len(seen)} repeats dropped, {len(keep)} kept, {len(authors)} authors")
print("first:", keep[0]["hash"][:10], keep[0]["question"][:70]); print("last: ", keep[-1]["hash"][:10], keep[-1]["question"][:70])
