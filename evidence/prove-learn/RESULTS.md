# The context graph across sessions: `modeld prove --learn` (exploratory, 2026-10-20)

**Not pre-registered.** This is the first run of a new command, written the same day. It shows what the command
reports; it is not a test with predictions fixed in advance.

**The question:** a coding agent's knowledge of a repository lives in its context. It is gone when the session ends,
and paid for again once the prompt cache expires (an hour at most on Claude). Model D keeps a context graph on disk:
- code fingerprints;
- each answered question, linked to the line that answered it.

Does that graph survive many sessions and rebuilds, shared by many people, and does it point the next session to the
right code?

**The replay (offline, zero tokens), on each repository's last 50 fixes in commit order:**
1. **A new session for every fix:** a fresh map of the fix's parent commit.
2. **The graph comes along from disk:** every earlier lesson is found again in the new code by its exact line
   (`build --carry`).
3. **The fix is asked twice:** against the map alone (cold), and again with the graph carried over.
4. **Then the fix lands:**
   - its main file is written as the fix left it;
   - the first line the fix wrote is taught as the answer, as the Stop hook teaches an agent's TEACH line.
5. **One workspace for every author,** as on a team's shared server.

Nothing about a fix is taught before it is asked.

**Results:**

| | Graphify (v8, 86c57be8) | claude-mem (main, 9e4f313a) |
|---|---|---|
| lessons taught | 47, from 19 authors | 48, from 18 authors |
| **lessons still found at the last fix** | **45 of 46** | **47 of 47** |
| right file first, cold → with the graph | 21 → **23** (grep 19) | 15 → **16** (grep 1) |
| right file in the top 5, cold → with the graph | 37 → 38 (grep 40) | 27 → 27 (grep 10) |
| readouts a lesson led / right | 13 / 7 | 2 / 2 |
| right leads from another author's lesson | 5 | 2 |
| fixes on a file taught earlier in the window | 30 of 50 | 9 of 50 |
| right file first on those, cold → with the graph | 12 → 15 (grep 14) | 5 → 6 (grep 0) |

**What it shows:**
- **The graph persists.** After 50 fresh sessions and rebuilds, 92 of 93 lessons were found in the new code by their
  exact line. The one lost was on a line a later change rewrote.
- **The graph is shared.** Lessons from one author pointed a later fix by another author to the right file, 7 times
  across the two repositories.
- **The gain on new bug reports is small.** Each fix is a new question, even when it lands in a file fixed before:
  - right file first rose by 2 and by 1, within chance at 50 fixes;
  - on Graphify, 6 of the 13 readouts a lesson led were wrong: the lesson was from a different bug in a nearby place.
    The normal top 4 still follow it (since 0.5.1).
- **Where memory pays most is not in this replay:**
  - the same question asked again, in any words (5–10x cheaper; reworded repeats right 107 of 114, learning-ablation);
  - a team's year of work (2.09x on Django: 85% from pointing, 15% from memory, team-year).

**To reproduce:**

```bash
modeld prove <repo> --fixes 50 --learn --json out.json
```

Use the commits above. The JSON files here are those outputs, with each author's name replaced by "author N" and the
local path by the repository name.
