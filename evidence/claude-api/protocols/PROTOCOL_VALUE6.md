# PROTOCOL_VALUE6: teach the kit the basics first, then the scattered bugs (fixed before any request)

The user's claim: a kit taught the basics of a codebase takes more of the expensive decisions, so it saves more even on
scattered bugs. Prices, MODEL D, scoring, statistics and the $175 cap are as in PROTOCOL_VALUE.md.

**The basics: Django's own fix history**
- Every "Fixed #" commit in replay/stream.json dated before 2019-01-30 (the earliest of the 114 bugs).
- Kept when every file it changed exists in the snapshot's corpus.
- Each one is taught to a copy of swe/ws_base, through the kit's own teach endpoint, with no model calls:
  - the question is the commit subject;
  - the line is the one in its changed files sharing the most words with the subject (the replay's rule).
- None of the 114 fixes exist before that date, so no answer can leak.

**Runs**
- Two runs of MODEL D (the shipped `ocm.hybrid.run`, Claude provider), each on a fresh copy of the warm workspace,
  learning on, over E1's 114 reports in order.
- Baselines:
  - cold MODEL D: E1 and F1 runs 2 and 3;
  - ALONE: the same three runs.
- Per-issue means across runs. Intervals by paired bootstrap over the 114 issues (20,000, seed 20261008).

**Predictions**
- K1: warm MODEL D costs less per bug than cold MODEL D (interval above 1.0).
- K2: warm MODEL D's cost saving against ALONE is at least 1.5x. Cold was 1.35x.
- K3: warm MODEL D's mean right per run is within 5 of ALONE's.
- K4: warm MODEL D's read path fires on at least 10 of the 114 per run. Cold fired on 2.
