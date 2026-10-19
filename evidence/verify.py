"""Recompute every public Model D number from the evidence in this folder, and check the pre-registration hashes.

    python evidence/verify.py

Numbers marked "rows" are recomputed here from the per-question records; numbers marked "report" are read from the
report its own script wrote (claude-api/scripts/report.py and the others in this folder). Standard library only."""
import hashlib, json, os
from statistics import mean

E = os.path.dirname(os.path.abspath(__file__))
ROWS = f"{E}/claude-api/rows"


def load(path):
    return json.load(open(f"{E}/{path}"))


def rows(name):
    return [json.loads(l) for l in open(f"{ROWS}/{name}")]


def paired(a_name, d_name, pass_=None):
    """Alone and Model D rows for the same questions, errors dropped, as the report pairs them."""
    keep = lambda r: not r["error"] and (pass_ is None or r.get("pass") == pass_)
    A = {r["id"]: r for r in rows(a_name) if keep(r)}
    D = {r["id"]: r for r in rows(d_name) if keep(r)}
    ids = [i for i in A if i in D]
    return [A[i] for i in ids], [D[i] for i in ids]


def usd_factor(a, d):
    return mean(r["usd"] for r in a) / mean(r["usd"] for r in d)


def line(claim, value, source):
    print(f"  {claim:<62} {value:<26} {source}")


def section(title):
    print(f"\n{title}")


# --- 1. Pre-registration -------------------------------------------------------------------------------------------
section("Pre-registration: each plan's SHA-256, recorded before its first model call")
prereg = load("prereg_hashes.json")
manifest = {m["from"]: m for m in load("MANIFEST.json")}
match = changed = elsewhere = 0
for key, v in prereg.items():
    src = key.split(" (")[0]
    m = manifest.get(src)
    if not m:
        elsewhere += 1
        continue
    if m["sha256"] == v["sha256"]:
        match += 1
    elif not any(k.split(" (")[0] == src and prereg[k]["sha256"] == m["sha256"] for k in prereg):
        changed += 1
        print(f"  changed after it was fixed: {src} (see the .deviations file of its protocol)")
line("plans and inputs in this folder that match their recorded hash", f"{match}", "prereg_hashes.json")
line("recorded plans not included here (other studies)", f"{elsewhere}", "")

# --- 2. The Claude API program -------------------------------------------------------------------------------------
section("Claude API program (Claude Sonnet 5.5 and Haiku 5.5; list prices from the API's own usage fields)")
R = load("claude-api/reports/report_value.json")
held = [v for v in R.values() if isinstance(v, bool)]
line("predictions that held", f"{sum(held)} of {len(held)}", "report")

a1, d1 = paired("e1_alone.jsonl", "e1_md.jsonl")
a2, d2 = paired("e2_alone.jsonl", "e2_md.jsonl")
line("228-question stream, bill alone -> Model D", f"${sum(r['usd'] for r in a1 + a2):.2f} -> ${sum(r['usd'] for r in d1 + d2):.2f}", "rows e1, e2")
line("228-question stream, right alone / Model D", f"{sum(bool(r['right']) for r in a1 + a2)} / {sum(bool(r['right']) for r in d1 + d2)}", "rows e1, e2")
line("reworded reports, per question alone -> Model D", f"${mean(r['usd'] for r in a2):.3f} -> ${mean(r['usd'] for r in d2):.3f}", "rows e2")
reads = [r for r in d2 if r["path"] == "read"]
line("reworded reports answered by one read of learned code", f"{len(reads)} of {len(d2)}", "rows e2")
line("those reads judged right", f"{sum(bool(r['right']) for r in reads)} of {len(reads)}", "rows e2")
line("cost of a learned question (one read)", f"${mean(r['usd'] for r in reads):.4f}", "rows e2")

pooled_a, pooled_d = [], []
for a_name, d_name in (("e1_alone.jsonl", "e1_md.jsonl"), ("f1_r2_alone.jsonl", "f1_r2_md.jsonl"), ("f1_r3_alone.jsonl", "f1_r3_md.jsonl")):
    a, d = paired(a_name, d_name); pooled_a += a; pooled_d += d
