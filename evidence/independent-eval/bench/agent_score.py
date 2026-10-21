"""Score the agent-in-the-loop runs: right file named first, tool calls, tokens, wall time, per setup.
Tool calls exclude the one Read every run spends opening its task file."""
import os, json, statistics as st

S = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_set.json")))
rows = [l.rstrip("\n").split("\t") for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_results.tsv")) if l.strip()]
res = {}
for key, ans, tok, tools, ms in rows:
    i, cfg = key.split("_")
    gold = S[int(i)]["gold"]
    f = ans.split(":")[0]
    res[(int(i), cfg)] = {"ok": f in gold, "answered": ans != "NOANSWER", "tokens": int(tok), "tools": int(tools) - 1, "s": int(ms) / 1000}
names = {"base": "No tool", "md": "Model D", "gf": "Graphify"}
print(f"{'':10}{'right':>8}{'tool calls':>12}{'tokens':>10}{'seconds':>9}   (means; n = runs back)")
for cfg in ("base", "md", "gf"):
    v = [r for (i, c), r in res.items() if c == cfg]
    print(f"{names[cfg]:10}{sum(r['ok'] for r in v):>4}/{len(v):<3}{st.mean(r['tools'] for r in v):>12.1f}"
          f"{st.mean(r['tokens'] for r in v):>10.0f}{st.mean(r['s'] for r in v):>9.1f}")
both = sorted({i for i, c in res} )
full = [i for i in both if all((i, c) in res for c in ("base", "md", "gf"))]
print(f"\npaired on the {len(full)} questions every setup finished:")
for cfg in ("md", "gf"):
    d = [res[(i, cfg)]["tools"] - res[(i, "base")]["tools"] for i in full]
    t = [res[(i, cfg)]["s"] - res[(i, "base")]["s"] for i in full]
    fewer = sum(x < 0 for x in d); more = sum(x > 0 for x in d)
    print(f"  {names[cfg]:9} vs no tool: tool calls {st.mean(d):+.1f} per question (fewer on {fewer}, more on {more}), time {st.mean(t):+.1f}s")
print("\nper question (tool calls: base / md / gf, x = wrong file)")
for i in full:
    cell = lambda c: f"{res[(i, c)]['tools']}{'' if res[(i, c)]['ok'] else ('x' if res[(i, c)]['answered'] else '?')}"
    print(f"  {i:>2} {S[i]['repo']:8} {cell('base'):>4} {cell('md'):>4} {cell('gf'):>4}  {S[i]['question'][:60]}")
