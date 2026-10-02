# Optimal Context Mapping

**A shared workspace memory your team's AI agents ask first and teach back, so the same research is not paid for twice.**

When engineers use AI agents (Claude Code, Cursor, Windsurf and others) on the same codebases, each agent searches and
re-reads the code on its own, every time, and each step is a paid model request. Optimal context mapping gives the whole
team one workspace over its code and docs: an agent asks it first, gets the few code blocks, sentences or teammates'
notes most likely to answer, searches only when that misses, and at the end teaches back what it found in one call.
The next person's agent, asking the same thing in other words, gets the answer straight away.

## What it achieved in our tests

Live, pre-registered tests with fresh Claude agents and blind judges (details and evidence in `results/RESULTS.md`):

| test | accuracy | model requests |
|---|---|---|
| A seven-role project team (PM, team lead, senior, backend, frontend, junior, HR) on a real codebase plus web research | same (41/41 both ways) | **1.66x fewer** with batched teaching; research (searches and reads) halved |
| Single-fact questions over 7 real codebases (7M tokens) | same (28/28) | **6.1x fewer**, billed input 2.8x lower |
| Repeated questions on a 10.8M-token codebase (a teammate asked before, in other words) | same (30/30) | **9.2x fewer** |
| Multi-file deep dives | same (40/40) | 1.2x fewer (the honest weak spot) |

The cost arithmetic in this kit predicted a live run before it ran: 83 requests predicted, **84 measured**; 1.66x
predicted, **1.66x measured**. `python -m ocm calc` uses the same arithmetic on your mix of questions.

## How it works

1. **Build** a workspace over your repositories and docs: every code block and doc sentence becomes a 1,024-bit meaning
   fingerprint, made by a small embedding model on your machine. Nothing is sent anywhere.
2. **Serve** it to the team. The router law (eight free checks, no model) picks each readout: the one note a teammate
   taught for this question, or the 10 best units by meaning, by keyword, or both.
3. **Connect** each person's agent through the MCP plugin: four tools, `workspace_ask`, `workspace_next`,
   `workspace_recall`, `workspace_teach`.
4. **Teach**: at the end of a session the agent teaches every finding in one call. Notes never overwrite anything.

## Quick start

```bash
pip install -e .                                   # Python 3.10+; numpy, torch, transformers
python -m ocm build ~/code/our-service ~/code/our-docs --out ~/ocm-workspace
python -m ocm serve ~/ocm-workspace --port 7700    # one per team; --host 0.0.0.0 to share on your network
```

Connect Claude Code (or any MCP client) to it: add to the project's `.mcp.json` (Cursor: `.cursor/mcp.json`, same shape)

```json
{"mcpServers": {"ocm": {"command": "python", "args": ["-m", "ocm", "mcp"], "env": {"OCM_URL": "http://127.0.0.1:7700"}}}}
```

and add `pilot/AGENT_INSTRUCTIONS.md` to the project's `CLAUDE.md` (or your agent's rules file), so agents ask the
workspace first and teach once at the end.

## Run a pilot

`pilot/PILOT.md` is a two-to-four-week plan: two comparable groups (or two periods), the same kind of work, measured from
the agents' own transcripts with `python -m ocm measure compare <before> <after>`. Fix the plan before you start
(`pilot/PREREGISTRATION.md`).

## Privacy

Everything runs on your machines. The embedding model is downloaded once from Hugging Face (set `OCM_OFFLINE=1`
afterwards); your code, questions and notes never leave your network. The builder skips `.env` files, keys,
certificates, credential files, lockfiles, dependency and build folders, and anything over 512 KB.

## Limits, stated plainly

- Savings come mostly from **repetition**: the more your team asks about the same code, the more it saves. Brand-new,
  one-off questions save less (about 2.4x fewer requests on lookups, about 1.6x with deep dives in the mix).
- **Deep dives** that chain across many files save little today: a taught note covers one answer, not a whole trail.
- **Billed input falls less than requests** (1.40x when requests fell 1.66x), because the readouts add reading.
- Notes cannot be edited once taught (append-only); rebuild the workspace after large code changes.
- Tested on open-source libraries, one client app and a web snapshot, with Claude agents and judges; your codebase
  is the real test.

Copyright (c) 2026 Devieswar Kancheti. Shared privately for evaluation; see `LICENSE`.