line("114 Django bugs x3: requests per bug alone -> Model D", f"{mean(r['requests'] for r in pooled_a):.2f} -> {mean(r['requests'] for r in pooled_d):.2f}", "rows e1, f1_r2, f1_r3")
line("114 Django bugs x3: cost factor", f"{usd_factor(pooled_a, pooled_d):.2f}x", "rows e1, f1_r2, f1_r3")
line("114 Django bugs x3: right alone / Model D", f"{sum(bool(r['right']) for r in pooled_a)} / {sum(bool(r['right']) for r in pooled_d)} of {len(pooled_a)}", "rows e1, f1_r2, f1_r3")
e3 = [r for r in rows("e3_md.jsonl") if not r["error"]]
line("misleading lessons taught; cheap reads that fired on one", f"{len(e3)}; {sum(r['path'] == 'read' for r in e3)}", "rows e3")

# An exploration that cites a line teaches it ("at"); the retest rows (rt_qa) do not record "at", so they are left out.
taught = [r for f in sorted(os.listdir(ROWS)) if f.endswith("_md.jsonl") for r in rows(f) if r.get("path") == "teach" and not r["error"] and "at" in r]
line("explorations that left a lesson (runs that record it)", f"{sum(bool(r['at']) for r in taught)} of {len(taught)}", "rows *_md")

v4, v7, j = R["V4"], R["V7"]["NS"], R["V4 judge"]
line("company repo, 5-role team x3 runs: cost factor", f"{v4['usd']['factor']:.2f}x", "report V4")
line("company repo, strict reader: cost factor", f"{v7['saving vs alone']:.2f}x", "report V7")
line("company repo, judged right alone / strict reader", f"{j['alone']['right'] * 100:.0f}% / {v7['right'] * 100:.0f}%", "report V4 judge, V7")
line("company repo, teammates' repeats: cost factor", f"{v4['repeats']['usd']['factor']:.2f}x", "report V4")
line("company repo, saving first half -> second half", f"{v4['first half usd factor']:.2f}x -> {v4['second half usd factor']:.2f}x", "report V4")

for label, a_name, d_name, p in (("research with web search", "e6", "e6", 1), ("research with web search, asked again", "e6", "e6", 2),
                                 ("deep research: code + docs + web", "f3", "f3", 1), ("deep research, asked again", "f3", "f3", 2),
                                 ("deep web research from tickets", "g1", "g1", 1), ("deep web research, asked again", "g1", "g1", 2)):
    a, d = paired(f"{a_name}_alone.jsonl", f"{d_name}_md.jsonl", p)
    line(label, f"{usd_factor(a, d):.1f}x cheaper", f"rows {a_name}, pass {p}")
for label, n in (("maximum-effort thinking, 30 hardest bugs", "g3"), ("bugs in sympy, scikit-learn, pytest", "e5"),
                 ("bugs in matplotlib, sphinx, requests, flask", "f4")):
    a, d = paired(f"{n}_alone.jsonl", f"{n}_md.jsonl")
    line(label, f"{usd_factor(a, d):.2f}x cheaper", f"rows {n}")
v5 = R["V5"]
line("writing the fix (Django's own tests): resolved alone / Model D", f"{v5['resolved alone']} / {v5['resolved modeld']} of {v5['n']}", "report V5")
line("writing the fix: $ per resolved alone -> Model D", f"${v5['usd per resolved alone']:.3f} -> ${v5['usd per resolved modeld']:.3f}", "report V5")
line("program spend", f"${R['program spend usd']:.2f}", "report")

