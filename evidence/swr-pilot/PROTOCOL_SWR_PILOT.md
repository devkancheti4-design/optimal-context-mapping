# SWR-Bench pilot: does Model D's context make code review better or cheaper? (written 2026-10-16, before any review)

## Question
A reviewer model reviews a pull request. Does adding the code Model D selects from the repository make it catch the same
or more real issues? And is it cheaper than a reviewer that explores the repository itself?

## Data
- **Benchmark:** SWR-Bench, github.com/ZZR0/SWRench at commit 67ae1d4 (MIT licence), file
  `data/swr_datasets_d5c5.jsonl`. It has 1,000 PRs from 12 Python projects: 500 with reviewer-confirmed issues and 500
  clean.
- **Pilot set:** `pilot_set.json`, drawn by `scripts/sample.py` with seed 20261016 before any review:
  - 50 PRs with issues and 50 clean PRs;
  - allocated across repositories in proportion to the full benchmark (largest remainder), then drawn uniformly within
    each repository;
  - ids sha256 `0de342abb08729a6…` (the full hash is in the file).
- **Ground truth and scoring:** the benchmark's own `changes` and its official judge (`swrbench/evaluation_struct.py`).

## Arms (same reviewer model, same prompt; only the context differs)
- **A, diff only.** The paper's base review prompt (`generate_task_base` in `swrbench/generation.py`), verbatim: the PR
  title, description, and every PR commit's message and diff.
- **B, diff + Model D.** A, plus one block inside the PR details, placed after the code changes:
  `- **Related Code in the Repository** (selected by a context tool): <readout>`.
  - **Workspace:** Model D (optimal-context-mapping main, 2435933), built over the repository checked out at the PR's
    `base_commit`, by `scripts/build_pr.py`. The build is Model D's own; the embedding cache in front of it was shown to
    give bit-identical fingerprints to a cold build (requests at 39f0c66: 4,446 of 4,446 units identical).
  - **The question asked:** the PR title, then the description, cut to 400 characters in total.
  - **The readout:** Model D's served readout for that question with `"scope": "code"`, unchanged. Nothing is taught;
    the workspace is cold.
- **C, diff + exploration (optional; its own protocol before it runs).** A, plus tools to list, search and read files of
  the repository at `base_commit`, with a cap on tool calls. It is defined and pre-registered separately, before any C
  review, so A and B are not delayed by it.

## Reviewer and judge
- **Reviewer:** Claude Sonnet 5.5 (`claude-sonnet-5-5`), Anthropic API, `max_tokens` 8192, one review per PR per arm.
  No thinking parameter, and no sampling parameters, since Sonnet 5.5 rejects a non-default temperature.
- **Judge:** the official judge, Gemini 2.5 Flash, through Gemini's OpenAI-compatible endpoint. Temperature 0 and the
  judge's other defaults. The same judge scores every arm.

## Measures
- Per arm, from the judge's output:
  - TP, FP and FN on change-actions;
  - precision, recall and F1, overall and on functional changes only (F.*);
  - the mean number of predicted issues on clean PRs (all false positives, by the benchmark's definition).
- **Cost:** input and output tokens per PR from the API's usage, and dollars from the price table in
  `optimal-context-mapping/scripts/live_api_test.py` (Sonnet: $2 in, $10 out per million tokens). Also Model D's readout
  size, as characters divided by 4.
- **Paired comparison of A and B:**
  - per ground-truth change-action, hit in A versus B (exact McNemar);
  - F1 difference with a 95% bootstrap interval (10,000 resamples of PRs, seed 20261016).

## Predictions (fixed now)
- **P1:** F1(B) ≥ F1(A).
- **P2:** functional-only recall, B ≥ A.
- **P3:** mean predicted issues per clean PR, B ≤ 1.2 × A. The context must not make the reviewer much noisier.
- **P4:** cost per PR, B ≤ 1.3 × A. The context is small next to the diff.

## Leak control
- Each workspace is built at the PR's `base_commit`.
- `scripts/prep_context.py` checks with git, for every pilot PR, that these are not ancestors of `base_commit`:
  - the PR's commits;
  - every change's introducing commit;
  - every change's resolving commit.

  Any PR that fails is reported and excluded. A commit missing from the clone is recorded as "not in clone".
- The ground truth (`changes`, `pr_timeline`) never reaches the reviewer. It sees only what arm A sees, plus B's block.

## Reporting
Every number is reported whichever way it comes out, with the deviations below. Hard spending caps: $10 for A and B
together, $2 for the judge. A run that reaches a cap stops and reports what it has.

## Deviations (recorded before running)
- **D0:** `swrbench/utils.py` line 13 reads `os.getenv['OPENAI_API_KEY']`, which raises at import. It is changed to
  `os.environ['OPENAI_API_KEY']`, with no other change to the judge.
- **D1:** the paper's reviews use temperature 0.2. Sonnet 5.5 rejects a non-default temperature, so every arm runs at
  the model's default.
- **D2 (2026-10-16, after the two smoke-test reviews, before any judging):** Gemini 2.5 Flash returned 404 ("no longer
  available to new users; use gemini-3.8-flash"). The judge is `gemini-3.8-flash`, with the same script, prompt and
  temperature, for every arm. A against B is unaffected. The absolute F1 values are no longer directly comparable with
  the paper's.
- **D3 (2026-10-16, before any Claude judging; the user chose it):** the Gemini key is on the free tier: 5 requests a
  minute, and "high demand" errors. Its partial output (judged_gemini_partial/) is not used. The judge is now Claude
  Haiku 5.5 (`claude-haiku-5-5`) for every arm, through `scripts/judge_claude.py`. That runs `evaluation_struct.evaluate`
  unchanged except for its single model call, which now goes to the Anthropic SDK:
  - the judge's own JSON schema is passed as `output_config` json_schema;
  - no temperature is sent;
  - the model's default adaptive thinking is used;
  - `max_tokens` is 16,000.

  The reviewer and the judge are now both Claude. Any preference for Claude-written reviews applies equally to A and B,
  but the absolute numbers are less comparable with the paper's. The judge cap stays $2.
