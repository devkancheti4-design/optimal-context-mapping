# Results: living-fused's Life as the CMLM's exact memory of what was taught, across a real code move (offline)

Protocol PROTOCOL_LIFE.md, hashed before running. The Life is life/life.py (MIT) from ~/living-fused at d083b61,
imported unchanged. The code move is the FastAPI template's own history: 36ddc1a (2025-09-08) to 13652b5
(2026-04-16), 400 commits. Script: life_replay.py.

Phase 1 taught 38 questions at the old code. 19 of their lines had moved by the new code: another file or another line.
The workspace was rebuilt at the new code, then questions 51-100 were asked and taught there.

| at the new code | carried right / wrong / lost | phase 2: answer in the readout | cross-phase repeats |
|---|---|---|---|
| REBUILD (the kit today: a rebuild loses what was taught) | 0 / 0 / 38 | 33/50 | 3/9 |
| CARRY-AS-IS (the old path:line) | 24 / 6 / 8 | 35/50 | 6/9 |
| **LIFE (exact memory, revised by exact identity)** | **38 / 0 / 0** | **36/50** | **7/9** |
| NO-MOVE (upper bound: the code never moved) | - | 36/50 | 7/9 |

On the 19 moved entries alone: LIFE carried 19 right; CARRY-AS-IS got 5 right, 6 wrong and lost 8.

## The Life's identity
- sha before save e53eaf44c91a5152, after reload e53eaf44c91a5152: byte-exact.
- 38 keys. The 19 revised keys each keep both values: the old location, then the new one winning.

## Predictions
- **F1 failed, on the baseline's half only.** LIFE was 38/38 right with 0 wrong, as predicted. But CARRY-AS-IS put 6
  wrong, not the 10 or more predicted; it lost 8 more where the old file no longer exists.
- **F2 held.** 36 against 33 and 35.
- **F3 held.** 7 against 3 cross-phase repeats.
- **F4 held.** The sha is identical, and every revised key keeps its history.

## What it shows
- **What was taught survives the code moving.** With the Life as its exact memory, the CMLM carried every taught
  entry across 400 commits to the right code, and matched the no-move upper bound exactly: 36/50, and 7/9 repeats.
- **The kit today loses it.** A rebuild forgets everything taught, and repeats fall from 7/9 to 3/9.
- **Carrying locations as they are is not enough.** Code moves, so 14 of the 19 moved entries landed wrong or nowhere.
- **Exact, never guessed.** Each new location was found by the exact line the answer was on. An entry whose code was
  gone would have abstained; none had to.
