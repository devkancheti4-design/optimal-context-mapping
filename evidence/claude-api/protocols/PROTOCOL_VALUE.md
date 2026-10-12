# PROTOCOL_VALUE: Model D on the Claude API, adversarial tests, new codebases, research with web search, and the maths

Fixed before any request of this program. Every number comes from the Claude API's own usage fields. Spend comes from
the user's Anthropic credit; the runner stops the whole program at $150 list price.

## Common setup

- **Prices** (Claude API docs, 2026-10-08), per 1M tokens:
  - Sonnet 5.5: input $2.00, cache write $2.50, cache read $0.20, output $10.00.
  - Haiku 5.5: input $0.10, cache write $0.125, cache read $0.01, output $0.50 (prompts up to 100K tokens).
  - Web search: $10 per 1,000 searches.
- **ALONE:** claude-sonnet-5-5 with four tools over the same workspace server, and no kit readout:
  - `search`: a case-insensitive regex over every line;
  - `read_file`;
  - `list_files`;
  - `submit`: the answer and its path:line.

  System prompt: Model D's teach prompt without the sentence about the workspace. At most 15 tool calls,
  `max_tokens` 8000, model defaults otherwise.
- **MODEL D:** `ocm.hybrid.run` from the compiled evaluation package (OCM_Evaluation_0.1.0, cp312), Claude provider.
  - It reads with claude-haiku-5-5 and teaches with claude-sonnet-5-5.
  - Learning is on, and it runs in stream order on a fresh copy of the workspace, unless an experiment says otherwise.
- **Right:**
  - If the answer is submitted, it is right when the submitted path:line's file is the gold file.
  - On the read path, it is right when the first item of the readout the reader was given is in the gold file.
- **Statistics:**
  - Factors are ALONE over MODEL D, per-issue means.
  - 95% intervals come from a paired bootstrap over issues: 20,000 resamples, seed 20261008.

## Experiments

**E1: 114 real django bugs, through the API.**
- Data: swe/issues.json, in its order, on the django snapshot workspace (swe/ws_base).
- Arms: ALONE and MODEL D, both on all 114.
- V1: MODEL D needs fewer requests than ALONE (interval above 1.0), and is right within 5 of ALONE.
- V2: MODEL D's list-price cost is lower than ALONE's (interval above 1.0).

**E2: reworded reports (adversarial).**
- Rewording:
  - claude-haiku-5-5 rewrites each of the 114 reports with this prompt: "Rewrite this bug report the way a different
    engineer on another team might report the same problem. Keep every technical fact needed to find the bug, but use
    your own words and sentence structure; do not copy sentences; do not name any file path that the original does
    not name. Reply with the rewritten report only."
  - The rewordings are frozen to value/paraphrases.json and hashed before E2's first request.
- Arms: MODEL D asks them on E1's taught workspace; ALONE asks them fresh.
- V3: the read path fires on at least 40% of the 114.
- V4: when it fires, the read is right at least 90% of the time.
- V5: MODEL D's cost on E2 is at least 2x lower than ALONE's.

**E3: misleading lessons (adversarial).**
- Pairs: B goes through the 114 in order. For each B, A is the nearest other issue whose gold file differs:
  - nearest by bge-base-en-v1.5 cosine over the issue texts, with CLS pooling;
  - pairs are kept disjoint, so no B is ever taught.
- Teaching: every A is taught at its gold line, through the kit's own teach endpoint, at no model cost.
- Then every B goes through MODEL D, with learning off: B's own answer is not taught.
- V6: MODEL D is right on B within 5 points of ALONE's E1 accuracy on the same issues.
- V7: false reads, meaning the read path answers with a wrong file, stay at or below 10% of the B issues.

**E4: names removed (adversarial).**
- Masking:
  - value/mask.py removes every code identifier: backticked spans, dotted names, snake_case, CamelCase, calls, paths,
    traceback lines and code blocks.
  - It is hashed with this protocol.
- Arms: ALONE and MODEL D on the 114 masked reports; MODEL D on a fresh workspace.
- V8: MODEL D needs fewer requests than ALONE (interval above 1.0), and is right within 5 of ALONE.

**E5: three new codebases.**
- Data: SWE-bench Lite's sympy (77), scikit-learn (23) and pytest (17) issues.
- Setup:
  - one workspace per repository, built by the compiled package at the base commit of that repository's latest
    issue;
  - the gold file is the first file in the gold patch;
  - each repository's issues run in created_at order.
- Arms: ALONE and MODEL D.
- V9: pooled over the 117 issues, MODEL D needs fewer requests than ALONE (interval above 1.0), and its accuracy is
  within 5 points of ALONE's.

**E6: research with web search.**
- Questions:
  - 30 django settings, sampled with seed 20261008, from settings in docs/ref/settings.txt at the snapshot whose
    `Default:` is one simple literal.
  - Pass 1 asks "In Django, what is the default value of the `<SETTING>` setting?"
  - Pass 2 asks "What does Django set `<SETTING>` to when a project does not configure it?"
- Tools: both arms also have the web search tool (`web_search_20260209`, at most 5 uses per question).
  - MODEL D runs the same decision as `ocm.hybrid.run`: the kit readout, a Haiku read when the readout is taught,
    otherwise a Sonnet teach with the tools and web search. A line it submits from the docs is taught.
- Right: the answer contains the documented default, normalised (case, quotes, spaces, and `[]` / `()` / `{}`
  written in words).
- V10: on pass 1, MODEL D is at least 2x cheaper than ALONE.
- V11: on pass 1, MODEL D's accuracy is within 3 questions of ALONE's.
- V12: on pass 2, MODEL D is at least 5x cheaper than ALONE.

## The maths (fixed now, scored on the data)

- **M1, the turn law.**
  - Formula: r_D = 1 + (1 − φ)(r_A − 1), with φ = 0.57 fixed (the published pooled value) and r_A ALONE's measured
    requests per issue.
  - Prediction: on E1, E4 and E5, |r_D predicted / r_D measured − 1| ≤ 0.20.
- **M2, the session-cost law.**
  - Formula: T(r, P) = rP + g·r(r−1)/2. g is fitted on ALONE's within-session token slope in the same experiment; P is
    each arm's mean first-request tokens; r is each arm's mean requests.
  - Prediction: on E1, E4 and E5, |S_pred / S_T measured − 1| ≤ 0.20.
- **M3, the hybrid law.**
  - Formula: S = A / ((1 − ν)E + νK).
  - Parameters, written to value/m3_params.json and hashed before E2:
    - A is ALONE's mean cost per issue on E1;
    - E is the mean cost of a one-request read (claude_live pass 2 and E1 reads);
    - K is MODEL D's mean cost on E1's teach-path issues.
  - ν is E2's measured share of issues not answered by a read.
  - Prediction: |S predicted / S measured − 1| ≤ 0.20 on E2.

## Order, budget and honesty

- Order: E1 ALONE runs in parallel with E1 MODEL D; then E2, E3, E4, E5, E6.
- Budget: the runner refuses every request once the program's ledger passes $150.
- Deviations: any deviation goes in PROTOCOL_VALUE.md.deviations before its numbers are read.
- Reporting: every prediction is reported held or failed, and a stopped experiment is reported unscored.
- Scope: one run per arm. File-level localisation, not patch-and-test.
