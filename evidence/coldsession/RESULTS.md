# ColdSession: results (2026-11-06)

Model D 0.5.3 as released, end to end (`ocm.hybrid.run`), on `reflex`, `scikit-learn` and `sphinx`. Model: `gemini-3.5-flash-lite`, temperature 0. Plan: `PROTOCOL.md`, hashed before any model call, with seven
deviations in `PROTOCOL.md.deviations` (the cap went from $5 to $8.50; three harness bugs and one grading error were fixed; one bug had hurt Model D; the order of the arms changed). `report.txt` has every number here.

**Spent:** $7.95, when the account's credits ran out. Every arm finished on all three repositories except the notes file, which finished on `reflex` and `scikit-learn` only. `sphinx`'s notes arm is reported as not run.

**Model D has the lowest tokens per right answer in every session, but it failed the pass conditions set before the run.** The map saves a lot. On heavily reworded questions, memory adds right answers rather than saving tokens.

## Tokens per right answer

All three repositories, 20 taught facts each. An arm with no memory runs only sessions 2 and 4.

| session | Model D | right | memory off | right | agent alone | right |
|---|---|---|---|---|---|---|
| 1. first time | **37,098** | 78.3% | – | | – | |
| 2. next day | **42,836** | 81.7% | 53,272 | 70.0% | 95,500 | 73.3% |
| 3. teammate | **43,130** | 71.7% | – | | – | |
| 4. a year later | **61,458** | 63.3% | 89,595 | 58.3% | 151,468 | 61.7% |
| 5. with 200 more lessons | **33,651** | 76.7% | – | | – | |

Same facts, Model D against the agent alone (95% bootstrap intervals over facts):

