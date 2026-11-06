# Model D on Agent Retrieval Bench (written 2026-11-05, before any Model D result on it)

**The question:** with no model calls, how well does Model D find the files a coding agent needs next, on a benchmark built
by others, against the baselines and the community result they publish?

**The benchmark:** Agent Retrieval Bench (arXiv 2607.24882), MIT, evaluator at
github.com/eyuansu62/agent-retrieval-bench commit 9e4d689; data from `eyuansu71/agent_retrieval_bench`, sha256 of each
`samples.jsonl` recorded in `HASHES.txt`. Tracks: `trace2code` (101), `edit2ripple` (58), `comment2context` (80),
`code2test` (106). `trace2code` runs first because it is the smallest; the others follow as disk allows. The abstention track
gets its own protocol first.

**Model D:** 0.5.3 exactly as released, the same for every track. No change, setting or tuning for this benchmark, and no
track or sample is left out of what is reported. Nothing is taught. No model calls: Model D's embedder runs locally.

**The method (`run.py`), for each sample:**
- **Source:** a fresh folder from the `kind=file` rows of the released corpus at the sample's `base_commit`, then `build`.
  Files Model D doesn't index can't be found, and that counts against it.
- **Query:** all strings in the sample's `query` object, shortest first, joined with blank lines (the rendering the Oko
  community result used), with no cut.
- **Ranking:** the files of `ask` (code scope), in order; then `next` until it has no more readouts; then the rest of Model
  D's own ranking by meaning (`Memory._rank`) to complete the list. So the top of the list is what an agent would really
  read, and the tail only serves Recall@20 and MRR when the gold file is deep.

**Measures:**
- Recall@5, Recall@10, Recall@20 and MRR from the benchmark's own `sample_metrics`.
- BCY at 4k, 8k, 16k and 32k from its own `report_bcy_budget_curve`, on the stored top 20.
- Tokens in Model D's first readout, and whether a gold file is already in it.
- A secondary run with `OCM_TESTS_TRAIL=off`, reported as a diagnostic, not as the result. It tells us what the shipped
  tests-after-code order costs on `code2test`.

**The bars, as published on 2026-11-05:**

| | MRR | Recall@20 | BCY@8k |
|---|---|---|---|
| Best official baseline over all 345 (a different one for each measure) | 0.2379 | 0.7029 | 0.3788 |
| Community result, Oko 0.9.1 (a paid reranker; partly tuned on these samples) | 0.4043 | 0.7019 | 0.5326 |

| track | best official MRR | Oko 0.9.1 MRR |
|---|---|---|
| `trace2code` | 0.2742 | 0.736 |
| `comment2context` | 0.3043 | 0.280 |
| `code2test` | 0.3225 | 0.279 |
| `edit2ripple` | 0.2877 | 0.226 |

**Predictions:**
- **R1:** on `trace2code`, Model D's MRR beats the best official baseline (0.2742). Failure traces name exact symbols.
- **R2:** on `trace2code`, Model D's MRR stays below Oko 0.9.1 (0.736).
- **R3:** over all 345 samples, Model D's MRR beats the best official baseline (0.2379) and stays below Oko 0.9.1 (0.4043).
- **R4:** `code2test` is Model D's weakest track by MRR, and below the best official MRR there (0.3225), because Model D
  puts tests after the code they test unless the question is about tests.

**Reporting:** every prediction is reported as held or failed, including R1–R4 if Model D loses. Any later change made
because of these results is reported as a separate run.
