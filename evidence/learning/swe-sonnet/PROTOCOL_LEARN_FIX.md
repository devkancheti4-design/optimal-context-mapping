# Protocol: frozen kit vs a learning kit whose lessons are placed correctly (Claude Sonnet 5.5)

Fixed before any agent runs; its SHA-256 goes in prereg_hashes.json.

## Why
- **The defect** (PROTOCOL_LEARN_SONNET.md.deviations, DL2): every earlier lesson was taught at the gold line number of
  the issue's own base commit, inside a workspace built from the 4a72da7 snapshot. Only 29 of 114 lessons landed on the
  code holding the fix.
- **The fix:** swe_sonnet/readouts_snapline.py reads the gold line at the base commit (histories/django), maps it to the
  snapshot with a line diff, and teaches at the nearest line the workspace holds.
  - All 114 lessons are placed; 94 move from the old line number.
  - The readouts are deterministic: readouts_snapline.json.
- **The issues:** this corrected learning kit's readout differs from the never-taught kit's on 29 issues (20 repeat-file;
  10 in the first half, 19 in the second). On the other 85 issues the input is byte-identical, so learning cannot
  change their cost.

## Design
- **Issues:** those 29.
- **Arms:** KIT sessions of PROTOCOL_SWE_SONNET.md (same task text, scripts, 15-call limit). Only the readout differs:
  - **Z:** the frozen readout (readouts_frozen.json);
  - **C:** the corrected learning readout (readouts_snapline.json).
- **Replicates:** 4 per arm and issue, every session a fresh workflow subagent (type general-purpose, model "sonnet").
  Arms are interleaved by replicate and issue.
- **The prompt** is the earlier one, plus one sentence saying this is one session of a benchmark the user is running
  and asking the agent to do the task as written. In PROTOCOL_LEARN_SONNET.md, 13 of 180 sessions declined; this
  sentence is meant to stop that. Both arms get the same prompt.
- **Non-attempts:** a session that runs no tool script and no submit.sh counts as not attempted and is dropped, as in
  DL1.

## Measures
- **Primary:** tool calls per session (search, read, list) from calls.jsonl.
- **Secondary:** requests from the transcripts.
- **Right:** the submitted file is the gold file. The rate is taken over attempted sessions.
- **Factor:** Z / C, the sum over issues of the arm means. Its 95% interval is a paired bootstrap over issues (20,000
  resamples, seed 20261008).

## Predictions
- **F1.** C makes fewer tool calls than Z on the 29 issues: Z / C above 1.0, with the 95% interval above 1.0.
- **F2.** C's right rate is at least Z's.
- **F3.** The learning saving (Z − C mean calls, summed) is larger in the second half of the stream than in the first.
- **F4.** On the 20 repeat-file issues, Z / C is above 1.0. The interval is reported.
