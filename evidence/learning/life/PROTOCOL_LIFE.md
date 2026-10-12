# Protocol: living-fused's Life as the CMLM's exact memory of what was taught, across real code moves (offline)

Fixed before the replay runs; its SHA-256 goes in prereg_hashes.json.

## Placement (the user's choice)
The Life is the CMLM's persistent, exact, revisable store of every taught question and its code. It is life/life.py
(MIT) from ~/living-fused at d083b61, imported from the checkout and unchanged. When code moves, the newest location
wins and the history is kept. Its identity is byte-exact (sha).

## The real code move
The FastAPI template's own git history: revision A = 36ddc1a (2025-09-08) and revision B = 13652b5 (2026-04-16, the
corpus, 400 commits later). Of the first 50 questions' taught lines (the live VEC-CMLM agents' TEACH lines at B), 38
existed at A, mapped back by line diff: 19 moved (another file or line) and 19 are in the same place.

## The stream
- **Phase 1, at A.** Questions 1-50 are taught at their A locations, for the 38 whose line existed at A. Each becomes a
  Life entry: key = the taught question, value = {"at": "path:line at A", "code": the exact line text}.
- **The code moves to B.** The workspace is rebuilt at B (ws_vec_base).
- **Phase 2, at B.** Questions 51-100 are asked and read out at B, each taught after it, as in the live run.

## Arms at B
- **REBUILD.** The kit today: a rebuild carries nothing over, so phase 1's teaching is lost.
- **CARRY-AS-IS.** Phase 1's entries are taught at B at their A path:line, unchanged.
- **LIFE.** Each Life entry is found at B by exact identity, then its CMLM vector is taught from the Life's current
  value.
  - Lookup order: the same exact line text in the same file (renames followed), nearest the old line; else the one
    file at B that holds that exact line.
  - The B location is written to the Life as a revision: newest wins, history kept.
  - An entry whose exact code is not found ABSTAINS and is not carried. Nothing is guessed.
- **NO-MOVE (upper bound).** Phase 1 taught at B's own locations (the live run).

## Measures
- **Carried entries.** Each is right (the same unit as the live TEACH location at B), wrong, or abstained.
- **Phase 2 readouts.** The readout holds the answer for questions 51-100, and for the cross-phase repeats (asked
  again in phase 2 after being taught in phase 1).
- **The Life's identity.** sha before and after save and load; every revised key keeps its history.

## Predictions
- **F1.** LIFE carries at least 90% of the entries it does not abstain on to the right unit, and none to a wrong one.
  CARRY-AS-IS carries at least 10 wrong.
- **F2.** LIFE holds the answer for at least as many phase-2 questions as each of REBUILD and CARRY-AS-IS.
- **F3.** On the cross-phase repeats, LIFE holds at least REBUILD's count.
- **F4.** The Life's sha is identical after save and load, and every revised key's history holds its A and B values.
