# Results

Every test below was run live with fresh Claude agents (the same model and the same instructions in both arms, except
the tools section), graded by blind judges who did not know which arm wrote an answer, and fixed in writing (with a
SHA-256 hash of the plan) before it ran. Costs come from the agents' own transcripts (model requests, input billed) and
the tool servers' logs. Deviations were recorded as they happened. The full evidence (protocols with their hashes,
questions, every answer, every verdict, call logs) is available on request.

## 1. A project team on a real codebase plus web research
Seven role agents (project manager, team lead, senior developer, backend developer, frontend developer, junior
developer, HR) did Phase-1 research for a project on a real client app (React + TypeScript, 63 files) and 62 web pages.
41 questions, written and independently verified (45 of 63 kept). Each condition was run with fresh agents:

| team | right | model requests | searches and reads | billed input (cache-weighted) |
|---|---|---|---|---|
| each role alone (run 1) | 41/41 | 138 | 122 | 1,054,776 |
| each role alone (run 2) | 41/41 | 141 | 123 | 1,063,918 |
| shared workspace, a note taught after every answer | 41/41 | 117 | 57 | 1,003,603 |
| **shared workspace, notes taught once per role (batched)** | **41/41** | **84** | **58** | **756,142** |

Batched teaching: **1.66x fewer requests** and **1.40x less billed input** than working alone, the same accuracy. Two
alone runs differed by 2%. Later roles gained most (the senior developer did 6 searches and reads instead of 21).

**The arithmetic, tested before the run.** Requests = searches and reads + teach calls + a fixed per-session overhead.
Frozen before the batched run: 83 requests (68 to 98), 1.66x (1.4 to 2.0), billed 1.48x (1.2 to 1.8). Measured: 84,
1.66x, 1.40x. `python -m ocm calc` is this arithmetic.

## 2. Seven codebases, single-fact questions
About 1M tokens from each of transformers, torch, scipy, pandas, sympy, scikit-learn and numpy (7M tokens, 133,875
units); 28 first-time questions, 4 per codebase.

| per right answer | Claude with search | one shared workspace | one workspace per codebase + overseer |
|---|---|---|---|
| right | 28/28 | 28/28 | 28/28 |
| model requests | 2.36 | **0.39** (6.1x fewer) | 1.11 (2.1x fewer) |
| billed input, cache-weighted | 16,370 | **5,766** (2.8x less) | 12,884 |

One workspace over everything beat one per codebase: the overseer sent 8 of 28 questions to the wrong codebase first.

## 3. One large codebase, first-time and repeated questions
The transformers library at two sizes (1.1M and 10.8M tokens). 30 questions, then the same 30 facts asked again in new
words by a different agent after the first one taught.

| tools / workspace, per right answer | 1.1M first | 1.1M repeat | 10.8M first | 10.8M repeat |
|---|---|---|---|---|
| model requests | 7.0x | 7.9x | 3.6x | **9.2x** |
| billed input, cache-weighted | 3.6x | 3.5x | 2.0x | 3.9x |
| right (each arm) | 30/30 | 30/30 | 30/30 | 30/30 |

## 4. Multi-file deep dives (the weak spot)
20 verified questions, each needing 2 to 3 files, on the 10.8M-token codebase, with the router law:
40/40 right in both arms; 1.17x fewer requests and 1.21x less billed input. A taught note covers one answer, not a whole
trail, so repeated deep dives were not cheaper.

## 5. Text research (earlier tests)
A stream of 120 research questions over 1M to 9M tokens of text: the same accuracy, 3 to 5x fewer requests; on repeated
questions 1.7 to 1.8x fewer tokens and 4.5 to 9.1x fewer requests.

A note on wording: the readout that serves one teammate's note alone was labelled "certified" during these runs.
It is the vector law's nearest match, not a verified answer, and is now labelled so ("a teammate's note, the nearest
match by meaning"). The ranking itself did not change.

## 6. A team proof of the kit as shipped (the prediction failed)
The kit exactly as shipped (the zip, unchanged) on a real app it had never seen: the Full Stack FastAPI Template (233
files). Two teams of five fresh Claude agents (team lead, backend, frontend, DevOps, new joiner) answered 5 questions
each: 25 verified questions, 7 of them repeating a fact a teammate asked earlier. One team searched and read alone. The
other followed `pilot/AGENT_INSTRUCTIONS.md` word for word: ask the workspace first, teach once at the end. The plan,
the questions and the prediction were fixed with hashes before the run. A blind judge graded the answers, and requests
were counted from the transcripts with `python -m ocm measure compare`.