section("Public benchmarks, retest with caching on both arms")
rt = load("claude-api/reports/report_retest.json")
q = rt["R2 swe-qa"]
line("SWE-QA, 91 questions: cost factor", f"{q['cost ratio']:.2f}x", "report_retest")
line("SWE-QA score alone / Model D (out of 100)", f"{q['alone score']} / {q['model d score']}", "report_retest")
cb = rt["R1 swe-contextbench"]
line("SWE-ContextBench, writing fixes: resolved alone / Model D", f"{cb['alone']['resolved']} / {cb['cold']['resolved']} of 28", "report_retest")
line("SWE-ContextBench: $ per task alone / Model D", f"${cb['alone']['$ per task']:.3f} / ${cb['cold']['$ per task']:.3f}", "report_retest")

# --- 3. The math ---------------------------------------------------------------------------------------------------
section("The math, with parameters fixed before the runs")
for k, label in (("M1 E1", "turn law, 114 Django bugs"), ("M1 V4", "turn law, company repo")):
    m = R[k]
    line(f"{label}: requests predicted / measured", f"{m['r_D predicted']:.2f} / {m['r_D measured']:.2f} ({m['error'] * 100:+.0f}%)", f"report {k}")
sets = ["e1", "f1_r2", "f1_r3", "e2", "e4", "f2", "e5", "f4", "e6", "f3", "g1", "g3"]
ka = []
for n in sets:
    A = [r["usd"] for r in rows(f"{n}_alone.jsonl") if not r["error"]]
    K = [r["usd"] for r in rows(f"{n}_md.jsonl") if not r["error"] and r["path"] == "teach"]
    ka.append(mean(A) / mean(K))
line("teaching cheaper than working alone (K < A), test sets", f"{sum(x > 1 for x in ka)} of {len(ka)}", "rows, 12 sets")
line("teaching's saving over working alone, range where K < A", f"{min(x for x in ka if x > 1):.2f}x to {max(ka):.2f}x", "rows, 12 sets")
m3 = R["M3 E2"]
line("learning formula, reworded reports: saving predicted / measured", f"{m3['S predicted']:.2f}x / {m3['S measured']:.2f}x ({m3['error'] * 100:+.0f}%)", "report M3 E2")

# --- 4. Ten years of Django, offline -------------------------------------------------------------------------------
section("Ten years of Django, replayed in order (5,333 real fixes, offline, no model)")
rp = load("replay/report_replay.json")
o, w = rp["raw"]["overall"], rp["raw"]["without repeat tickets"]
line("right file shown by the layer alone", f"{o['FROZEN file hit'] * 100:.1f}%", "report_replay")
line("questions landing on learned ground, first -> last decile", f"{w['lane first decile'] * 100:.0f}% -> {w['lane last decile'] * 100:.0f}%", "report_replay")
line("learned shortcut's first pick right, when it fired", f"{o['lane right when opened'] * 100:.0f}%", "report_replay")
line("file hit added by learning over the frozen layer", f"{o['learning advantage (hit points)'] * 100:+.1f} points", "report_replay")

# --- 5. Gemini, Model D end to end ---------------------------------------------------------------------------------
section("Model D end to end on Gemini 2.5 Flash (three runs)")
g = load("gemini/report_e2e.json")
for run in ("questions, run 1", "questions, run 2", "questions, run 3"):
    if run not in g:
        continue
    t = g[run]["taught (repeats)"]
    line(f"{run}: learned question requests alone -> Model D", f"{t['requests per question, alone / cmlm / model d'][0]} -> {t['requests per question, alone / cmlm / model d'][2]}", "report_e2e")
    line(f"{run}: bill factor", f"{g[run]['dollar factor vs alone']}x", "report_e2e")

# --- 6. Learning that lasts ----------------------------------------------------------------------------------------
section("The saving grows with the codebase: the same kit live on 148k tokens and on 10.8M tokens")
V = load("learning/live-vectors/report_vec.json")
line("FastAPI template (148k tokens): requests alone -> Model D", f"{V['alone']['requests']} -> {V['cmlm']['requests']} ({V['alone']['requests'] / V['cmlm']['requests']:.2f}x)", "report_vec")
L = load("learning/large-codebase/report_large.json")
line("transformers (10.8M tokens): requests alone -> Model D", f"{L['alone']['requests']} -> {L['cmlm']['requests']} ({L['alone']['requests'] / L['cmlm']['requests']:.2f}x)", "report_large")
line("transformers: right alone / Model D", f"{L['alone']['right']} / {L['cmlm']['right']}", "report_large")
am = L["absorbed map (second wordings)"]
line("reworded questions landing on what was learned", f"{am['right']} of {am['right'] + am['junk'] + am['not absorbed']}", "report_large")

