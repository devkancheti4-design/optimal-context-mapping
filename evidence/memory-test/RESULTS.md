# The memory on questions that aren't bug fixes: gin and httpx, a year apart (exploratory, 2026-11-06)

**Not pre-registered.** The 24 questions and their answer lines were written before Model D was asked any of them.
Their file's SHA-256 was recorded when the run started (`data/memtest/questions.sha256`), but no plan or prediction
was hashed beforehand. Model D 0.5.3, offline: no model calls, $0. Not rerun since.

**The question:** a lesson is taught once. Does it stay on disk and keep pointing to the right line:
- in a new session;
- on a teammate's own build;
- from a copied folder;
- after a year of real commits?

And does it ever point to an old answer?

**The questions:** 12 per repository, each with a second wording. None is about a bug fix. They cover a default, a
limit, how it works, architecture, errors, tests, CI, docs, release history and team rules, plus an entry point and
security on gin, and packaging and environment on httpx. Each answer line was found by reading the code with
`git grep`.

**The code:**

| | gin (Go) | httpx (Python) |
|---|---|---|
| a year back, where the lessons were taught | `9968c4b`, 2025-10-09 | `e70d0b0`, 2025-02-14 |
| now (the latest commit on 2026-11-06) | `0f09c3a`, 2026-10-10 | `b5addb6`, 2026-02-23 |
| between | 118 commits, 61 files changed | 20 commits, 28 files changed |
| map, then and now | 4,578 and 5,008 pieces | 5,360 and 5,375 pieces |
| answers that changed by now | 4 of 12 | 2 of 12 |

**The steps** (`memtest.py`). Each step is its own process, so nothing is kept in memory between them.
1. **Cold:** the map only, nothing taught.
2. **Teach:** every question is taught at its answer line, as `teach` takes it.
3. **Next session:** a new process with only what the folder holds.
4. **Teammate:** a teammate's own build of the same commit, carrying the lessons from the first (`modeld build --out
   --carry`).
5. **Copy:** the folder copied elsewhere, with the repository moved away.
6. **A year later:** `git checkout` to now and `modeld build .`, which carries the lessons when it rebuilds in place;
   then every question is asked again.
7. **Fresh:** the same code as step 6, in a new map with nothing taught.

**Results**, both repositories, 24 questions. `python summarize.py` recomputes every number.

| step | answer line in the readout: same words | other words | lesson opened: same words | other words |
|---|---|---|---|---|
| cold, nothing taught | 10 of 24 | 6 of 24 | – | – |
| next session | 22 of 24 | 12 of 24 | 20 of 20 | 8 of 20 |
| teammate's build | 22 of 24 | 12 of 24 | 20 of 20 | 8 of 20 |
| copied folder, repository gone | 22 of 24 | 12 of 24 | 20 of 20 | 8 of 20 |
| a year later, rebuilt in place | 19 of 24 | 10 of 24 | 17 of 20 | 6 of 20 |
| a year later, fresh map | 9 of 24 | 6 of 24 | – | – |

- **Taught once, kept everywhere:** `teach` placed 20 lessons, and all 20 opened in the next session, on a teammate's
  build, and from a copied folder after the repository was moved away.
- **A year of commits:** 17 of the 20 lessons were kept. 6 of those had moved to a new line, and they were followed
  there. 3 stepped aside:
  - **2 because their answer changed:**
    - gin: `var brokenPipe bool` became `var isBrokenPipe bool`;
    - httpx: `requires-python = ">=3.8"` became `">=3.9"`.
  - **1 although its answer stayed the same:** gin's `const defaultMultipartMemory = 32 << 20 // 32 MB` moved into a
    `const (...)` block, so the line now reads `defaultMultipartMemory = 32 << 20 // 32 MB`. A lesson follows its exact
    line, ignoring only whitespace, so this lesson was lost. The README's limits list this case: editing a line drops
    its lesson.
- **No old answers:** no readout at any step showed an old answer. Every readout in which a lesson opened held the
  answer line.
- **Other words are weaker:** asked in other words, 8 of 20 lessons opened, and the answer line was in the readout for
  12 of 24 questions.
- **Shorter readouts once taught:** same words, tokens per readout went from 471 cold to 356 in the next session on gin,
  and from 383 to 236 on httpx.
- **`teach` placed 20 of 24 and refused 4.** These were found by this test and are not fixed:
  - **2 paths under `.github/`:** `place()` in `ocm/server.py` strips the leading dot, so `.github/workflows/gin.yml`
    matches nothing.
  - **`README.md:46` on gin:** more than one folder holds a file of that name.
  - **`CHANGELOG.md:3` on gin (`## Gin v1.11.0`):** no piece of the map holds that line.

  Cited again with the repository's folder in front, as a readout prints paths (`gin/README.md:46`), 3 of the 4 were
  placed. The CHANGELOG line still wasn't.
- **A lesson with no line in the code is refused:** "we decided this in a meeting last March" was not placed. Model D
  stores pointers to code, not notes.
- **The real command line:** one gin question went through `modeld ask`, `teach`, `ask`, and then `ask` in other words,
  each its own process. The taught wording opened the lesson. The other wording got the plain map readout
  (`data/memtest/cli.json`).

**Files**
- `memtest_questions.json`: the 24 questions, their second wordings, and the answer lines then and now.
- `memtest.py`: the script that wrote `data/memtest/`. Only its first docstring line was reworded for publication.
- `data/memtest/`: every readout and reply, one file per repository and step. `<repo>.build.json` holds the build
  logs, with local paths shown as `<work>` and `<tmp>`.
- `summarize.py`: recomputes every number above.

**To rerun:** with Model D installed, run `python -I memtest.py <an empty folder>`. It clones both repositories, checks
out the commits above, and writes `data/memtest/` next to itself, replacing these files.
