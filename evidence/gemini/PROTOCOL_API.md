# Protocol: the kit through a raw model API (Vertex AI, billed to project cmlm-bench), 3 runs per arm

Fixed before any call; its SHA-256 goes in prereg_hashes.json.

## Why
- Every earlier live run went through Claude Code subagents. This one is a standalone harness that calls a model API
  directly and counts every request and every billed token. A company can rerun it with its own key.
- The model is gemini-2.5-flash on Vertex AI (global). Claude on Vertex is enabled, but its quota is still 0.
- The harness is model-agnostic: the same script runs Claude once quota exists.

## Domain and stream
- **Codebase:** transformers 5.8.1 (10.8M tokens), with the 30 facts of PROTOCOL_LARGE.md.
- **Tasks:** 6 tasks of 10 questions per session.
  - Tasks 1-3: the first wordings.
  - Tasks 4-6: the second wordings, which are the repeats.
- **Runs:** 3 independent runs per arm. Each CMLM run starts from a fresh copy of large/ws_L_base.

## Arms
- **CMLM.** Each question arrives with the hook's readout and RULE, built by ocm.loop.readout on the kit at 1d0008e,
  unchanged. Each answer carries a TEACH pair, which is taught.
- **ALONE.** No readout and no teaching.
- **The same in both arms:**
  - **Tools:** search, read_file and list_files, as function calls with the outputs of large/tools.py (the kit's own
    /search, /read and /list formats).
  - **submit_answer:** records the answer and returns the next question, as next.sh does.
  - **Instructions:** the same as the LARGE subagents', at most 15 tool calls per question.
- **Model settings:** default generation settings and thinking in both arms.
- **Concurrency:** six chains (3 runs x 2 arms) run at the same time, and the tasks in a chain run in order.

## Measures (from the API's own usage metadata, per request)
- **Requests:**
  - per question and per session;
  - the factor ALONE / CMLM, with a 95% interval from a paired bootstrap over the 18 (run, task) pairs: 20,000
    resamples, seed 20261008.
- **Billed tokens:** prompt, cached, output and thinking.
  - **Dollars:** at the Vertex list price for gemini-2.5-flash, and later from the project's billing report.
- **Wall-clock time per question.** The workspace stays loaded in the harness process, so the readout costs no process
  start.
- **Right:** a blind judge per judge/JUDGE.md on all answers, shuffled, with no arm shown.
- **Readout held the answer:** the logged readout against the unit holding the fact's line.

## Predictions
- **A1.** The request factor's 95% interval lies above 1.25.
- **A2.** The billed-dollar factor's 95% interval lies above 1.0.
- **A3.** On the repeats (tasks 4-6), CMLM makes at least 1.5x fewer requests than ALONE.
- **A4.** CMLM's judged right count is at least ALONE's, less 3 per run on average (out of 60).
- **A5.** CMLM's wall-clock time per question is no more than ALONE's.