section("Lessons carried through a real code move (400 commits of the FastAPI template, offline)")
lf = load("learning/life/report_life.json")
line("lessons re-found after the move (19 of 38 had moved)", f"{lf['carried']['LIFE']['right']} of {lf['entries taught at A']}", "report_life")
line("same, if lessons are carried as-is", f"{lf['carried']['CARRY-AS-IS']['right']} right, {lf['carried']['CARRY-AS-IS']['wrong']} wrong", "report_life")

# --- 7. Finding the fixed file: SWE-bench Lite in full repositories, against Graphify -----------------------------
section("Finding the fixed file: 285 SWE-bench Lite issues, 12 full repositories, offline (PROTOCOL_CODEONLY)")
issues = {it["instance_id"]: it for v in load("swe-bench-lite/swebench_lite_by_repo.json").values() for it in v["issues"]}
kept = load("swe-bench-lite/kept_issues.json")
arms = (("Model D, code scope", "codeonly.json"), ("Model D, full scope", "regress_all2.json"), ("Graphify 0.9.87", "graphify_ranked_087.json"))
for key, label in (("query_title", "issue title"), ("query_400", "title + 400 characters")):
    for name, f in arms:
        R = load(f"swe-bench-lite/{f}")
        hits = [sum(any(g in issues[i]["gold_files"] for g in R[s][i][key]["files"][:k]) for s, i in kept) for k in (1, 3, 5)]
        tok = mean(R[s][i][key]["chars"] / 4 for s, i in kept)
        line(f"{label}, {name}: top-1 / 3 / 5", f"{' / '.join(map(str, hits))} · {tok:,.0f} tok", f"rows {f}")
held = load("swe-bench-lite/report_codeonly.json")["predictions"]
line("pre-registered predictions that held", f"{sum(held.values())} of {len(held)}", "report_codeonly")

# --- 8. A team's year: Django's 2022 fixes through the product, against the agent alone ----------------------------
if os.path.isdir(f"{E}/team-year"):
    section("A team's year: Django's 2022 fixes, in order, the product against the agent alone (PROTOCOL_TEAM_YEAR)")
    for line_ in open(f"{E}/team-year/PREREG_HASHES.txt"):
        parts = line_.split()
        if len(parts) == 2 and len(parts[0]) == 64 and parts[1].split("/")[-1] in ("PROTOCOL_TEAM_YEAR.md", "PROTOCOL_TEAM_YEAR_GATE.md", "window_2022.json", "keep.json"):
            f = f"{E}/team-year/{parts[1].split('/')[-1]}"
            ok = hashlib.sha256(open(f, "rb").read()).hexdigest() == parts[0]
            line(f"pre-registered {parts[1].split('/')[-1]}", "hash matches" if ok else "HASH MISMATCH", "PREREG_HASHES.txt")
    ty = lambda name: {json.loads(l)["k"]: json.loads(l) for l in open(f"{E}/team-year/rows/{name}")}
    al = ty("alone.jsonl")
    for arm in ("md", "gate"):
        md = ty(f"{arm}.jsonl"); ks = sorted(md.keys() & al.keys())
        cited = lambda r: r["right"] if r["path"] != "read" else any(g in r["answer"] or "django/" + g in r["answer"] for g in r["gold"])
        a_usd, d_usd = sum(al[k]["usd"] for k in ks), sum(md[k]["usd"] for k in ks)
        name = "Model D" if arm == "md" else "Model D, gated"
        line(f"{name}: paired fixes, cost alone -> {name}", f"{len(ks)} · ${a_usd:.2f} -> ${d_usd:.2f} ({a_usd / d_usd:.2f}x)", f"rows {arm}.jsonl")
        line(f"{name}: right (pre-registered / cited, D4) vs alone", f"{sum(md[k]['right'] for k in ks)} / {sum(cited(md[k]) for k in ks)} vs {sum(al[k]['right'] for k in ks)}", f"rows {arm}.jsonl")
        line(f"{name}: novelty (share on the teach path)", f"{sum(md[k]['path'] == 'teach' for k in ks) / len(ks):.2f}", f"rows {arm}.jsonl")


