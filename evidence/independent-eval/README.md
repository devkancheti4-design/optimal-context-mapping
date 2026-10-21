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

**Reproduce it from nothing** (no API key, no model calls):

```bash
python3 reproduce.py --repos aiohttp     # one repository, both tools and the baselines: about 15 minutes
python3 reproduce.py                     # everything: 120 fixes plus Saleor's 200 as a team, about 4 hours
```

What `reproduce.py` does:
1. **Installs both tools as the evaluation ran them:**
   - Model D 0.5.3 (commit ec440d7) and Graphify 0.9.93 (commit b90b9df), each in its own Python 3.12 environment;
   - every library pinned to the evaluation's versions (`env/*.lock.txt`);
   - Model D's embedding model pinned to the revision it used.
2. **Clones** aiohttp, fastify, zod and Saleor.
3. **Re-runs** the evaluation's own runners on the published question sets.
4. **Compares** every answer with the published rows, and exits 0 only when every right-file-first and top-5 count
   matches.

The evaluation ran on Apple Silicon, where Model D embeds on the GPU. Other hardware can round a few floats
differently, which can move a handful of answers.

**Or recompute the tables from the raw rows, from this folder:**

```bash
python3 bench/analyze.py          # test 1: 120 fixes, right file first / top 5 / MRR / tokens
python3 bench/analyze_team.py     # test 5: Saleor, 200 fixes as a team
python3 bench/agent_score.py      # test 3: agents in fresh sessions
python3 bench/agent_score_b.py    # test 4: shared memory between teammates
```

**Changes from the agent's folder:**
- The copied files had the evaluator's home-folder path in them; it is replaced with `~/eval`.
- The four analysis scripts read their data from beside themselves instead, or from `$RESULTS` when it is set.
- `bench/run_graphify.py` finds Graphify through `$GRAPHIFY` or the PATH, instead of the evaluator's folder.
- Added for reproduction: `reproduce.py` and `env/` (lock files frozen from the evaluator's two environments).
- Section 13 of the report, a note about the evaluator's local machine setup, is left out.
- Logs and caches (3 GB) are not included; `bench/results/` holds every per-question row.
- Nothing else was changed.

**The question sets** (`bench/q_*.json`) are the published ones, with each fix's commit. `reproduce.py` re-runs on
them, not on new questions. `bench/questions.py` and `bench/team_questions.py` show how they were drawn from each
repository's git history.
