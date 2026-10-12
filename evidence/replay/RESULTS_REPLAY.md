# Results: ten years of Django engineers' fixes through one shared kit (PROTOCOL_REPLAY.md)

- **Protocol:** sha256 7ace11fe…10e6, fixed before running.
- **Data:** 5,333 "Fixed #" commits, 2013-01-02 to 2023-07-06, many contributors, replayed in commit order through the
  kit.
- **Offline:** no model calls; nothing downloaded. Rows are in rows_*.jsonl; report_replay.json is made by
  report_replay.py.

## The laws alone: the core brain, before any learning
- **Within about 5 files of readout, the frozen kit showed the right file:**
  - on **83.9%** of questions phrased as the engineers wrote them (77% in 2013 → 88% by 2021–23);
  - on **49.2%** with every code name removed.
- **Dumb baselines with the same budget:**
  - the 5 most-touched files so far: 13.9%;
  - the 5 most recently touched files: 9.1%.
- **R1 holds:** the frozen kit's hit is at least 60% on RAW questions.

## Learning: novelty dies, the saving rises, and precision is the limit

| Decile (date range) | Frozen hit | Learning hit | Shortcut fires | Shortcut first pick right | Projected hybrid saving (requests) |
|---|---|---|---|---|---|
| 1 (2013) | 0.773 | 0.780 | 0.424 | 0.350 | 1.70x |
| 5 (2015–16) | 0.846 | 0.833 | 0.649 | 0.390 | 1.79x |
| 10 (2021–23) | 0.884 | 0.903 | 0.697 | 0.522 | 1.92x |
| All 5,333 | 0.839 | 0.845 | 0.629 | 0.428 | 1.81x (realistic 1.58x) |

- **R2 holds:** learning beats frozen overall, and its advantage grows from +0.7 to +1.9 points.
- **R5 holds:** on MASKED questions, the advantage grows from +1.5 to +3.7 points and the shortcut rate from 0.56 to
  0.70.
- **R3 fails:** the taught shortcut fires on more and more questions (42% → 70%: novelty dying), but its first pick is
  right only 43% of the time (35% → 52%).
- **R4 fails:**
  - the projected hybrid cost per question falls over the decade (2.07 → 1.83 requests), so the saving rises from 1.70x
    to 1.92x;
  - but it does not reach 2.0x overall (1.81x).
- **Projected dollars:**
  - laws only: 1.49x;
  - hybrid, pre-registered rule: 2.26x;
  - hybrid, realistic rule (the cheap read falls back to search whenever the shortcut's first pick is wrong): 1.85x.
- **Repeat tickets:** excluding the 81 questions whose ticket was fixed in an earlier commit changes nothing (shortcut
  rate 0.415 → 0.695).

## What to improve next
The shortcut fires often but is wrong more than half the time. A confidence gate would let the cheap read take only the
shortcuts the kit is sure of, which raises the hybrid's saving without cost. That needs a pre-registered test of its own.

## Caveats
- **The questions are commit subjects,** which name the code more than real tickets do. MASKED is the conservative
  bound.
- **The lessons go on the line of the gold file with the most word overlap,** not the exact changed line (the clone has
  no file contents).
- **The costs are projections:** measured hit and shortcut rates times the conditional costs measured on Sonnet 5.5's
  114 real bugs.
