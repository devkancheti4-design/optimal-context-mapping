# Results: does the kit save more as it learns? (Claude Sonnet 5.5, real django issues)

Three pre-registered steps: PROTOCOL_SWE_SONNET.md (S4/S5), PROTOCOL_LEARN_SONNET.md (L1–L4) and PROTOCOL_LEARN_FIX.md
(F1–F4). There were also three independent audits, run as workflow agents. One rebuilt every number from the raw files
without my report code, one reviewed the code, and one ran the statistics.

## 1. S4 and S5 failed, and the failure is real
- **Reproduced:** two auditors rebuilt every number from the 235 transcripts and answer files without report.py. Within
  rounding, they got the published values. No scoring or parsing bug.
- **The second half really did cost more:** MODEL D's factor fell from 1.58 to 1.38. The difference interval is
  [-0.39, -0.01], wrong side of zero.
- **The cause is the issue mix.** Second-half issues are ones where even the never-taught kit's readout misses the gold
  file more often: 12 of 57, against 3 of 57 in the first half (p = 0.024).
  - When the gold file is missing, KIT costs 6.46 requests per issue; when it is present, 3.42.
  - Controlling for that, the difference between halves is +0.15 requests [-0.22, +0.51]: about zero.
- **The halves test barely measured learning.** On 86 of 114 issues the learning kit's readout is byte-identical to the
  never-taught kit's, so learning could not change their cost.

## 2. A real defect: lessons were taught at the wrong line
- **The bug:** each lesson was taught at the gold line number of the issue's own base commit, but the workspace is the
  4a72da7 snapshot.
  - 10 lessons were not placed at all.
  - Only 29 of 114 landed on the code holding the fix.
- **Scope:** the Gemini SWE run (PROTOCOL_SWE.md) has the same defect.
- **The fix:** swe_sonnet/readouts_snapline.py maps each gold line to the snapshot with a line diff; all 114 lessons are
  placed.

## 3. Frozen kit vs learning kit, same issues (tool calls the agent made; fewer is cheaper)

| | lessons as run (L test) | lessons placed correctly (F test) |
|---|---|---|
| Issues and replicates | 28, 3 each | 29, 4 each |
| Frozen / learning, all issues | 1.13x [0.89, 1.54] | **1.32x** [0.93, 2.27] |
| Repeat-file issues | 1.10x [0.77, 1.69] | **1.52x** [0.89, 3.70] |
| New-file issues | 1.10x | 1.02x |
| Learning saving by quarter of the stream | 0, 1.3, 1.0, 1.5 | **0, 1.0, 3.25, 4.25** |
| First half vs second half saving | 1.3 vs 2.5 | **1.0 vs 7.5** |
| Right | all attempted sessions right | frozen 116/116, learning 115/116 |

**F-test scores:**
- **F3 holds:** the saving grows across the stream.
- **F4 holds as a point estimate:** 1.52x on repeat files.
- **F1 fails strictly:** the interval includes 1.0.
- **F2 fails by one session:** 115/116 against 116/116.

**Per issue:**
- Where an earlier fix taught the exact place, the agent stops searching.
  - 15814 (#94): 5, 5, 4, 6 calls frozen; 0, 0, 0, 0 learning.
  - 14580 (#69): 3, 2, 2, 3 frozen; 0, 0, 1, 0 learning.
  - 13033 (#42): 2, 0, 2, 2 frozen; 0, 0, 0, 0 learning.
- Two issues went the other way: 15738 (0, 2, 0, 0 against 1, 1, 4, 2) and 16229.
- On 12 of the 29 issues both arms made 0 calls: the frozen kit had already given the agent everything.

## What this means
- **The selling point needs no learning.** On novel bugs, the kit's laws hand the agent the right code before it starts.
  - Sonnet 5.5: 2.0x fewer API-equivalent requests, accuracy 112 against 111.
  - Gemini Flash: 1.72–1.94x, accuracy 84 to 93–94.
- **Learning adds on top where work repeats.** With lessons placed correctly, the saving grew quarter by quarter (0 to
  4.25 calls) and reached 1.52x on repeat-file issues.
  - On this bug stream it is not yet statistically conclusive, because the frozen kit is already at the floor on many
    issues.
  - On repeated questions (Gemini stream, 3 runs) learned questions cost 1.0–1.1 requests and about 1.3k tokens. The agent
    alone needed about 5 requests and 120k–140k tokens.
- **Caveats:** the 13 sessions that declined in the L test are excluded (DL1); none declined in the F test. One django
  snapshot. File localisation only.
