# A team's year on one codebase: does Model D's bill bend as novelty falls? (written 2026-10-16, before any model call)

## The claim
From the Model D site and its learning law S(n) = A / ((1 − ν(n))·E + ν(n)·K):
- as a team keeps working the same code, novelty ν falls;
- more questions are answered by one cheap read E instead of a full exploration K;
- so the saving over an agent working alone, A, grows.

This test runs the real product on a real team's real year.

## Data
- **Fixes:** Django's own "Fixed #" commits from 2022, in commit order: 290 fixes by Django's engineers.
  - Source: `optimal-context-mapping/evidence/replay/stream.json`, the same file as the published ten-year replay.
  - Kept: every fix with at least one changed file present in the snapshot.
- **Question:** "Where is the code behind this change: <the commit's subject line, as the engineer wrote it>". Both arms
  get the same text.
- **Code:** Django at `0ab58c1209` (2022-01-03), the parent of the year's first fix. It is frozen for the whole year, so
  no fix's code is in the snapshot.
- **Right:** the answer's location (`at`, path:line) is in one of the files that fix changed. For an answer read from
  learned code, the first file of the readout it was read from must be one of them.

## Arms
- **Model D:** the product as shipped. `ocm.hybrid.run` with the Claude provider (`ocm/providers/claude_api.py`):
  - Haiku 5.5 reads learned code with the strict READ prompt;
  - Sonnet 5.5 explores and teaches with the workspace tools (MAX_CALLS 15);
  - one workspace server over the snapshot, cold on 2022-01-03;
  - it learns only from its own explorations, in commit order, sequentially. Nothing from the answers is ever taught.
- **Alone:** Sonnet 5.5 with the same tools on its own server, never taught. Its system prompt is the product's TEACH
  prompt minus the sentence about the workspace's ranked code. The user message is the question only. Its loop is
  identical to the product's teacher loop.
- Neither arm uses prompt caching, as the product ships.

## Measures
- Per question: path (read / teach / alone), right, requests, tokens, dollars at list price (Sonnet $2 / $10, Haiku
  $0.10 / $0.50 per million).
- **Per quarter of the year:**
  - novelty ν (share of questions that took the teach path);
  - E (mean cost on the read path);
  - K (mean cost on the teach path, including a read that fell back);
  - A (mean cost alone);
  - the measured saving A / mean(Model D);
  - the law's predicted saving A / ((1 − ν)E + νK).

## Predictions (fixed now)
- **T1, the bill:** over the year, Model D's total cost ≤ the alone total / 1.5.
- **T2, the work:** Model D's right count ≥ alone's − 3% of questions.
- **T3, novelty falls:** ν in Q4 < ν in Q1.
- **T4, the saving grows:** the measured saving in Q4 > in Q1.
- **T5, the law holds:** in every quarter, the predicted saving is within 15% of the measured one.

## Caps and reporting
- Caps: Model D $8, alone $12. Each arm stops at its cap and reports what it has.
- Every number is reported whichever way it comes out. Deviations go in `PROTOCOL_TEAM_YEAR.md.deviations`.
