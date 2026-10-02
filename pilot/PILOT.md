# A two-to-four-week pilot

**Goal:** measure, on your own codebase and your own team's work, how many model requests and how much billed input
the workspace saves, at the same quality.

## Setup (day 1)
1. Build one workspace over the repositories and docs the team works on (`python -m ocm build ... --out ...`) and serve
   it (`python -m ocm serve ...`) on a machine everyone's agents can reach.
2. Pick two comparable groups doing the same kind of work (for example two squads on the same services), or one group
   in two periods (two weeks without, then two weeks with).
3. Group B adds the MCP plugin (`.mcp.json`) and `AGENT_INSTRUCTIONS.md`. Group A works as usual.
4. Write down the plan before starting (`PREREGISTRATION.md`): who, how long, what counts.

## During
Work as normal. Nothing else changes. The workspace logs its calls to `<workspace>/calls.jsonl`.

## Measure (end)
Claude Code keeps every session's transcript under `~/.claude/projects/<project>/`. Collect each group's transcripts for
the pilot window into two folders, then:

```bash
python -m ocm measure compare group-a/ group-b/ --since 2026-11-01 --until 2026-11-14
```

It prints model requests and input billed (raw and cache-weighted) per session for both groups, and their ratio.

## Quality
Sample 30 to 50 answers or changes from each group and have a senior engineer grade them blind (without knowing the
group). The workspace should not change quality; check it did not.

## Predict first
Before the pilot, estimate your mix and run the calculator:

```bash
python -m ocm calc --repeat 0.5 --deep 0.3 --questions-per-month 16800
```

Write the prediction into `PREREGISTRATION.md`; compare it with what you measure.
