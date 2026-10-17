# Results: are Graphify's Python import edges right? (METHOD.md, D1, A1)

- **Corpus:** four real Python repositories, 203 .py files in all.
- **Tool:** Graphify `update` with defaults (AST only, no LLM).
- **Ground truth:** every import edge is checked against Python's own parser (`ast`).

| repository | .py files | 0.9.64 (2026-09-18): wrong / edges | found | 0.9.92 (2026-10): wrong / edges | found |
|---|---|---|---|---|---|
| psf/requests | 37 | 0 / 412 | 117 / 117 | **0 / 413** | 117 / 117 |
| pallets/itsdangerous | 15 | 0 / 123 | 73 / 73 | **0 / 123** | 73 / 73 |
| encode/httpx | 60 | 32 / 447 | 90 / 124 | **0 / 447** | 123 / 124 |
| pallets/click | 91 | 10 / 598 | 326 / 336 | 11 / 598 | 326 / 336 |
| **all** | 203 | **42 / 1,580 (2.7%)** | 606 / 650 (93%) | **11 / 1,581 (0.7%)** | **639 / 650 (98%)** |

- **The 11 in 0.9.92 are click's tests.** There, `import click.utils` and `from click._utils import UNSET` go to a
  node marked `ambiguous_python_import` instead of to `src/click/utils.py` (a src layout). They are flagged as
  ambiguous, not linked to a wrong file.
- **The 32 in 0.9.64 are httpx's own `import httpx`.** In the tests and in `_transports/default.py`, it went to an
  external node. 0.9.92 resolves it.
- **No import edge pointed to a wrong file** in either version.
- **Call edges:** 1,506 in 0.9.64 and 2,353 in 0.9.92.
  - Every call edge passes a name check (the callee's name, or a module attribute call, appears on the edge's line),
    except 1 in 0.9.64 and 14 in 0.9.92.
  - All 15 are calls through an import alias, which Graphify resolved correctly: `t.cast(...)` with
    `import typing as t`, and `f()` with `from ._termui_impl import raw_terminal as f`.

**Reading it:** "half the edges were wrong" does not reproduce on these four repositories for import or call edges,
and import resolution improved between September and October.

**Limits:**
- Four well-structured repositories; the post's repository is not known.
- Only import edges and a necessary condition on call edges were checked. The `references`, `uses`, `inherits` and
  `rationale_for` edges were not.

**Deviations:** D1 lists three ground-truth errors and two scoring errors of my own, found on inspection before
sharing. All five favoured Graphify once fixed.
