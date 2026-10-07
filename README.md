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

The saving grows with repetition. In Claude Code, clear the session between tasks and let the CMLM carry what was learned.

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

### 3. Serve it to the team

```bash
python -m ocm serve ~/ocm-workspace --port 7700                  # just you
python -m ocm serve ~/ocm-workspace --port 7700 --host 0.0.0.0   # your team, on your network
```

Run one server per team; everyone's agents share it. Every call is logged to `<workspace>/calls.jsonl`.

### 4. Put it in your agents' loop

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

**Any other agent loop:** call `ocm.loop.prefetch(question)` before the model call, put the result in the prompt, and
call `ocm.loop.teach_from_reply(reply)` after it.

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
| Scanning | 3,898 units in 13 s (about 300 units a second); a 10.8M-token codebase is 183,875 units, about 10 minutes at that rate |
| Storage | 128 bytes of fingerprint per unit: 183,875 units take 23.5 MB |
| Readout per request | 0.07 s over 183,875 units (the bit comparison itself takes 2.5 ms) |
| Results at size | 9.2x fewer requests on repeated questions over 10.8M tokens; 6.1x over 7 codebases at once (7M tokens) |

- **Scope it.** Build one workspace over the repositories a team actually works in; one workspace over everything beat
  one per codebase in our test.
- **Recall falls as size grows.** First-time questions find their answer less often in the first readout. Repeated
  questions, drawn by a taught question's vector, hold up.
- **Rebuild after large code changes.** A rebuild starts fresh, and vectors taught to the old workspace are not carried
  over yet.

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
- **Taught vectors are append-only**, and they are not carried over a rebuild.
- **The tests are narrow:** open-source code and one client app, with Claude agents and judges. Your codebase is the
  real test.

Copyright (c) 2026 Devieswar Kancheti. Shared privately for evaluation; see `LICENSE`.