def mcnemar(a, b):
    """Exact two-sided McNemar on paired booleans: (a only, b only, p)."""
    import math
    n10 = sum(x and not y for x, y in zip(a, b)); n01 = sum(y and not x for x, y in zip(a, b)); n = n10 + n01
    k = min(n10, n01)
    return n10, n01, (1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n))


def prereg(folder, names, hashfile="PREREG_HASHES.txt"):
    """Check each named file against every hash recorded for it in <folder>/PREREG_HASHES.txt."""
    rec = {}
    for line_ in open(f"{E}/{folder}/{hashfile}"):
        parts = line_.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            rec.setdefault(parts[1].split("/")[-1] if "/" not in parts[1] or parts[1].startswith(("~", "/")) else parts[1], []).append(parts[0])
    for name in names:
        h = hashlib.sha256(open(f"{E}/{folder}/{name}", "rb").read()).hexdigest()
        hs = rec.get(name) or rec.get(name.split("/")[-1], [])
        line(f"pre-registered {name}", "hash matches" if h in hs else "HASH MISMATCH", f"{folder}/{hashfile}")


# --- 9. Real comprehension questions: bluesky atproto's answered Discussions, blind judge --------------------------
if os.path.isdir(f"{E}/oss-comprehension"):
    section("Real comprehension questions: 115 atproto Discussions, blind judge (PROTOCOL_OSS_COMPREHENSION)")
    prereg("oss-comprehension", ["PROTOCOL_OSS_COMPREHENSION.md", "comp_questions.json", "comp_meta.json"])
    oc = lambda name: {json.loads(l)["k"]: json.loads(l) for l in open(f"{E}/oss-comprehension/rows/{name}")}
    md, al = oc("md.jsonl"), oc("alone.jsonl")
    V = {(r["key"].split("|")[0], int(r["key"].split("|")[1])): r["verdict"] for r in map(json.loads, open(f"{E}/oss-comprehension/rows/judged.jsonl"))}
    ks = sorted(k for k in md.keys() & al.keys() if ("md", k) in V and ("alone", k) in V)
    a_usd, d_usd = sum(al[k]["usd"] for k in ks), sum(md[k]["usd"] for k in ks)
    line("paired and judged questions; cost alone -> Model D", f"{len(ks)} · ${a_usd:.2f} -> ${d_usd:.2f} ({a_usd / d_usd:.2f}x)", "rows md/alone.jsonl")
    for arm, name in (("md", "Model D"), ("alone", "alone")):
        c = [V[(arm, k)] for k in ks]
        line(f"{name}: RIGHT / PARTIAL / WRONG", f"{c.count('RIGHT')} / {c.count('PARTIAL')} / {c.count('WRONG')}", "rows judged.jsonl")
    ok = lambda arm: [V[(arm, k)] in ("RIGHT", "PARTIAL") for k in ks]
    n10, n01, p = mcnemar(ok("md"), ok("alone"))
    line("right or partial, paired: Model D only / alone only, p", f"{n10} / {n01}, p = {p:.2f}", "rows judged.jsonl")
    pts = lambda arm: sum({"RIGHT": 2, "PARTIAL": 1}.get(V[(arm, k)], 0) for k in ks)
    line("quality points, Model D / alone", f"{pts('md')} / {pts('alone')} ({pts('md') / pts('alone'):.0%})", "rows judged.jsonl")

