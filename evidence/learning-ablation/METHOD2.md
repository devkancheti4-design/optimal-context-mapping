# Two fixes for taught pointers that crowd out the right code (written 2026-10-19, before any readout)

**Prompted by:** the replay in METHOD.md. After a year of real teaching, Django's 288 questions were right first 84
times against 111 cold, and in the top 5 107 against 197. Taught pointers led 181 readouts, each with a single item.

**Fixes (applied in the experiment by patching, not yet in the product):**
- **F1, a taught readout keeps the normal top 4.** A taught-led readout lists the taught item first, then the
  meaning-and-keyword lane's items, up to five, without repeats. The header still says it is taught-led, so the
  product's read path is unchanged.
- **F2, the relation gate.** `OCM_CERT_MIN_OVER_OWN=37`: a taught pointer leads only when its cue beats the code's own
  text by 37 bits (one sd of chance agreement).
- **Arms:** base, F1, F2, F1+F2.

**Test sets (offline, no model calls):**
- **B, new questions after real teaching:** the team-year replay of METHOD.md (288 fixes in order; each read, then its
  real submitted line taught).
- **R, repeated questions:**
  - SWE-bench Lite Django's 114 issues at snapshot 4a72da7 (`claude-api/inputs/issues.json`), in a cold 0.5.0
    workspace.
  - Each issue text is taught onto its true line (`file:line` in issues.json). Then each reworded report
    (`paraphrases.json`) is asked.
  - This is the "asked again in other words" case the website claims 5-10x on.
- **A, coverage:** the covered workspace (23,770 taught questions), the 288 questions.

**Measures:**
- right file first and in the top 5, for each set and arm;
- for R, also taught-led and right.
- Exact McNemar against base.

**Predictions:**
- **P1:** B, F1 top 5 > base (107).
- **P2:** B, the best fix arm right first ≥ 100.
- **P3:** R, no fix arm loses more than 5 right-first of base on the reworded questions.
- **P4:** A, no fix arm loses more than 5 right-first of base (149).

## Addendum, after the four arms (2026-10-19)
- **Results:** F1 lifted the top 5 (B 107 → 163, A 193 → 219) and kept repeats (R 109/114 right first). P1, P3 and
  P4 held.
- **P2 failed:** right first on B stayed at 84 in every arm. With F2, 40 fewer readouts were taught-led, yet right
  first did not move. So taught cues must also bias the meaning ranking itself, where a unit's strong score is its
  best taught cue.
- **F3, the relation limit:** `OCM_RELATION_LIMIT=37`. Taught cues count for a question only if the best of them beats
  the best code text by 37 bits; otherwise the code alone ranks it. Arms F3 and F1+F3, on the same sets.
- **Prediction P5:** B, F1+F3 right first ≥ 100, with R right first ≥ 104.
