# Protocol: Model D, the kit as brain and the LLM as eyes and body

Fixed before any call; its SHA-256 goes in prereg_hashes.json.

## The idea
- **The brain** (no model calls) decides how much of the LLM each task needs:
  - the CMLM: vectors, laws, the taught lane;
  - neo4d: verified fixes after self-mutation.
- **The eyes** (one call, no tools) look at what the brain hands over and answer.
- **The body** (the full agent with tools) works the task when the brain cannot.
- **The model** is gemini-2.5-flash on Vertex AI (project cmlm-bench), the same model as PROTOCOL_API.md and
  PROTOCOL_FIX.md.

## Routing (fixed)
- **Questions (transformers, the 60-question stream of PROTOCOL_LARGE.md).** The brain's readout comes from the kit at
  1d0008e.
  - **Taught lane** (the readout opens with "(readout: the code a taught question"): the eyes get one call with the
    question and the readout. The instruction is to answer from that code only, or to reply exactly NEED_SEARCH.
  - **An answer:** done, 1 request.
  - **NEED_SEARCH, or no taught lane:** the body runs the CMLM arm's agent.
- **Bugs (QuixBugs, 40 programs, PROTOCOL_FIX.md phase 2).**
  - **REPAIRED:** the brain applies neo4d's verified fix (0 requests). The program's tests confirm it.
  - **AMBIGUOUS:** the eyes get one call with the program and neo4d's verified candidates, and pick one; the tests
    check the pick. If it fails, the body runs the NEO4D arm's agent.
  - **REFUSED:** the body runs the NEO4D arm's agent.

## How it is measured
- **The brain's readouts.** The stream is replayed in order on a fresh copy of large/ws_L_base with the live L-CMLM
  agents' TEACH lines, as math_slices.py does. This gives the readout Model D's brain hands over for each question,
  and whether it is the taught lane.
- **The eyes.** 3 runs of every eyes call: questions on the taught lane, and bugs neo4d found AMBIGUOUS.
  - Logged: requests and billed tokens.
  - Question answers: a blind judge per judge/JUDGE.md, shuffled.
  - Bug picks: the program's own tests.
- **The body.** Body costs per question and per program come from the matching arms of PROTOCOL_API.md (CMLM arm, per
  question) and PROTOCOL_FIX.md (NEO4D arm, per program), in the same runs.
- **Model D's total.** Brain (0 requests) + eyes + body wherever the routing sends a task on. This is compared with
  ALONE and with CMLM / NEO4D on the same tasks.

## Predictions
- **D1.** On the taught lane, the eyes alone answer at least 25 of 30 questions right, with 1 request each, in every run.
- **D2.** Across the 60 questions, Model D makes at least 1.3x fewer requests than the CMLM arm and at least 2x fewer than
  ALONE, at equal right count (within 2).
- **D3.** On the 40 bugs, Model D makes fewer requests than the NEO4D arm and fixes at least as many.
- **D4.** Brain-only fixes (REPAIRED) pass their tests with 0 model calls.
