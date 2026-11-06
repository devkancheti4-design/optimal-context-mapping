"""landing.py's results over the repositories, plus how many lessons each rebuild kept and what an agent's own lessons did. No model calls.

    <modeld python> -I diagnostics/landing_report.py reflex scikit-learn sphinx"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C
from ocm.life import Life

repos = sys.argv[1:]
mean = lambda v: sum(v) / len(v) if v else 0
rows = [dict(r, repo=x) for x in repos for r in C.rows(C.results(x, "landing.jsonl"))]


def show(name, v):
    if v:
        print(f"{name:<44} n={len(v):<4} lesson led {100 * mean([r['lesson_led'] for r in v]):5.1f}%  fact in readout {100 * mean([r['fact_in_readout'] for r in v]):5.1f}%  tokens {mean([r['tokens'] for r in v]):5.0f}")


print("## perfect lessons, the first wording taught; plain wordings for taught, sibling and unrelated, template wordings for named")
taught = lambda r: r["role"] == "taught"
show("next day, cold map, taught facts", [r for r in rows if r["session"] == 2 and r["map"] == "cold" and taught(r)])
show("next day, with lessons, taught facts", [r for r in rows if r["session"] == 2 and r["map"] == "taught" and taught(r)])
show("next day, with lessons, named control", [r for r in rows if r["session"] == 2 and r["map"] == "taught" and r["role"] == "named"])
show("next day, cold map, named control", [r for r in rows if r["session"] == 2 and r["map"] == "cold" and r["role"] == "named"])
show("next day, with lessons, new questions", [r for r in rows if r["session"] == 2 and r["map"] == "taught" and r["role"] in ("sibling", "unrelated")])
show("next day, cold map, new questions", [r for r in rows if r["session"] == 2 and r["map"] == "cold" and r["role"] in ("sibling", "unrelated")])
show("teammate, with lessons", [r for r in rows if r["session"] == 3 and taught(r)])
for status in ("same", "moved", "changed"):
    show(f"a year later, with lessons, {status}", [r for r in rows if r["session"] == 4 and r["map"] == "taught" and r["status"] == status and taught(r)])
    show(f"a year later, cold map, {status}", [r for r in rows if r["session"] == 4 and r["map"] == "cold" and r["status"] == status and taught(r)])
show("with 200 more lessons", [r for r in rows if r["session"] == 5 and taught(r)])
for x in repos:
    v = [r for r in rows if r["repo"] == x]
    print(x, "next day: lesson led %.0f%%, fact in readout %.0f%%; cold fact in readout %.0f%%; extra lessons: %s" % (100 * mean([r["lesson_led"] for r in v if r["session"] == 2 and r["map"] == "taught" and taught(r)]), 100 * mean([r["fact_in_readout"] for r in v if r["session"] == 2 and r["map"] == "taught" and taught(r)]), 100 * mean([r["fact_in_readout"] for r in v if r["session"] == 2 and r["map"] == "cold" and taught(r)]), sorted({r["map"] for r in v if r["session"] == 5})))
print("\n## lessons through the rebuilds, perfect lessons")
for x in repos:
    print(x, *[f"{n.split('_')[1]}: {len(Life(C.work(x, 'maps', n, 'taught.life.json')).store)} held, {len(json.load(open(C.work(x, 'maps', n, 'carry_misses.json')))) if os.path.exists(C.work(x, 'maps', n, 'carry_misses.json')) else 0} without a place" for n in ("landing_first", "landing_mate", "landing_T1", "landing_T2")], sep=" | ")
print("\n## lessons through the rebuilds, the agent's own")
for x in repos:
    print(x, *[f"{n.split('_')[1]}: {len(Life(C.work(x, 'maps', n, 'taught.life.json')).store)} held, {len(json.load(open(C.work(x, 'maps', n, 'carry_misses.json')))) if os.path.exists(C.work(x, 'maps', n, 'carry_misses.json')) else 0} without a place" for n in ("modeld_first", "modeld_mate", "modeld_T1", "modeld_T2")], sep=" | ")
