# Protocol: the laws do the thinking in bits. One formula for the saving, across models (existing data only)

Fixed before computing; its SHA-256 goes in prereg_hashes.json. No new model calls.

## The formula
- **An agent session is r requests.** Request j re-sends everything so far, so it processes about x_j = P + g·(j − 1)
  tokens.
  - P is the fixed part: system prompt, tools, the question, and with the kit, the readout.
  - g is what each step adds: the tool output and the model's turn.
  - A session processes T(r) = r·P + g·r(r − 1)/2 tokens. That is quadratic in r: every skipped step saves its own
    tokens and all the re-sending after it.
- **Every model thinks the same way:** it decides where to look, looks, and decides again. Those decisions are the
  exploration calls (search, read, list).
- **The laws make that decision before the model starts,** in bits, at zero tokens. φ is the share of the agent's
  exploration calls the laws remove: φ = 1 − calls_kit / calls_alone.
- **Predicted token saving:** S_pred = T(r_alone; P_alone, g) / T(r_kit; P_kit, g).
  - g is fitted on ALONE sessions only: least squares of x_j on (j − 1), within sessions, pooled.
  - P_alone and P_kit are the arms' mean first-request tokens.
  - r_alone and r_kit are the arms' mean requests per session.

## Datasets (existing sessions; tokens processed = input + cache write + cache read + output, including thinking)
- **D1:** Claude Sonnet 5.5, 114 real django issues (PROTOCOL_SWE_SONNET.md). ALONE and KIT, one issue per session.
  - Requests are API-equivalent: the task read and the hand-back are removed.
  - Calls are counted from calls.jsonl.
- **D2:** Gemini 2.5 Flash, the same 114 issues (PROTOCOL_SWE.md), ALONE and KIT, one issue per session. Calls are taken
  as requests − 1: this log keeps no call list, and the last request submits.
- **D3:** Gemini 2.5 Flash, the 60-question transformers stream (PROTOCOL_API.md), ALONE and CMLM. 3 runs × 6 sessions of
  10 questions. Calls come from each request's call list (search, read_file, list_files).
- **D4:** Claude Opus 5.5, the same stream (PROTOCOL_LARGE.md), ALONE and CMLM, 6 sessions each. Calls are the search.sh,
  read.sh and list.sh commands in the transcripts.
- **D5:** Claude Sonnet 5.5, the same stream (PROTOCOL_SONNET.md, slice SON), measured as D4.
- **Multi-question sessions** (D3–D5) are measured per session: requests and context run across the 10 questions.

## Measures per dataset
calls_alone, calls_kit, φ, r_alone, r_kit, P_alone, P_kit, g, S_pred, the measured token saving S_T (sum over sessions,
ALONE / KIT) and the measured request saving S_r.

## Predictions
- **G1.** The laws take over the thinking on every model: φ ≥ 0.5 on every dataset.
- **G2.** The formula explains the saving: S_pred is within ±20% of S_T on every dataset.
- **G3.** Skipped steps cost more than the average step: S_T > S_r on every dataset.
- **G4.** S_T ≥ 2.0 on at least 3 of the 5 datasets.
