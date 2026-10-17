# Addendum A1 to PROTOCOL_VS_GRAPHIFY: Graphify's "71.5x fewer tokens" (written 2026-10-17, before computing it)

## The claim
Graphify's docs (docs/how-it-works.md at 0.9.92) say: "71.5x fewer tokens per query vs reading the raw files directly".
That was on its Karpathy corpus of 52 files. `graphify/benchmark.py` computes it as:
- **corpus tokens:** total words × 4/3;
- **divided by query tokens:** the mean characters / 4 of `query_graph` answers (BFS, depth 3, budget 2,000) to five
  sample questions.

## Tests (offline, $0, except where Part B already spends)
1. **Their number, their way:** `run_benchmark` on Graphify's own `worked/karpathy-repos/graph.json` (0.9.92 code).
2. **Their formula on real code:** `run_benchmark` on the Django 2022 graph:
   - with `total_words` from Graphify's own `detect()` on the snapshot;
   - with their five sample questions;
   - with the 288 real questions (query `q`).
   The same formula is applied to Model D's readouts (Part A, `md_cold` and `md_cover`).
3. **What an agent actually spends:** Part B already runs Claude + Graphify on the 288 fixes. Its paired bill against
   Sonnet alone (`team-year/rows_alone*.jsonl`, the same prompt, tools and loop, without Graphify) is the measured
   saving. It is reported next to the claim.
   - The rows hold dollars, not tokens. Both arms use the same model at the same price, so the dollar ratio is the
     ratio of the token bill (input and output weighted at list price). Tokens are not split here.

**No predictions.** The claim's own formula is reproduced and applied as written.
