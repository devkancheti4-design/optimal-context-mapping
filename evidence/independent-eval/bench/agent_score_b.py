"""Session B: a reworded question in a fresh session. No tool vs Model D cold vs Model D with session A's lessons.
Tool calls exclude the one Read every run spends opening its task file."""
import os, json, statistics as st

S = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_set.json")))
res = {}
for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_results_b.tsv")):
    if not l.strip():
        continue
    key, ans, tok, tools, ms = l.rstrip("\n").split("\t")
    i, cfg = key.split("_")
    res[(int(i), cfg)] = {"ok": ans.split(":")[0] in S[int(i)]["gold"], "tokens": int(tok), "tools": int(tools) - 1, "s": int(ms) / 1000}
names = {"base": "No tool", "mdcold": "Model D, cold", "mdmem": "Model D + memory"}
full = [i for i in range(12) if all((i, c) in res for c in names)]
taught = [i for i in full if i != 9]
for label, qs in (("all questions", full), ("the 11 taught questions", taught)):
    print(f"\n{label} (n={len(qs)}):")
    print(f"  {'':18}{'right':>7}{'median calls':>14}{'mean calls':>12}{'total tokens':>14}{'median s':>10}")
    for c, n in names.items():
        v = [res[(i, c)] for i in qs]
        print(f"  {n:18}{sum(r['ok'] for r in v):>4}/{len(v):<2}{st.median(r['tools'] for r in v):>14}{st.mean(r['tools'] for r in v):>12.1f}"
              f"{sum(r['tokens'] for r in v):>14,}{st.median(r['s'] for r in v):>10.1f}")
    b = sum(res[(i, 'base')]['tools'] for i in qs); m = sum(res[(i, 'mdmem')]['tools'] for i in qs)
    print(f"  tool calls, no tool / Model D + memory: {b} / {m} = {b / m:.2f}x")
print("\nper question (tool calls: no tool / cold / memory)")
for i in full:
    print(f"  {i:>2} {S[i]['repo']:8} {res[(i, 'base')]['tools']:>3} {res[(i, 'mdcold')]['tools']:>4} {res[(i, 'mdmem')]['tools']:>4}"
          f"  {'(no lesson)' if i == 9 else ''}")
