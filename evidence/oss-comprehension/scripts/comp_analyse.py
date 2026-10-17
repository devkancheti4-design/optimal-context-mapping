"""PROTOCOL_OSS_COMPREHENSION analysis: blind verdicts, cost and learning by half; predictions C1-C4.

    python comp_analyse.py "rows_md*.jsonl" "rows_alone*.jsonl" judged.jsonl"""
import glob, json, sys
from collections import Counter
load = lambda g: {r["k"]: r for f in sorted(glob.glob(g)) for r in map(json.loads, open(f))}
md, al = load(sys.argv[1]), load(sys.argv[2])
V = {}
for r in map(json.loads, open(sys.argv[3])):
    arm, k = r["key"].split("|"); V[(arm, int(k))] = r["verdict"]
ks = sorted(k for k in md.keys() & al.keys() if ("md", k) in V and ("alone", k) in V)
h = len(ks) // 2; halves = {"first half": ks[:h], "second half": ks[h:], "all": ks}
print(f"paired and judged: {len(ks)} (Model D {len(md)}, alone {len(al)}, verdicts {len(V)})\n")
for name, sel in halves.items():
    a, m = sum(al[k]["usd"] for k in sel), sum(md[k]["usd"] for k in sel)
    vm, va = Counter(V[("md", k)] for k in sel), Counter(V[("alone", k)] for k in sel)
    reads = sum(md[k]["path"] == "read" for k in sel)
    print(f"{name:<12} n {len(sel):>3}  alone ${a:.3f} vs Model D ${m:.3f} -> {a / m:.2f}x | requests {sum(al[k]['requests'] for k in sel)} vs {sum(md[k]['requests'] for k in sel)}"
          f" | reads {reads} | Model D R/P/W {vm['RIGHT']}/{vm['PARTIAL']}/{vm['WRONG']} vs alone {va['RIGHT']}/{va['PARTIAL']}/{va['WRONG']}")
A = lambda sel: sum(al[k]["usd"] for k in sel) / sum(md[k]["usd"] for k in sel)
ok = lambda arm, sel: sum(V[(arm, k)] in ("RIGHT", "PARTIAL") for k in sel)
n = len(ks); r1 = sum(md[k]["path"] == "read" for k in halves["first half"]); r2 = sum(md[k]["path"] == "read" for k in halves["second half"])
print("\npredictions")
print(f"C1 bill alone/MD {A(ks):.2f}x >= 1.5x  {'held' if A(ks) >= 1.5 else 'FAILED'}")
print(f"C2 work R+P: MD {ok('md', ks)} >= alone {ok('alone', ks)} - {0.05 * n:.1f}  {'held' if ok('md', ks) >= ok('alone', ks) - 0.05 * n else 'FAILED'}")
print(f"C3 saving second half {A(halves['second half']):.2f}x > first {A(halves['first half']):.2f}x  {'held' if A(halves['second half']) > A(halves['first half']) else 'FAILED'}")
print(f"C4 read share second half {r2} > first {r1}  {'held' if r2 > r1 else 'FAILED'}")
