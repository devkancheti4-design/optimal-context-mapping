# Results: final Model D against Graphify (PROTOCOL_VS_GRAPHIFY.md, Addendum A1)

- **Versions:** Model D 0.5.0 (commit 418dc602) and Graphify 0.9.92 from PyPI. Graphify was queried through its own MCP
  server with its defaults.
- **The plan:** hashed before the first readout (PREREG_HASHES.txt).
- **Deviations:** D1 and D2. The Anthropic API credit ran out during the run. Part A is complete except for coverage
  on 6 large Lite repositories; Part B is interim.

## The difference in one line
Graphify gives Claude a neighbourhood of its graph to explore, about 1,500 tokens per query. Model D gives it a pointer,
about 400 tokens, and one item when the code is learned.

## Part A: pointing, offline (complete)

**Django 2022, the 288 real fixes**, asked as "Where is the code behind this change: <subject>":

| | right file first | top 3 | top 5 | tokens per readout |
|---|---|---|---|---|
| **Model D, taught once (`modeld cover`, $0.97)** | **149** | **185** | 193 | **390** |
| Model D, cold | 111 | 170 | **197** | 735 |
| Graphify 0.9.92 | 89 | 121 | 137 | 1,537 |

- **Paired, right first:** taught Model D against Graphify, 89 found by Model D only and 29 by Graphify only
  (p = 2.8e-8). Cold Model D against Graphify, 62 against 40 (p = 0.037).
- **Top 5:** cold Model D against Graphify, 90 against 30 (p = 3.8e-8).
- **Coverage replicated:** with a fresh set of generated questions, cold 111 became 149 (68 against 30, p = 0.00016).
  The first coverage run gave 142. The top 5 again did not improve (193 against 197, p = 0.72).
- **With the subject alone:** 155 / 111 / 91 right first, the same order.

**SWE-bench Lite, 285 issues in 12 repositories**, right first / top 3 / top 5:

| query | Model D, taught* | Model D, cold | Graphify 0.9.92 | tokens (cold / Graphify) |
|---|---|---|---|---|
| issue title | **87** / 152 / 176 | 80 / **154** / 176 | 78 / 115 / 131 | 634 / 1,500 |
| title + 400 characters | **99** / 159 / 181 | 96 / 161 / **183** | 67 / 99 / 122 | 700 / 1,674 |

- **\*Coverage was taught on 6 of the 12 repositories (D2).** On those 6 repositories' 40 issues, titles, the right
  file came first 14 times taught, against 7 cold and 10 for Graphify.
- **Top 5 on titles, paired:** cold Model D against Graphify, 72 against 27 (p = 6.9e-6).
- Graphify 0.9.92 listed the same top-5 files as 0.9.87 on 371 of 396 readouts checked.

## Addendum A1: Graphify's "71.5x fewer tokens"
The figure is the size of the whole corpus divided by one `query_graph` answer (`graphify/benchmark.py`).

| formula run on | result |
|---|---|
| Graphify's own Karpathy example (92,616 words), 0.9.92 code | **33.0x** (answers now average 3,742 tokens; 71.5x was measured with an April build) |
| Django 2022 (2,036,363 words), Graphify, the 288 real questions | 1,787x |
| Django 2022, Model D cold / taught, same formula | 3,695x / 6,970x |

The ratio grows with the size of the repository for any tool. It does not measure what an agent spends. Part B does.

## Part B: end to end with the same Claude (interim: the API credit ran out, D1)
Paired on the 236 fixes Claude + Graphify reached. Model D cold and Claude alone come from the earlier team-year runs,
in the same harness.

| | bill | requests | $ per request | right |
|---|---|---|---|---|
| Claude alone | $20.81 | 1,315 | 0.0158 | 213 |
| Claude + Graphify | $21.84 | 1,136 | 0.0192 | 210 |
| **Claude + Model D (cold)** | **$10.27** | **961** | **0.0107** | 210 |

- **Claude + Graphify:** 14% fewer requests than alone, but each carries more tokens, so the bill is 5% higher. Right
  answers are level with alone (4 against 7, p = 0.55).
- **Claude + Model D:** 27% fewer requests, each 32% cheaper, so the bill is 2.03x lower at the same right count.
- **Model D final (taught once, learning as it goes):** reached 110 of 288 before the credit ran out.
- **G5–G7 are not decided.** They need the full 288. The scorer's G5–G7 output on the partial overlap is not a
  result.

## Predictions
- **G1 held:** Django, taught Model D right first 149 > Graphify 89.
- **G2 held:** Lite titles, cold Model D top 5 176 > Graphify 131.
- **G3 held as written:** Lite titles, right first 87 > 80. Only 6 of 12 repositories were covered (D2).
- **G4 held:** Model D's readouts are smaller than Graphify's on all four query sets (390–735 tokens against
  1,494–1,674).
- **G5, G6 and G7 are open.** Part B is incomplete (D1).

## Spend
- `modeld cover`: $0.97 for Django and $1.49 for 6 Lite repositories.
- Claude + Graphify: $21.84 over 236 fixes. Model D final: $2.46 over 110 fixes.
