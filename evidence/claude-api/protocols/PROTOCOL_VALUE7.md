# PROTOCOL_VALUE7: fixing the cheap read (fixed before any request)

V4's blind judge found Model D's teach path as accurate as ALONE (87% against 86% judged right). The cheap Haiku read
was usually only partly complete: 22 right, 41 partial and 7 wrong of 70. This tests three changes to the read step on
the same company repo. The reader already sees the kit's next readout whenever the first readout is a learned match.

**Setup**
- Data: V4's codebase, workspace build and 100 team questions, in qid order.
- Runs: one run per variant, each on a fresh workspace copy, learning on.
- The teach step is unchanged (claude-sonnet-5-5 with the shipped TEACH prompt and tools).
- Reader prompts:
  - STRICT: "You read code for an engineering team. Answer the question from the code below only, completely, in one
    to three sentences. If the code below does not contain everything the question asks for, reply exactly
    NEED_SEARCH."
  - READ: the shipped prompt.
- Variants:
  - S, strict Haiku: claude-haiku-5-5 with STRICT.
  - N, Sonnet reader: claude-sonnet-5-5 with READ.
  - NS, Sonnet strict: claude-sonnet-5-5 with STRICT.
- Judge: V4's corrected blind judge (value/judge4.py's prompt and VERDICT parser), shuffled with seed 20261012.
- Baselines: V4's judged ALONE (85.7% right) and V4's judged MODEL D (74.0% right, $0.0099 per question).

**Predictions**
- Q1: at least one variant is judged RIGHT on at least 80.7% (ALONE less 5 points) and stays at least 2x cheaper than
  V4's ALONE ($0.0276 per question).
- Q2: S raises the share of reads judged RIGHT above V4's 31%.
- Q3: N's reads are judged RIGHT at least 60% of the time.
