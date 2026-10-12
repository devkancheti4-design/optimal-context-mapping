# Results: the kit with the Life inside, live, across a real code move

Protocol PROTOCOL_LIFE_LIVE.md, hashed before any agent ran. The kit under test is frozen as kit_life.diff (plus
ocm/life.py, living-fused's life/life.py vendored unchanged from d083b61). The code move is the FastAPI template from
36ddc1a (2025-09-08) to 13652b5 (2026-04-16), 400 commits. One blind judge graded all 100 phase-2 answers.
Reproduce: `python3 life_live_report.py report`.

## Phase 1, at the old code
5 fresh CMLM sessions answered and taught questions 1-50 on ws_A_life. The Life recorded 47 taught entries, each with
its exact line.

## The code moves
`ocm build corpus --out ws_B_life --carry ws_A_life`:
- **Carried:** 40 of 47 taught entries, 21 of them to a new place.
- **Abstained:** 7, whose exact line no longer exists (for example the old bcrypt-only hashing code). Kept in the
  Life, not taught, not guessed.

## Phase 2, at the new code (questions 51-100, two chains of 5 fresh sessions run together)
| | right | requests | cache-weighted input | search/read/list | the 9 cross-phase repeats: requests / calls |
|---|---|---|---|---|---|
| REBUILD (the kit before the Life) | 49/50 | **137** | 1,053,024 | 104 | 28 / 32 |
| **LIFE (carried)** | **50/50** | 142 | 1,093,696 | 99 | 30 / 30 |
| reference: no move (VEC-CMLM tasks 6-10) | | 136 | 1,038,587 | 97 | 31 / 29 |
| reference: no CMLM (VEC-ALONE tasks 6-10) | | 169 | 1,247,912 | 156 | 35 / 40 |

Requests per session: REBUILD 25, 30, 29, 25, 28; LIFE 27, 27, 32, 24, 32.

## Predictions
- **LL1 failed.** LIFE made 142 requests against 137.
- **LL2 failed.** On the cross-phase repeats, 30 against 28.
- **LL3 held.** 50 against 49. REBUILD's one miss was a cross-phase repeat (r43); LIFE got it right.

## What it shows
- **The Life works in the kit.**
  - It recorded every taught question with its exact line.
  - Across a real 400-commit move it carried 40 of 47 entries and abstained on the 7 whose code is gone.
  - Offline, the same mechanism carried 38/38 to the right unit (RESULTS_LIFE.md).
- **Live, it did not save requests.**
  - Both CMLM arms sit about 20% below no CMLM, and level with the no-move run.
  - The difference between them, 5 requests, is inside the session-to-session spread (24 to 32).
- **The reason is the same as before.** Not one of the 9 cross-phase repeats was answered without a search, in any
  CMLM arm, the no-move run included. The TEACH rule asks for the exact answer line, so agents read to confirm even
  when the carried code is ranked first. A carried vector can then only shorten a search, and here that did not show
  above the noise.
- **The one place it showed was accuracy.** It got the one cross-phase repeat REBUILD missed.
