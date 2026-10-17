# Final Model D against Graphify (written 2026-10-17, before any readout or model call)

## The question
Model D 0.5.0 maps a codebase, can be taught the whole codebase once (`modeld cover`), points Claude at the code, and
learns from every exploration. Graphify 0.9.92 builds a knowledge graph of the code that Claude queries over MCP.
- **Part A, pointing:** which tool's first readout names the file a real fix changed? How many tokens does it hand over?
- **Part B, end to end:** with the same Claude, which tool gives the smaller bill for the same work?

## Tools, fixed
- **Model D:** optimal-context-mapping commit `418dc602` (version 0.5.0), run from that checkout. Its defaults hold,
  with no gates set.
  - Readouts are `ask` with `"scope": "code"`.
  - `modeld cover --yes` writes and teaches one question per non-test code unit: Claude Haiku 5.5, the prompt of
    PROTOCOL_COVERAGE.
- **Graphify:** `graphifyy[mcp]==0.9.92` from PyPI, in its own environment.
  - Graphs are built by `graphify update <repo>` with defaults, clustering included, and written outside the repository
    (`GRAPHIFY_OUT`).
  - Queries go through Graphify's own MCP server (`python -m graphify.serve <graph> --transport http --json-response
    --stateless`): `query_graph` with the question only, so the server's defaults apply (BFS, depth 3, 2,000-token
    budget).
- **Disclosure:** the Django 2022 graph was built (38 s) and one `query_graph` call made before this plan was written,
  to check that the server answers. No readout was scored.

## Part A: pointing (offline; the only model calls are `modeld cover`)
- **Django 2022:**
  - The 288 kept fixes of PROTOCOL_TEAM_YEAR.
  - Code: Django at 0ab58c1209 (`team-year/ws/base`, copied).
  - Two queries per fix: `q` = "Where is the code behind this change: <subject>", the phrasing of the team-year and
    coverage runs; `raw` = the subject alone.
  - Arms:
    - `md_cold` (a copy of ws/base);
    - `md_cover` (another copy, after a fresh `modeld cover`, cap $2);
    - `gf`.
- **SWE-bench Lite:**
  - The 285 issues of PROTOCOL_CODEONLY whose fixed file exists in the repository snapshot, in 12 repositories, at the
    same snapshots.
  - Two queries: `title`, and `q400` (title + 400 characters).
  - Model D is rebuilt with 0.5.0 (`modeld build`). Each repository is read cold, then covered (`modeld cover`,
    $12 over all 12), then read again.
- **Files** are taken from each readout in order, without repeats:
  - Model D: the `[path:line]` items, with the indexed folder's name dropped;
  - Graphify: the `NODE ... [src=path` lines, as PROTOCOL_CODEONLY read them.
- **Measures:**
  - hit@1, hit@3, hit@5 (a changed file among the first k);
  - tokens (readout characters / 4);
  - taught-led readouts;
  - exact McNemar on paired hit@1 and hit@5.

## Part B: end to end with Claude (Django 2022, the 288 fixes in commit order)
- **Claude + Graphify:**
  - Sonnet 5.5 with Graphify's own MCP tools, all 10 as its server lists them (names, descriptions, schemas). It also
    has the alone arm's `search`, `read_file`, `list_files` and `submit`, over the same never-taught tools server.
  - The system prompt is the alone arm's (PROTOCOL_TEAM_YEAR), then the CLAUDE.md block that `graphify install` writes,
    verbatim, then one sentence: "Here graphify runs as tools, not a shell: `graphify query` is query_graph,
    `graphify path` is shortest_path and `graphify explain` is get_node; graphify-out/ is not readable with read_file."
  - The alone arm's loop and the same 15-call tool limit. It never learns, so it runs in 3 shards.
- **Model D final:**
  - The product as shipped (`ocm.hybrid`, `team_year.py md`).
  - Its server runs over the covered Django workspace (Part A's `md_cover`, copied before any end-to-end call), with
    code scope as in the team-year run.
  - It learns from its own explorations, sequentially.
- **Reported alongside, from earlier runs of the same harness on the same 288:** Model D cold (`rows_md.jsonl`,
  $12.32) and Sonnet alone (`rows_alone*.jsonl`, $25.72).
- **Measures:**
  - dollars at list price (Sonnet $2/$10, Haiku $0.10/$0.50 per million tokens);
  - requests;
  - right: the submitted line is in a changed file; a read-path answer is right if it cites one (PROTOCOL_TEAM_YEAR's
    D4 measure);
  - exact McNemar on paired right;
  - the saving by quarter.

## Predictions (fixed now)
- **G1:** Django 2022, query `q`: `md_cover` right file first > `gf`.
- **G2:** Lite titles: `md_cold` top-5 > `gf` top-5.
- **G3:** Lite titles: `md_cover` right first > `md_cold` right first (coverage replicates on 12 more repositories).
- **G4:** readout tokens per question: `md_cold` and `md_cover` < `gf`, on all four query sets.
- **G5:** the bill: Claude + Graphify $ / Model D final $ ≥ 1.5x.
- **G6:** the work: Model D final right ≥ Claude + Graphify right − 3% of the paired fixes.
- **G7:** coverage pays end to end: Model D final $ < Model D cold $ on the paired fixes.

**Exploratory, no prediction:**
- the `raw` and `q400` query sets;
- per-repository counts;
- Graphify's tool use (calls per tool, characters returned);
- Claude + Graphify against alone.

## Caps and reporting
- Caps:
  - `modeld cover`: $2 for Django and $12 for Lite;
  - Claude + Graphify: $12 per shard;
  - Model D final: $15.
- A run that stops at a cap is reported as it stands.
- Every number is reported whichever way it comes out. Departures go to `PROTOCOL_VS_GRAPHIFY.md.deviations` before
  the analysis goes on.
- **Scripts:**
  - `scripts/questions.py`;
  - `scripts/point.py`;
  - `scripts/gf_mcp.py`;
  - `scripts/e2e_graphify.py`;
  - `scripts/run_django_a.sh`, `scripts/run_lite.sh`, `scripts/run_e2e.sh`;
  - `scripts/score.py`.