| | alone | team with the workspace |
|---|---|---|
| right (blind judge) | 24/25 | 24/25 |
| model requests | 67 | **101 (1.51x more)** |
| input billed, cache-weighted | 686,850 | 795,746 (1.16x more) |
| search, read and list calls | 67 | 58 |
| workspace calls | none | 25 ask, 3 next, 5 teach |

Predicted by `python -m ocm calc` before the run: 2.77x fewer requests (2.41 to 3.21). Measured: 0.66x. **The team
with the workspace made more requests, and the prediction failed.**

Why, from the same logs:
- **The ask round trip.** Every question began with a separate `ask` call: 25 asks and 3 nexts, each a model round
  trip. The earlier tests handed agents the first readout with the question at no request, and the calculator's data
  comes from those tests.
- **Agents checked the code anyway.** They made 58 search, read and list calls with the workspace against 67 without,
  only 13% fewer.
- **Two top-ranked notes were wrong.** The workspace served a teammate's note as its whole readout 6 times: 4 right (all
  on repeat questions) and 2
  wrong. For q26 and q32 it served a teammate's note about a different fact; the agents noticed and searched instead.
- **Notes cost requests too.** Writing notes and teaching added 6 file writes and 5 teach calls.
- **The overhead showed before any note existed.** The first role, with nothing taught yet, already made 19 requests
  against 16.
- **Dockerfiles are not indexed.** One question (q26) could not be fully answered in either arm, because the kit skips
  files without an extension, such as `Dockerfile`.

What it means: as shipped, on a five-person team asking first-time lookups with 28% repeats, the kit does not save
requests; it costs about half again as many, at the same accuracy. The fixes it points to:
- deliver the first readout together with the question (a prompt hook, so it costs no request);
- serve a note alone only when it answers the same fact;
- index files without an extension.

**Measured on the map itself, not the agents.** The same 25 questions were replayed with no agents against a fresh
copy of the scanned workspace, with the team's real notes taught in the same order (`map_measure.py`).

The scan: the repository's 449,756 tokens, of which the kit kept 146,763, stored as 3,898 fingerprints (499 KB). It
used no model tokens and took 33 seconds.

| per question | tokens of code handed to the model |
|---|---|
| without the map: what agents fetched by search, read and list (server log) | 1,245 |
| the map's first readout | 359 |
| a teammate's note served alone (the 4 right ones) | 135 |
| on the 11 questions whose first readout held the answer | 366 (3.4x fewer) |
| the map first, then search when both readouts miss (computed) | 1,414 (0.88x) |

How often the map held the answer:
- the first readout held the answering lines for 11 of 25 questions, and the first or second for 13;
- 4 of the 7 repeats were answered by a teammate's note served alone;
- 2 notes served alone were wrong.

Where the map holds the answer it hands over 3.4x fewer tokens, or 9x fewer for a teammate's note. Here it held the
answer too rarely to save on balance, so coverage is the lever. In the live run agents fetched both: 1,200 tokens of
code per question with the map, against 1,245 without.

Video, 76 seconds, every number read from the run's files: [`team_proof.mp4`](team_proof.mp4).

Limits: one run per team, 25 questions, one codebase; Claude wrote and judged the questions. A network outage
interrupted the team's last agent; it was resumed, and all its requests are counted.

## 7. The same team proof with the workspace inside the model's loop
The kit rebuilt so the model never calls the workspace (`ocm/loop.py`, run as Claude Code hooks):
- **Before each request**, the workspace's recall goes in with it.
- **The model** answers from those facts or searches, and ends its reply with a TEACH: line.
- **After the reply**, that line is taught locally.

There is no `ask` round trip and no carried transcript. The same 25 questions were run with a fresh agent per question
and a blind judge on all 75 answers; the plan was fixed with a hash first.

| | right | model requests | input billed, cache-weighted |
|---|---|---|---|
| a fresh agent per question, no workspace | 24/25 | 115 | 1,001,993 |
| **a fresh agent per question, workspace in the loop** | **24/25** | **71 (1.62x fewer)** | **748,032 (1.34x less)** |
| section 6: the workspace as a tool | 24/25 | 101 | 795,746 |
| section 6: role sessions alone, each carrying 5 questions of transcript | 24/25 | 67 | 686,850 |

- **In the loop beats the same setup without memory** by 1.62x in requests at equal accuracy.
- **10 of 25 questions took a single request**, with no search at all.
- **Repeats are where it pays most:** 14 requests against 33 (2.4x) on the 7 questions a teammate had asked before.
- **It beats the tool placement** (71 requests against 101).
- **It does not beat short sessions that carry their own transcript** (71 against 67). Five questions leave little
  transcript to replace; the transcript saving needs long sessions, which is what the CMLM is for, and a long-session
  test is the next one.
