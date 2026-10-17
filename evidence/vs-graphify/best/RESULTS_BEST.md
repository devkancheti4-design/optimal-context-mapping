# Results: both readings, as pre-registered and with Graphify at its best (METHOD_BEST.md, post hoc)

**What each column is:**
- **printed:** Graphify 0.9.92's files in the order its `query_graph` answer prints them (pre-registered).
- **at best:** its own node scores summed per file (the PR #4481 method), docs dropped. This is the best of its
  three readings in every dataset.
- **Model D:** 0.5.0 with code scope, unchanged. "Same filter" also drops tests, as the at-best reading does.

Right file first / top 5:

| dataset (query) | Graphify printed | **Graphify at best** | Model D cold | Model D cold, same filter | Model D taught |
|---|---|---|---|---|---|
| Django 2022, 288 (q) | 89 / 137 | **116 / 172** | 111 / 197 | 129 / 197 | 149 / 193 |
| Django 2022 (raw subject) | 91 / 142 | **118 / 168** | 111 / 212 | 131 / 211 | 155 / 198 |
| SWE-bench Lite, 285 (title) | 78 / 131 | **86 / 159** | 80 / 176 | 107 / 181 | 87 / 176 (6 of 12 repos taught) |
| SWE-bench Lite (title + 400) | 67 / 122 | **81 / 150** | 96 / 183 | 127 / 187 | 99 / 181 |
| Four Python repos, 172 (q) | 52 / 107 | **72 / 124** | 65 / 124 | 73 / 125 | (no API credit) |
| Four Python repos (raw subject) | 58 / 103 | **76 / 114** | 79 / 125 | 87 / 126 | (no API credit) |

**Paired against Graphify at its best (exact McNemar):**
- **Model D cold, right first:** level in 5 of 6. Django 111 vs 116, p = 0.70; Lite titles 80 vs 86, p = 0.59; four
  repos 65 vs 72, p = 0.44. Lite title + 400 is 96 vs 81, p = 0.13.
- **Model D cold, top 5:** ahead on Django (p = 0.014, and 1.6e-5 raw) and Lite title + 400 (p = 0.0004). Lite titles
  p = 0.09; level on the four repos (124 vs 124).
- **With the same test filter, right first:** ahead on Lite (titles p = 0.04, title + 400 p = 3.7e-6); not
  significant on Django (129 vs 116, p = 0.23) or the four repos (73 vs 72).
- **Model D taught, right first:** ahead on Django (149 vs 116, p = 0.002; raw 155 vs 118, p = 0.001).

**Reading it:**
- **Read as it prints, Graphify loses everywhere** (the pre-registered result).
- **Read at its best, Graphify's ranking puts the right file first about as often as cold Model D.** Model D keeps a
  clear lead in the top 5 on the large repositories, a lead when taught, and a lead on Lite with the same test filter.
- **The at-best reading is not what Graphify returns today.** Its answer still leads in printed order and is about
  1,500–1,650 tokens, against Model D's 400–735. That reading is what PR #4481 would make it return first.
- **On a pointing task, most of Graphify's gap is how it orders its answer, not what it knows.**

**The four repositories, as pre-registered (METHOD_VS_MODELD.md):** Model D cold 65 / 105 / 124 against Graphify
52 / 84 / 107, and 591 against 1,649 tokens. V1, V2 and V3 held. Paired: right first p = 0.12, top 5 p = 0.021.
