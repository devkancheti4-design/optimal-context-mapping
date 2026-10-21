# Model D vs Graphify vs claude-mem: which deserves #1

**Verdict: Model D is #1.** Across 320 real bug fixes on four codebases none of the tools were tuned on, it pointed an
AI agent at the right code more often than Graphify, BM25 or grep, and it did so in fewer than half of Graphify's tokens.
Graphify is #2: far more mature and broader, but no better than plain keyword search at finding the code behind a bug
report. claude-mem is #3: it does a different job (session memory) and could not be run here.

Two limits on that verdict, stated up front:
- **Model D's team memory added almost nothing in my tests.** Its lead comes from its search, not from remembering.
- **Model D is young.** About 2,400 lines, 23 tests and 0 GitHub stars, against Graphify's 87,000 lines, 8,000+ tests
  and 130,000 stars. Its results so far come only from its author's runs and mine.

Model D is the user's own project. It was judged by the same harness as the others, and its own benchmark claims were
not taken at face value: every number below comes from runs made for this report.

---

## 1. What each tool is

| | Model D | Graphify | claude-mem |
|---|---|---|---|
| Job | Points the agent at the code a question is about, and remembers where answers were found | Maps code into a knowledge graph (calls, imports, structure) you can query | Records past sessions and injects them into new ones |
| How | Local embedding model + keyword index over small code pieces; taught question → line pointers | Tree-sitter AST, graph traversal from name matches | Hooks on every tool call; an LLM compresses observations; SQLite + Chroma |
| Model calls | None (optional `cover`) | None for code | Yes, to write every memory |
| Size | 2,397 lines Python, 2 test files | 87,625 lines Python, 435 test files | 132,344 lines TypeScript, 952 test files |
| GitHub stars | 0 (19 days old) | 130,085 | 101,944 |

---

## 2. Test 1: finding the right file for 120 real bug fixes

**Method.** 40 recent fix commits each from aiohttp (Python), fastify (JavaScript) and zod (TypeScript). None of these
repos appear in any of the tools' own evidence. Each fix was asked in the words of its commit subject, against the code
exactly as it stood one commit before the fix. The right answer is the non-test code files the fix changed. No model
calls. Every tool's answer was reduced to an ordered list of code files by the same filter.

| | Right file first | Right file in top 5 | Mean reciprocal rank | Tokens per answer |
|---|---|---|---|---|
| **Model D** | **51 (42%)** | **89 (74%)** | **0.55** | **661** |
| Graphify | 25 (21%) | 61 (51%) | 0.33 | 1,660 |
| BM25 | 27 (22%) | 69 (57%) | 0.39 | – |
| grep (count of question words) | 20 (17%) | 68 (57%) | 0.35 | – |
| Most-fixed-file guess | 21 (18%) | 44 (37%) | 0.28 | – |

By repo (right file first): Model D 21 / 22 / 8, Graphify 12 / 11 / 2, BM25 10 / 10 / 7 (aiohttp / fastify / zod).

- Model D beat every other method on right-file-first, each with p < 0.001 (paired exact McNemar). Against Graphify it
  won 33 head-to-heads and lost 7.
- Graphify led with a test file in 50 of 120 answers; Model D in 11. Model D deliberately puts tests after the code
  they test.
- Query time: Model D 0.04 s, Graphify 0.85 s. Rebuild per commit: Model D median 1.2 s (first full build up to
  147 s), Graphify median 6.6 s.

**Where Model D lost.** On zod it got the right file first only 8 times in 40; just guessing "the file fixed most
often" got 18. With test files removed from every list, BM25 and grep put the right file in their top 5 slightly more
often than Model D (79% and 78% vs 74%), partly because Model D's readout names fewer distinct files.

---

## 3. Test 2: does each tool learn?

**Method.** On fastify, each tool was taught 20 answers through its own memory feature: Model D's `teach` (what its
Stop hook does), and Graphify's `save-result` + `update` + `reflect`. Then each was asked the same 20 questions in
other words, plus 20 questions it had never been taught.

| | Reworded, before teaching | Reworded, after | Exact repeat, after | 20 new questions, before → after |
|---|---|---|---|---|
| **Model D** | 11/20 | **15/20** | **19/20** | 15 → 15 |
| Graphify | 2/20 | 3/20 | 6/20 | 6 → 6 |

