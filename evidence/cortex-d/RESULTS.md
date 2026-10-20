# Cortex D on Django, next to Graphify's knowledge graph (exploratory, 2026-10-20)

**Not pre-registered.** This is the first run of `modeld cortex` (0.5.3). It reports what the command builds, and how
it compares with Graphify 0.9.92's own graph of the same commit.

**What was built:**
- **Cortex D:** `modeld cortex` on the Django workspace that learned the codebase once (`modeld cover`, from
  evidence/vs-graphify).
  - 3,143 files and 113,271 pieces of code;
  - 23,770 questions, each linked to its exact line;
  - 6,945 meaning edges: the 3 nearest files each, kept at 74+ bits over the median agreement of 523.
  - Built in 1.9 s, with no model calls.
- **Graphify:** its own `graph.json` for the same commit (built_at_commit 0ab58c12).
  - 46,373 nodes and 108,300 links across 2,840 files;
  - links: calls 28,769, method 24,031, imports and imports_from 20,720, contains 9,982, …

**Overlap:** 4,726 of Cortex D's meaning edges join two files that Graphify's graph covers.
- Graphify links 908 of those pairs directly (19%), mostly by imports and calls.
- The other 3,818 (81%) it does not link.

**Examples of links only Cortex D has:**
- the GIS MySQL and Oracle backends;
- `core/management/sql.py` and the `sqlmigrate` command;
- flatpages' URLs and their test URLs.

Some links are loose, mostly between test files (e.g. `test_fakepayload.py` and `test_simplelazyobject.py`).

**One question, both tools** (`example.json`): one of the 288 fixes, picked with `random.Random(20261020)`. The fix
changed 7 files.

| | tokens | first changed file in the answer |
|---|---|---|
| Graphify, `query_graph` defaults | 1,728 | none of the 7 among the 28 files it lists |
| Model D, cold | 427 | position 2 |
| Model D, taught once | 761 | position 7 (worse than cold on this one) |

One question is an example. The 288-fix results are in evidence/vs-graphify and evidence/tests-trail.

**Not measured:** whether an agent does better when it is also given Cortex D's meaning edges. Today's readout uses the
pieces of code and the taught links, not the file-to-file edges.

**To reproduce:**

```bash
modeld cortex <workspace> --out <dir>
python overlap.py <dir>/cortex.json <graphify-out>/graph.json
```
