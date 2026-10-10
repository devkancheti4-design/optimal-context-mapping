# Optimal Context Mapping

**A shared memory over your team's code that sits inside your AI agents' loop, so the same research is not paid for
twice.**

When engineers use AI agents (Claude Code, Cursor and others) on the same codebases, each agent searches and re-reads
the code on its own, every time, and each step is a paid model request. Optimal context mapping scans your
repositories once into a workspace of vectors (1,024-bit meaning fingerprints) ranked by small laws. Before each
request, it hands the model the few code blocks and doc lines its laws rank for the question. After the reply, it learns
where the answer was: the question's vector is put on that code. The next person's agent, asking the same thing in other
words, is drawn to it.

## What it achieved in our tests

Live tests with fresh Claude agents and blind judges, each plan fixed with a hash before it ran (evidence in
`results/RESULTS.md`):

| test | accuracy | model requests |
|---|---|---|
| **A long Claude Code session** (25 questions, one session carrying its transcript), with the CMLM in the loop | same (24/25 both) | **1.35x fewer**; billed input 1.21x lower; searches and reads 55 to 33 |
| **A large codebase, live: transformers, 10.8M tokens** (60 questions, fresh sessions) | same (60/60 both) | **1.71x fewer**; billed input **1.61x lower**; searches and reads 2.7x fewer; every reworded question landed on its taught code (30/30, no junk) |
| **100 questions, clearing the session between tasks, this kit** (vectors only) | same (100/100 both) | **1.25x fewer** than the same fresh sessions without it; billed input **1.19x lower**; searches and reads 1.58x fewer; the saving held from the first half to the second (1.26x, 1.24x) |
| 100 questions, clearing between tasks, the kit before vectors-only teaching | same (98/100) | 1.25x fewer; billed input 1.20x lower, 1.31x lower than one long session; but the saving fell from 1.40x to 1.13x as notes piled up |
| A 100-question Claude Code session, with the CMLM in the loop and never cleared | same (98/100 both) | about the same (202 against 208), but billed input **1.25x higher**: the injected facts pile up in the transcript |
| **The kit as shipped, in the loop**: a five-role team on a real app (Full Stack FastAPI Template), one fresh agent per question | same (24/25 both) | **1.62x fewer** than the same agents without it; 2.4x fewer on questions a teammate asked before |
| A seven-role project team on a real codebase plus web research (research harness) | same (41/41) | 1.66x fewer with batched teaching |
| Single-fact questions over 7 real codebases (7M tokens) | same (28/28) | 6.1x fewer, billed input 2.8x lower |
| Repeated questions on a 10.8M-token codebase | same (30/30) | 9.2x fewer |
| Multi-file deep dives | same (40/40) | 1.2x fewer (the weak spot) |

Where it did not help:
- **As a tool the agent calls**, it cost more requests than it saved (section 6).
- **Against agents that keep a short 5-question session**, in the loop came out about even (71 against 67 requests,
  section 7).

The saving grows with repetition and with the size of the codebase. In Claude Code, clear the session between tasks and let the CMLM carry what was learned.

## How to use it

### 1. Install (Python 3.10+)

```bash
pip install -e .
```

This installs numpy, torch and transformers. The embedding model (bge-base-en-v1.5) downloads once on the first build;
after that you can set `OCM_OFFLINE=1`.

### 2. Scan your repositories into a workspace

```bash
python -m ocm build ~/code/our-api ~/code/our-web ~/code/our-docs --out ~/ocm-workspace
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
python -m ocm build ~/code/our-api ~/code/our-web --out ~/ocm-workspace-new --carry ~/ocm-workspace
```

The workspace keeps an exact memory of what was taught (`taught.life.json`, a Life from living-fused). On a carry,
each taught question is found in the new code by its exact line and its vector is taught again; an entry whose line
is gone abstains instead of guessing.

### 3. Serve it to the team

```bash
python -m ocm serve ~/ocm-workspace --port 7700                  # just you
python -m ocm serve ~/ocm-workspace --port 7700 --host 0.0.0.0   # your team, on your network
```

Run one server per team; everyone's agents share it. Every call is logged to `<workspace>/calls.jsonl`.

### 4. Put it in your agents' loop

**One command per agent.** `ocm init` writes the right config into a repository. It merges into existing files, keeps
your other settings, and is safe to run again:

```bash
python -m ocm init claude ~/code/our-api --url http://ws.internal:7700    # Claude Code: two hooks + a CLAUDE.md note
python -m ocm init kiro   ~/code/our-api --url http://ws.internal:7700    # Kiro: .kiro/settings/mcp.json + .kiro/steering/ocm.md
python -m ocm init codex  ~/code/our-api --url http://ws.internal:7700    # OpenAI Codex: .codex/config.toml + AGENTS.md
python -m ocm init gemini ~/code/our-api --url http://ws.internal:7700    # Gemini CLI: .gemini/settings.json + GEMINI.md
python -m ocm init all    ~/code/our-api --url http://ws.internal:7700    # all four
```

What each writes, by hand, follows.

**Claude Code (recommended): two hooks, nothing for the model to call.** Add this to the project's
`.claude/settings.json`, and point `OCM_URL` at the team's server if it is not local:

```json
{"env": {"OCM_URL": "http://127.0.0.1:7700"},
 "hooks": {
  "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python -m ocm hook prompt"}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "python -m ocm hook stop"}]}]
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
{"mcpServers": {"ocm": {"command": "python", "args": ["-m", "ocm", "mcp"], "env": {"OCM_URL": "http://127.0.0.1:7700"}}}}
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
python -m ocm hybrid "What stops a deploy with placeholder secrets?" --provider claude   # ANTHROPIC_API_KEY
python -m ocm hybrid "..." --provider openai                                             # OPENAI_API_KEY (pip install openai)
python -m ocm hybrid "..." --provider gemini                                             # GEMINI_API_KEY, or a Vertex project
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
python -m ocm calc --repeat 0.5 --deep 0.3 --questions-per-month 16800   # an estimate for your mix
python -m ocm measure compare ~/before-transcripts ~/after-transcripts    # the real thing, from your agents' transcripts
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

Model D's retrieval is compared with Graphify on LOCOMO and on finding the answer file in a full-stack repository. The
study is reproducible, and the Claude Code plugin is in the same repository:
https://github.com/devkancheti4-design/model-d-graphify

## Licence

Apache License 2.0 (see `LICENSE` and `NOTICE`).
- `ocm/life.py` is also available under the MIT licence (`ocm/LIFE_LICENSE`).
- Third-party components are listed in `THIRD_PARTY_NOTICES`.

## Cite

If you use this work, please cite it as `CITATION.cff` describes. The DOI is added once the Zenodo record is
published.

Copyright 2026 Devieswar Kancheti.
