# Model D (Optimal Context Mapping)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23289068.svg)](https://doi.org/10.5281/zenodo.23289068)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

**AI on your codebase, with a bill that flattens as your team works.**

Every AI coding agent on a team pays to search the same code again, and each search step is a paid model request.
Model D is a deterministic kit fused with the Claude API you already use:
- The kit maps your code once, on your machines, into 1,024-bit fingerprints ranked by small laws.
- Before each request, it decides where to look, at zero tokens.
- Claude reads what the kit already knows and explores only what is new.
- Every exploration teaches the kit, so the next engineer's question costs less.

```bash
uv tool install git+https://github.com/devkancheti4-design/optimal-context-mapping   # PyPI: uv tool install model-d
modeld install                                       # wires it into Claude Code, Codex, Gemini CLI and Kiro
modeld build . --cache ~/.cache/modeld/embed.sqlite  # maps this repository; rebuilds embed only what changed
```

## Where it pays

| work | vs the same agent alone | measured on |
|---|---|---|
| **A team's real year of fixes on one codebase** | **2.09x cheaper, the same work (252 vs 253 right); 1.88x → 2.57x as the year went on** | Django's 288 fixes from 2022, in order ([evidence/team-year](evidence/team-year)) |
| A team asking about its own repository | 2.3–2.8x cheaper, same accuracy | a company app, 5 roles, 3 runs |
| The same question again, in other words | 5–10x cheaper | 228-question stream; Gemini, 3 runs |
| Brand-new, scattered bugs | about 1.35x | 114 Django bugs, 3 runs |
| Finding the fixed file, offline | top-5 176 vs Graphify's 131, of 285 | SWE-bench Lite, 12 full repositories |
| Code review | small, about 1.3x at most: reviewers search about 3 times per PR | SWR-Bench pilot, partial ([evidence/swr-pilot](evidence/swr-pilot)) |

Every plan was hashed before it ran, and `python evidence/verify.py` recomputes every number from the raw rows.

## Pricing
- **Open source, $0:** the whole kit under Apache-2.0, self-hosted, for one developer or a team server.
- **Team, $49 per engineer per month:** we set up your team server, send a monthly savings report from your own
  logs, and give priority fixes and a private support channel.
- **Enterprise, by contract:** air-gapped installs, rollout across many repositories, and a guaranteed response time.

Model D adds no model cost of its own. It cuts the API bill you already pay. For a team server, Docker and offline
installs, see [DEPLOY.md](DEPLOY.md). To get the most out of it, see [GUIDE.md](GUIDE.md).

## Why it works: work on a codebase isn't novel

Ten years of Django, 5,333 real fixes, touched only 650 files. After the first thousand fixes, 96–99% landed in a
file already fixed before. The files a team touches grow like the square root of its work (Heaps' law, fitted:
D(n) = 12·n^0.48). So the search for where to look should be paid once. The learning law says how much that
saves: S = A / ((1 − ν)·E + ν·K), where ν is the share of new work, E one learned read ($0.0004) and K a first
exploration with the kit. On Django's 2022 it forecast each quarter's saving from the earlier ones within 14%.

## How to use it

### 1. Install (Python 3.10+)

```bash
uv tool install model-d     # or pipx install model-d, or pip install model-d; from a clone: pip install -e .
```

This installs the `modeld` command (and `modeld-mcp`), with numpy, torch and transformers. `python -m ocm` runs
the same commands. The embedding model (bge-base-en-v1.5) downloads once on the first build;
after that you can set `OCM_OFFLINE=1`.

### 2. Scan your repositories into a workspace

```bash
modeld build ~/code/our-api ~/code/our-web ~/code/our-docs --out ~/ocm-workspace
```

- **What gets kept:** every code and doc file under the folders you pass. Code is cut into blocks and docs into
  sentences, and each becomes a 1,024-bit fingerprint, computed on your machine.
- **What is skipped:** `.env` files, keys, certificates, credential files, lockfiles, dependency and build folders, and
  anything over 512 KB.
- **Also indexed:** build files with no extension (`Dockerfile`, `Makefile` and the like), `.conf`, `.mjml`, `.vscode`.
  Doc sentences keep their line numbers.
- **Device:** a GPU is used automatically when present (CUDA, or Apple silicon); `--device cpu` forces the CPU.

**Rebuilding after code changes?** Carry what the team taught into the new workspace:

```bash
modeld build ~/code/our-api ~/code/our-web --out ~/ocm-workspace-new --carry ~/ocm-workspace
```

The workspace keeps an exact memory of what was taught (`taught.life.json`, a Life from living-fused). On a carry,
each taught question is found in the new code by its exact line and its vector is taught again; an entry whose line
is gone abstains instead of guessing.

### 3. Serve it to the team

```bash
modeld serve ~/ocm-workspace --port 7700                  # just you
modeld serve ~/ocm-workspace --port 7700 --host 0.0.0.0   # your team, on your network
```

Run one server per team; everyone's agents share it. Every call is logged to `<workspace>/calls.jsonl`.

