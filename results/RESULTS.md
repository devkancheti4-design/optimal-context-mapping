# Results

Every test below was run live with fresh Claude agents (the same model and the same instructions in both arms, except
the tools section), graded by blind judges who did not know which arm wrote an answer, and fixed in writing (with a
SHA-256 hash of the plan) before it ran. Costs come from the agents' own transcripts (model requests, input billed) and
the tool servers' logs. Deviations were recorded as they happened. The full evidence (protocols with their hashes,
questions, every answer, every verdict, call logs) is available on request.

## 1. A project team on a real codebase plus web research
Seven role agents (project manager, team lead, senior developer, backend developer, frontend developer, junior
developer, HR) did Phase-1 research for a project on a real client app (React + TypeScript, 63 files) and 62 web pages.
41 questions, written and independently verified (45 of 63 kept). Each condition was run with fresh agents:

| team | right | model requests | searches and reads | billed input (cache-weighted) |
|---|---|---|---|---|
| each role alone (run 1) | 41/41 | 138 | 122 | 1,054,776 |
| each role alone (run 2) | 41/41 | 141 | 123 | 1,063,918 |
| shared workspace, a note taught after every answer | 41/41 | 117 | 57 | 1,003,603 |
| **shared workspace, notes taught once per role (batched)** | **41/41** | **84** | **58** | **756,142** |

Batched teaching: **1.66x fewer requests** and **1.40x less billed input** than working alone, the same accuracy. Two
alone runs differed by 2%. Later roles gained most (the senior developer did 6 searches and reads instead of 21).

**The arithmetic, tested before the run.** Requests = searches and reads + teach calls + a fixed per-session overhead.
Frozen before the batched run: 83 requests (68 to 98), 1.66x (1.4 to 2.0), billed 1.48x (1.2 to 1.8). Measured: 84,
1.66x, 1.40x. `python -m ocm calc` is this arithmetic.

## 2. Seven codebases, single-fact questions
About 1M tokens from each of transformers, torch, scipy, pandas, sympy, scikit-learn and numpy (7M tokens, 133,875
units); 28 first-time questions, 4 per codebase.

| per right answer | Claude with search | one shared workspace | one workspace per codebase + overseer |
|---|---|---|---|
| right | 28/28 | 28/28 | 28/28 |
| model requests | 2.36 | **0.39** (6.1x fewer) | 1.11 (2.1x fewer) |
| billed input, cache-weighted | 16,370 | **5,766** (2.8x less) | 12,884 |

One workspace over everything beat one per codebase: the overseer sent 8 of 28 questions to the wrong codebase first.

## 3. One large codebase, first-time and repeated questions
The transformers library at two sizes (1.1M and 10.8M tokens). 30 questions, then the same 30 facts asked again in new
words by a different agent after the first one taught.

| tools / workspace, per right answer | 1.1M first | 1.1M repeat | 10.8M first | 10.8M repeat |
|---|---|---|---|---|
| model requests | 7.0x | 7.9x | 3.6x | **9.2x** |
| billed input, cache-weighted | 3.6x | 3.5x | 2.0x | 3.9x |
| right (each arm) | 30/30 | 30/30 | 30/30 | 30/30 |

## 4. Multi-file deep dives (the weak spot)
20 verified questions, each needing 2 to 3 files, on the 10.8M-token codebase, with the router law:
40/40 right in both arms; 1.17x fewer requests and 1.21x less billed input. A taught note covers one answer, not a whole
trail, so repeated deep dives were not cheaper.

## 5. Text research (earlier tests)
A stream of 120 research questions over 1M to 9M tokens of text: the same accuracy, 3 to 5x fewer requests; on repeated
questions 1.7 to 1.8x fewer tokens and 4.5 to 9.1x fewer requests.

## What it predicts for a team (`python -m ocm calc`)

| repeat share | lookups only | with 30% deep dives |
|---|---|---|
| 0% | 2.39x fewer requests (2.03 to 2.84) | 1.56x (1.37 to 1.79) |
| 50% | 3.17x (2.83 to 3.57) | 1.63x (1.47 to 1.82) |
| 90% | 4.33x (3.91 to 4.78) | 1.69x (1.47 to 1.97) |

95% bootstrap intervals over 395 measured question-runs (`python -m ocm calc --table` reproduces this table exactly).
At 16,800 questions a month (40 engineers x 20 a day x 21 days, an assumption), lookup work makes about 27,700 to
36,000 fewer requests a month. Projections, not a live test at that size.

## Limits
- One run per condition in most tests; questions written by Claude; judges Claude; open-source code, one client app
  and Wikipedia pages. Your codebase and your team are the real test: see `pilot/`.
- Billed input falls less than requests; deep dives save little; notes are append-only.
- Agents sometimes broke instructions (piping tool output through grep); every case was counted and reported.
