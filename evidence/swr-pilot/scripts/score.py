"""Score the pilot (PROTOCOL_SWR_PILOT.md): the official judge's numbers per arm, cost per arm, and the paired A-B tests.

    python score.py judged/judged_A.jsonl reviews_A.jsonl [judged/judged_B.jsonl reviews_B.jsonl]

The headline metrics are the judge's own (evaluation_struct.analyze_result): issue-level F1 (f1_point), functional
recall (change_by_F), predicted issues per clean PR, and PR-level F1. The bootstrap rebuilds f1_point per resample from
each PR's own contribution, counted exactly as the judge counts it."""
import json, random, sys
from math import comb

SEED, N_BOOT = 20261016, 10_000


def load(judged, reviews):
    d = json.load(open(judged))
    rv = {json.loads(l)["instance_id"]: json.loads(l) for l in open(reviews)}
    per = {}
    for x in d["details"]:
        preds = {p["id"] for p in x["pred_points"]}
        hit = {g["hit_by"] for g in x.get("gt_points", []) if g.get("hit_by") in preds}
        if x["change_introduced"]:
            if not x["pred_points"] and not x.get("gt_points"):
                continue
            per[x["instance_id"]] = (len(hit), len(preds - hit), len(x.get("gt_points", [])) - len(hit))
        else:
            per[x["instance_id"]] = (0, len(x["pred_points"]), 0)
    return d["analysis_results"], rv, per, d["details"]


def f1(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0; r = tp / (tp + fn) if tp + fn else 0
    return 2 * p * r / (p + r) if p + r else 0


def summary(name, ar, rv):
    o, c, F = ar["overall"], ar["clean"], ar["change_by_F"]
    usd = sum(x["usd"] for x in rv.values()); n = len(rv)
    print(f"\n== arm {name}: {ar.get('valid', '?')} valid of {ar.get('submit', '?')} submitted, {ar.get('error', 0)} judge errors")
    print(f"issue-level   P {o['precision_point']:.4f}  R {o['recall_point']:.4f}  F1 {o['f1_point']:.4f}   "
          f"(tp {o['tp_point']}, fp {o['fp_point']}, fn {o['fn_point']})")
    print(f"functional    P {F['precision']:.4f}  R {F['recall']:.4f}  F1 {F['f1']:.4f}   (tp {F['tp']}, fp {F['fp']}, fn {F['fn']})")
    print(f"clean PRs     {c['pred_points_avg']:.2f} predicted issues per PR, {c['identified_as_good']} of {c['count']} called good")
    print(f"PR-level      P {o['precision']:.4f}  R {o['recall']:.4f}  F1 {o['f1']:.4f}  accuracy {o['accuracy']:.4f}")
    print(f"cost          ${usd:.3f} total, ${usd / n:.4f} per PR; mean in {sum(x['input_tokens'] for x in rv.values()) / n:,.0f}, "
          f"out {sum(x['output_tokens'] for x in rv.values()) / n:,.0f} tokens")
    return {"f1": o["f1_point"], "fR": F["recall"], "clean": c["pred_points_avg"], "usd_pr": usd / n}


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n)


