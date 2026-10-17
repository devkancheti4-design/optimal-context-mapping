"""PROTOCOL_COVERAGE evaluation (offline): teach every coverage question once, then compare cold and covered readouts on the
288 real Django 2022 questions.

    python coverage_eval.py ws/base ws/cover coverage_questions.jsonl window_2022.json keep.json coverage_eval.json"""
import json, math, os, re, shutil, sys, time
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
from ocm.cmlm_vector.memory import Memory  # noqa: E402
from ocm.server import Workspace  # noqa: E402
from ocm.loop import TAUGHT  # noqa: E402

base, cover, qfile, window, keepf, out = sys.argv[1:7]
if not os.path.exists(os.path.join(cover, "memory", "manifest.json")):
    shutil.copytree(base, cover)
    m = Memory(os.path.join(cover, "memory"))
    pairs = [(r["question"], r["unit"]) for r in map(json.loads, open(qfile))]
    t0 = time.time()
    for s in range(0, len(pairs), 2000):                        # the product's teach_at, in chunks, one save at the end
        m.teach_at(pairs[s:s + 2000]); print(f"  taught {min(s + 2000, len(pairs)):,}/{len(pairs):,} ({time.time() - t0:.0f}s)", flush=True)
    m.save()
    json.dump({"taught": len(pairs), "law": m.law.state()}, open(os.path.join(cover, "coverage.json"), "w"), indent=1, default=str)
keep = set(json.load(open(keepf)))
items = [x for x in json.load(open(window)) if x["k"] in keep]
CITE = re.compile(r"^\s*\d+\.\s*\[([^\]]+?):\d+\]", re.M)
norm = lambda p: p.split("/", 1)[1] if p.startswith("django/django/") else p
hit = lambda files, gold: any(norm(f) == g or norm(f).endswith("/" + g) for f in files for g in gold)
res = {}
for name, ws in (("cold", base), ("covered", cover)):
    w = Workspace(ws); rows = []
    for x in items:
        q = f"Where is the code behind this change: {x['raw']}"
        ro = w.routed(q, True, "code")
        files = list(dict.fromkeys(CITE.findall(ro)))
        _, obs = w.lanes.measure(q, allow=w.code)
        rows.append({"k": x["k"], "first": files[0] if files else None, "top5": files[:5], "taught": ro.startswith(TAUGHT),
                     "from_cue": obs.get("from_cue"), "m": obs.get("over_own"), "cert": obs.get("cert_lead"),
                     "right1": hit(files[:1], x["gold"]), "right5": hit(files[:5], x["gold"])})
    res[name] = {"rows": rows, "law": w.mem.law.state(), "cues": len(w.mem.cue_texts)}
    print(f"{name}: cues {len(w.mem.cue_texts):,} | right first {sum(r['right1'] for r in rows)} | top 5 {sum(r['right5'] for r in rows)} | "
          f"taught-led {sum(r['taught'] for r in rows)} of {len(rows)} | law {w.mem.law.state().get('law')} active {w.mem.law.state().get('active')}", flush=True)
json.dump(res, open(out, "w"), default=str)


def wilson(k, n, z=1.96):
    if not n: return (float("nan"),) * 3
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


cold, cov = {r["k"]: r for r in res["cold"]["rows"]}, {r["k"]: r for r in res["covered"]["rows"]}
led = [r for r in cov.values() if r["taught"]]
print(f"\ntaught-led readouts: {len(led)}; right first {sum(r['right1'] for r in led)}; on the same questions cold right first {sum(cold[r['k']]['right1'] for r in led)}")
print(f"{'margin m (bits)':<16}{'n':>4}{'right first':>13}{'95% CI':>16}{'cold right first':>18}")
for lo, hi in ((-999, 0), (0, 20), (20, 37), (37, 50), (50, 74), (74, 999)):
    sel = [r for r in led if r["m"] is not None and lo <= r["m"] < hi]
    p, a, b = wilson(sum(r["right1"] for r in sel), len(sel))
    print(f"{(str(lo) if lo > -999 else '<0'):>5} to {(str(hi) if hi < 999 else '+'):<6}{len(sel):>4}{sum(r['right1'] for r in sel):>8} ({p:.0%})   [{a:.0%}, {b:.0%}]{sum(cold[r['k']]['right1'] for r in sel):>12}")
hi37 = [r for r in led if r["m"] is not None and r["m"] >= 37]
c5, v5 = sum(r["right5"] for r in cold.values()), sum(r["right5"] for r in cov.values())
print("\npredictions")
print(f"V1 ranking holds: covered top-5 {v5} >= cold {c5}  {'held' if v5 >= c5 else 'FAILED'}")
p37 = sum(r["right1"] for r in hi37) / len(hi37) if hi37 else float("nan")
print(f"V2 taught-led with m >= 37: right first {sum(r['right1'] for r in hi37)}/{len(hi37)} ({p37:.0%}) >= 60%  {'held' if hi37 and p37 >= 0.6 else 'FAILED'}")
print(f"V3 coverage used: taught-led {len(led)}/{len(cov)} ({len(led) / len(cov):.0%}) >= 30%  {'held' if len(led) >= 0.3 * len(cov) else 'FAILED'}")
print(f"right first overall: cold {sum(r['right1'] for r in cold.values())}, covered {sum(r['right1'] for r in cov.values())} of {len(cov)}")
