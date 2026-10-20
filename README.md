# Model D (Optimal Context Mapping)

[![PyPI](https://img.shields.io/pypi/v/model-d)](https://pypi.org/project/model-d/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23289068.svg)](https://doi.org/10.5281/zenodo.23289068)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

**What your AI coding agent learns about your codebase lives in its context: gone when the session ends, and paid
for again once the prompt cache expires (an hour at most on Claude). Model D keeps it on disk, as Cortex D: a context
graph of the repository. It tells the agent where to look in every new session, and never lets it pay twice for the same
question.**

On a real team's year of work (Django's 288 fixes from 2022), the same Claude agent cost **2.09x less with Model D**
(95% interval 1.84x–2.39x), at the same accuracy: 252 vs 253 right.

---

## Try it on your own code first

You need no API key, and nothing leaves your machine:

```bash
uv tool install "model-d[claude]"      # or: pipx install "model-d[claude]"  /  pip install "model-d[claude]"
cd your-repo
modeld forecast .                      # from your git history: how much of your work repeats, and the saving it predicts
modeld prove .                         # replays your last 50 real bug fixes and checks whether Model D finds the code
                                       # each one changed, side by side with a plain search
modeld prove . --learn                 # the same as a team over time: each fix a new session, every lesson kept on disk
modeld cortex                          # see Cortex D, your repository's context graph, as a page that opens offline
```

- **`forecast`** reads only `git log` and answers in about a second.
- **`prove`** downloads a small embedding model once (about 440 MB) and maps your code on your machine. The first
  build takes minutes on a large repository; every later one takes seconds.
- **Example:** on Hono (TypeScript, 241 real fixes), `prove` found the right file first 31% of the time against 16%
  for grep, and in its top 5 60% against 42%.

---

## What it is, and what it is not

**It is** a small layer under the coding agent you already use: Claude Code, Kiro, Codex, Gemini CLI, or any MCP
client.
1. **It builds Cortex D, a context graph of your codebase, once, on your machine.** Every piece of code becomes a 1,024-bit
   fingerprint, and every question your agents answer becomes a link from that question to the line that answered it.
   The graph lives on disk, so it outlasts any session or cache, and a rebuild carries every link into the new code:
   replaying Graphify's last 50 fixes as 50 fresh sessions, 45 of 46 links were still found at the end.
2. **Before the agent spends a token, it points it to the likely code** (about 400–700 tokens), so the agent searches
   less. The pointing costs nothing: it is arithmetic, not a model call.
3. **When the agent finds an answer, Model D pins the question to that line.** The same question later, in any
   wording, costs one cheap read ($0.0004) instead of a new search.
4. **It stores pointers, never answers.** The agent always reads the current code, so nothing goes stale.

**It is not** an agent. It does not write code, run tests or plan work; your agent does that. Nor is its graph a
call or import graph: it links questions to code, and leaves the code's structure to the agent reading it. It saves most where
work repeats: a team on one codebase, support questions, onboarding. It saves little on one-off questions, writing
fixes or code review (see Limits).

---

## Cortex D: the context graph

Cortex D is what Model D keeps between sessions, made visible with `modeld cortex`:
- **every piece of code**, as a 1,024-bit meaning fingerprint;
- **every question your agents answered**, linked to the exact line that answered it;
- **files linked by meaning:** each file to its nearest files, whether or not either imports the other.

It is built from the workspace in seconds, with no model calls. It lives on disk, so it outlasts the session, the
prompt cache and the teammate who taught it, and a rebuild carries every link into the new code.

**On Django** (the same commit Graphify 0.9.92 was run on):

| | Graphify's knowledge graph | Cortex D |
|---|---|---|
| made of | 46,373 named nodes, 108,300 edges (calls, methods, imports) | 113,271 pieces of code, 23,770 question links, 6,945 meaning edges |
| what a link means | how code is wired | what code means, and where an answer was found |
| overlap | | 81% of its meaning edges join files Graphify does not link directly |
| right file first, 288 real fixes | 89 (116 read at its best) | 133 cold, 153 after learning once |
| tokens per answer | 1,537 | 597–735 |

Graphify answers how things connect: call paths, what a change touches, architecture. Cortex D answers where the
answer is, and remembers it. It never draws a call graph or a blast radius. Built in 1.9 s on Django
([cortex-d](evidence/cortex-d), [tests-trail](evidence/tests-trail), [vs-graphify](evidence/vs-graphify)).

---

## Results

Every test plan was written and hashed before it ran. The raw rows are in [`evidence/`](evidence), and
`python evidence/verify.py` recomputes every number below.

| work | result, against the same agent alone | measured on |
|---|---|---|
| **A team's real year of fixes** | **2.09x cheaper (1.84x–2.39x), same work (252 vs 253 right); 1.88x → 2.57x as work repeated** | Django's 288 fixes from 2022, in order ([team-year](evidence/team-year)) |
| Real "how does this work?" questions | 2.36x cheaper at 93% of the quality (gap not significant, p = 0.24) | bluesky atproto, 115 real GitHub Discussions, blind judge ([oss-comprehension](evidence/oss-comprehension)) |
| A team asking about its own app | 2.3–2.8x cheaper, same accuracy | a company-style app, 5 roles, 3 runs ([claude-api](evidence/claude-api)) |
| The same question again, in other words | 5–10x cheaper | 228-question stream; Gemini, 3 runs ([gemini](evidence/gemini)) |
| Repository Q&A benchmark | 2.22x cheaper, score 61.0 vs 65.3 out of 100; a retest with caching on both sides: 1.90x, 73.3 vs 75.9 | SWE-QA: 336 questions in 7 repositories; the retest on 91 ([claude-api](evidence/claude-api)) |
| Brand-new, scattered bugs | 1.33–1.50x | 114 Django bugs; sympy, scikit-learn, pytest; matplotlib, sphinx, requests, flask |
| A TypeScript codebase it had never seen (offline, no model) | right file first 31% vs 16% for grep; top 5 60% vs 42% (0.5.2: 25%, 56%) | 241 real honojs/hono fixes, each against the code right before it ([new-codebase-hono](evidence/new-codebase-hono), [tests-trail](evidence/tests-trail)) |
| Writing fixes | not cheaper ($0.197 vs $0.160 per fix) | 19 Django issues |
| Code review | about 1.3x at most | SWR-Bench pilot, partial ([swr-pilot](evidence/swr-pilot)) |

**In one line:** 1.3x to 2.8x cheaper, depending on how much your work repeats; 2.09x on a real team's year.

**Where Django's 2.09x comes from** ([learning-ablation](evidence/learning-ablation)):
- **85% from pointing.** The agent explores less. On fixes it still had to explore, it was 1.92x cheaper.
- **15% from memory.** 40 fixes were answered by one $0.0004 read of code an earlier question had pinned.
- **The learned law added nothing.** Forced on, it changed no result, so it is treated as experimental.

**Against Graphify 0.9.92** ([vs-graphify](evidence/vs-graphify)), on Django's 288 questions, offline:

| | right file first |
|---|---|
| Model D 0.5.3, cold | **133** (0.5.2: 111) |
| Model D 0.5.3, after learning the codebase once | **153** (0.5.2: 149) |
| Graphify, as it prints its answer | 89 |
| Graphify, read at its best by its own scores | 116 (a tie with cold 0.5.2) |

Model D hands over 597–735 tokens per answer (0.5.3, taught and cold), against Graphify's 1,537. Graphify's graph itself is accurate: only
0.7% of its Python import edges were wrong.

---

## How it works

```text
your repo ──► cut into pieces ──► embedded on your machine ──► 1,024-bit fingerprints + keyword index
                                     (bge-base-en-v1.5)            (SimHash)          (SQLite FTS5)

question ──► router law picks the code (0 tokens) ──► learned code?  ──► Claude Haiku reads it ($0.0004)
                                                      new code?      ──► Claude Sonnet explores from there (~$0.05)
                                                                              │
                                                    the question is pinned to the line it found ◄┘
```

- **Fingerprints.** Each piece of code (blocks of up to 400 characters; docs as sentences) is embedded locally by
  `BAAI/bge-base-en-v1.5` (768 numbers). Then 1,024 fixed random planes turn it into 1,024 sign bits (128 bytes).
  Two texts that share more bits mean more nearly the same thing, so a question in new words still lands near what it
  means.
- **The router law.** Eight yes/no checks, all free (lead size, crowding, rare words, agreement between meaning and
  keywords), pick which readout to send: taught code, the nearest by meaning, by keyword, or both. Its thresholds
  were set once from the geometry: a lead under 8 bits is noise, and 74 bits is twice the 37-bit spread of chance.
- **Memory.** A taught question's vector becomes a pointer on the code that answered it. Since 0.5.1:
  - it counts only when it clearly beats the code's own match (by 37 bits, the relation limit), so a merely similar
    question is not pulled to an old answer;
  - a taught pointer leads the readout, followed by the normal top four.
- **Tests after code (0.5.3).** In a readout, test files come after the code they test, unless the question is about
  tests. Before, a test file often led (23 of 50 readouts on Graphify, 73 of 241 on Hono), because a test names the
  behaviour in the words of a bug report. With the same items reordered, right file first rose on every set, with no answer lost
  ([tests-trail](evidence/tests-trail)):
  - Django, cold: 111 → 133 of 288;
  - Hono: 60 → 74 of 241;
  - Graphify: 12 → 21 of 50.
- **No summaries.** Model D never summarises code. What the model gets back is always the code itself, with its path
  and line.

The laws, their constants and the cost formulas are in [GUIDE.md](GUIDE.md) and the evidence folders.

---

## How to use it

### 1. Install (Python 3.10+)

```bash
uv tool install "model-d[claude]"     # plain "model-d" works too, but leaves out the Anthropic SDK (needed by cover and hybrid)
```

This installs the `modeld` command, with numpy, torch and transformers. The embedding model downloads once, on the
first build. After that, `OCM_OFFLINE=1` keeps everything offline.

### 2. Map your repositories

```bash
modeld build ~/code/our-api ~/code/our-web --out ~/ocm-workspace --cache ~/.cache/modeld/embed.sqlite
```

- **Read:** every code and doc file, whatever its size. That covers:
  - Python;
  - TypeScript and JavaScript (`.ts .tsx .mts .cts .d.ts .js .jsx .mjs .cjs`), Vue, Svelte and Astro;
  - Go, Rust, Java, Kotlin, C#, C/C++, Ruby, PHP and Swift;
  - SQL, shell, YAML/TOML/JSON configs, Dockerfiles and Makefiles.
- **Skipped, because it isn't your code:**
  - `.git`, dependencies (`node_modules`, `vendor`, `venv`…) and build output;
  - lockfiles, minified bundles (`*.min.js`, `*.min.css`) and `.json` data dumps over 2 MB;
  - anything that looks like a secret (`.env`, keys, certificates).

  Add `--max-file-kb N` if you want a size limit.
- **Rebuilds are fast:** with `--cache`, only changed code is embedded again. What was taught carries over (add
  `--carry <old workspace>` when building into a new folder). Each pointer follows its exact line, and a pointer
  whose line is gone is dropped, never guessed.
- **A GPU** (CUDA or Apple silicon) is used automatically when present.

### 3. Optional: teach it the whole codebase once

```bash
export ANTHROPIC_API_KEY=...          # or OCM_VERTEX_PROJECT for Claude on Vertex AI
modeld cover --workspace ~/ocm-workspace
```

- **What it does:** Claude Haiku writes one question for every piece of non-test code, and each is taught as a
  pointer to that code.
- **What it costs:** it shows an estimate and asks before spending (`--yes` skips the prompt, `--cap` sets a limit).
  Django's 23,976 pieces cost $0.97.
- **What it did:** on 288 real questions it had never seen, the right file came first 142–149 times against 111 cold,
  and the top 5 rose to 219 against 197. With 0.5.3's tests-after-code, 153 against 133.
- **After a rebuild:** run it again, and it writes questions only for new or changed code.

### 4. Serve it to your team

```bash
modeld serve ~/ocm-workspace --port 7700                  # just you
modeld serve ~/ocm-workspace --port 7700 --host 0.0.0.0   # your team, on your network (see Limits: no login yet)
```

- **One server per team:** everyone's agents share one memory.
- **Logging:** every call is logged to `<workspace>/calls.jsonl`.
- **Code scope:** for bug reports and code questions, ask with `"scope": "code"`, or set `OCM_SCOPE=code`, so
  release notes and docs stay out of the ranking.
- **Docker and offline installs:** see [DEPLOY.md](DEPLOY.md).

### 5. Put it in your agent's loop

```bash
modeld install                                                    # registers Model D with the agents on this machine
modeld init claude ~/code/our-api --url http://ws.internal:7700   # Claude Code: two hooks + a CLAUDE.md note
modeld init kiro   ~/code/our-api --url http://ws.internal:7700   # Kiro: MCP config + steering file
modeld init codex  ~/code/our-api --url http://ws.internal:7700   # OpenAI Codex: MCP config + AGENTS.md
modeld init gemini ~/code/our-api --url http://ws.internal:7700   # Gemini CLI: MCP config + GEMINI.md
modeld init all    ~/code/our-api --url http://ws.internal:7700   # all four
```

`init` merges into existing files, keeps your settings, and is safe to run again.

**Claude Code (recommended): two hooks, nothing for the model to call.** In the project's `.claude/settings.json`:

```json
{"env": {"OCM_URL": "http://127.0.0.1:7700"},
 "hooks": {
  "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "modeld hook prompt"}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "modeld hook stop"}]}]
}}
```

- **Before each request,** the prompt hook adds the code Model D ranks for the question.
- **The model** answers from it when it answers the question, searches when it does not, and ends with
  `TEACH: <question> | <path>:<line>`.
- **After the reply,** the stop hook pins those lines on your machine, at no model cost.
- **Between tasks, run `/clear`.** Model D keeps what was learned, so the transcript doesn't have to.

**Cursor and other MCP clients.** Add this to `.mcp.json` (Cursor: `.cursor/mcp.json`), and add
`pilot/AGENT_INSTRUCTIONS.md` to the agent's rules. The tools are `workspace_ask`, `workspace_next`,
`workspace_recall` and `workspace_teach`.

```json
{"mcpServers": {"ocm": {"command": "modeld", "args": ["mcp"], "env": {"OCM_URL": "http://127.0.0.1:7700"}}}}
```

**Any other agent loop:** call `ocm.loop.prefetch(question)` before the model call, put the result in the prompt,
and call `ocm.loop.teach_from_reply(reply)` after it.

### 6. Or let Model D drive the model: the hybrid

`modeld hybrid` makes every decision with its laws, and calls a model for one of two jobs only:
- **Read:** if it has learned this code, a small model reads it once and answers, or says the code doesn't hold the
  answer.
- **Explore and teach:** otherwise a stronger model explores (search, read, list) until it finds the line, and Model D
  learns it.

```bash
modeld hybrid "What stops a deploy with placeholder secrets?" --provider claude   # ANTHROPIC_API_KEY
```

| provider | reads with | explores with | status |
|---|---|---|---|
| `claude` | Claude Haiku 5.5 | Claude Sonnet 5.5 | run live: Django's team year, atproto, SWE-QA |
| `gemini` | gemini-2.5-flash | gemini-2.5-flash | run live: 3 runs on transformers |
| `openai` | `--reader` (default `gpt-5.6-terra`) | `--teacher` | offline tests only |

In code: `from ocm.hybrid import run, provider, Workspace`, then
`run(question, provider("claude"), Workspace("http://ws.internal:7700"))`.

### 7. Measure what it saves you

```bash
modeld forecast .                                                   # from git history, before you install anything
modeld prove .                                                      # pointing quality on your own fixes, zero tokens
modeld measure compare ~/before-transcripts ~/after-transcripts     # the real bill, from your agents' transcripts
```

[`pilot/PILOT.md`](pilot/PILOT.md) is a two-to-four-week plan for a fair before-and-after. Fix it before you start
([`pilot/PREREGISTRATION.md`](pilot/PREREGISTRATION.md)).

---

## Big repositories

| | measured on a MacBook (Apple silicon) |
|---|---|
| Django (54 MB of source, 3,808 files) | 113,271 pieces; first build about 10 minutes; workspace 80 MB |
| Hugging Face transformers (43 MB, 2,347 files) | 183,830 pieces; first build 28 minutes |
| Storage | 128 bytes of fingerprint per piece |
| One readout | 0.07 s over 183,875 pieces |
| Rebuild with the cache | seconds (0.4 s per Hono commit) |

- **Size on disk is not the issue.** Repositories are gigabytes mostly because of `.git`, dependencies, build output
  and media, none of which Model D reads.
- **Not yet tested:** monorepos with gigabytes of actual source. By extrapolation, 1 GB of source is a few million
  pieces and roughly half a day for the first build on a laptop. Build it once on a server and share it with
  `modeld serve`.

---

## Privacy

- **Model D itself sends nothing anywhere.** Mapping, fingerprints, ranking and memory all run on your machines.
  Only the embedding model is downloaded, once.
- **Your agent still sends the code it reads to its own model provider,** as it does without Model D. Model D usually
  means it reads less.
- **`modeld cover` and `modeld hybrid` call Claude** (or Gemini, or OpenAI) with code pieces, and only when you run
  them. `cover` shows its estimate and asks first.

---

## Limits, stated plainly

- **Savings depend on repetition.** On all-new, one-off work the saving is about 1.3x. Writing fixes and code review
  barely benefit.
- **Memory helps repeated questions, not new ones.** A remembered answer doesn't make it smarter at a different
  question.
  - In 0.5.0, a year of real teaching even made pointing on new questions worse: 84 vs 111 right file first, out of
    288.
  - 0.5.1 recovers most of it (99, with the top 5 at 176 vs 197), while reworded repeats stay at 107 of 114.
  - `OCM_RELATION_LIMIT=off` restores 0.5.0.
- **Tests after code can hide a test that is the answer.** If the question doesn't say "test" (or spec, pytest,
  fixture...), test files go last. In every measured set the answer was code, so this risk is unmeasured.
  `OCM_TESTS_TRAIL=off` turns it off.
