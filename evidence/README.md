# Evidence

The data behind every number on the Model D site and in `results/RESULTS.md` sections 12-14. To check them:

```bash
python evidence/verify.py
```

`verify.py` uses only the standard library. It does three things:
- recomputes the numbers from the per-question records where it can;
- reads the rest from the reports their own scripts wrote;
- checks each pre-registered plan against the SHA-256 recorded before its first model call.

## How the tests were run
- **Plans first:** every plan was written and hashed before it ran. The hashes and their timestamps are in
  `prereg_hashes.json`.
- **Same setup in both arms:** the model, the instructions and the questions were the same for "alone" and "Model D".
  The only difference was the arm.
- **Costs:** taken from the API's own usage fields, at list price.
- **Grading:** accuracy was graded by a blind judge, or by the project's own tests where the task was a fix.
- **Deviations:** recorded as they happened, in the `.deviations` and `.addendum` files next to each protocol.

## What is where

| claim | where | what to look at |
|---|---|---|
| **a team's year: Django's 288 real 2022 fixes, in order, the product against the agent alone: 2.09x cheaper ($12.32 vs $25.72), right 252 vs 253 (cited); the saving rose from 1.88x to 2.57x as novelty fell 0.89 -> 0.78; the law forecast each quarter within 14%** | `team-year/` | `RESULTS_TEAM_YEAR.md`, `PROTOCOL_TEAM_YEAR.md` (+ `.deviations`, `_GATE.md`), `rows/md.jsonl`, `rows/alone.jsonl`, `rows/gate.jsonl` |
| company repo, 5-role team, 3 runs: 2.34-2.79x cheaper; repeats 3.49x; saving grew 2.66x -> 3.17x | `claude-api/` | `PROTOCOL_VALUE4.md`, `PROTOCOL_VALUE7.md`; rows `v4_r*`, `v7_*`, `v4_judge.jsonl`; report keys `V4`, `V7`, `V4 judge` |
| 228 questions in one stream: $11.56 -> $4.20, 215 vs 213 right | `claude-api/` | `PROTOCOL_VALUE.md`; rows `e1_*`, `e2_*` |
| learning: 84 of 114 reworded reports answered by one read, 81 of them right, $0.0005 each | `claude-api/` | rows `e2_md.jsonl` (`path` = `read`) |
| 114 real Django bugs, 3 runs: 4.03 -> 2.54 requests, 1.35x cheaper, 325 vs 321 right of 342 | `claude-api/` | rows `e1_*`, `f1_r2_*`, `f1_r3_*` |
| safety: 57 misleading lessons taught, 0 answers read from one | `claude-api/` | rows `e3_md.jsonl`; `PROTOCOL_VALUE.md` (E3) |
| 1,854 of 1,865 explorations left a lesson | `claude-api/` | the `at` field of every `*_md.jsonl` row on the teach path |
| research with web search: 2.3x first, 9.8x asked again; deep research 2.2x / 9.4x; tickets 1.3x / 5.4x | `claude-api/` | rows `e6_*`, `f3_*`, `g1_*` (`pass` 1 and 2) |
| seven more codebases: 1.33x and 1.50x; maximum-effort thinking: 1.17x | `claude-api/` | rows `e5_*`, `f4_*`, `g3_*` |
| writing fixes: 16 vs 15 of 19 resolved, $0.197 vs $0.160 per fix | `claude-api/` | `PROTOCOL_VALUE5.md`; report key `V5`; rows `w_*` |
| SWE-QA: 1.90x cheaper at 73.3 vs 75.9 of 100; SWE-ContextBench: 11 vs 12 of 28 | `claude-api/` | `report_retest.json`, `report_sweqa.json`, `report_swecb.json`, `RESULTS_SWEQA_SWECB.md` |
| 31 of 45 predictions held | `claude-api/` | every true/false key in `report_value.json` |
| the turn law: -9% and -4%; the learning formula: -11% | `claude-api/` | report keys `M1 E1`, `M1 V4`, `M3 E2`; `formula/` |
| teaching cost less than working alone (K < A) in 11 of 12 test sets, 1.17x to 1.85x | `claude-api/` | rows: mean cost of the teach path against the alone arm, per set |
| ten years of Django, 5,333 fixes, offline: right file 83.9%; learned ground 42% -> 70% | `replay/` | `RESULTS_REPLAY.md`, `report_replay.json`, `rows_*.jsonl` |
| Gemini 2.5 Flash, 3 runs: a learned question takes 1.0-1.1 requests (vs 5.1-5.4); bill 6-12x lower | `gemini/` | `PROTOCOL_MODEL_D_E2E.md`, `report_e2e.json`, `e2e/` |
| saving grows with the codebase: 1.25x on 148k tokens, 1.71x on 10.8M; 30 of 30 reworded questions land on what was learned | `learning/` | `live-vectors/report_vec.json`, `large-codebase/report_large.json` |
| lessons survive a code move: 38 of 38 re-found across 400 commits | `learning/life/` | `RESULTS_LIFE.md`, `report_life.json` |
| finding the fixed file, 285 SWE-bench Lite issues in 12 full repositories: code scope 176 / 183 top-5 vs Graphify 0.9.87 131 / 122; 5 of 5 predictions held | `swe-bench-lite/` | `PROTOCOL_CODEONLY.md`, `RESULTS_CODEONLY.md`, `codeonly.json`, `graphify_ranked_087.json` |

## What failed
These are reported in the same files as the wins:
- **Code names removed from bug reports:** the accuracy loss replicated (`E4`, `F2`).
- **Writing fixes:** not shown to be cheaper per resolved fix at this sample size (`V5`, SWE-ContextBench).
- **Lessons from past fixes misled 2 tasks** on SWE-ContextBench (`report_swecb.json`, arm `exp`).
- **A kit warmed from commit history did not beat a cold one** (`PROTOCOL_VALUE6*.md`).
- **The learned shortcut in the ten-year replay:** its first pick was right 43% of the time when it fired. Learning
  added 0.6 points of file hit over the frozen layer.
- **The learning curve on Claude Sonnet failed** (S4 and S5 in `learning/swe-sonnet/`). The cause was the issue mix,
  confirmed by three audits.
- **Carrying lessons through the code move saved nothing in the live run** (`RESULTS_LIFE_LIVE.md`).
- **In full repositories, the full-scope readout lost to Graphify on issue titles:** 117 vs 131 top-5. Documentation
  filled about half its top-5 places (`swe-bench-lite/score_087.md`). The code scope was added for this and tested
  against a plan fixed in advance.

- **A team's year, T2 as pre-registered:** 227 vs 253 right. The rule scored a cheap read by the readout's first file. 25 reads that cite the changed file count as wrong under it (D4, `team-year/`).
- **The relation gate (OCM_CERT_MIN_OVER_OWN=37) on a team's year:** read precision was not higher (87% vs 90%), so it stays off by default (G1).

## Not included
- **Agent transcripts and built indexes:** gigabytes; they can be rebuilt with the scripts.
- **The client-app study in `results/RESULTS.md` section 1:** it runs on a client's private code.
- **The run logs.**

`MANIFEST.json` lists each file, where it came from, and its SHA-256. Pre-registered files are copied byte for byte,
so they still match their hashes. Some of them contain the author's home-directory paths. In every other file the
home directory is shortened to `~`.
