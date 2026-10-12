# PROTOCOL_SWEQA: Model D on a public repository Q&A benchmark (fixed before any request)

**Benchmark:** SWE-QA (peng-weihan/SWE-QA-Bench, Apache-2.0, cloned 2026-10-09, `Benchmark/*.jsonl`): the 12 v1
repositories listed first in `repo_commit.txt`, 48 questions each (576), every repository checked out at its pinned
commit (sweqa/shas.txt). Each question has a reference answer written from the code.

**Kit:** Model D 0.2.1 as shipped (~/ocm-eval/venvs/t021), its index built over each whole repository with
`ocm build` (sweqa/ws/<repo>), nothing taught at the start.

**Arms** (claude-sonnet-5-5 explores in both; the tools are the same: search, read_file, list_files, 15 calls at most):
- **MODEL D:** `ocm.hybrid.run` as shipped, learning on. The kit's readout is given first. A learned match goes to
  the strict Haiku reader, and anything else goes to Sonnet with the readout, which then teaches the kit. Each
  repository's 48 questions are asked in the file's order, one after another, as a team would ask them.
- **ALONE:** Sonnet with the same tools, and a prompt that differs only by dropping the readout sentence
  (`harness.ALONE_SYS`). There is no kit and no learning. Answers are produced 3 in parallel.

**Grading:** SWE-QA's own judge rubric, verbatim (`Benchmark construction/score/llm-as-a-judge.py`): five dimensions
(correctness, completeness, relevance, clarity, reasoning), each 1-20, total out of 100.
- The judge is claude-sonnet-5-5, once per answer.
- The paper used GPT-5 with five votes. That is a deviation, fixed here.
- The judge is blind: it sees the question, the reference and one answer, never the arm, in shuffled order.
- An answer the judge's reply cannot be parsed for is reported as unparsed and left out of both arms' means.

**Budget and order:** this program may spend $35 of its own (the ledger at its first start, plus $35).
- Repositories run in a fixed order: sorted, then shuffled with Random(20261009):
  sqlfluff, sphinx, requests, xarray, pylint, django, astropy, pytest, flask, scikit-learn, matplotlib, sympy.
- Each repository runs whole: both arms, then grading.
- A new repository starts only if the spend so far, plus 1.15x the dearest finished repository, stays under the cap.
- Results are reported over the repositories finished in both arms and graded. The repositories not reached are named.

**Measures:** cost per question (the ledger's priced tokens), requests per question, the judge's total per answer,
and the share of Model D answers given by the reader (learned match). Model D minus ALONE comes with a paired
bootstrap (20,000 resamples by question, seed 20261008) for the score difference and for the cost ratio.

**Predictions**
- Q1: Model D costs less per question than ALONE: ALONE/MODEL D mean cost ratio at least 1.3.
- Q2: Model D's mean judged total is no more than 3 points (of 100) below ALONE's (non-inferiority).
- Q3: Within each repository, the saving grows: the cost ratio over questions 25-48 is at least the ratio over 1-24
  (pooled over finished repositories).
- Q4: fewer than 20% of Model D's answers come from the reader. These are 48 different questions per repository,
  so learned matches should be rare; the saving should come from the readout cutting search.

**Not claimed:** any comparison with the paper's published scores (different judge, scale and models). Only the
paired comparison on the same questions is reported.