# --- 10. Coverage: teach the whole codebase once, then the 288 real Django 2022 questions ---------------------------
if os.path.isdir(f"{E}/team-year/coverage"):
    section("Coverage: one generated question per piece of Django code, taught once (PROTOCOL_COVERAGE)")
    h = hashlib.sha256(open(f"{E}/team-year/coverage/PROTOCOL_COVERAGE.md", "rb").read()).hexdigest()
    line("pre-registered PROTOCOL_COVERAGE.md", "hash matches" if h in open(f"{E}/team-year/PREREG_HASHES.txt").read() else "HASH MISMATCH", "team-year/PREREG_HASHES.txt")
    line("questions written and taught", f"{sum(1 for _ in open(f'{E}/team-year/coverage/coverage_questions.jsonl')):,}", "coverage_questions.jsonl")
    cv = load("team-year/coverage/coverage_eval.json")
    cold, cov = {r["k"]: r for r in cv["cold"]["rows"]}, {r["k"]: r for r in cv["covered"]["rows"]}
    ks = sorted(cold.keys() & cov.keys())
    for key, label in (("right1", "right file first"), ("right5", "right file in the top 5")):
        n10, n01, p = mcnemar([cov[k][key] for k in ks], [cold[k][key] for k in ks])
        line(f"{label}: cold -> covered (covered only / cold only, p)", f"{sum(cold[k][key] for k in ks)} -> {sum(cov[k][key] for k in ks)} ({n10} / {n01}, p = {p:.2g})", "coverage_eval.json")
    line("readouts led by taught code", f"{sum(cov[k]['taught'] for k in ks)} of {len(ks)}", "coverage_eval.json")

