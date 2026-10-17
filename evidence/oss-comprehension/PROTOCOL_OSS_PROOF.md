# Proof on a project Model D has never seen: bluesky-social/social-app (written 2026-10-17, before any model call)

## Why this project
bluesky's social-app (TypeScript, about 18k stars) already pays for Claude on its own repository:
- `.github/workflows/claude-mention.yml` answers @claude in pull-request comments;
- `.github/workflows/claude-review.yml` reviews every pull request with `anthropics/claude-code-action`.

It is a different language and a different team from the Django year that calibrated the forecast.

## The forecast, from history only, fixed before any model call (`forecast.json`)
- **Fixes:** its 150 earliest fix commits of the year 2025-10-19 → 2026-10-14 (by `history.py`), each keeping at least
  one changed file present in the snapshot. In commit order, they run 2025-10-19 → 2026-08-06.
- **File repetition:** r = 0.447 over the window (0.293 in the first half, 0.600 in the second).
- **The law, calibrated on Django 2022 (evidence/team-year):** S = 1 / ((1 − ν)·E/A + ν·K/A), with ν = 1 − c·r,
  c = 0.23, A/K = 1.80 and E/A = 0.0044.
- **Forecast saving: 2.00x** (1.91–2.16 across c = 0.13–0.38). By half: 1.93x, then 2.09x.

## Run (the PROTOCOL_TEAM_YEAR harness, unchanged: scripts/team_year.py)
- **Code:** social-app at `f3b6d85913` (the parent of the window's first fix), frozen for the whole window.
- **Question:** "Where is the code behind this change: <the commit's subject line>".
- **Model D:** the product as shipped (`ocm.hybrid`, Claude provider: Haiku 5.5 reads, Sonnet 5.5 explores and
  teaches), on one workspace server, code scope, cold at the snapshot, learning only from its own explorations, in
  commit order.
- **Alone:** Sonnet 5.5 with the same tools, never taught. It may run in parallel shards, since it never learns.
- **Right:** decided this time before the run (the lesson of D4 in the team year):
  - an explored answer is right if its `at` file is a changed file;
  - a read answer is right if its text cites a changed file;
  - the old first-file rule is reported too.

## Predictions
- **O1, the forecast:** the measured saving (alone $ / Model D $) is within ±15% of 2.00x, so in [1.70, 2.30].
- **O2, the work:** Model D's right count ≥ alone's − 3% of the questions.
- **O3, learning over time:** the saving on the second 75 fixes > on the first 75.
- **O4, novelty falls:** Model D's teach share on the second 75 < on the first 75.

## Caps and reporting
- Caps: alone $14, Model D $8. An arm that reaches its cap stops and reports what it has.
- Every number is reported whichever way it comes out. Deviations go in `PROTOCOL_OSS_PROOF.md.deviations`.
