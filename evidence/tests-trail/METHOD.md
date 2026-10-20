# Tests after code (written 2026-10-20, before any run of the shipped code)

**Why:** on Graphify's last 50 fixes (offline, nothing taught), Model D 0.5.2 put a changed file first 12 times
against grep-first's 19. In 23 of the 50, its first item was a test file. The true answer never counts tests. The
same happened on Hono (a test led 73 of 241 bare-query readouts).

**The change (0.5.3, `ocm/server.py`, `ocm/units.py`):**
- Within every readout, units from test files move after the others. Each group keeps its own order, and the readout
  keeps the same items.
- **Test files** (`units.is_test`, on the repository-relative path): `tests/`, `__tests__/`, `spec/`, `specs/`
  anywhere; `test/` only at the top of the repository, or Java's `src/test/` (so `django/test/`, which is library
  code, is not a test); `test_*.py`, `*_test.py`, `*_test.go`, `*.test.*`, `*.spec.*`, `conftest.py`.
- **Exempt:**
  - a question about tests (a word such as test, tests, testing, test*, spec, pytest, unittest, jest, vitest, mocha,
    conftest, fixture);
  - a taught pointer keeps the lead, even when it points into a test.
- `OCM_TESTS_TRAIL=off` restores 0.5.2's order.

**Already seen before this file:** the rule was designed after reading Graphify's misses, so Graphify is the discovery
set. A simulation on recorded readouts was also computed first:

| set | recorded | right file first, 0.5.2 → simulated |
|---|---|---|
| Graphify, 50 | top 5 files only | 12 → 21 |
| claude-mem, 50 | top 5 files only | 13 → 15 |
| Hono, 241, bare query | 10 items | 62 → 76 (top 5: 135 → 147) |
| Hono, 241, subject query | 10 items | 81 → 118 (top 5: 178 → 186) |

The simulation used a slightly different test rule (`test/` anywhere), and only the items recorded. This run uses the
shipped code.

**Sets (offline, no model calls):**
1. **Graphify:** the last 50 fixes (`modeld prove`'s rule), each built at its parent commit.
2. **claude-mem:** the last 50 fixes, the same way.
3. **Hono:** the 241 fixes of `evidence/new-codebase-hono/questions.json`, both queries; bare is the primary.
4. **Django 2022, cold:** the 288 kept fixes of the team year on its cold workspace (`team-year/ws/base`). Query:
   "Where is the code behind this change: {raw}", code scope, as in `learning-ablation`.
5. **Django 2022, taught:** the same 288 on the coverage workspace (`vs-graphify/ws/dj_cover`, 23,770 taught
   questions).

**Arms:** OFF (`OCM_TESTS_TRAIL=off`) and ON, asked of the same workspace for every question.

**Measures:**
- right file first, and right file in the top 5 (the readout's distinct files, in order);
- a changed line in the top 5 (sets 1-3; a readout unit's span overlaps a changed range);
- grep-first, for reference (sets 1-3);
- exact McNemar on paired right-first, ON against OFF;
- questions exempt because they are about tests.

**Predictions:**
- **T1 (Hono, bare):** ON right-first > OFF.
- **T2 (Django cold):** ON right-first ≥ OFF − 2. A check that it does no harm where tests are a library package.
- **T3 (Django taught):** ON right-first ≥ OFF − 2.
- **T4 (Graphify):** ON right-first > grep-first's 19.
- **T5 (claude-mem):** ON right-first ≥ OFF.

**Check of the harness:** OFF must reproduce the earlier numbers within ±2:
- Graphify 12 / 36;
- claude-mem 13 / 24;
- Hono 62 / 135 (bare);
- Django cold 111 / 288.
If it does not, that goes in `METHOD.md.deviations` before the results.
