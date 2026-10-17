# Model D against Graphify on the same four Python repositories (written 2026-10-18, before any readout)

**The question:** the import check (RESULTS.md) showed Graphify's import edges are right. Here both tools are
measured at the job an agent needs from them: on a real question, do they point at the code the answer is in?

**Questions:** the real fix commits of psf/requests, pallets/itsdangerous, encode/httpx and pallets/click, 2018 to
2026 (`fixes.py`).
- **Fix commits:** a subject matching the FIX rule of oss-claude/history.py, merges excluded.
- **Code:** each fix is asked against the code as it stood at the start of its year, one snapshot per repository and
  year (27 snapshots).
- **Gold:** the non-test .py files the fix changed that exist at that snapshot. A fix with none is dropped.
- **Count:** 172 questions (requests 29, itsdangerous 3, httpx 31, click 109).
- **Two queries per fix:** `q`, "Where is the code behind this change: <subject>" (as in PROTOCOL_VS_GRAPHIFY), and
  `raw`, the subject alone.

**Arms (offline, no model calls):**
- **Model D 0.5.0 cold** (commit 1f06f9b): `modeld build` at each snapshot, then `ask` with code scope. With the API
  credit gone, `modeld cover` cannot run, so there is no taught arm.
- **Graphify 0.9.92** (PyPI): `graphify update <snapshot>` with defaults, written outside the snapshot. It is queried
  through its own MCP server with `query_graph` and the question only.

**Reading and scoring:** the readout runner and file reading of PROTOCOL_VS_GRAPHIFY (`point.py`).
- **Measures:** hit@1, hit@3 and hit@5 (a gold file among the first k files), and readout tokens (characters / 4).
- **Test:** exact McNemar on paired hit@1 and hit@5, pooled over the 172.

**Predictions (pooled, query `q`):**
- **V1:** Model D right file first > Graphify.
- **V2:** Model D top 5 > Graphify.
- **V3:** Model D readout tokens < Graphify.

**Exploratory:** the `raw` query, and the counts per repository.
