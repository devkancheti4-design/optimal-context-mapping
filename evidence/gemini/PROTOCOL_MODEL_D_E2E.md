# Protocol: Model D end to end, one model, routing live

Fixed before any call; its SHA-256 goes in prereg_hashes.json. It runs PROTOCOL_MODEL_D.md and its amendment live, with
every part on gemini-2.5-flash on Vertex AI (project cmlm-bench).

## Questions (the 60-question stream of PROTOCOL_LARGE.md, transformers 10.8M tokens)
- **Runs:** 3, each with a fresh copy of large/ws_L_base, resident in the harness.
- **For each question, in stream order, the kit decides:**
  - **Taught lane** (the readout opens with "(readout: the code a taught question"): the eyes make one call with no
    tools, using the question and the readout, with the instruction of PROTOCOL_MODEL_D.md. If the eyes answer, the
    question is done. If they reply NEED_SEARCH, the body runs.
  - **Otherwise:** the body runs. That is a fresh agent session for this one question, with the CMLM arm's prompt,
    tools, readout and RULE (api_bench.py), at most 15 tool calls (enforced as D2). Its TEACH pair is taught.
- **Model D keeps no transcript between questions;** the kit is the memory.

## Bugs (the 40 QuixBugs programs, PROTOCOL_FIX.md)
- **Runs:** 3.
- **REPAIRED and AMBIGUOUS:** the kit applies its pick (neo4d's first verified candidate in law order, 0 calls), checked
  by the tests. If the tests fail, the body runs.
- **REFUSED:** the body runs, which is the NEO4D arm's agent session (agent_fix.py).

## Measures
- Per run: requests, billed tokens, dollars (gemini-2.5-flash list price, reports/common.py), seconds, and the right count:
  - questions: a blind judge per judge/JUDGE.md;
  - bugs: the program's tests.
- **Questions compared with** PROTOCOL_API.md's ALONE and CMLM arms: same model, same stream, same runs.
- **Bugs compared with** PROTOCOL_FIX.md's ALONE and NEO4D arms.
- **Intervals:** paired bootstrap, 95%, 20,000 resamples: over questions for the question stream, over programs for the
  bugs.

## Predictions
- **E1.** Questions: Model D makes at most half of ALONE's requests per question, and fewer than CMLM's. Its right count
  is within 2 of ALONE's per run.
- **E2.** Questions: Model D's dollars per question are lower than ALONE's, with the 95% interval of the factor above 1.0.
- **E3.** Bugs: Model D makes fewer requests than both ALONE and NEO4D, and fixes at least as many as ALONE per run.
- **E4.** Every taught-lane question is answered by the eyes in 1 request in at least 2 of 3 runs.
