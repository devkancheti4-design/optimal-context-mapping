# Model D on a codebase it has never seen: honojs/hono (written 2026-10-18, before any readout)

**Why:** almost all earlier evidence is Python. Hono is a TypeScript web framework, never used in any Model D test or
in tuning.

**Questions (`questions.py`):**
- **Fix commits:** every one in honojs/hono since 2025-01-01 (FIX rule of oss-claude/history.py, merges excluded)
  that changes a non-test source file present in its parent commit. 241 fixes.
- **Code:** each fix is asked against its own parent commit, the code exactly as it stood before the fix.
- **True answer, files:** the non-test .ts/.tsx/.js files the fix changed.
- **True answer, lines:** the parent-side line range of every change in those files (`git diff -U0`). A pure
  insertion counts as the two lines around it.
- **Two queries per fix:**
  - `subject`: the commit subject, PR number removed, e.g. "fix(css): Fix multiline CSS handling in style
    replacement". This often names the module.
  - `bare`: the same with the `fix(scope):` prefix removed. This is the primary query, closer to a developer's
    words.

**Model D:** 0.5.0 (commit a1ec2f2, unchanged), offline, with no model calls.
- `modeld build` at each parent, with an embedding cache shared across builds; `ask` with code scope.
- Nothing is taught: each build is cold. There is no `modeld cover`, because the API credit is gone.

**Baseline, a grep-first agent's first look:**
- **Files:** every code file of the snapshot. Docs are excluded, which is the same file set as Model D's code scope.
- **Ranking:** by the number of distinct query words (3+ characters, not stopwords) the file contains, then by
  their total count, then by path.

**Measures (per query):**
- **file hit@1, @3, @5** and **MRR@10**, for both tools;
- **line hit@1, @5** (Model D only, since the baseline has no lines): a readout item's unit span overlaps a true
  changed range exactly; with ±5 lines, reported as a secondary;
- **readout tokens** (characters / 4), **ask latency** and **build time**;
- **exact McNemar** on paired file hit@1 and hit@5 against the baseline, and **Wilson 95%** intervals.

**Predictions (bare query):**
- **N1:** Model D file hit@1 > baseline.
- **N2:** Model D file hit@5 > baseline.
- **N3:** Model D line hit@5 ≥ 25%.

**Trace for the explanation:** for every question, these are recorded so one real question can be shown step by
step:
- the router's eight observations and the lane it chose;
- the top five units by the vector law, with their bits shared.
