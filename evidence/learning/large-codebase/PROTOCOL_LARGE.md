# Protocol: the kit live on a large codebase (a closed domain), and the map it absorbs

Fixed before any agent runs; its SHA-256 goes in prereg_hashes.json.

## The domain
transformers 5.8.1: ~/cmlm-bench5/L/corpus, 2,347 files, 43 MB, about 10.8M tokens. It is the large codebase of
cmlm-bench5 (PROTOCOL_CODE.md), with its 30 verified facts. Each fact has a question, a second wording written
separately, an answer and the file:line it rests on.

## Stream
60 questions in 6 tasks of 10, each task a fresh session:
- **Tasks 1-3:** the first wordings of c01 to c30, in order.
- **Tasks 4-6:** the second wordings, in the same order. These are the repeats; the CMLM has been taught the first
  wordings.

## Arms (two chains of 6 sessions, one after another, run at the same time)
- **L-CMLM.** The kit at 8002a4e, unchanged: vectors-only teaching, the router law with its ADVANCE, and the Life.
  - The workspace is a fresh build over the corpus (large/ws_L_base).
  - Each question comes with the hook's readout and RULE, and each TEACH line is taught.
- **L-ALONE.** No readout, no teaching.
- **Tools, the same in both arms.** search.sh, read.sh and list.sh over the kit's own file list for the corpus, with
  the same outputs as the kit's /search, /read and /list. They are run directly, so a tool call does not load the
  workspace.

## Measures
- **Right:** a blind judge (JUDGE.md) on all 120 answers, shuffled, with no arm shown.
- **From the transcripts:** requests, cache-weighted input, and search, read and list calls, per task. Reported for
  the first wordings (tasks 1-3) and the repeats (tasks 4-6).
- **The absorbed map, checked against the truth.** For every second wording in L-CMLM, the readout logged before it
  reached the agent: the taught lane opened on the unit holding the fact's line (right), opened on another unit
  (junk), or did not open (not absorbed).
- **Reference:** the same kit live on the FastAPI template (about 148k tokens), 1.25x fewer requests (results
  section 12).

## Predictions
- **G1.** L-CMLM makes fewer requests than L-ALONE, by a larger factor than 1.25x.
- **G2.** On the repeats (tasks 4-6), L-CMLM makes at least 1.5x fewer requests than L-ALONE.
- **G3.** L-CMLM is right on at least L-ALONE's count, less 2, out of 60.
- **G4.** For the second wordings, the taught lane opens on the right unit for at least 24 of 30, and on another unit
  for at most 3.
