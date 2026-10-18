# Results: Model D on a codebase it had never seen, honojs/hono (METHOD.md, D1)

**The test:**
- **Questions:** 241 real fix commits of Hono, a TypeScript web framework, from 2025-01 to 2026-10.
- **Code:** each fix is asked against its parent commit, the code exactly as it stood before the fix.
- **True answer:** the non-test source files the fix changed, and the exact lines (`git diff -U0`).
- **Model D:** 0.5.0, offline and cold: nothing taught, no model calls.
- **Baseline:** a grep-first look, ranking files by how many of the question's words they contain.

**The plain question**, e.g. "handle HEAD request in trailing slash middleware":

| | Model D | grep-first |
|---|---|---|
| right file first | **62 / 241 (25.7%, 95% CI 20.6–31.6%)** | 39 (16.2%, CI 12.1–21.4%) |
| right file in the top 3 | **109 (45.2%)** | 82 (34.0%) |
| right file in the top 5 | **135 (56.0%)** | 102 (42.3%) |
| MRR@10 | **0.376** | 0.277 |
| exact changed lines in item 1 / top 5 | 27 (11.2%) / **66 (27.4%, CI 22.1–33.3%)** | (no lines) |
| the same, within 5 lines | 33 / 80 (33.2%) | |

- **Paired, right file first:** Model D only 36, grep only 13 (exact McNemar p = 0.0014).
- **Paired, top 5:** 51 against 18 (p = 8.8e-5).

**The commit subject with the module name**, e.g. "fix(trailing-slash): handle HEAD request …":

| | right file first | top 5 | MRR |
|---|---|---|---|
| Model D | 81 (33.6%) | 178 (73.9%) | 0.501 |
| grep-first | 44 (18.3%) | 138 (57.3%) | 0.357 |

- Exact lines in the top 5: 80 (33.2%).
- Paired right file first: 51 against 14 (p < 1e-5).

**Operating numbers:**
- 685 tokens per readout;
- ask time 19 ms median, 25 ms at p90;
- 2.5 s for the first build, then 0.4 s per commit from the embedding cache;
- about 10,400 units per snapshot.

**Predictions:**
- **N1 held:** right file first, 62 > 39.
- **N2 held:** top 5, 135 > 102.
- **N3 held:** exact lines in the top 5, 66 of 241 = 27.4% ≥ 25%.

**Reading it:**
- **It carries to a new language.** With nothing taught, on a non-Python codebase Model D had never seen, the
  first free look puts the right file first 1.6x as often as grep, and in the top 5 more than half the time.
- **Lines are the harder bar,** at about a quarter of fixes in the top 5. That is why the agent still reads around
  the pointer.

**Limits:**
- These are cold numbers. Teaching once (`modeld cover`) needs API credit, and it is not run here.
- The baseline is a first grep ranking, not a full agent's search.

`run.py` needs a clone of honojs/hono; its HEAD at the time of the run is in `hono_head.txt`.
