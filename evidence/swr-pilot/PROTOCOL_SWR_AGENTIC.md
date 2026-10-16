# SWR-Bench, the product test: an exploring reviewer, alone and with Model D (written 2026-10-16, before any C or D review)

## The claim being tested (from the Model D site)
Model D fuses a deterministic kit with the Claude API. The kit maps the code once and takes the expensive decisions
(where to look) at zero model cost. Claude reads what the kit chose and explores only what is new. The claim is the same
quality at a lower bill. So the comparison is against an agent that explores the repository on its own, not against a
reviewer that never explores (arms A and B, PROTOCOL_SWR_PILOT.md).

## Data
The same 100 PRs as the pilot (`pilot_set.json`, seed 20261016; 50 with issues, 50 clean), the same benchmark file, and
the same ground truth.

## Arms (same model, same tools, same cap; the only difference is Model D's readout)
- **C, agent alone.** Claude Sonnet 5.5 reviews the PR. It has the tools of Model D's own workspace server, implemented
  exactly as `ocm/server.py` serves them, over the same file list that Model D indexes (`ocm.units.files`):
  - `search`: a case-insensitive regex over every line, first 40 hits;
  - `read_file`: up to 200 lines;
  - `list_files`: first 300.

  The repository is checked out at the PR's `base_commit`. It also has `submit_review`, and at most 15 tool calls (the
  product's MAX_CALLS), after which every tool returns "Tool limit reached: call submit_review now."
- **D, Model D.** C, plus the kit's served readout for the PR, the same readout as arm B (`contexts.jsonl`: code scope,
  cold workspace at `base_commit`). It is given as "The code the team's workspace ranked for this pull request". The
  system prompt adds the product's own instruction: if that code holds what the review needs, review from it without
  searching.
- **The user message** in both arms is the paper's base review prompt, verbatim (as in arm A), followed in D by the
  readout block.
- **The system prompt** in both arms is the product's TEACH prompt, adapted from finding an answer to reviewing a PR (in
  `scripts/run_agent_review.py`).
- **Not tested here: learning across PRs.** The pilot's PRs in one repository are years apart. Learning is a separate,
  dense-stream study with its own protocol.

## Settings
- Sonnet 5.5, `max_tokens` 8,000 per turn (the product's), no thinking or sampling parameters.
- Automatic prompt caching (`cache_control` ephemeral at top level) in both arms, as a production agent would run.
- The judge is Claude Haiku 5.5 through `scripts/judge_claude.py`, exactly as for arm A (D3).

## Measures
- The judge's issue-level P, R and F1, functional recall, issues per clean PR, and PR-level F1.
- Per PR:
  - requests and tool calls;
  - input tokens (uncached, cache writes, cache reads) and output tokens;
  - dollars at the price table: Sonnet $2.00 in, $2.50 cache write, $0.20 cache read, $10.00 out per million.
- Paired C against D: the per-issue McNemar test and a bootstrap interval on the F1 difference, as in the pilot.

## Predictions (fixed now)
- **P5, same quality:** F1(D) ≥ F1(C) − 0.02.
- **P6, a lower bill:** dollars per PR, D ≤ C / 1.25.
- **P7, less exploring:** tool calls per PR, D < C.

## Running
- **Smoke test:** the first 3 pilot PRs, in both arms, cap $1.50 in total. It measures real per-PR cost before the full
  run.
- **Full run:** a cap agreed with the user after the smoke test. Each arm stops taking new PRs at its cap and reports
  what it has.
- Every number is reported whichever way it comes out, with any deviations below.

## Deviations
(none yet)
