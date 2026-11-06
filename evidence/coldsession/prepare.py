"""One repository's pins, snapshots and sampled facts. GitHub and git only, no model calls.

    <modeld python> -I prepare.py psf/requests

Writes data/<repo>/pins.json, data/<repo>/rates.json and data/<repo>/pool.jsonl (the sampled facts in order, more than a session needs, so that a fact whose wordings fail
can be replaced), and leaves the snapshots in <work>/<repo>/snap/{T0,T1,T2,mate}/repo. The folder is always called repo: Model D's paths start with the folder's name."""
import json, os, random, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import facts as F  # noqa: E402
from ocm.units import wanted  # noqa: E402

slug = sys.argv[1]
repo = slug.split("/")[1]
os.makedirs(C.data(repo), exist_ok=True)
pins = {t: dict(zip(("sha", "committed"), C.pin(slug, d)), date=d) for t, d in zip(("T0", "T1", "T2"), C.DATES)}
json.dump({"repo": slug, **pins}, open(C.data(repo, "pins.json"), "w"), indent=1)
seen = {}
for t in pins:
    snap = C.work(repo, "snap", t, "repo")
    C.fetch(slug, pins[t]["sha"], snap)
    seen[t] = F.snapshot_facts(snap)
    for d, _, files in os.walk(snap, topdown=False):       # only what Model D and the agent's tools can see, to save disk
        for f in files:
            if not wanted(os.path.relpath(os.path.join(d, f), snap)):
                os.remove(os.path.join(d, f))
        if not os.listdir(d):
            os.rmdir(d)
shutil.rmtree(C.work(repo, "snap", "mate"), ignore_errors=True)
shutil.copytree(C.work(repo, "snap", "T0", "repo"), C.work(repo, "snap", "mate", "repo"))

at_t1 = {(r["kind"], r["subject"], r["param"]): r for r in F.compare(seen["T0"], seen["T1"])}
rows = F.compare(seen["T0"], seen["T2"])
json.dump(F.rates(rows), open(C.data(repo, "rates.json"), "w"), indent=1)
keep = []
for r in rows:
    k = (r["kind"], r["subject"], r["param"])
    if F.askable(r) and r["status"] != "gone" and at_t1[k]["status"] != "gone":   # a subject that has disappeared has no checkable answer
        keep.append({**r, "id": "|".join(str(x) for x in k), "t1_status": at_t1[k]["status"], "t1_path": at_t1[k]["new_path"], "t1_line": at_t1[k]["new_line"]})
keep.sort(key=lambda r: r["id"])
rng = random.Random(0)
rng.shuffle(keep)                                           # a fixed order: the pool is simply the order facts are tried in
def turns(rows):
    """Rows in the same order within each kind, taking the kinds in turn, so one common kind can't crowd out the others."""
    by = {}
    for r in rows:
        by.setdefault(r["kind"], []).append(r)
    return [by[k][i] for i in range(max(map(len, by.values()), default=0)) for k in sorted(by) if i < len(by[k])]


pool = turns([r for r in keep if r["status"] == "changed"]) + turns([r for r in keep if r["status"] == "moved"])
same = {}
for r in keep:
    if r["status"] == "same":
        same.setdefault(r["kind"], []).append(r)
for i in range(60):                                         # same facts in equal shares of each kind, however common each kind is
    for k in sorted(same):
        if i < len(same[k]):
            pool.append(same[k][i])
have = {r["id"] for r in pool}
defaults = [r["subject"] for r in keep if r["kind"] == "default"]
pool += [r for r in keep if r["kind"] == "default" and r["status"] == "same" and r["id"] not in have and defaults.count(r["subject"]) > 1][:40]   # another parameter of the same function
with open(C.data(repo, "pool.jsonl"), "w") as f:
    for r in pool:
        f.write(json.dumps(r) + "\n")
print(slug, {t: pins[t]["sha"][:9] for t in pins}, "facts", len(seen["T0"]), "pool", len(pool), "changed", sum(r["status"] == "changed" for r in pool), "moved", sum(r["status"] == "moved" for r in pool), flush=True)
