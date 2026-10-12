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
section("Claude API program (Claude Sonnet 5.5, Haiku 5.5 reader; list prices from the API's own usage fields)")
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
