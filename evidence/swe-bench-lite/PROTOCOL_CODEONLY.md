# PROTOCOL_CODEONLY: Model D's code scope against Graphify on SWE-bench Lite (fixed before any code-scope readout)

## Question
On the full-repository test of 2026-10-12, Model D's readout gave about half its top-5 places to documentation. Its
top-5 hits were 117 against Graphify's 131 on issue titles, and 157 against 122 on title + 400 characters, over 285
issues in 12 repositories. Does a readout scope that leaves documentation out find the fixed file more often than
Graphify, and more often than Model D's full scope?

## What is fixed
- **Model D code:** optimal-context-mapping commit `c7408509ab75d9c642b2e0848adee8ea7f22e403` (branch
  `code-only-scope`). `ask` with `"scope": "code"` ranks every unit whose file is not documentation, as defined by
  `ocm.units.DOCS` (.md, .mdx, .rst, .txt, .adoc). The lanes and the router law's observations are computed over those
  units only. The definition is the index's existing split between code and documentation; it was not chosen for this
  test.
- **Indexes:** the 12 Model D workspaces in `lite/ws/`, built on 2026-10-12 with Model D 0.2.1 after Graphify's output
  was moved out of the repositories. They contain no Graphify files. They are not rebuilt.
- **Issues and queries:** `swebench_lite_by_repo.json` (sha256 9485b76b…dd99): 300 SWE-bench Lite issues. Each is
  asked twice: by its title, and by its title plus the first 400 characters. An issue is scored when one of its fixed
  files exists in its repository's snapshot (285 issues).
- **Graphify:** version 0.9.87 results, already computed: `graphify_ranked_087.json` (sha256 81c054ca…9967). Graphs were
  built with `graphify update --no-cluster` and written outside the repositories. Queries ran with defaults (BFS,
  depth 2, 2,000-token budget).
- **Model D full scope:** `regress_all2.json`, made by the same commit with no scope. It must list the same files as
  the shipped 0.2.1 readouts (`modeld_ranked.json`, sha256 6696400d…0d3b) on all 600 readouts. Otherwise this is a
  deviation.
- **Runner:** `run_modeld_scope.py` (sha256 f8b41746…fb34), run as
  `PYTHONPATH=<checkout at the commit> python run_modeld_scope.py code codeonly.json`. Files come from the readout's
  result headers in rank order, with the indexed folder's name dropped; the first 10 are kept.
- **Scorer:** `score_codeonly.py` (sha256 9e5c16b6…d6b). hit@k means a fixed file is among the first k files listed.
  Tokens are readout characters divided by 4. Paired top-5 hits are compared with an exact two-sided McNemar test.

## Predictions
Each prediction holds or fails on the counts over the scored issues.
- **C1:** on issue titles, Model D code scope has more top-5 hits than Graphify (131).
- **C2:** on title + 400 characters, Model D code scope has more top-5 hits than Graphify (122).
- **C3:** on issue titles, Model D code scope has at least as many top-1 hits as Graphify (78).
- **C4:** on both queries, Model D code scope has at least as many top-5 hits as Model D full scope (117 and 157).
- **C5:** on both queries, Model D code scope hands over fewer tokens per issue than Graphify (1,520 and 1,652).

**Reported, with no prediction:**
- the McNemar p-values;
- top-1 and top-3 on title + 400 characters;
- per-repository top-5.

## Disclosure
The predictions were made after seeing one post-hoc analysis: the files of the full-scope readout's top 10, filtered to
.py/.pyx/.c/.h/.js/.ts. On titles that filter gave 80 / 135 / 146 top-1/3/5, and on title + 400 characters 99 / 155 /
167. The code scope differs from that filter in two ways:
- it keeps config and build files;
- it re-ranks the whole pool of code units, not a truncated list.

So its result is not known in advance.

## Deviations
Any departure from this plan is written to `PROTOCOL_CODEONLY.md.deviations`, with its reason, before the
analysis goes on.
