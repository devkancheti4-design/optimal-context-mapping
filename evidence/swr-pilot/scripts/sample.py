"""Draw the pilot set from SWR-Bench before any review is run: 50 PRs that introduced reviewer-confirmed issues and 50
clean PRs, allocated across repositories in proportion to the full benchmark (largest remainder), then drawn uniformly
within each repository with a fixed seed. Writes the instance ids, in draw order, and a sha256 of the list."""
import hashlib, json, random, sys
from collections import Counter
src, out, seed, per_label = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
rows = [json.loads(l) for l in open(src)]
pick = []
for label in (True, False):
    pool = [r for r in rows if r["change_introduced"] is label]
    cnt = Counter(r["repo"] for r in pool)
    quota = {rp: per_label * n / len(pool) for rp, n in cnt.items()}
    alloc = {rp: int(q) for rp, q in quota.items()}
    for rp in sorted(quota, key=lambda rp: (-(quota[rp] - alloc[rp]), rp))[:per_label - sum(alloc.values())]:
        alloc[rp] += 1
    rng = random.Random(f"{seed}-{label}")
    for rp in sorted(alloc):
        ids = sorted(r["instance_id"] for r in pool if r["repo"] == rp)
        pick += [(rp, label, i) for i in rng.sample(ids, alloc[rp])]
ids = [i for _, _, i in pick]
json.dump({"seed": seed, "per_label": per_label, "source_sha256": hashlib.sha256(open(src, "rb").read()).hexdigest(),
           "instances": [{"repo": rp, "change_introduced": lb, "instance_id": i} for rp, lb, i in pick],
           "ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest()}, open(out, "w"), indent=1)
c = Counter((rp, lb) for rp, lb, _ in pick)
for rp in sorted({rp for rp, _, _ in pick}):
    print(f"{rp:<28} change {c[(rp, True)]:>3}  clean {c[(rp, False)]:>3}")
print("total", len(pick), "| ids sha256", hashlib.sha256("\n".join(ids).encode()).hexdigest()[:16])
