# `modeld prove` on gin (Go) and httpx (Python) (exploratory, 2026-11-06)

**Not pre-registered.** These were the first `modeld prove` runs on these repositories, and no plan was hashed before
them. Model D 0.5.3, offline: cold (nothing taught), no model calls, zero tokens. Not rerun since.

Model D was not tuned on either repository, but both had appeared in earlier cold tests:
- gin in Agent Retrieval Bench, 88 of its 345 samples ([agent-retrieval-bench](../agent-retrieval-bench));
- httpx in the comparison with Graphify, 31 fixes ([vs-graphify/four-repos](../vs-graphify/four-repos)).

**The test** is `modeld prove`, the test of [new-codebase-hono](../new-codebase-hono):
- It replays a repository's real fix commits.
- Each fix is asked in the words of its commit subject, against the code exactly as it stood one commit before.
- The true answer comes from git: the non-test source files the fix changed, and its changed lines.
- **The baseline is a grep-first look:** files ranked by how many of the question's words they contain.

**Results: every fix in the window** (`--fixes 200`)

| | gin (Go) | httpx (Python) |
|---|---|---|
| repository | gin-gonic/gin @ `0f09c3a9b4` | encode/httpx @ `b5addb64f0` |
| fixes replayed | 149, from 2016-12 to 2026-10 | 72, from 2019-05 to 2025-02 |
| right file first: Model D | **58 (38.9%, 31.5–46.9%)** | **42 (58.3%, 46.8–69.0%)** |
| right file first: grep-first | 38 (25.5%, 19.2–33.1%) | 23 (31.9%, 22.3–43.4%) |
| right file first, paired: Model D only / grep only | 31 / 11, p = 0.0029 | 22 / 3, p = 0.00016 |
| right file in the top 5: Model D / grep-first | 97 (65.1%) / 87 (58.4%), p = 0.099 | 55 (76.4%) / 54 (75.0%), p = 1 |
| a changed line in Model D's top 5 | 39 (26.2%) | 20 (27.8%) |
| tokens per readout | 541 | 496 |

Intervals are 95% Wilson intervals. p is an exact two-sided McNemar test on the same fixes.

- **Right file first:** Model D was ahead on both repositories, by 13 points on gin and 26 on httpx.
- **Top 5:** about even. Model D's lead there is within chance on both.
- **The commits:** each is the latest commit on 2026-11-06. gin's is the commit right after its last replayed fix;
  httpx had no commits between February and the run.

**The default run** (`modeld prove`: the last 24 months, up to 50 fixes)
- **gin, 26 fixes:** right file first 15 vs 8 for grep-first (p = 0.039); top 5, 22 vs 20.
- **httpx, 3 fixes:** right file first 1 vs 1; top 5, 1 vs 2. Three fixes are too few to read anything into.

**With memory** (`modeld prove --learn`, the same 26 gin fixes)
- **The replay:** every fix is a new session that carries the lessons from disk. After it is asked, the fix is taught
  where it landed. Lessons from every author go into one workspace.
- **Right file first:** 15 cold, 17 with memory. **Top 5:** 22 cold, 24 with memory.
- **Lessons:** the 26 fixes, from 24 authors, taught 23 lessons. At the last fix, 19 of 22 were still found in the
  code.
- **Pointers:** a taught pointer led 2 readouts. It was right both times, and both lessons came from another author.
- **httpx's 3 fixes:** no change.

**Files**
- `<repo>.<run>.json`: every fix asked, and the files each side returned.
- `<repo>.<run>.txt`: what the command printed.
- The runs are `long` (`--fixes 200`), `prove` (the default) and `learn` (`--learn`).
- Local paths are shown as `<work>`. Author names are replaced by `author N`, numbered per repository, as in
  [prove-learn](../prove-learn).
- `summarize.py` recomputes every number above.

The same session also ran `modeld forecast` on gin. A forecast is a projection, not a measurement, so it isn't
included.

**To rerun:**
1. Clone the repository and `git checkout` the commit above.
2. Run `modeld prove . --fixes 200 --months 120`.
   - The command line wasn't saved. `--months 120` is inferred from gin's first replayed fix (2016-12-03).
   - httpx's whole history falls inside that window.
3. For the default runs, run `modeld prove .` and `modeld prove . --learn`.
