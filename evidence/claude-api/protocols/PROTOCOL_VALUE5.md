# PROTOCOL_VALUE5: write the fix, scored by Django's own tests (fixed before any request)

Prices, the ledger, statistics and the $175 cap are as in PROTOCOL_VALUE.md.

**Data**
- Issues: the 30 most recent django issues of SWE-bench Lite (2022-01 to 2023-07; Django 4.1–5.0), in created order.
- The evaluable set (value/w_eval.json, made by value/prep_w.py with no model calls) keeps an issue only if, on this
  machine:
  - the official fix plus the official tests resolves it;
  - the official tests alone do not.
- Tests are run SWE-bench's way: Python 3.11, `tests/runtests.py --verbosity 2 --settings=test_sqlite --parallel 1` on
  the test modules the test patch touches. Every FAIL_TO_PASS test must pass, and every PASS_TO_PASS test must pass or
  skip.

**Arms:** claude-sonnet-5-5, both arms, `max_tokens` 16000, at most 30 tool calls.
- Each agent works in its own copy of the repository at the issue's base commit.
- Tools: search, read_file, list_files, edit_file (exact unique replacement) and finish.
- ALONE: the issue only.
- MODEL D: the issue plus the kit's readout from the django workspace (the 4a72da7 snapshot), with the system prompt
  saying to start from it when relevant. After finish, the first edited line is taught to the kit. Learning is on, in
  issue order.

**Score:** the agent's git diff is applied to a fresh copy. The test files the test patch touches are reset, the test
patch is applied, and the tests run. Resolved means every FAIL_TO_PASS passes and every PASS_TO_PASS passes or skips.

**Predictions**
- W1: MODEL D resolves at least as many issues as ALONE, less 2.
- W2: MODEL D's list-price cost per issue is lower than ALONE's (paired bootstrap interval above 1.0).
- W3: MODEL D needs fewer requests than ALONE (interval above 1.0).
- W4: MODEL D's cost per resolved issue is lower than ALONE's.