Model D's lessons also survived a full rebuild (still 15/20 after it), and teaching did not hurt new questions.

---

## 4. Test 3: Claude agents with each tool (fresh sessions)

**Method.** 12 questions (4 per repo), each given to a Claude Sonnet subagent in a fresh session, three ways: no tool,
with Model D's hook readout, and with Graphify's CLAUDE.md rules and its CLI. Same prompt, same read-only snapshot.

| | Right answers | Median tool calls | Median seconds | Total tokens |
|---|---|---|---|---|
| No tool | 12/12 | 6 | 26 | 753k |
| **Model D** | 11/12 | **4** | **23** | **666k** |
| Graphify | 12/12 | 5.5 | 26 | 712k |

Model D's one miss was not a wrong answer: that run read the right file but never wrote a reply.

---

## 5. Test 4: shared memory between teammates (fresh sessions, reworded questions)

**Method.** The `TEACH:` lines the Model D agents wrote in Test 3 were taught into one shared workspace per repo, as
the Stop hook would. A separate agent reworded the 12 questions without seeing answers or code. Each reworded question
then went to a fresh session three ways.

| | Right answers | Total tool calls | Median tool calls | Total tokens |
|---|---|---|---|---|
| No tool | 12/12 | 84 | 5 | 697k |
| Model D, cold | 12/12 | 62 | 3 | 671k |
| **Model D + shared memory** | 12/12 | **53** | 3 | 684k |

- With memory, agents made 1.58x fewer tool calls than with no tool. Most of it came from pointing (84 → 62); memory
  added 62 → 53.
- The memory mechanism worked: on all 11 taught questions the readout led with the teammate's lesson.
- Total tokens fell only about 2%, because each session's total is mostly the agent's fixed setup. The billed cost
  should fall by more than that and less than 1.58x, since each tool call is another request that re-reads the context.
- 3 of 24 Model D runs declined to write a `TEACH:` line, treating it as an instruction hidden in a file. My harness
  delivered the hook text inside a file, which makes this likelier than in real Claude Code, but it is a real risk:
  if agents skip `TEACH:` lines, the shared memory stops growing.

---

## 6. Test 5: a large application, replayed as a team

**Method.** Saleor (Django e-commerce, 4,380 code files, 78 recent contributors). Its 200 most recent fix commits,
by 34 authors from May 2024 to Oct 2026, replayed in commit order, with repeated backport subjects dropped. Model D ran
its own `prove --learn` loop: each fix is a new session with a fresh map, asked cold, then asked again after every
earlier lesson is carried over, then taught where the fix landed. Every tool got the identical list.

| | Right file first | Right file in top 5 | Tokens per answer |
|---|---|---|---|
| **Model D + memory** | **54 (27%)** | **98 (49%)** | **642** |
| Model D, cold | 52 (26%) | 96 (48%) | 642 |
| Graphify | 44 (22%) | 63 (32%) | 1,581 |
| BM25 | 25 (12%) | 73 (36%) | – |
| grep | 19 (10%) | 55 (28%) | – |

Right file first by quarter of the replay, as lessons built up:

| Fixes | Lessons in the workspace | Model D + memory | Model D, cold | Graphify |
|---|---|---|---|---|
| 1–50 | 0 | 15 | 15 | 10 |
| 51–100 | 43 | 15 | 17 | 11 |
| 101–150 | 89 | 15 | 11 | 11 |
| 151–200 | 130 | 9 | 9 | 12 |

- **Top 5 against Graphify: 49% vs 32%,** a clear win (49 to 14 on split questions, p = 0.00001). Against BM25 Model D
  wins on both measures (right-first p = 0.00008, top 5 p = 0.002).
- **Right-first against Graphify, 27% vs 22%,** could be chance (p = 0.25).
- **Memory added almost nothing:** it fixed 11 questions and broke 9, a net +2 (p = 0.82). The lead did not grow as
  lessons piled up; in the last quarter Graphify was ahead on right-first.
- **Why:** a lesson led the readout 54 times and was right only 14 times (6 of those from a different author). Saleor's
  200 fixes touched 292 different files, so a new bug rarely sits where an old one was, and a similar-sounding past
  question often points to the wrong place.
