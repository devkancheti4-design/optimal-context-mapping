# Coverage: teach Model D the whole codebase once, then ask real questions (written 2026-10-17, before any generation)

## The question
If Model D is taught one question for every piece of source code before anyone asks anything, does it answer new real
questions from what it learned? If so, at which threshold is a learned answer right? And what do its laws do (the
router law, the vector law, the learned law) when nearly everything is taught?

## Data
- **Workspace:** Django at 0ab58c1209 (2022-01-03), `ws/base` of PROTOCOL_TEAM_YEAR (113,271 units).
- **Coverage:** every non-test code unit, 23,976 of them: code scope (not `ocm.units.DOCS`), and not under `tests/` or
  in a file named `test*`.
  - Claude Haiku 5.5 writes one question per unit, in batches of 25, with structured output.
  - Prompt: "the one question a developer on this codebase would ask whose answer is in this block, in the words of a
    bug report or a how/where/why question, at most 25 words".
  - Each question is taught onto its unit with the workspace's own `teach_at` (the vector law's cue vectors). The
    learned law observes every one, as the product does.
- **Real questions:** the 288 kept Django 2022 fixes of PROTOCOL_TEAM_YEAR, each phrased "Where is the code behind this
  change: <subject>". None of them sees the coverage questions, and no coverage question sees a 2022 fix.

## Arms (offline, no model calls after the generation)
- **Cold:** `ws/base` as built.
- **Covered:** a copy, with all 23,976 questions taught.

## Measures, per real question, with code scope
- **The first readout (`routed`):**
  - its first file;
  - the files of its top five items;
  - whether it is led by taught code (the learned lane, `TAUGHT`).
- **The router's readings:**
  - `from_cue`: the top unit's best signal is a cue;
  - `over_own`: the margin m, the cue's agreement minus the best code text's agreement;
  - `cert_lead`.
- **The learned law's state** after coverage.
- **Right:** the first file, or any of the top-five files, is a file the fix changed.
- **The threshold curve:** the precision of taught-led readouts by margin band, with Wilson 95% intervals.

## Predictions (fixed now)
- **V1, ranking holds:** the covered top-5 file hit ≥ cold's.
- **V2, a threshold exists:** taught-led readouts with m ≥ 37 bits are right (first file) at least 60% of the time.
- **V3, coverage is used:** at least 30% of the 288 readouts are led by taught code.
- **Exploratory:** the full threshold curve; the right-first count among taught-led readouts, against cold on the same
  questions.

## Cap
Generation $6. There are no other model calls.
