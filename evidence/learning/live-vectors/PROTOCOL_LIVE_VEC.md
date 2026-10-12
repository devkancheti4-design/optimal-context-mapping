# Protocol: the rebuilt kit (vectors only, the law's ADVANCE) live, clear between tasks, 100 questions

Fixed before any agent runs; its SHA-256 goes in prereg_hashes.json.

## The kit under test (optimal-context-mapping, working tree after the rebuild)
- **Teaching stores no text.** A TEACH line `<question> | <path>:<line>` puts the question's vector as a cue on the unit
  holding that line (Memory.teach_at), and is an example for the learned law.
- **The hook sends the router law's first readout,** and when that is the taught lane, the law's own next readout
  (ADVANCE).
- **The index covers** Dockerfile and other extensionless build files, .conf, .mjml and .vscode. Doc sentences keep
  their lines.
- **Unchanged:** the vector law, the router law, the learned law and their thresholds.
- **Offline check before this run** (kit_validate.py, each question taught on its true answer line):
  - all 100: 65 against 61 untaught;
  - repeats: 13/15 and 8/11, against 7/15 and 5/11 untaught;
  - first-time questions lost 5.

## Arms (the same 100 questions, the same 10 tasks of 10, the same tools and prompt otherwise)
- **VEC-CMLM.**
  - 10 fresh sessions, one after another, on one workspace (a fresh copy of ws_vec_base) that keeps what was taught.
  - Each question comes with the hook's readout (ocm.loop.readout, in process) and the kit's RULE.
  - Each answer's TEACH line is taught through /teach.
- **VEC-ALONE.**
  - 10 fresh sessions, one after another, on its own fresh copy of ws_vec_base, for search, read and list only.
  - No readout and no teaching.
- **Run together.** Both chains run at the same time, each one session after another, so both read Claude's shared
  prompt from cache alike.
- **References (not rerun):** CLEAR-CMLM and CLEAR-ALONE (RESULTS_CLEAR.md: the kit before the rebuild, on the old
  index).

## Measures
- **Right:** blind judges (JUDGE.md) on all 200 new answers, shuffled, with no arm shown.
- **From the transcripts:**
  - requests and cache-weighted input (new 1, cache writes 1.25, cache reads 0.1);
  - context with the fixed prompt taken out;
  - search, read and list calls;
  - each per question (scale_check.py's split), for first-time and asked-before questions, tasks 1-5 and tasks 6-10;
  - TEACH lines placed and not placed.

## Predictions
- **L1.** VEC-CMLM makes fewer requests than VEC-ALONE.
- **L2.** VEC-CMLM's cache-weighted input is lower than VEC-ALONE's.
- **L3, the scale question.** The request saving (VEC-ALONE / VEC-CMLM) in tasks 6-10 is at least that in tasks 1-5.
  Before the rebuild it fell from 1.40 to 1.13.
- **L4.** VEC-CMLM is right on at least VEC-ALONE's count, less 2.
- **L5.** On asked-before questions, VEC-CMLM's requests per question are at most 0.6 of VEC-ALONE's.