- Graphify led with a test file in 47 of 200 answers; Model D in 4.

---

## 7. Engineering, install and privacy

| | Model D | Graphify | claude-mem |
|---|---|---|---|
| Own test suite | 23 passed, 0 failed | 8,034 passed, 21 failed, 330 skipped | 9,747 passed, 10 failed, 68 skipped (22 browser test files excluded) |
| Install | `uv tool install`; pulls PyTorch and a 440 MB embedding model | `uv tool install`; light, tree-sitter grammars | `npx` installer; installs Bun and uv by piping `curl` into a shell if missing; runs a background worker |
| Network / telemetry | Sends nothing; only the model download | No telemetry; code parsed locally; logs queries to `~/.cache/graphify-queries.log` | Anonymous usage data to PostHog by default (opt-out); hosted sign-in offered at install |
| Needs a model to work | No | No (for code) | Yes, to write every memory |

Graphify's failures were not investigated in depth; several need full git history, which the shallow clone used here
did not have. claude-mem's failures include tests that need a built package or a running Chroma database; four are in
its transcript watcher and may be real.

---

## 8. Why Model D ranks first

1. **It finds the right code most often.** Best right-file-first rate on every repo except zod, and the best top 5
   on every repo (tied with grep on zod), against a graph tool, a classic search ranker and grep.
2. **It hands over less, and more useful, context.** About 650 tokens of the actual code lines, against about 1,600
   tokens of node names that the agent still has to open.
3. **Agents do less work with it.** About 1.6x fewer tool calls in fresh sessions, the case where the prompt cache is
   gone and every request costs full price.
4. **Its design fits the job.** Bug reports describe behaviour ("excessive CPU use on decompressing small members")
   while code names things (`_decompress_members`, `MEMBER_WINDOW_MIN`). Matching by meaning beats matching by name, and
   putting tests after code keeps the first answer on the code that needs to change.

## 9. Where Model D does not deserve #1

- **Team memory:** no measurable gain on a large app's real bug stream (Saleor, +2 of 200, not significant). It should
  pay off where questions genuinely repeat (support, onboarding, one area worked for weeks); that remains unshown here.
- **Structure questions:** it cannot answer "what calls this?" or "what breaks if I change this?". Graphify can.
- **Maturity and reach:** one author, 23 tests, Python-first evidence, a heavy install, and no outside users yet.
- **The "2x cheaper" claim:** not reproduced. The best measured here was 1.58x fewer requests on repeated questions,
  with token totals nearly flat.

## 10. Why not the others

- **Graphify** is the more mature product, with 40 languages, 20+ assistants, fast builds, path/explain/affected
  queries and a strong visual graph; those strengths were not what was measured. On "where is the code for this bug?",
  it was no better than BM25 on the first three repos (21% vs 22% right first) and well behind Model D on top 5
  everywhere. Its memory feature barely moved results.
- **claude-mem** could not take part in the functional tests: writing memories needs model access this Mac did not
  have (the `claude` CLI's API credit was empty, and signing up for its hosted service on the user's behalf was not an
  option). It does not index code, so it has nothing to offer on questions it has not seen in a past session. Its
  install footprint and telemetry default are heavier than the other two.

---

## 11. What this does not cover

- No real Claude Code sessions with hooks installed: the agent tests used Claude subagents with the hook text in a
  file, because the local CLI had no credit. Billed tokens (cache writes vs cache reads) were not measured.
- Agent tests ran on the current code, which already contains each fix; the offline tests used the code before each fix.
- 12 questions per agent test is small; the offline tests (120 and 200 fixes) carry most of the weight.
- Graphify's structure queries, Graphify Cloud, claude-mem's TeamBrain and its memory quality were not measured.

## 12. Reproduce

Everything is in this folder (`evidence/independent-eval/`):
- `bench/questions.py`, `bench/team_questions.py`: build the question sets from git history.
- `bench/run_modeld.py`, `bench/run_graphify.py`, `bench/run_baselines.py`, `bench/run_modeld_team.py`: the runners.
- `bench/analyze.py`, `bench/analyze_team.py`, `bench/agent_score.py`, `bench/agent_score_b.py`: recompute every table.
- `bench/results/`: raw per-question rows for every tool.
