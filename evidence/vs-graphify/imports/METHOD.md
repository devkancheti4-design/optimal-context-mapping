# Are Graphify's Python import edges right? (written 2026-10-18, before any edge is scored)

**Prompted by:** a post shared in the Graphify Discord, claiming Graphify "choked on python imports and half the edges
were wrong" on a 40-file repository.

**Tool:** Graphify 0.9.92 (PyPI), `graphify update <repo>` with defaults (AST only, no LLM), graphs written outside the
repositories.

**Repositories:** fresh shallow clones of `psf/requests` (37 .py files), `pallets/itsdangerous` (15), `encode/httpx`
(60) and `pallets/click` (91), at the commits in `repos.txt`.

**Ground truth:** Python's own parser (`ast`) on every .py file Graphify graphed. Each `import` / `from ... import`
statement is resolved to files in the repository:
- **Relative imports** are resolved by their level from the importing file's package.
- **Absolute imports** are resolved against the repository root, then `src/`, then the importing file's own folder.
- **Acceptable targets of a statement:**
  - the module's file (`x.py` or `x/__init__.py`);
  - for `from X import y`, also `X/y.py` when y is a submodule;
  - also the file that defines y, following re-exports in `__init__` files up to 3 hops.
- **External:** a statement no file in the repository resolves is external.

**Scored:** every Graphify edge with relation `imports`, `imports_from` or `re_exports` whose source is a .py file.
- **Right (internal):** the target node's file is an acceptable target of an import statement on the edge's line.
- **Wrong target:** the target is a repository file that no statement on that line imports.
- **Wrong, missed internal:** the target is an external (fileless) node, but the statement resolves inside the
  repository.
- **Right (external):** the target is an external node and the statement is external.
- **Wrong line:** no import statement on the edge's line.
- **Recall:** each internal import statement in the ground truth counts as found if some Graphify import edge from
  that file, on that line, reaches an acceptable target.

**Also reported:** for `calls` edges, whether the callee's name appears as a call on the edge's line (a necessary
condition, not proof the right definition was chosen), split by EXTRACTED and INFERRED.
