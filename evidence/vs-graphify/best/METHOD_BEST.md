# Graphify at its best (a sensitivity analysis, written 2026-10-18, after the pre-registered results)

**Why:** the pre-registered scoring reads Graphify's files in the order its answer prints them. That order comes
from walking the graph, not from a relevance ranking, so it may understate Graphify. This analysis scores Graphify
from its own ranking, three ways, and reports the best of them. It is post hoc and favours Graphify by
construction.

**Graphify 0.9.92 variants**, all computed with its own code (`_query_terms`, `_score_query`, `_pick_seeds`), on the
same graphs and questions:
- **printed:** as pre-registered, the `[src=` order of the `query_graph` answer.
- **seeds:** the files of its chosen start nodes in their order, then the files of its ranked nodes in score order.
- **by file:** files ranked by the summed score of their nodes among the 50 best-scored nodes, as in PR #4481 (test
  files passed over unless the question names tests, or unless only tests match). Then the files of its ranked nodes
  in score order.

**Both tools, the same filter:**
- documentation files (.md, .mdx, .rst, .txt, .adoc) are dropped from every list;
- Model D is also shown with test files dropped, the same test filter the "by file" variant gets.

**"Graphify at its best"** is, for each dataset and query, the variant with the most right-first hits. Picking it
after seeing the results favours Graphify.

**Datasets:** Django 2022 (288), SWE-bench Lite (285) and the four Python repositories (172). The same gold files and
the same hit@k as before.
