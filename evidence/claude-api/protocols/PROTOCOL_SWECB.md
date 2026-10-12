# PROTOCOL_SWECB: does Model D reuse experience? SWE-ContextBench Lite, Django (fixed before any request)

**Benchmark:** SWE-ContextBench (jiayuanz3/SWEContextBench on Hugging Face, MIT, downloaded 2026-10-09; the paper is
arXiv 2602.08316).
- Lite has 300 experience tasks (SWE-bench Lite) and 99 related tasks, linked by real issue and PR references.
- This run uses the 36 Django related tasks, because Django's tests run locally on this Mac (no Docker).
- Of those, only the tasks that validate locally are kept: the official fix passes the official tests, and the tests
  fail without it. Django 4.0 and later run on Python 3.11, earlier versions on Python 3.10
  (`swecb/cb_prep.py validate`, results in `swecb/cb_eval.json`).
- The experience pool is the 114 Django experience tasks.

**The kit:** Model D 0.2.1 (~/ocm-eval/venvs/t021). For each kept task, `ocm build` runs over the `django/` package
at the task's base commit:
- **COLD:** that index, nothing taught.
- **EXP:** the same index, taught the experience pool: each experience task's issue text, placed on the first line its
  merged fix changed, found by that line's text in this task's code (nearest to the fix's line number). An experience
  task whose line is not in this version's code is not placed. Placement counts are in `swecb/cb_build.json`.
  - This is the "free" setting: the kit picks which experience is relevant. No oracle link is given.
  - The pool comes from merged fixes (a team's history), not from agent trajectories as in the paper. That is a
    deviation, fixed here.

**Arms** (claude-sonnet-5-5 in all; V5's tools: search, read_file, list_files, edit_file, finish, at most 30 calls;
V5's prompts):
- **ALONE:** the issue only (`run5.SYS`).
- **COLD:** the issue plus the COLD kit's readout (`run5.SYS_D`).
- **EXP:** the issue plus the EXP kit's readout (`run5.SYS_D`).

Tasks run in time order, and each task's three arms run before the next task.

**Scoring:** the official FAIL_TO_PASS and PASS_TO_PASS tests on the task's base checkout, with the model's patch and
the official test patch applied (`run_cb.py score`).

**Budget:** $15 of this program's own spend. If the cap stops it, results are reported over the tasks finished in all
three arms.

**Predictions**
- C1: EXP resolves at least as many tasks as ALONE.
- C2: EXP resolves at least as many tasks as COLD: experience does not hurt, unlike the paper's free-retrieval rows.
- C3: EXP's cost per resolved task is lower than ALONE's.
- C4: EXP's readout names a file the official fix changed more often than COLD's.

**Reference, not compared:** the paper's Table 4 (Claude Code with Sonnet 4.5, all 99 Lite related tasks). These
differ in agent, model and task subset, so only this run's paired arms are compared:

| Setting | Resolved | Cost per task |
|---|---|---|
| No context | 26.3% | $0.79 |
| Free context | 26.3% | $0.98 |
| Mem0 | 24.2% | $0.62 |
| OpenViking | 29.2% | $0.53 |
| Supermemory | 30.3% | $0.58 |
