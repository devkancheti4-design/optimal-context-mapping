# PROTOCOL_VALUE3: deep web research, long-running sessions, deep thinking (fixed before any request of this batch)

Prices, ALONE's tools and prompt, scoring by file, statistics and the ledger are as in PROTOCOL_VALUE.md. The cap for
all three batches together is now $175 on the shared ledger.

Batch 3's MODEL D runs in two forms, both the shipped decision logic:
- **G1 and G3, the hybrid.** The kit readout first. A claude-haiku-5-5 read (READ prompt) when the readout is the
  taught one and the read answers. Otherwise a claude-sonnet-5-5 teach (TEACH prompt with the readout) and a lesson on
  the submitted line. Batch 3 runs this decision in the harness (as E6 did), so it can add web search (G1) and effort
  (G3).
- **G2, in the loop.** The Claude Code hook design: every user turn carries the kit readout, and every submitted line
  is taught after the answer.

## G1: deep web research (multi-hop)
- Questions: 30 django tickets from replay/stream.json, sampled with seed 20261010. Each was fixed between 2022-01-01
  and 2023-07-06, by a commit naming one ticket, and changed one or two django/ files that exist at the snapshot.
- Pass 1: 'Django ticket #<N>: "<commit subject>". Research it (the ticket, its fix and the code) and tell me which
  file in Django's source the fix changed and, in one sentence, what was wrong.'
- Pass 2: 'Which Django source file was changed to fix ticket #<N> (<commit subject>)?'
- Both arms have web search (at most 8 uses) and the code tools.
- Right: the answer or the submitted path names a file the fix changed (by path or dotted module).
- G1a: pass 1, MODEL D is at least 1.3x cheaper than ALONE.
- G1b: pass 1, MODEL D's accuracy is within 3 of ALONE's.
- G1c: pass 2, MODEL D is at least 4x cheaper than ALONE.

## G2: long-running sessions
- Sessions: 3, each one conversation working through 15 of the django reports in order (E1's first 45), with the
  whole transcript kept.
  - After each submit, the next report arrives in the same conversation.
  - Prompt caching is on for both arms: an ephemeral cache breakpoint on the newest user block, as agent tools do.
  - At most 15 tool calls per report.
- Arms:
  - ALONE: the same tools, no readout.
  - MODEL D in the loop: each report arrives with the kit's readout, and each submitted line is taught after the
    answer (a fresh workspace per session).
- G2a: in each of the 3 sessions, MODEL D's total cost is lower than ALONE's.
- G2b (compounding): pooled over the sessions, the cost factor (ALONE / MODEL D) over reports 9–15 is larger than over
  reports 1–7.
- G2c (the maths, theorem 4 of the CTO proof): the session-level token factor exceeds the per-report request factor.
  When a transcript is carried, removing turns saves more than its share.

## G3: deep thinking
- Data: the 30 django reports on which ALONE needed the most requests in E1 (ties broken by tokens), in E1 order.
- Settings: both arms at `output_config={"effort": "max"}`, `max_tokens` 16000. MODEL D's reads stay at Haiku's
  default.
- MODEL D runs on a fresh workspace, with learning on.
- G3a: MODEL D needs fewer requests than ALONE (interval above 1.0).
- G3b: MODEL D's cost is lower than ALONE's (interval above 1.0).
- G3c: MODEL D's accuracy is within 3 of ALONE's.

## Honesty
- Deviations go in PROTOCOL_VALUE3.md.deviations before the affected numbers are read.
- Every prediction is reported held or failed.
