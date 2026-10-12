# PROTOCOL_RETEST: the same two benchmarks, with two unfairnesses removed (fixed before any request)

Two things in PROTOCOL_SWEQA and PROTOCOL_SWECB counted against Model D for reasons that are not the kit's decision:
1. **No prompt caching** (0 cache reads in the ledger). Every production agent caches. Without caching, the kit's
   readout, which sits in the first message, was billed in full on every request.
2. **Unequal answer standard on SWE-QA.** Model D's reader is told to answer in one to three sentences, and the
   judge's rubric scores completeness against long reference answers. So part of the score gap measured prose
   length, not the decision.

The original results stand as recorded. This is a new test.

**Caching:** every request in every arm sends top-level `cache_control: {"type": "ephemeral"}` (automatic caching).
Cache writes and reads are priced as in harness.PRICE.

**R1: SWE-ContextBench, the same 28 Django tasks, the same tools, prompts, kits and scoring** (`run_rt.py cb`).
- Arms: ALONE and COLD (Model D's kit readout, nothing taught).
- EXP is not rerun.
- Predictions:
  - RC1: COLD's cost per task is no more than ALONE's.
  - RC2: COLD resolves at least ALONE's count less 1.

**R2: SWE-QA, the first 3 repositories of the fixed order (sqlfluff, sphinx, requests), all 144 questions, the same
judge** (`run_rt.py qa`).
- Both arms get the same answer standard. The sentence "Answer completely: name the files, classes and functions
  involved and explain how they work." is added to ALONE's prompt and to Model D's teach prompt.
- Model D's Haiku reader gets: "You read code for an engineering team. Answer the question from the code below only,
  completely: name the files, classes and functions involved and explain how they work. If the code below does not
  contain everything the question asks for, reply exactly NEED_SEARCH."
- Model D's flow is otherwise as shipped: readout, then the reader when the readout is a learned match, else Sonnet
  with the readout, which then teaches the kit. Learning is on, and the questions go in file order.
- Repositories run concurrently.
- Predictions:
  - RQ1: Model D is at least 1.5x cheaper per question.
  - RQ2: Model D's judged total is no more than 2 points below ALONE's (paired, 95% CI reported).

**Budget:** R1 $5 and R2 $8 of their own spend. Results are reported over finished items.
