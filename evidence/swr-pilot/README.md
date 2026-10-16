# SWR-Bench pilot: code review (partial, stopped; 2026-10-16)

The data behind "code review: small saving" in the main README. The pilot was stopped when the work was redirected to
the team-year test (`../team-year`). Only these parts completed:

- **Arm A, the paper's base review prompt, diff only, Claude Sonnet 5.5:** 100 of 100 PRs, judged by Claude Haiku 5.5
  through the official SWR-Bench judge (deviation D3).
  - Issue-level F1 0.174: precision 0.10, recall 0.68.
  - 6.4 comments per clean PR.
  - Files: `rows/reviews_A.jsonl`, `rows/judged_A.json`.
- **Arm C, an exploring reviewer** (Sonnet 5.5 with Model D's own search / read / list tools, 15 calls, prompt
  caching): 76 of 100 PRs, not judged.
  - Mean tool calls per PR: 2.88 (median 3; 11 of 76 explored nothing).
  - Mean requests: 3.03; $0.038 per PR.
  - File: `rows/reviews_C.jsonl`.
  - **Why the saving is small:** a reviewer barely searches, so there is little for Model D to take over. The turn law
    gives S = r_a / (q + (1 − φ)(r_a − q)) ≈ 1.3x at r_a ≈ 3.
- **Not completed:** arm B (17 of 100), arm D (3 of 100) and the learning stream. They are not reported.

The benchmark data is SWR-Bench (github.com/ZZR0/SWRench at 67ae1d4, MIT). The protocols, deviations D0–D3 and hashes
are in this folder. The prompts are left out of the rows: they repeat the benchmark's PR text.
