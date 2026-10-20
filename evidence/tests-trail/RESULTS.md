# Results: tests after code (METHOD.md, D1)

**The change (0.5.3):** within a readout, test files move after the code they test. The readout keeps the same items.
It is exempt when the question is about tests, and a taught pointer keeps the lead. Every question below was asked
twice of the same workspace: OFF (0.5.2's order) and ON.

**Right file first:**

| set | OFF (0.5.2) | ON (0.5.3) | grep-first | ON only / OFF only | exact McNemar p |
|---|---|---|---|---|---|
| Hono, 241, plain question (primary) | 60 (25%) | **74 (31%)** | 39 (16%) | 14 / 0 | 0.00012 |
| Hono, 241, with "fix(module):" | 79 (33%) | **117 (49%)** | 44 (18%) | 38 / 0 | 7.3e-12 |
| Django 2022, 288, cold | 111 (39%) | **133 (46%)** | – | 22 / 0 | 4.8e-7 |
| Django 2022, 288, taught (`cover`) | 149 (52%) | **153 (53%)** | – | 4 / 0 | 0.125 |
| Graphify, 50 (the discovery set) | 12 (24%) | **21 (42%)** | 19 (38%) | 9 / 0 | 0.0039 |
| claude-mem, 50 | 13 (26%) | **15 (30%)** | 1 (2%) | 2 / 0 | 0.5 |

**Right file in the top 5:**
- Hono: 134 → 145 (plain question); 179 → 187 (with the module name);
- Django: 197 → 204 (cold); 219 → 220 (taught);
- Graphify: 36 → 37, against grep's 40;
- claude-mem: 24 → 27.

**A changed line in the top 5:**
- Hono: 63 → 74 (plain question); 79 → 97 (with the module name);
- Graphify: 11 → 13;
- claude-mem: 7 → 10.

**Predictions:** all five held.

| prediction | result |
|---|---|
| T1, Hono ON > OFF | 74 > 60 |
| T2, Django cold ≥ OFF − 2 | 133 ≥ 109 |
| T3, Django taught ≥ OFF − 2 | 153 ≥ 147 |
| T4, Graphify ON > grep's 19 | 21 |
| T5, claude-mem ON ≥ OFF | 15 ≥ 13 |

**Check of the harness:** OFF reproduced the earlier runs:
- Graphify 12 / 36, claude-mem 13 / 24 and Django cold 111, exactly;
- Hono 60 / 134 against 62 / 135, within the ±2 allowed. Since that run, 0.5.2 removed the 512 KB file limit.

**What this does and does not show:**
- **No losses here, but by construction.** In all of these sets the true answer is code, never a test file (0 of
  629 fixes, by the 0.5.3 test rule). When the answer is code, moving tests back can only move the answer up.
  "None lost" is therefore guaranteed here, not evidence of safety.
- **The real risk** is a question whose answer is a test, worded without any test word. It is not measured here.
  `OCM_TESTS_TRAIL=off` turns the change off.
- **Graphify:** Model D now leads grep on right file first (21 vs 19, within chance at 50 fixes). It still trails in
  the top 5 (37 vs 40).
- **Django's library `test/` package** is treated as code by the rule. That covers 13 of the 288 fixes, and none of
  them lost.
- **Cold pointing only.** This measures pointing with nothing remembered. What memory adds on top is measured by
  `modeld prove --learn` (see RESULTS_LEARN.md, when written) and by the team-year evidence.

**Files:**
- results_*.jsonl: every readout, OFF and ON, with the grep baseline;
- report.json: the numbers above;
- score.py: recomputes them;
- run.py: the run;
- HASHES.txt: hashes of METHOD.md and run.py, taken before any run;
- METHOD.md.deviations: D1, a reading bug in the Hono set, fixed before any Hono result.
