# PROTOCOL_VALUE4: Model D on a real application, a five-role team's question stream (fixed before any request)

Prices, the ALONE arm, MODEL D (the shipped `ocm.hybrid.run`, Claude provider), statistics and the ledger are as in
PROTOCOL_VALUE.md. The cap for all batches together stays $175.

**Data**
- Codebase: the Full Stack FastAPI Template (cmlm-bench10/corpus): a FastAPI + SQLModel backend, a React frontend,
  Docker Compose and CI.
- Workspace: built fresh by the compiled package.
- Questions: questions_100.json, the earlier team study's 100 questions in qid order. Five roles (lead, backend,
  frontend, DevOps, new joiner) ask them as a team would. 26 are marked counts_as_repeat: a teammate already asked for
  that fact in other words.

**Runs**
- Three runs, each with a fresh workspace for MODEL D, learning on, in stream order.
- ALONE asks the same questions.

**Right:** the submitted path:line (or, on the read path, the first item of the readout the reader was given) is in one
of the question's evidence files.

**Predictions** (pooled over the 3 runs, intervals by paired bootstrap over question-runs)
- C1: MODEL D's list-price cost is lower than ALONE's (interval above 1.0).
- C2: MODEL D's accuracy is within 5 points of ALONE's.
- C3: on the repeat questions, MODEL D is at least 3x cheaper.
- C4: MODEL D's read path answers at least 50% of the repeat questions.
- C5: the cost factor over questions 51–100 is higher than over questions 1–50 (coverage grows as the team teaches).
- M1 and M2 (turn law, session-cost law) on the pooled runs, with value 1's 20% criteria.
