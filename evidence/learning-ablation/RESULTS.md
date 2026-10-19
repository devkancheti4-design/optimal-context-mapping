# Results: what the learning in Model D does, and two fixes shipped in 0.5.1 (METHOD.md, METHOD2.md)

Prompted by a reviewer's question: what share of the saving comes from learning, and does the learned law matter?

## Where Django's 2.09x comes from (team-year rows, 285 paired fixes)
- **The saving:** 2.09x, bootstrap 95% interval 1.84x–2.39x (10,000 resamples of fixes, seed 0).
- **85% of the dollars saved come from retrieval.** On the 245 fixes Model D still explored, it was 1.92x cheaper than
  Claude alone, because the readout came first.
- **15% come from memory.** 40 fixes were answered by one read ($0.0004) of code an earlier question had pinned.
  Priced as explorations instead, the year would have been 1.80x.
- **The learned law stayed off all year.** Its prequential gate never let it in.

## The learned law, forced on (METHOD.md)

| | right file first | top 5 |
|---|---|---|
| A, coverage workspace: law on / forced off | 149 / 150 | 193 / 192 |
| B, team year replayed: forced on / as shipped | 84 / 84 | 107 / 107 |

- **Its contribution is nil:** on against off was 6 against 7 (p = 1.0) on A, and identical on B.

## The bigger finding, and the fixes (METHOD2.md)
After a year of real teaching (B), right-file-first on new questions fell from 111 (cold) to 84, and the top 5 from
197 to 107. Two causes:
- **Taught pointers led 181 readouts,** each with a single item.
- **Taught cues also biased the meaning ranking.**

| arm | B: new questions after a year (first / top 5) | R: reworded repeats, of 114 | A: coverage |
|---|---|---|---|
| cold, nothing taught | 111 / 197 | — | 111 / 197 |
| 0.5.0 | 84 / 107 | 109 / 111 | 149 / 193 |
| F1: the taught item, then the normal top 4 | 84 / 163 | 109 / 113 | 149 / 219 |
| F2: the relation gate, 37 bits | 84 / 128 | 109 / 113 | 149 / 195 |
| F3: the relation limit, 37 bits | 99 / 139 | 107 / 108 | 149 / 195 |
| **F1 + F3 = 0.5.1 defaults** (`run_product.py`, the shipped code) | **99 / 176** | **107 / 108** | **149 / 219** |

**0.5.1 against 0.5.0 (exact McNemar):**
- B: right first 21 against 6 (p = 0.006); top 5 72 against 3 (p < 1e-17).
- R: right first 2 against 4 (p = 0.69, unchanged).
- A: top 5 27 against 1 (p = 2e-7).

**0.5.1 against cold on B:**
- right first 21 against 33 (p = 0.13, not significant);
- top 5 16 against 37 (p = 0.005), still below cold.

**Predictions:**
- **P1 held:** F1 top 5 163 > 107.
- **P2 failed:** right first stayed at 84 in the first four arms.
- **P3 held:** repeats kept.
- **P4 held:** coverage kept.
- **P5 failed by one:** 99, with 100 needed. The repeats part held.

## What it means
- **Memory is real and works on repeats.** A reworded question lands on the learned pointer: 107 of 114 right first.
- **It does not make Model D better at brand-new questions.** In 0.5.0 it made them worse. 0.5.1 recovers most of
  that loss, but new questions after heavy teaching still trail cold on the top 5.
- **The learned law is experimental.** It is off by its own gate, and forced on it changed nothing.