def main():
    a = sys.argv[1:]
    arA, rvA, perA, detA = load(a[0], a[1])
    sA = summary("A", arA, rvA)
    if len(a) < 4:
        return
    arB, rvB, perB, detB = load(a[2], a[3])
    sB = summary("B", arB, rvB)
    gA = {(x["instance_id"], g["description"]): bool(g.get("hit")) for x in detA for g in x.get("gt_points", [])}
    gB = {(x["instance_id"], g["description"]): bool(g.get("hit")) for x in detB for g in x.get("gt_points", [])}
    common = gA.keys() & gB.keys()
    b = sum(1 for k in common if gB[k] and not gA[k]); c = sum(1 for k in common if gA[k] and not gB[k])
    print(f"\n== paired, per ground-truth issue ({len(common)} matched of {len(gA)} / {len(gB)}): "
          f"B hits and A misses {b}, A hits and B misses {c}, exact McNemar p = {mcnemar(b, c):.4g}")
    ids = sorted(perA.keys() & perB.keys()); rng = random.Random(SEED); diffs = []
    for _ in range(N_BOOT):
        s = [rng.choice(ids) for _ in ids]
        tA = [sum(perA[i][k] for i in s) for k in range(3)]; tB = [sum(perB[i][k] for i in s) for k in range(3)]
        diffs.append(f1(*tB) - f1(*tA))
    diffs.sort()
    print(f"F1 difference B - A: {sB['f1'] - sA['f1']:+.4f}, 95% bootstrap interval "
          f"[{diffs[int(0.025 * N_BOOT)]:+.4f}, {diffs[int(0.975 * N_BOOT)]:+.4f}] over {len(ids)} PRs")
    print("\n== predictions")
    print(f"P1 F1(B) >= F1(A):                      {sB['f1']:.4f} vs {sA['f1']:.4f}  {'held' if sB['f1'] >= sA['f1'] else 'FAILED'}")
    print(f"P2 functional recall B >= A:            {sB['fR']:.4f} vs {sA['fR']:.4f}  {'held' if sB['fR'] >= sA['fR'] else 'FAILED'}")
    print(f"P3 clean-PR issues B <= 1.2 x A:        {sB['clean']:.2f} vs {1.2 * sA['clean']:.2f}  {'held' if sB['clean'] <= 1.2 * sA['clean'] else 'FAILED'}")
    print(f"P4 cost per PR B <= 1.3 x A:            ${sB['usd_pr']:.4f} vs ${1.3 * sA['usd_pr']:.4f}  {'held' if sB['usd_pr'] <= 1.3 * sA['usd_pr'] else 'FAILED'}")


if __name__ == "__main__" and sys.argv[1:2] != ["--interim"]:
    main()


def interim(judged_a, reviews_a, judged_b, reviews_b):
    """A and B on the PRs both have, counted as the judge counts them (issue-level tp/fp/fn summed per PR)."""
    _, rvA, perA, detA = load(judged_a, reviews_a)
    _, rvB, perB, detB = load(judged_b, reviews_b)
    ids = sorted(perA.keys() & perB.keys())
    clean = {x["instance_id"] for x in detA if not x["change_introduced"]}
    print(f"interim, {len(ids)} PRs in both arms ({len([i for i in ids if i not in clean])} with issues, "
          f"{len([i for i in ids if i in clean])} clean)")
    out = {}
    for name, per, rv in (("A", perA, rvA), ("B", perB, rvB)):
        t = [sum(per[i][k] for i in ids) for k in range(3)]
        p = t[0] / (t[0] + t[1]) if t[0] + t[1] else 0; r = t[0] / (t[0] + t[2]) if t[0] + t[2] else 0
        cl = [per[i][1] for i in ids if i in clean]
        usd = sum(rv[i]["usd"] for i in ids)
        out[name] = f1(*t)
        print(f"arm {name}: issue-level P {p:.4f} R {r:.4f} F1 {f1(*t):.4f} (tp {t[0]}, fp {t[1]}, fn {t[2]}) | "
              f"{sum(cl) / max(1, len(cl)):.2f} comments per clean PR | ${usd / len(ids):.4f} per PR")
    rng = random.Random(SEED); diffs = []
    for _ in range(N_BOOT):
        s = [rng.choice(ids) for _ in ids]
        diffs.append(f1(*[sum(perB[i][k] for i in s) for k in range(3)]) - f1(*[sum(perA[i][k] for i in s) for k in range(3)]))
    diffs.sort()
    print(f"F1 B - A {out['B'] - out['A']:+.4f}, 95% bootstrap [{diffs[int(0.025 * N_BOOT)]:+.4f}, {diffs[int(0.975 * N_BOOT)]:+.4f}]")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--interim":
    interim(*sys.argv[2:6])
