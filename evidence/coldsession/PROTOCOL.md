# ColdSession: what does the next cold session still know? (written 2026-11-06, before any model call and before Model D's first full run)

**The question:** someone works something out in a repository. Then the session ends, a teammate starts their own, and months of commits land. How much of that work is kept, what does it
cost to use it, and is it still true?

**Why it's new:** existing memory benchmarks for coding agents don't measure this together. VibeMemBench (arXiv 2609.23570) doesn't record memory-side tokens, and tests no teammate, rewording or stale
fact. SWE-Bench-CL and SWE-ContextBench test related tasks, not repeated needs through real code changes. MemStrata (arXiv 2606.26511) tests changing facts but reports no tokens.

**What it tests in Model D:** its three parts, as released (0.5.3, `ocm.hybrid.run`, end to end, nothing changed):
- **Optimal context mapping:** the tokens needed to reach the right code the first time.
- **Vector generalization:** a lesson landing on the same need asked in other words.
- **Permanent context on disk:** lessons surviving new processes, a teammate's own build, and rebuilds over real commits.

This doesn't compare Model D with search tools. It compares it with other ways of carrying context forward, and with having none.

## The data

**Repositories:** from SWE-QA's 15, chosen by others. Those with fewer than 5,000 checkable facts (so they fit on this disk), the 3 where the most facts changed in the year: `reflex-dev/reflex` (1,244),
`scikit-learn/scikit-learn` (44), `sphinx-doc/sphinx` (20). Run in that order. `psf/requests` is the development repository and isn't in the results.

**Commits:** the last commit on the default branch before T0 2025-11-01, T1 2026-05-01 and T2 2026-11-01 (`data/<repo>/pins.json`).

**Facts:** read from the code by a program (`facts.py`), so the right answer at any commit is known without a judge. Four kinds, about public, repository-unique subjects in non-test Python source:
the default of a parameter, the value of a constant, the classes a class inherits from, and the file that defines something. Values someone could guess (None, True, False, 0, 1, -1, an empty or very short
string) are left out. Comparing T0 with T2 gives each fact's status: **same**, **moved** (same value, another file) or **changed**. A subject that has disappeared has no checkable answer and is left out.

**How often facts really change (`rates.json`, all 15 repositories, T0 to T2):** 14 of the 15 have 0.0% to 1.6% changed; `reflex` has 46%, from a large restructure. So changed facts are rare in most
repositories, and they are oversampled here so they can be measured at all. Results are reported by status and also at each repository's own real mix.

**Questions, per repository (`wordings.py`):**
- **taught, 20:** up to 8 changed, up to 4 moved, the rest same. Four wordings each, from one fixed prompt that sees the code at T0 and must avoid the code's names and the answer. A program rejects any wording
  that breaks this. The wordings ship with the data, so everyone answers the same questions.
- **sibling, up to 3, and unrelated, to 6 in all:** never asked before session 2. Siblings are another parameter of a function a taught fact is about.
- **named, 4:** asked by the code's exact name from fixed templates, as a control. When a question names the code, plain search is already cheap, and memory should save little.

## The sessions

Each session is its own process, with nothing carried over except what is on disk.

| session | code | who | asked |
|---|---|---|---|
| 1 | T0 | the first person, the first time | taught and named |
| 2 | T0 | the same person, the next day | taught and named, reworded, plus the new questions |
| 3 | T0 | a teammate, own checkout, own build, only the first person's lessons on disk | taught, reworded |
| 4 | T2 | a year later, after a rebuild at T1 and another at T2 | taught, reworded, with the answer as the code has it then |
| 5 | T0 | session 2 again, with 200 more lessons on disk | taught, in session 2's wording |

Session 5's extra lessons are other facts of the repository, right answers and right lines, given alike to Model D and the notes file.

## The arms

All use the same model, tools and code. `search`, `read_file`, `list_files` and `submit` are Model D's own tool code, at most 15 tool calls, one new conversation per question.

| arm | what it carries | sessions |
|---|---|---|
| **alone** | nothing | 2, 4 |
| **notes** | a notes file: every answer written down, all of it read back with every question, marked as possibly out of date | 1–5 |
| **map** | Model D's map with memory off: its code goes in with the question, nothing is taught | 2, 4 |
| **modeld** | Model D end to end: a question near a lesson costs one read; anything new is explored, and the line the agent cites is taught | 1–5 |
| **guess** | no code, no tools: what the model already knows | 1 |

An arm with no memory has no use for sessions 1, 3 and 5. Agents alone are the expensive arm, so `alone`'s session 2 also stands in for its first time.

**Model:** `gemini-3.5-flash-lite`, temperature 0, for every arm.

## Scoring

A program grades every answer against the code at that commit (`grade.py`): **right**, **stale** (states what used to be true and not what is true now), **hedged** (states both) or **miss**. Only right counts as right.

**Measures:** right; stale; requests; billed tokens and dollars, from the API's own counts; **tokens per right answer**, the headline; for Model D, how many answers took one read. Paired differences with 95% bootstrap
intervals over facts. Session 4 is reported by status and at each repository's real mix.

**Also, with no model calls (`landing.py`):** Model D taught perfect lessons, and whether they land and bring the fact in each session. This separates what the mechanism can do from what an agent's own lessons do.

## What I expect, written before running

A dry run with no model calls, on the development repository and template wordings only, has already been seen: every lesson landed in a new session and on a teammate's build, and 12 of 24 lessons were lost by T2 because
their exact lines had been edited, although the facts hadn't changed. These predictions take that into account.

- **P1, first time:** Model D's session 1 uses at most half of `alone`'s tokens, and is right within 5 points.
- **P2, next day:** at least 60% of taught facts are answered in one read, at most a fifth of `alone`'s tokens, right within 5 points of `alone`.
- **P3, teammate:** session 3 uses at most 1.25x session 2's tokens, right within 5 points of session 2.
- **P4, a year later, facts that stayed true (same and moved):** at least 40% answered in one read, at most half of `alone`'s tokens, right within 5 points of `alone`.
- **P5, facts that changed:** in session 4, Model D is stale on at most 10%, and `notes` on at least 50%.
- **P6, a prediction against Model D:** in session 2, with about 30 lessons, `notes` uses fewer tokens than Model D. A short notes file is cheap, and the model reads it well.
- **P7, more on disk:** in session 5, Model D uses fewer tokens than `notes`, right within 5 points.
- **P8, what memory adds:** in session 2, Model D uses at most half of `map`'s tokens.

**Model D passes only if P2, P3, P4, P5 and P7 all hold.** My rough estimate is 1 chance in 3.

## Spending

A hard cap of $5.00 across every script and arm, enforced in the code. One repository at a time; anything the cap stops is reported as not run.

## Limits to state with any result

- We designed this benchmark and our tool is in it, so it counts for less than a third party's. All code, data, answers and grades are published so anyone can check them or enter another tool.
- The questions are lookups with one checkable answer, not how-does-this-work understanding. That is what lets a program grade them, and it's a real narrowing.
- Python only, one cheap model, one run of each arm, 3 repositories.
- Plain wordings are written by a model, not by people.
- Facts are sampled evenly from public definitions. Real questions may lean towards code that's changing, so the real mix could be worse than the one reported.
- A real team might prune or organize its notes. This notes file is the simple version.
- The first-time comparison uses `alone`'s session 2, with different wording from Model D's session 1.

## Reporting

Every prediction is reported as held or failed. Anything changed in Model D because of these results is a separate run with its own label. New tools enter by the same scripts.
