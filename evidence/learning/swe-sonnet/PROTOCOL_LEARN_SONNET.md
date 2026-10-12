# Protocol: does the kit save more because it learned? Same issues, frozen kit vs learning kit (Claude Sonnet 5.5)

Fixed before any agent runs; its SHA-256 goes in prereg_hashes.json.

## Why
- **S4 and S5 of PROTOCOL_SWE_SONNET.md failed.** Those verdicts stand.
- **They compared different issues:** the first half of the stream against the second, and new files against repeat
  files. Issue difficulty changed between those groups: ALONE needed 5.32 requests per issue in the first half and 5.72
  in the second, and was right on 57/57 and 54/57.
- **The audit** (audit_learning.py, readouts_fixed.py, no model calls) found:
  - 104 of the 114 lessons were placed. The other 10 pointed at a line the workspace does not hold, such as a blank
    line.
  - The frozen kit (never taught) already shows the gold file on 99 of 114 issues; the learning kit shows it on 101.
  - Learning changed the readout on 28 issues (20 of them repeat-file), with more in later quarters: 3, 7, 7, 11.
  - Placing all 10 lessons at the nearest held line changes 3 more readouts.
- **On the other 86 issues,** the frozen and learning kits give the agent byte-identical input, so learning cannot change
  their cost.
- **The test of "saves more as it learns"** is therefore the same issues, with and without what was learned.

## Design
- **Issues:** the 29 issues whose readout differs between the frozen kit and either learning kit. All three readout sets
  are deterministic and computed already.
- **Arms:** KIT sessions of PROTOCOL_SWE_SONNET.md, with the same task text, scripts and 15-call limit. Only the readout
  differs:
  - **Z (frozen):** the readout of swe/ws_base, never taught (readouts_frozen.json).
  - **L (learning, as run):** the readout of the learning kit in PROTOCOL_SWE_SONNET.md (readouts.json), on the 28
    issues where it differs from Z.
  - **X (learning, every lesson placed):** readouts_fixed.json, on the 3 issues where it differs from L.
- **Replicates:** 3 per arm and issue, every session a fresh subagent. All sessions run in one batch, in the same harness
  (workflow subagents, type general-purpose, model "sonnet"). Results are never mixed with the PROTOCOL_SWE_SONNET.md
  sessions.

## Measures
- **Primary:** the agent's own tool calls per session (search, read, list), from each folder's calls.jsonl. This does
  not depend on the harness.
- **Secondary:** requests per session, from the transcripts, where the transcripts can be found.
- **Right:** the submitted file is the gold file.
- **Factor:** Z / L, the sum over issues of the mean calls across replicates. Its 95% interval is a paired bootstrap
  over issues (20,000 resamples, seed 20261008).
- **Learning saving over the stream:**
  - on each issue the learning touched, the measured Z − L mean calls;
  - 0 by construction on the 86 issues where the input is identical.
  - This is summed by quarter and by half of the stream.

## Predictions
- **L1.** On the 28 issues where learning changed the readout, the learning kit makes fewer tool calls than the frozen
  kit: Z / L above 1.0, with the 95% interval above 1.0.
- **L2.** The learning kit is right at least as often as the frozen kit, summed over the 3 replicates on those issues.
- **L3.** The learning saving (Z − L calls, summed) is larger in the second half of the stream than in the first.
- **L4.** On the repeat-file issues among the 28, Z / L is above 1.0. This is reported with its interval; with 20 issues
  it is a weaker test.

## Also run (audit, no prediction)
- Two independent checks of the S4/S5 numbers in report_swe_sonnet.json, recomputed from the raw answer files and
  transcripts without report.py.
- A code review of report.py, transcripts.py and readouts.py for anything that would bias S4/S5.
