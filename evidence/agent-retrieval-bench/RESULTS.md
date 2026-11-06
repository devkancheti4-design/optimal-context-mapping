# Model D on Agent Retrieval Bench: results (2026-11-06)

All 345 positive samples on all 4 tracks. Model D 0.5.3 as released (commit `ec440d7`), nothing taught, no model calls. Plan: `PROTOCOL.md`, hashed before
any Model D result, with one deviation in `PROTOCOL.md.deviations` (the run stopped and resumed; its method didn't change). Code: `run.py`, `score.py` and
`run_tracks.sh`; every ranking is in `results/`, and `report.py` prints every number here into `report.txt`.

**Model D did not beat the published baselines.** It ranks 7th of 9 on MRR, 8th of 9 on Recall@20 and 7th of 9 on BCY@8k, and three of my four predictions
failed. It beats BM25 on all three measures. RepoMap, which uses no embedding model, beats Model D on all three.

| method | MRR | Recall@20 | BCY@8k |
|---|---|---|---|
| Oko 0.9.1 (community; paid reranker, partly tuned on these samples) | 0.4043 | 0.7019 | 0.5326 |
| CodeNib dense (community) | 0.2425 | 0.5736 | 0.3355 |
| Qwen3-Embedding-4B | 0.2379 | 0.6306 | 0.3409 |
| Qwen3-Embedding-8B | 0.2336 | 0.7029 | 0.3732 |
| pplx-embed-v1-4b | 0.2267 | 0.6072 | 0.3549 |
| RepoMap | 0.2158 | 0.6333 | 0.3788 |
| CodeNib hybrid (community) | 0.2144 | 0.5972 | 0.3101 |
| nomic-embed-code | 0.1986 | 0.5244 | 0.2781 |
| jina-code-embeddings-0.5b | 0.1914 | 0.4823 | 0.2783 |
| **Model D 0.5.3** | **0.1904** | **0.4721** | **0.2674** |
| CodeNib Zoekt (community) | 0.1605 | 0.4400 | 0.2569 |
| Lexical | 0.1574 | 0.4940 | 0.2650 |
| BM25 | 0.1520 | 0.4452 | 0.2051 |
| CodeNib BM25 (community) | 0.1211 | 0.3889 | 0.1659 |
| CodeNib graph expansion (community) | 0.1197 | 0.3498 | 0.1659 |

Model D's 95% bootstrap intervals over its 345 samples: MRR 0.1617 to 0.2210, Recall@20 0.4244 to 0.5201. The others are published means, so there is no paired
test here. The plan's bars left out CodeNib's rows, which are on the same page as Oko's; they change no verdict.

| track | n | MRR (95%) | R@5 | R@10 | R@20 | BCY@8k | gold in first readout | first readout tokens | best official MRR | Oko 0.9.1 MRR |
|---|---|---|---|---|---|---|---|---|---|---|
| `trace2code` | 101 | 0.2243 (0.1654 to 0.2884) | 0.3102 | 0.3845 | 0.4785 | 0.3152 | 38.6% | 562 | 0.2742 | 0.736 |
| `edit2ripple` | 58 | 0.2292 (0.1617 to 0.3068) | 0.3003 | 0.4023 | 0.5086 | 0.3261 | 34.5% | 816 | 0.2877 | 0.226 |
| `comment2context` | 80 | 0.1518 (0.1088 to 0.2033) | 0.1854 | 0.3146 | 0.4521 | 0.2396 | 23.7% | 679 | 0.3043 | 0.280 |
| `code2test` | 106 | 0.1659 (0.1170 to 0.2208) | 0.1682 | 0.2862 | 0.4610 | 0.2107 | 23.6% | 729 | 0.3225 | 0.279 |
| **all** | **345** | **0.1904 (0.1617 to 0.2210)** | **0.2360** | **0.3411** | **0.4721** | **0.2674** | **29.9%** | **683** | **0.2379** | **0.4043** |

BCY over all 345 is the sample-weighted mean of the tracks. Model D is below the best official MRR on every track.

**Predictions:**

| | result | |
|---|---|---|
| R1: `trace2code` MRR beats the best official, 0.2742 | 0.2243 | **failed** |
| R2: `trace2code` MRR stays below Oko, 0.736 | 0.2243 | held |
| R3: MRR over all 345 beats 0.2379 and stays below 0.4043 | 0.1904; the top of its interval, 0.2210, is under 0.2379 | **failed** |
| R4: `code2test` is the weakest track and below 0.3225 | 0.1659 is below 0.3225, but `comment2context` is weaker at 0.1518 (their intervals overlap) | **failed** |

**R4's reason was wrong too.** I said Model D would lose on `code2test` because it puts tests after code. But 93 of its 106 queries mention tests, so that rule
stays off for them, and switching the rule off adds only 0.0010 MRR there.

**The tests-after-code rule on this benchmark (`OCM_TESTS_TRAIL=off`, a diagnostic).** MRR over all 345 goes from 0.1904 to 0.1950 with the rule off (+0.0047,
+0.0007 to +0.0102). It changed 12 samples, all 12 better with it off. The rule only reorders inside one readout, and about half the gold files on `edit2ripple` and `comment2context` are tests.

## Why it lost (found after the run, not predicted)

**Model D doesn't rank the kind of file the task needs.**

| track | gold files that are tests | tests in Model D's top 5 |
|---|---|---|
| `trace2code` | 0 of 127 | 59% |
| `edit2ripple` | 48 of 99 | 13% |
| `comment2context` | 62 of 140 | 25% |
| `code2test` | 146 of 148 | 19% |

All 101 failure traces name tests, so tests crowd the top when the file to fix is never a test. On `code2test` the reverse happens.

**An estimate of the size of this, from reordering the saved lists.** This is not a run of Model D: it moves test files to the end or the front of each list
it already produced.

| | MRR as run | MRR reordered | change (95%) | Recall@20 as run | Recall@20 reordered |
|---|---|---|---|---|---|
| `trace2code`, tests last | 0.2243 | 0.3766 | +0.1523 (+0.1093 to +0.2007) | 0.4785 | 0.6403 |
| `code2test`, tests first | 0.1659 | 0.4485 | +0.2826 (+0.2250 to +0.3430) | 0.4610 | 0.7132 |

With `trace2code` changed alone, MRR over all 345 would be 0.2350, about level with the best official. With both, 0.3218. These numbers can't be set against
the table above:
- Both moves were found on the samples they are measured on, and a real change may gain less.
- `code2test` queries are only a changed file, a PR title and a PR body. They don't say tests are wanted, so tests-first needs the task from outside the query.
- The benchmark's official results use all files and treat task-aware filters as diagnostics. The baselines could gain from the same moves.

A failure trace can be recognised from its own text, so the `trace2code` move is the one a real change could make without being told the task.

**Most queries are longer than the embedder reads.** It reads 128 tokens, and 265 of the 345 queries are longer. In every track with both groups, the shorter queries
score higher: `trace2code` 0.363 against 0.206, `comment2context` 0.166 against 0.145, `code2test` 0.191 against 0.150. This isn't a controlled test, and even the
short group's MRR (0.209) is below the best official 0.2379. Oko cut queries at 4,000 bytes and CodeNib's dense model at 512 tokens.

**Scores differ widely by language, but Go carries the total.** Go 0.280 (142 samples), Rust 0.141 (54), TypeScript/JavaScript 0.132 (36), Python 0.123 (104), Java
0.078 (9). One repository, `gin-gonic/gin`, is 88 of the 345 samples; without it, MRR is 0.1576. Repository, language and track are all mixed here.

**Click scores below a random order, and that's real.** Its MRR is 0.031 against 0.051 for a random order of the same lists. I checked for a setup error: gold paths
resolve, and the stored scores match a recount. All 26 Click samples are `trace2code`, and test files and CI configuration such as `.github/workflows/tests.yaml` fill
the top. Over all 345, Model D scores 0.1904 against 0.0246 for a random order, and 84 samples fall below their random expectation.

**The index isn't the problem.** Only 2 of the 514 gold files were missing from Model D's lists.

## What this doesn't show

- **Memory.** Nothing was taught, so lessons, repeat questions and sessions are untested here.
- **The size of Model D's readouts.** BCY packs whole ranked files, not Model D's short readouts. A gold file was in the first readout on 29.9% of samples at 683
  tokens on average, and no published result gives a comparable number.
- **The no-gold cases.** The abstention track (82 samples) didn't run. It needs its own protocol first.

Having no model calls isn't an edge over every baseline here: RepoMap, Lexical and BM25 use no model at all. Across the run, the ranking took 0.44 s per sample on average, and index builds took
about 13,200 s in all, which is only indicative because the run was paused and resumed.

## Reproduce

`report.py` reprints every number from `results/`. To run it all again from the benchmark (about 1 GB of downloads, deleted track by track as it goes):

```bash
git clone https://github.com/eyuansu62/agent-retrieval-bench ~/arb-work/agent-retrieval-bench
git -C ~/arb-work/agent-retrieval-bench checkout 9e4d689
./run_tracks.sh
python pack.py
python report.py > report.txt
```

Use a Python with Model D 0.5.3 and the benchmark's package installed; `run_tracks.sh` names the paths it used. Any later change to Model D made because of these results
is reported as a separate run.
