# Independent evaluation: Model D vs Graphify vs claude-mem (2026-10-21)

**What this is:** a separate Claude agent was given only the three GitHub repositories (Model D, Graphify,
claude-mem) and asked which deserves #1. It did not use Model D's own evidence. It built its own question sets from
the git history of codebases none of the tools had been tested on, and ran every tool through the same harness.
Model D's author commissioned it; the agent wrote [REPORT.md](REPORT.md).

**Its verdict:** Model D #1, Graphify #2, claude-mem #3, with its limits stated up front.
- **Model D's team memory added almost nothing** in its tests.
- **The "2x cheaper" claim was not reproduced:** it measured 1.58x fewer tool calls, with token totals nearly flat.
- **claude-mem could not be run:** writing its memories needs model access the machine did not have.

**The sets:**
- 120 real fixes from aiohttp, fastify and zod;
- 200 Saleor fixes replayed as a team;
- a memory test on fastify;
- 24 Claude agent sessions.

**Recompute the tables from the raw rows, from this folder:**

```bash
python3 bench/analyze.py          # test 1: 120 fixes, right file first / top 5 / MRR / tokens
python3 bench/analyze_team.py     # test 5: Saleor, 200 fixes as a team
python3 bench/agent_score.py      # test 3: agents in fresh sessions
python3 bench/agent_score_b.py    # test 4: shared memory between teammates
```

**Changes from the agent's folder:**
- The copied files had the evaluator's home-folder path in them; it is replaced with `~/eval`.
- The four analysis scripts read their data from beside themselves instead.
- Section 13 of the report, a note about the evaluator's local machine setup, is left out.
- Logs and caches (3 GB) are not included; `bench/results/` holds every per-question row.
- Nothing else was changed.

**To rerun the benchmarks themselves**, you need the runners `bench/run_*.py` and the question builders
`bench/questions.py` and `bench/team_questions.py`. They need local clones of the target repositories and each
tool installed, so they do not run from this folder alone.