For a bug report, or any question whose answer is in code, ask with `"scope": "code"`. Documentation (`.md`, `.rst`,
`.txt` and the like) then stays out of the ranking. In a full repository, release notes and reference pages can
otherwise fill much of the readout. `OCM_SCOPE=code` makes it the server's default; the MCP tools take `scope` too.

### 4. Put it in your agents' loop

**One command per agent.** `ocm init` writes the right config into a repository. It merges into existing files, keeps
your other settings, and is safe to run again:

```bash
modeld init claude ~/code/our-api --url http://ws.internal:7700    # Claude Code: two hooks + a CLAUDE.md note
modeld init kiro   ~/code/our-api --url http://ws.internal:7700    # Kiro: .kiro/settings/mcp.json + .kiro/steering/ocm.md
modeld init codex  ~/code/our-api --url http://ws.internal:7700    # OpenAI Codex: .codex/config.toml + AGENTS.md
modeld init gemini ~/code/our-api --url http://ws.internal:7700    # Gemini CLI: .gemini/settings.json + GEMINI.md
modeld init all    ~/code/our-api --url http://ws.internal:7700    # all four
```

What each writes, by hand, follows.

**Claude Code (recommended): two hooks, nothing for the model to call.** Add this to the project's
`.claude/settings.json`, and point `OCM_URL` at the team's server if it is not local:

```json
{"env": {"OCM_URL": "http://127.0.0.1:7700"},
 "hooks": {
  "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "modeld hook prompt"}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "modeld hook stop"}]}]
}}
```

- **Before each request**, the prompt hook adds the code its laws rank for the question: the code a taught question's
  vector points to (and then the router's next readout), or the nearest code and docs by meaning and keyword.
- **The model** answers from them when they answer the question, searches when they do not, and ends its reply with
  `TEACH: <question> | <path>:<line>`, the line its answer is on.
- **After the reply**, the stop hook teaches those lines on your machine, at no model cost: each question's vector
  becomes a cue on the code holding that line. No answer text is stored.
- **Between tasks**, run `/clear`. The next task starts from the workspace, not from the old transcript.

**Cursor and other MCP clients: as tools.** Add this to `.mcp.json` (Cursor: `.cursor/mcp.json`), and add
`pilot/AGENT_INSTRUCTIONS.md` to the agent's rules:

```json
{"mcpServers": {"ocm": {"command": "modeld", "args": ["mcp"], "env": {"OCM_URL": "http://127.0.0.1:7700"}}}}
```

This costs a round trip per question, and in our team proof it did not save requests on its own (section 6). Use the
hooks where you can.

**Kiro, OpenAI Codex, Gemini CLI: as MCP tools.** `ocm init kiro|codex|gemini` registers the same four tools in each
tool's own MCP config, and puts the instructions where that agent reads them (`.kiro/steering/`, `AGENTS.md`,
`GEMINI.md`).

**Any other agent loop:** call `ocm.loop.prefetch(question)` before the model call, put the result in the prompt, and
call `ocm.loop.teach_from_reply(reply)` after it.

### The hybrid: the kit decides, the model reads or teaches

`ocm hybrid` runs a question through the hybrid. The kit's laws make every decision, at no model cost, and a model is
called only for one of two jobs:

- **Read:** the question is near one the kit was taught. The model reads the code the kit chose, once and with no tools,
  and answers. If that code does not hold the answer, it says so and the question goes on to be taught.
