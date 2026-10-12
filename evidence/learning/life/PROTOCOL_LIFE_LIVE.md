# Protocol: the kit with the Life inside, live, across a real code move

Fixed before any agent runs; its SHA-256 goes in prereg_hashes.json.

## The kit under test (optimal-context-mapping working tree, frozen as kit_life.diff)
The vectors-only kit plus living-fused's Life (ocm/life.py, MIT, vendored unchanged from d083b61):
- /teach records each taught question with its exact line in <workspace>/taught.life.json.
- `ocm build --carry OLD` re-finds every entry by its exact line, writes it as a revision, and teaches its vector. An
  entry whose line is gone abstains.
- The laws, the readout and the TEACH rule are unchanged.

## The code move
The FastAPI template from 36ddc1a (2025-09-08; revA/corpus, 3,010 units) to 13652b5 (2026-04-16; the corpus, 3,945
units), 400 commits.

## Runs
- **Phase 1, at the old code.** 5 fresh CMLM sessions, one after another, answer questions 1-50 on ws_A_life, exactly
  as VEC-CMLM did: the hook's readout with each question, and each answer's TEACH line taught. Phase 1 answers are not
  scored, because the questions were written against the new code.
- **The code moves.** Two workspaces at the new code:
  - **REBUILD:** a plain build, a copy of ws_vec_base. This is the kit before the Life: nothing is carried.
  - **LIFE:** a build with `--carry ws_A_life`.
- **Phase 2, at the new code.** Questions 51-100, in two chains of 5 fresh sessions, one after another, run at the
  same time: REBUILD on its workspace, LIFE on its own. Both teach as they go.
- **References (not rerun):**
  - VEC-CMLM tasks 6-10: the same kit, taught at the new code all along (no move).
  - VEC-ALONE tasks 6-10: no CMLM.

## Measures
- **Right:** blind judges (JUDGE.md) on the 100 phase-2 answers, shuffled, with no arm shown.
- **From the transcripts:** requests, cache-weighted input, and search, read and list calls, per arm and per question.
  Reported separately for the cross-phase repeats (asked in phase 2 after being taught in phase 1).
- **The carry:** entries, carried, moved, abstained, and the Life's sha.

## Predictions
- **LL1.** LIFE makes fewer phase-2 requests than REBUILD.
- **LL2.** On the cross-phase repeats, LIFE makes fewer requests per question than REBUILD.
- **LL3.** LIFE is right on at least REBUILD's count, less 2.

## Stated in advance
Only 9 of the 50 phase-2 questions are cross-phase repeats, and sessions vary by a few requests. A small effect may not
show above that noise.