# --- 11. Final Model D against Graphify 0.9.92 --------------------------------------------------------------------
if os.path.isdir(f"{E}/vs-graphify"):
    section("Final Model D against Graphify 0.9.92 (PROTOCOL_VS_GRAPHIFY; Part B interim, D1)")
    G = f"{E}/vs-graphify"
    prereg("vs-graphify", ["PROTOCOL_VS_GRAPHIFY.md", "ADDENDUM_A1_TOKEN_CLAIM.md", "questions/django2022.json", "scripts/point.py",
                           "scripts/gf_mcp.py", "scripts/e2e_graphify.py", "scripts/score.py"])
    arms = (("md_cover", "Model D taught"), ("md_cold", "Model D cold"), ("gf", "Graphify 0.9.92"))

    def hits(qs, res, q):
        return {a: [[any(f in it["gold"] for f in res[a][str(it["id"])][q]["files"][:k]) for it in qs] for k in (1, 3, 5)] for a, _ in arms}

    dj = json.load(open(f"{G}/questions/django2022.json"))
    R = {a: json.load(open(f"{G}/results/dj_{a}.json")) for a, _ in arms}
    H = hits(dj, R, "q")
    for a, name in arms:
        tok = mean(R[a][str(it["id"])]["q"]["chars"] / 4 for it in dj)
        line(f"Django 2022 (288), {name}: top-1 / 3 / 5", f"{' / '.join(str(sum(x)) for x in H[a])} · {tok:,.0f} tok", f"rows dj_{a}.json")
    n10, n01, p = mcnemar(H["md_cover"][0], H["gf"][0])
    line("Django right first, Model D taught only / Graphify only, p", f"{n10} / {n01}, p = {p:.1e}", "rows")
    lite = [(json.load(open(f"{G}/questions/lite_{n}.json")), {a: json.load(open(f"{G}/results/lite_{a}_{n}.json")) for a, _ in arms})
            for n in sorted(p_.split("lite_")[1][:-5] for p_ in os.listdir(f"{G}/questions") if p_.startswith("lite_"))]
    for q, label in (("title", "issue title"), ("q400", "title + 400 characters")):
        tot = {a: [0, 0, 0] for a, _ in arms}
        for qs, res in lite:
            for a, x in hits(qs, res, q).items():
                tot[a] = [t + sum(v) for t, v in zip(tot[a], x)]
        line(f"SWE-bench Lite ({sum(len(qs) for qs, _ in lite)}), {label}: top-1 / 3 / 5",
             "  ".join(f"{ {'md_cover': 'taught', 'md_cold': 'cold', 'gf': 'Graphify'}[a]} {'/'.join(map(str, tot[a]))}" for a, _ in arms), "rows lite_*.json")
    rb = load("vs-graphify/best/report_best.json")
    for title, q in (("Django 2022 (288 fixes)", "q"), ("SWE-bench Lite (285 issues, 12 repos)", "title"), ("Four Python repos (requests, itsdangerous, httpx, click; 172 fixes)", "q")):
        t = rb[title][q]["top1/3/5"]; best = rb[title][q]["graphify at its best"]
        line(f"read at its best ({title.split(' (')[0]}): Graphify / Model D cold, top-1 / 5", f"{t[best][0]}/{t[best][2]} vs {t['md_cold'][0]}/{t['md_cold'][2]}", "best/report_best.json")
    tc = load("vs-graphify/results/token_claim.json")
    line("Graphify's token formula on its own Karpathy example (0.9.92)", f"{tc['karpathy, its reported corpus words']['reduction_ratio']}x (claimed 71.5x)", "token_claim.json")
    line("the same formula on Django 2022: Graphify / Model D cold", f"{tc['django 2022, the 288 real questions']['reduction_ratio']:,}x / {tc['django 2022, formula on Part A readouts: md_cold']['reduction_ratio']:,}x", "token_claim.json")
    gfr = {json.loads(l)["k"]: json.loads(l) for f in sorted(os.listdir(f"{G}/rows")) if f.startswith("rows_gf") for l in open(f"{G}/rows/{f}")}
    al = {json.loads(l)["k"]: json.loads(l) for l in open(f"{E}/team-year/rows/alone.jsonl")}
    md = {json.loads(l)["k"]: json.loads(l) for l in open(f"{E}/team-year/rows/md.jsonl")}
    ks = sorted(gfr.keys() & al.keys() & md.keys())
    cited = lambda r: r["right"] if r["path"] != "read" else any(g in r["answer"] or "django/" + g in r["answer"] for g in r["gold"])
    for d, name in ((al, "Claude alone"), (gfr, "Claude + Graphify"), (md, "Claude + Model D (cold)")):
        line(f"Part B, interim ({len(ks)} fixes): {name}", f"${sum(d[k]['usd'] for k in ks):.2f} · {sum(d[k]['requests'] for k in ks)} req · {sum(cited(d[k]) for k in ks)} right", "rows")

# --- 11b. A codebase Model D had never seen: 241 real Hono fixes, file and line level -------------------------------
if os.path.isdir(f"{E}/new-codebase-hono"):
    section("A new codebase: 241 real honojs/hono fixes, each against its parent commit (METHOD.md, offline)")
    prereg("new-codebase-hono", ["METHOD.md", "questions.json", "questions.py"], "HASHES.txt")   # run.py changed by D1, before any result
    HQ = {q["id"]: q for q in load("new-codebase-hono/questions.json")}
    HR = [json.loads(l) for l in open(f"{E}/new-codebase-hono/results.jsonl")]
    for qn, label in (("bare", "plain question"), ("subject", "commit subject")):
        md = [list(dict.fromkeys(i[0] for i in r["q"][qn]["items"])) for r in HR]; gr = [r["q"][qn]["grep"] for r in HR]
        gold = [HQ[r["id"]]["gold"] for r in HR]
        h = lambda F, k: [any(f in g for f in L[:k]) for L, g in zip(F, gold)]
        n10, n01, p = mcnemar(h(md, 1), h(gr, 1))
        line(f"{label}: right file first / top 5, Model D vs grep", f"{sum(h(md, 1))}/{sum(h(md, 5))} vs {sum(h(gr, 1))}/{sum(h(gr, 5))} of {len(HR)}", "rows results.jsonl")
        line(f"{label}: right file first, paired (MD only / grep only, p)", f"{n10} / {n01}, p = {p:.2g}", "rows results.jsonl")
        lh = lambda it, gl: any(a <= hi and b >= lo for p_, a, b in [it] for lo, hi in gl.get(p_, []))
        l5 = sum(any(lh(x, HQ[r["id"]]["gold_lines"]) for x in r["q"][qn]["items"][:5]) for r in HR)
        line(f"{label}: exact changed lines in the top 5", f"{l5} of {len(HR)} ({l5 / len(HR):.1%})", "rows results.jsonl")

