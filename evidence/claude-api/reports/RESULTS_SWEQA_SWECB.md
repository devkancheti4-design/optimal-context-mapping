# Results: SWE-QA and SWE-ContextBench (2026-10-09)

Protocols: PROTOCOL_SWEQA.md and PROTOCOL_SWECB.md (hashed in prereg_hashes.json before any request), with
deviations in *.deviations (DQ1, DQ2 and DCB1, DCB2; none of them changes what was measured). Numbers come from
value/report_sweqa.json and value/report_swecb.json (`python value/stats_bench.py qa|cb`).

## SWE-QA: repository Q&A, 7 repositories, 336 questions, graded blind with SWE-QA's own rubric

Repositories: sqlfluff, sphinx, requests, xarray, pylint, django and astropy. The run stopped before pytest, by the
budget rule fixed in advance.

| | Sonnet alone | Model D 0.2.1 |
|---|---|---|
| $ per question | 0.0522 | 0.0236 |
| requests per question | 4.02 | 2.87 |
| judged total /100 | 65.33 | 61.04 |

- **Cost:** ALONE/MODEL D = **2.22x** (95% CI 1.95-2.55).
- **Score:** MODEL D - ALONE = **-4.28** (95% CI -5.26 to -3.34).
- **Per dimension (/20), alone vs Model D:**
  - correctness 13.45 vs 12.87
  - completeness 9.89 vs 8.52
  - relevance 15.35 vs 14.84
  - clarity 15.21 vs 14.78
  - reasoning 11.42 vs 10.04
- **Answer length:** Model D's answers are shorter: 589 vs 763 characters on average.
- **Score gap by how Model D answered:**
  - reader (11 answers): -13.5
  - 1 request: -6.5
  - 2 requests: -3.5
  - 3 or more: -4.0
- **Predictions:**
  - Q1 (ratio at least 1.3x): held.
  - Q2 (no more than 3 below): **failed**, at -4.3.
  - Q3 (saving grows, 2.06x then 2.41x): held.
  - Q4 (reader under 20%, 11 of 336): held.
- **Per repository**, $ alone / $ Model D and score alone / score Model D:

| Repository | $ alone | $ Model D | Score alone | Score Model D |
|---|---|---|---|---|
| sqlfluff | 2.84 | 1.08 | 64.0 | 60.4 |
| sphinx | 2.80 | 1.15 | 63.5 | 60.3 |
| requests | 1.01 | 0.65 | 72.1 | 68.3 |
| xarray | 1.26 | 0.85 | 69.0 | 65.4 |
| pylint | 4.61 | 1.47 | 56.4 | 52.3 |
| django | 1.95 | 1.05 | 67.4 | 58.9 |
| astropy | 3.08 | 1.66 | 64.9 | 61.6 |

- **In one line:** 93% of Sonnet's judged quality at 45% of the cost.
- **Not compared:** the paper's published scores, which used a different judge, scale and models.

## SWE-ContextBench Lite: Django related tasks that validate locally (28 of 36), writing the fix, Django's tests

| | resolved | $ per task | $ per resolved | requests per task | readout named a gold file |
|---|---|---|---|---|---|
| ALONE (no kit) | 12/28 | 0.116 | 0.270 | 6.61 | n/a |
| COLD (kit, nothing taught) | 13/28 | 0.149 | 0.322 | 6.29 | 23/28 |
| EXP (kit taught 114 experience fixes) | 11/28 | 0.133 | 0.338 | 6.21 | 24/28 |

- **Learned matches:** EXP's readout led with a learned match on 11 tasks.
  - On those 11, EXP resolved 2 and COLD resolved 4.
  - On the other 17, both resolved 9.
- Experience placed by the kit itself, from other issues' fixes, misled the fix on 2 tasks. The paper found the same
  for unfiltered experience.
- **Predictions:**
  - C1 (EXP at least ALONE): **failed**.
  - C2 (EXP at least COLD): **failed**.
  - C3 (EXP cheaper per resolved fix): **failed**.
  - C4 (EXP names gold more than COLD): held, 24 vs 23, which is a trivial margin.
