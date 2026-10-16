"""PROTOCOL_TEAM_YEAR analysis: per quarter novelty nu, E, K, A, the measured saving and the learning law's prediction;
then predictions T1-T5.

    python analyse.py rows_md.jsonl "rows_alone*.jsonl"
"""
import glob, json, sys

md = {json.loads(l)["k"]: json.loads(l) for l in open(sys.argv[1])}
al = {json.loads(l)["k"]: json.loads(l) for f in sorted(glob.glob(sys.argv[2])) for l in open(f)}
ks = sorted(md.keys() & al.keys())
q = lambda d: (int(d[5:7]) - 1) // 3 + 1                                   # quarter of the fix's date
mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")


def cited(r):
    """D4, secondary: a read-path answer is right if its text cites a changed file; others keep their 'at'."""
    if r["path"] != "read":
        return r["right"]
    t = r.get("answer", "")
    return any(g in t or ("django/" + g) in t for g in r["gold"])


print(f"paired questions: {len(ks)} (Model D {len(md)}, alone {len(al)})\n")
print(f"{'quarter':<8}{'n':>4}{'novelty':>9}{'E read':>9}{'K teach':>9}{'A alone':>9}{'MD mean':>9}{'saving':>8}"
      f"{'law':>8}{'law err':>9}{'right MD':>10}{'right alone':>12}")
rows = {}
for Q in (1, 2, 3, 4, None):
    sel = [k for k in ks if Q is None or q(md[k]["date"]) == Q]
    if not sel:
        continue
    reads = [md[k]["usd"] for k in sel if md[k]["path"] == "read"]
    teach = [md[k]["usd"] for k in sel if md[k]["path"] == "teach"]
    nu = len(teach) / len(sel)
    E, K, A = mean(reads) if reads else 0.0005, mean(teach), mean([al[k]["usd"] for k in sel])
    m = mean([md[k]["usd"] for k in sel]); s = A / m
    law = A / ((1 - nu) * E + nu * K); err = law / s - 1
    rmd, ral = sum(md[k]["right"] for k in sel), sum(al[k]["right"] for k in sel)
    rows[Q] = dict(n=len(sel), nu=nu, s=s, law=law, err=err, rmd=rmd, ral=ral, A=A, m=m)
    print(f"{('Q' + str(Q)) if Q else 'year':<8}{len(sel):>4}{nu:>9.2f}{E:>9.4f}{K:>9.4f}{A:>9.4f}{m:>9.4f}{s:>7.2f}x"
          f"{law:>7.2f}x{err:>+9.1%}{rmd:>10}{ral:>12}")
y = rows[None]
tot_md, tot_al = sum(md[k]["usd"] for k in ks), sum(al[k]["usd"] for k in ks)
reads_right = [md[k]["right"] for k in ks if md[k]["path"] == "read"]
reads_cited = [cited(md[k]) for k in ks if md[k]["path"] == "read"]
print(f"\ntotals: Model D ${tot_md:.3f}, alone ${tot_al:.3f} -> {tot_al / tot_md:.2f}x; requests "
      f"{sum(md[k]['requests'] for k in ks)} vs {sum(al[k]['requests'] for k in ks)}")
print(f"read path: {len(reads_right)} questions, right {sum(reads_right)} ({mean(reads_right):.0%}) as pre-registered; "
      f"{sum(reads_cited)} ({mean(reads_cited):.0%}) by the file the answer cites (D4)")
print(f"right, whole year: Model D {sum(md[k]['right'] for k in ks)} pre-registered / {sum(cited(md[k]) for k in ks)} cited (D4); "
      f"alone {sum(al[k]['right'] for k in ks)}")
qs = [Q for Q in (1, 2, 3, 4) if Q in rows]
print("\npredictions")
print(f"T1 bill: alone/MD {tot_al / tot_md:.2f}x >= 1.5x  {'held' if tot_al / tot_md >= 1.5 else 'FAILED'}")
print(f"T2 work: right MD {y['rmd']} >= alone {y['ral']} - {0.03 * y['n']:.1f}  {'held' if y['rmd'] >= y['ral'] - 0.03 * y['n'] else 'FAILED'}")
if 1 in rows and 4 in rows:
    print(f"T3 novelty: Q4 {rows[4]['nu']:.2f} < Q1 {rows[1]['nu']:.2f}  {'held' if rows[4]['nu'] < rows[1]['nu'] else 'FAILED'}")
    print(f"T4 saving grows: Q4 {rows[4]['s']:.2f}x > Q1 {rows[1]['s']:.2f}x  {'held' if rows[4]['s'] > rows[1]['s'] else 'FAILED'}")
print(f"T5 (as written, an identity, D2): {', '.join(f'Q{Q} {rows[Q]['err']:+.1%}' for Q in qs)}")
fc = []
for Q in qs[1:]:                                   # T5': forecast quarter Q from all earlier quarters' E, K, A and its own nu
    prev = [k for k in ks if q(md[k]["date"]) < Q]; cur = [k for k in ks if q(md[k]["date"]) == Q]
    r = [md[k]["usd"] for k in prev if md[k]["path"] == "read"]; t = [md[k]["usd"] for k in prev if md[k]["path"] == "teach"]
    E, K, A = mean(r) if r else 0.0005, mean(t), mean([al[k]["usd"] for k in prev])
    pred = A / ((1 - rows[Q]["nu"]) * E + rows[Q]["nu"] * K); err = pred / rows[Q]["s"] - 1; fc.append((Q, pred, rows[Q]["s"], err))
print("T5' forecast from earlier quarters: " + ", ".join(f"Q{Q} {p:.2f}x vs {m:.2f}x ({e:+.1%})" for Q, p, m, e in fc) +
      (f"  {'held' if fc and all(abs(e) <= 0.15 for *_, e in fc) else 'FAILED'}" if fc else "  (needs Q2)"))