# --- 11c. What the learning does: the saving's sources, the learned law forced on, and the 0.5.1 fixes ----------------
if os.path.isdir(f"{E}/learning-ablation"):
    section("Learning: where the 2.09x comes from, the learned law forced on, and the 0.5.1 fixes (evidence/learning-ablation)")
    import random
    ty = lambda name: {json.loads(l)["k"]: json.loads(l) for l in open(f"{E}/team-year/rows/{name}")}
    al, md = ty("alone.jsonl"), ty("md.jsonl"); ks = sorted(al.keys() & md.keys())
    A_, M_ = sum(al[k]["usd"] for k in ks), sum(md[k]["usd"] for k in ks)
    rnd = random.Random(0); rs = []
    for _ in range(10000):
        smp = [rnd.choice(ks) for _ in ks]; rs.append(sum(al[k]["usd"] for k in smp) / sum(md[k]["usd"] for k in smp))
    rs.sort()
    line("team year: saving, bootstrap 95% interval", f"{A_ / M_:.2f}x ({rs[250]:.2f}x-{rs[9750]:.2f}x)", "rows team-year")
    teach = [k for k in ks if md[k]["path"] == "teach"]; reads = [k for k in ks if md[k]["path"] == "read"]
    K_ = sum(md[k]["usd"] for k in teach) / len(teach); nolearn = sum(md[k]["usd"] for k in teach) + K_ * len(reads)
    line("share of dollars saved: retrieval / memory", f"{(A_ - nolearn) / (A_ - M_):.0%} / {(nolearn - M_) / (A_ - M_):.0%}", "rows team-year")
    G = f"{E}/learning-ablation"; tot = lambda rows, key: sum(r[key] for r in rows)
    a_on, a_off = load("learning-ablation/results_A_on.json")["rows"], load("learning-ablation/results_A_off.json")["rows"]
    line("learned law on / off (coverage): right first", f"{tot(a_on, 'right1')} / {tot(a_off, 'right1')}", "results_A_*.json")
    for arm, label in (("base", "0.5.0"), ("f13", "0.5.1 (F1 + F3)")):
        b = load(f"learning-ablation/results2_B_{arm}.json"); r = load(f"learning-ablation/results2_R_{arm}.json")["rows"]
        a = load(f"learning-ablation/results2_A_{arm}.json")
        line(f"{label}: new / repeats / coverage, right first", f"{tot(b, 'right1')} / {tot(r, 'right1')} of {len(r)} / {tot(a, 'right1')}", "results2_*.json")
        line(f"{label}: new / repeats / coverage, top 5", f"{tot(b, 'right5')} / {tot(r, 'right5')} / {tot(a, 'right5')}", "results2_*.json")

# --- 12. Every evidence file is present and unchanged ---------------------------------------------------------------
section("Every file listed in MANIFEST.json, present with its recorded SHA-256")
M = load("MANIFEST.json")
bad = [m["file"] for m in M if not os.path.exists(f"{E}/{m['file']}") or hashlib.sha256(open(f"{E}/{m['file']}", "rb").read()).hexdigest() != m["sha256"]]
line("files listed / missing or changed", f"{len(M)} / {len(bad)}", "MANIFEST.json")
for f in bad:
    line(f"  MISSING OR CHANGED {f}", "", "MANIFEST.json")