- **What this sample can show:** differences of 1-2 tasks out of 28 are within noise. The firm findings are that
  experience did not help, and that the kit's readout found the right file on 82-86% of tasks at zero tokens.
- **Scoring check** (scratchpad cbdiag.py, on three tasks every arm failed): the patches applied, the tests ran, and
  the FAIL_TO_PASS tests genuinely failed.

**Spend:** SWE-QA $29.70, SWE-ContextBench $11.14. Ledger total after both: $183.45 of the $200 credit.

## Retest (PROTOCOL_RETEST, 2026-10-10): prompt caching on every request; on SWE-QA, the same answer standard for both arms

**R1: SWE-ContextBench, the same 28 Django tasks**

| | resolved | $ per task | requests per task |
|---|---|---|---|
| ALONE | 12 | 0.0601 | 6.89 |
| COLD (Model D's kit) | 11 | 0.0627 | 5.93 |

- RC1 (COLD's cost no more than ALONE's): failed, at +4%.
- RC2 (COLD resolves at least ALONE's count less 1): held.
- Caching halved both arms' cost. The kit cut requests by 14%, and its readout's tokens offset that saving.

**R2: SWE-QA, sqlfluff, sphinx and requests.** The $8 budget stopped the run after 30-33 questions per repository,
which gave 91 graded pairs (2 Model D answers stopped by the cap were left out). Grading cost $1.37 under its own
$2 cap, `rt_judge.py`.

| | $ per question | judged /100 | answer chars |
|---|---|---|---|
| ALONE | 0.0447 | 75.92 | 2,188 |
| Model D | 0.0235 | 73.27 | 1,909 |

- Cost: **1.90x cheaper** (RQ1, at least 1.5x: held).
- Score: **-2.65** (95% CI -4.07 to -1.26). RQ2 (no more than 2 below): failed.
- The gap narrowed from -4.3 to -2.65, and Model D is now at 96.5% of ALONE's score.

Ledger after the retest: $196.33 of the $200 credit.

## Investigation, no API (value/investigate_law.py, investigate_split.py): where the kit saves and where it does not

The turn law T = rP + g r(r-1)/2 is fitted on every run.
- r: requests.
- P: first-prompt tokens.
- g: tokens added per turn.
- phi = (r_alone - r_D) / (r_alone - 1): the share of the model's exploration turns that the kit's decision removed.

| run | turns alone -> D | phi | growth per turn g | cost |
|---|---|---|---|---|
| company repo, V4 (3 runs) | 3.1 -> 2.0 | 0.49-0.57 | 2,800 -> 1,000-1,260 | 2.66-2.93x |
| SWE-QA, 7 repos | 4.02 -> 2.87 | 0.38 | 3,163 -> 1,660 | 2.22x |
| SWE-QA retest (caching) | 4.33 -> 3.10 | 0.37 | 4,317 -> 1,731 | 1.90x |
| ContextBench fixes | 6.61 -> 6.29 | 0.06 | 1,894 -> 2,584 | 0.78x |
| ContextBench fixes (caching) | 6.89 -> 5.93 | 0.16 | 2,077 -> 2,264 | 0.96x |

- **The rule:** with these runs' own P, g and readout size, 1.5x needs phi of about 1/3, in Q&A and in fixes alike.
  - Q&A meets it. There the kit's decision replaces the search turns, which carry the big outputs (search hits and
    reads), so g halves too.
  - Fixes do not. 33 of 36 issues already name the code (tracebacks, function and class names; 16 of the 28 name the
    fixed file's path or the function the fix sits in), so Sonnet's first search lands on the place. The turns that
    remain are reading, editing and verifying, which the kit does not replace.
  - SWE-QA questions are mostly in plain words (272 of 720 name an identifier), which is why "where" is expensive
    there.
- **Split by whether the issue names the code (ContextBench):**
  - names it: 0.68x (no caching), 0.87x (caching);
  - does not name it: 0.91x, 1.07x.
- **The shipped product:** Model D 0.2.1 has no fix-writing mode. `ocm.hybrid.run` ends in an answer and a
  path:line. The fix arms used the harness prompt from V5.