- **Teach:** the question is new. The model explores (search, read, list on the team's workspace) just enough to find
  the one line the answer is on. The kit learns that line, so the next question like it costs one read.

```bash
export OCM_URL=http://ws.internal:7700
modeld hybrid "What stops a deploy with placeholder secrets?" --provider claude   # ANTHROPIC_API_KEY
modeld hybrid "..." --provider openai                                             # OPENAI_API_KEY (pip install openai)
modeld hybrid "..." --provider gemini                                             # GEMINI_API_KEY, or a Vertex project
```

| Provider | Reads with | Teaches with | Keys |
|---|---|---|---|
| `claude` (Anthropic SDK) | Claude Haiku 5.5 | Claude Sonnet 5.5 | `ANTHROPIC_API_KEY`, or `OCM_VERTEX_PROJECT` for Claude on Vertex AI |
| `openai` (OpenAI SDK) | `--reader`, default `gpt-5.6-terra` | `--teacher`, same default | `OPENAI_API_KEY` |
| `gemini` (REST) | gemini-2.5-flash | gemini-2.5-flash | `GEMINI_API_KEY`, or `OCM_VERTEX_PROJECT` |

In code: `from ocm.hybrid import run, provider, Workspace`, then
`run(question, provider("claude"), Workspace("http://ws.internal:7700"))`. It returns the path taken (`read` or
`teach`), the answer, the line taught, and the number of model requests. Measured so far (gemini-2.5-flash): one read
was right on 90/90 taught questions, and on 30/30 with Claude Haiku 5.5. The Gemini adapter has been run live end to
end. The Claude and OpenAI adapters are covered by the offline tests, but have not yet been run against their live
APIs.

### 5. Measure what it saves you

```bash
modeld calc --repeat 0.5 --deep 0.3 --questions-per-month 16800   # an estimate for your mix
modeld measure compare ~/before-transcripts ~/after-transcripts    # the real thing, from your agents' transcripts
```

`pilot/PILOT.md` is a two-to-four-week plan for a fair before-and-after; fix it before you start
(`pilot/PREREGISTRATION.md`). Run the kit's tests with `python -m pytest -q tests`.

## Big repositories

What we measured with this kit on a MacBook (Apple silicon; its GPU was picked automatically):

| | measured |
|---|---|
| Scanning | 3,898 units in 13 s; transformers (10.8M tokens, 2,347 files) is 183,830 units and took 28 minutes |
| Storage | 128 bytes of fingerprint per unit: 183,875 units take 23.5 MB |
| Readout per request | 0.07 s over 183,875 units (the bit comparison itself takes 2.5 ms) |
| Results at size | live, this kit: 1.71x fewer requests over 10.8M tokens against 1.25x over 148k; earlier research harness: 9.2x on repeats over 10.8M, 6.1x over 7 codebases (7M tokens) |

- **Scope it.** Build one workspace over the repositories a team actually works in; one workspace over everything beat
  one per codebase in our test.
- **Recall falls as size grows.** First-time questions find their answer less often in the first readout. Repeated
  questions, drawn by a taught question's vector, hold up.
- **Rebuild after large code changes,** with `--carry` to bring what was taught along.

## How it works

The workspace is a CMLM: vectors and laws, not a store of text.
- **The vector law** ranks every unit by bits shared with the question: through the vectors of questions taught on
  it, and through its own text.
- **The router law** picks which readout to send from eight free checks: the code a taught question's vector points
  to, the 10 nearest by meaning, by keyword, or both. When the first readout is the taught one, the hook also sends
  the router's next readout (its ADVANCE), so a near miss costs no search.
- **The learned law** reorders the nearest by meaning once it beats the vector order on your team's own questions.

**Teaching trains the CMLM on your machine, at no model cost.** A TEACH line names a question and the line its answer
is on. The question's vector becomes a cue on the unit holding that line, so a later question near it in meaning is
drawn to that code (vector generalisation), and it is an example for the learned law. Nothing the model wrote is
stored, and what the model gets back is always the code itself, with its path and line.

It is ranking math. The readout is ranked, not verified, so the model is told to use it only if it answers the
question.

## Privacy

Everything runs on your machines. Only the embedding model is downloaded, once; your code and questions never leave
your network.

## Limits, stated plainly

- **Repetition drives savings.** One-off questions save less, and short sessions that keep their own context gain
  little.
- **Clear the session between tasks.** In Claude Code the facts the hook adds stay in the transcript and are re-read
  on every later request:
  - At 100 questions in one session, that cost 1.25x more than no CMLM (section 10).
  - The same 100 questions in fresh 10-question sessions cost 1.31x less than one long session, at the same accuracy
    (section 11). The CMLM keeps what was taught.
  - If you must keep one long session, `OCM_COMPACT=1` cuts each readout to its top 3 items. That cut the pile-up
    1.19x, but it still cost 1.05x more than no CMLM.
- **Repeats still cost a read today.** The TEACH rule asks for the exact line, and agents read the file to confirm it
  even when the readout held the answer. Only 6 of 100 questions were answered with no search (section 12).
- **Deep dives** that chain across many files save little today: a taught question points at one line, not a whole
  trail.
- **Billed input falls less than requests**, because readouts add reading.
- **The learned law rarely switches on for code** in our tests.
- **Taught vectors are append-only.** A rebuild carries them only with `--carry`: to the same line, or to the same line
  reformatted (whitespace ignored), and `--prune-after N` drops a lesson whose line has been gone for N rebuilds in a
  row. In our live test a carry over 400 commits kept 40 of 47 entries, but it did not save requests (section 13).
- **The tests are narrow:** open-source code and one client app, with Claude agents and judges. Your codebase is the
  real test.

## Public benchmarks

Model D's retrieval is compared with Graphify on LOCOMO and on finding the file a fix changed. On 285 SWE-bench Lite
issues in 12 full repositories, with the code scope and the test plan fixed before it ran, Model D listed the fixed file
in its first five 176 times (issue titles) and 183 times (title + 400 characters), against 131 and 122 for Graphify
0.9.87, with about 2.4x fewer tokens (`evidence/swe-bench-lite/`). The study is reproducible, and the Claude Code
plugin is in the same repository: https://github.com/devkancheti4-design/model-d-graphify

## Licence

Apache License 2.0 (see `LICENSE` and `NOTICE`).
- `ocm/life.py` is also available under the MIT licence (`ocm/LIFE_LICENSE`).
- Third-party components are listed in `THIRD_PARTY_NOTICES`.

## Cite

If you use this work, please cite it:

> Kancheti, D. (2026). *Optimal Context Mapping (Model D): a shared, learning retrieval layer for AI coding agents*
> (Version 0.2.1) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.23289068

`CITATION.cff` has the same citation, and the DOI for all versions is 10.5281/zenodo.23289067.

Copyright 2026 Devieswar Kancheti.