- **The calculator's 2.77x prediction failed again.** The workspace still served a wrong note alone on 2 questions, and
  both agents caught it.

## 8. How the CMLM should train in the loop (offline replay)
The design says the CMLM trains locally after each reply: vectors generalise and laws learn. We replayed the 25
questions in team order through the kit's own server, teaching after each role the real TEACH lines the in-the-loop
agents wrote, in three modes. Each question's first readout was measured before anything about it was taught. The plan
was fixed with a hash first.

| how the CMLM trains | answer in the first readout | every needed file | wrong note served alone | tokens per readout | repeats answered |
|---|---|---|---|---|---|
| note only (the kit until now) | 15/25 | 12/25 | 2 | 366 | 6/7 (296 tokens) |
| **note + the learned law trains (now the default)** | 15/25 | 12/25 | 2 | 366 | 6/7 (296 tokens) |
| note + cues on the cited code + the learned law | 14/25 | 11/25 | 0 | 511 | 5/7 (589 tokens) |

- **The law trains in both law modes** (73 examples each).
- **With note + law, it stayed off.** It never beat the plain vector order (4 right first each), so its gate kept it
  off, and that mode measures the same as note only.
- **With the cited code cued, it switched on** (7 right first against 4). But the note and the cited code then tie,
  so the cheap readout of one teammate's note stops firing: 40% more tokens per readout and one answer fewer, though
  no wrong note was ever served alone.
- **Choosing the default.** The rule fixed in advance (most answers shown) tied note only with note + law on every
  measure. Note + law was chosen because it costs nothing now and lets the law switch on by itself if it ever beats
  plain order on a team's own work.

## 9. A long session: Claude's own transcript against the CMLM giving the context
One agent answered all 25 questions in one session, as people use Claude Code, carrying its transcript, with and
without the CMLM's facts arriving with each question (the prompt hook's output; the stop hook taught each answer). A
blind judge graded all answers; the plan was fixed with a hash first.

Every Claude request carries a fixed 41,579-token prompt (system prompt and tools) that the CMLM cannot change, so each
bill below is split into that fixed part and the context part:

| arm (25 questions) | right | requests | billed input, cache-weighted | of which context | context tokens read |
|---|---|---|---|---|---|
| long session, alone | 24/25 | 74 | 643,156 | 287,656 | 2,205,996 |
| **long session, CMLM in the loop** | **24/25** | **55 (1.35x fewer)** | **529,939 (1.21x less)** | 253,439 | 1,803,836 |
| a fresh call per question with the CMLM, no transcript | 24/25 | 71 | 748,031 | 184,406 | 351,159 (6.3x less) |

- **In a normal long Claude Code session, the CMLM saves** 1.35x requests and 1.21x billed input at equal accuracy;
  searches and reads fell from 55 to 33.
- **With no transcript at all, the CMLM's own design reads 6.3x less context.** Inside Claude Code, though, every
  fresh call pays the fixed prompt's start again, which made its whole bill the highest; in a custom loop with a
  small prompt, context would dominate instead.
- **The transcript grew 2,267 tokens per question,** re-read by every request, so its cost grows with the square of
  the session's length. Longer sessions should favour the CMLM more; that is arithmetic, not yet measured.

## What it predicts for a team (`python -m ocm calc`)

| repeat share | lookups only | with 30% deep dives |
|---|---|---|
| 0% | 2.39x fewer requests (2.03 to 2.84) | 1.56x (1.37 to 1.79) |
| 50% | 3.17x (2.83 to 3.57) | 1.63x (1.47 to 1.82) |
| 90% | 4.33x (3.91 to 4.78) | 1.69x (1.47 to 1.97) |

95% bootstrap intervals over 395 measured question-runs (`python -m ocm calc --table` reproduces this table exactly).
These pools come from tests that handed agents the first readout with the question. For the kit as shipped, where
agents call `ask` themselves, the arithmetic did not hold: section 6 predicted 2.77x and measured 0.66x.
At 16,800 questions a month (40 engineers x 20 a day x 21 days, an assumption), lookup work makes about 27,700 to
36,000 fewer requests a month. Projections, not a live test at that size.

## Limits
- One run per condition in most tests; questions written by Claude; judges Claude; open-source code, one client app
  and Wikipedia pages. Your codebase and your team are the real test: see `pilot/`.
- Billed input falls less than requests; deep dives save little; notes are append-only.
- As shipped, the separate `ask` call can cost more requests than it saves (section 6); the earlier gains came with
  the first readout handed to agents with the question.
- Agents sometimes broke instructions (piping tool output through grep); every case was counted and reported.