| | Model D's tokens, as a share of the agent's | right, Model D minus the agent |
|---|---|---|
| first time (the agent's session 2 stands in) | 0.41x | +5.0 points (-10.0 to +20.0) |
| next day | 0.50x (0.36 to 0.65) | +8.3 points (-1.7 to +18.3) |
| a year later | 0.42x (0.31 to 0.53) | +1.7 points (-10.0 to +13.3) |

## Against the notes file

`reflex` and `scikit-learn` only, 40 facts per session.

| session | Model D tokens per question | right | notes tokens per question | right | Model D's tokens as a share of notes | right, notes minus Model D |
|---|---|---|---|---|---|---|
| 1. first time | **21,569** | 82.5% | 47,054 | 80.0% | 0.46x (0.30 to 0.63) | -2.5 points (-12.5 to +7.5) |
| 2. next day | **35,816** | 75.0% | 44,977 | 70.0% | 0.80x (0.57 to 1.04) | -5.0 points (-22.5 to +12.5) |
| 3. teammate | **28,063** | 70.0% | 43,563 | **87.5%** | 0.64x (0.40 to 0.96) | **+17.5 points (+7.5 to +30.0)** |
| 4. a year later | **43,741** | 57.5% | 71,230 | **75.0%** | 0.61x (0.45 to 0.80) | **+17.5 points (+7.5 to +30.0)** |
| 5. with 200 more lessons | **31,660** | 70.0% | 90,208 | 80.0% | 0.35x (0.24 to 0.45) | +10.0 points (-2.5 to +22.5) |

Model D stays flat as lessons pile up; the notes file doubles. The notes file is right more often later on. The agent doesn't simply trust its notes: it went on searching, at about 9 requests per question.

## Predictions

| | result | |
|---|---|---|
| P1, first time: at most half the agent's tokens, right within 5 points | 0.41x, +5.0 points | held |
| P2, next day: at least 60% in one read, at most a fifth of the agent's tokens, right within 5 points | **20%**, **0.50x**, +8.3 points | **failed** |
| P3, teammate: at most 1.25x session 2's tokens, right within 5 points of it | 0.88x, **-10.0 points** | **failed** |
| P4, a year later, facts that stayed true: at least 40% in one read, at most half the agent's tokens, right within 5 points | **31%**, 0.42x, +5.6 points | **failed** |
| P5, changed facts: Model D stale on at most 10%, notes on at least 50% | **12.5%**, **18.8%** | **failed** |
| P6, against Model D: the notes file uses fewer tokens next day | Model D used 0.80x the notes file's tokens | **failed, in Model D's favour** |
| P7, 200 more lessons: fewer tokens than notes, right within 5 points | 0.35x, **-10.0 points** | **failed** |
| P8, what memory adds: at most half of memory-off's tokens next day | **0.94x**, right +11.7 points | **failed** |

**Model D needed P2, P3, P4, P5 and P7 to pass. All five failed.** My estimate before the run was 1 chance in 3.

## What memory does

Next-day tokens per question: agent alone 70,034, memory off 37,290, memory on 34,983. So most of the saving is the map. Memory on against memory off, same facts: next day 0.94x the tokens and +11.7 points right (+1.7 to +21.7); a year later 0.74x the tokens (0.58 to 0.94) and +5.0 points (-6.7 to +16.7). Model D's next day used more tokens than its first time (34,983 against 29,060), though the wordings differ.

**When the question names the code, memory saves a lot.** Next-day control, 12 questions: Model D 4,108 tokens, 1.75 requests, all right; agent alone 9,577 and 11 of 12 right; memory off 12,857 and all right; notes 9,724 on 8 questions, all right.

**With perfect lessons and no model (`landing_report.txt`),** the lesson brings the fact into a readout of about 650 tokens far more often than the map alone. Over the 60 taught facts:

| session | lesson opens | fact in the readout with lessons | without lessons |
|---|---|---|---|
| next day | 53.3% | **66.7%** | 30.0% |
| teammate | 61.7% | **73.3%** | – |
| a year later, same facts | 50.0% | **57.1%** | 14.3% |
| a year later, moved facts | 50.0% | 62.5% | 25.0% |
| a year later, changed facts | 37.5% | 50.0% | 20.8% |
| with about 200 more lessons | 55.0% | **75.0%** | – |

More lessons on disk didn't lower it. Named control: 100% with lessons, 58.3% without. New questions got little: 22.2% with lessons, 16.7% without.

**With the agent's own lessons (`leak.txt`, `funnel.txt`),** on each session's map before that session taught anything, of 60:

| session | lesson opens | it brings the fact's line | answered in one read | had the line but searched anyway |
|---|---|---|---|---|
| next day | 30 | 21 | 12 | 10 |
| teammate | 40 | 29 | 19 | 12 |
| a year later | 33 | 27 | 15 | 12 |

Three leaks of similar size: heavily reworded questions don't open the lesson; the agent's lessons are imprecise (it cited within 3 lines of the fact on 33 of 60); and this cheap model often searches although it has the line. This is one cheap model, and a stronger reader might behave differently. That hasn't been tested here.

## Staying true

**Real facts rarely change** (`rates.json`, all 15 SWE-QA repositories, a year): 14 of the 15 have 0.0% to 1.6% changed, 0.3% overall. `reflex` has 46%, from a restructure.

**Lessons through a year of real commits.** Perfect lessons without a place by T2: `reflex` 6 of 24, `scikit-learn` 6 of 24, `sphinx` 3 of 23, so 79% kept. The agent's own: 41 of 217 without a place, so 81% kept. None was lost on a teammate's build. A lesson follows its exact line, so editing that line drops it: on the development repository `requests`, adding type hints dropped 12 of 24.

**Session 4 by what happened to the fact** (the notes file on 2 repositories):

| | Model D right / stale / tokens | notes | memory off | agent alone |
|---|---|---|---|---|
| same | 75.0% / 0% / 29,522 | 72.2% / 0% / 60,570 | 64.3% / 0% / 46,175 | 67.9% / 0% / 90,956 |
| moved | 50.0% / 0% / 75,108 | 83.3% / 0% / 125,329 | 50.0% / 0% / 88,223 | 50.0% / 0% / 106,486 |
| changed | 54.2% / 12.5% / 37,830 | 75.0% / 18.8% / 62,935 | 54.2% / 12.5% / 47,380 | 58.3% / 16.7% / 91,902 |

At each repository's real mix of same, moved and changed: Model D right 73.1%, stale 0.2%, 53,276 tokens per right answer; memory off 66.9%, 0.2%, 83,760; agent alone 71.0%, 2.1%, 136,655. On the 2 repositories with notes: Model D 64.8%, 0.3%, 72,816; notes 80.5%, 3.1%, 89,720.

Two of Model D's three stale answers are deprecation placeholders (`enet_path` `n_alphas`, `CalibrationDisplay.from_predictions` `n_bins`), where the old number stays in effect and every arm said the same. The third missed a newly added parent class. With no code and no tools at all, the model got 25% of these questions right.

## Limits

- We designed this benchmark and our tool is in it, so it counts for less than a third party's.
- 3 repositories, 20 taught facts each, one run of each arm, one cheap model; the notes file on only 2 repositories.
- Lookup questions with one checkable answer, in Python, reworded by a model to avoid the code's names, which is hard on lessons. Real questions may keep more names.
- Facts are sampled evenly from public definitions, with changed facts oversampled.
- The first-time comparison uses the agent's session 2, with different wordings.
- The notes file is the simple version: everything read back every time, marked as possibly out of date.

## Files

`report.txt` every table, `landing_report.txt` perfect lessons, `funnel.txt` and `leak.txt` the agent's own lessons, `results/` every answer, `data/` every fact and wording, `rates.json` how often facts change, `results/bug_mate_path/` the `reflex` answers set aside by deviation D5.