- **The learned law is experimental.** It rarely switches on, and forced on it changed nothing.
- **Clear the session between tasks.** In one 100-question session, what the hook added piled up in the transcript
  and cost 1.25x more than no Model D. The same questions in fresh sessions cost 1.31x less (results/RESULTS.md,
  sections 10–11).
- **Deep dives across many files save little:** a pointer marks one line, not a whole trail.
- **The team server has no login yet,** and there is no SSO and no audit log. Run it inside your own network.
- **Evidence:** mostly Python, plus one TypeScript project and one app with a React frontend. Every test was run by
  us. Your codebase is the real test, which is why `forecast` and `prove` exist.

---

## Pricing

- **Open source, $0:** everything in this repository, Apache-2.0, self-hosted.
- **Team, $49 per engineer per month:**
  - we set up your team server;
  - you get a monthly savings report from your own logs;
  - you get priority fixes and a private support channel.

  It starts with a free 2-week pilot measured on your real bill. If it doesn't save at least 1.5x, you owe nothing.
- **Enterprise, by contract:** air-gapped installs, many repositories, and a guaranteed response time.

Model D adds no model cost of its own, apart from the optional `cover`. It cuts the API bill you already pay.

---

## Evidence and reproducibility

[`evidence/README.md`](evidence/README.md) lists every claim with its folder, plan and raw rows, including the
predictions that failed.

```bash
python evidence/verify.py     # recomputes every number and checks all 627 evidence files against their hashes
```

## Licence

Apache License 2.0 (see `LICENSE` and `NOTICE`).
- `ocm/life.py` is also available under the MIT licence (`ocm/LIFE_LICENSE`).
- Third-party components are listed in `THIRD_PARTY_NOTICES`.

## Cite

> Kancheti, D. (2026). *Optimal Context Mapping (Model D): a shared, learning retrieval layer for AI coding agents*
> [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.23289067

That DOI covers all versions; the archived record is version 0.2.1 (10.5281/zenodo.23289068). `CITATION.cff` has the
same citation.

Copyright 2026 Devieswar Kancheti.
