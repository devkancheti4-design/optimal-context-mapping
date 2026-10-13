# RESULTS_CODEONLY (2026-10-13, offline, no API)

Plan: PROTOCOL_CODEONLY.md (sha256 aebf2ef6…c541, recorded 2026-10-13T10:50:02+0530 before any code-scope readout).
Model D commit c7408509 (`ask` with `"scope": "code"`), Graphify 0.9.87. The test covers 285 SWE-bench Lite issues in 12
repositories, with each tool indexing the whole repository. No deviations.

| query | Model D, code scope | Model D, full scope | Graphify 0.9.87 | tokens per issue (code / full / Graphify) |
|---|---|---|---|---|
| issue title, top-1 / 3 / 5 | **80 / 154 / 176** | 32 / 80 / 117 | 78 / 115 / 131 | 634 / 524 / 1,520 |
| title + 400 characters, top-1 / 3 / 5 | **96 / 161 / 183** | 64 / 129 / 157 | 67 / 99 / 122 | 700 / 620 / 1,652 |

**Paired top-5, exact McNemar** (issues each arm finds and the other misses):

| query | code vs Graphify | code vs full scope |
|---|---|---|
| issue title | 72 vs 27, p = 6.9e-6 | 59 vs 0, p = 3.5e-18 |
| title + 400 characters | 82 vs 21, p = 1.1e-9 | 27 vs 1, p = 2.2e-7 |

**Predictions: 5 of 5 held.**
- C1: 176 > 131.
- C2: 183 > 122.
- C3: 80 >= 78.
- C4: 176 >= 117 and 183 >= 157.
- C5: 634 < 1,520 and 700 < 1,652.

**Per repository** (top-5, code scope vs Graphify):
- Code scope is ahead in 10 of 12 repositories on titles and in 10 of 12 on title + 400 characters.
- Graphify is ahead on seaborn (4 issues; 1 vs 4 and 1 vs 3) and flask (3 issues, titles only; 2 vs 3).
- Graphify is also ahead on xarray (5 issues, title + 400 only; 2 vs 3).
- requests ties on both queries.

**Reading it:**
- **Top-1 on titles is level:** 80 against 78.
- **The gains are in the top three and top five,** and on longer queries.
- **Tokens:** the code scope hands over about 2.4x fewer tokens than Graphify, and about 15% more than the full scope.

**Files:**
- `codeonly.json`, `regress_all2.json` (full scope at the same commit, the same files as the shipped 0.2.1 on all 600
  readouts), `graphify_ranked_087.json`;
- `report_codeonly.json` (from `score_codeonly.py`).
