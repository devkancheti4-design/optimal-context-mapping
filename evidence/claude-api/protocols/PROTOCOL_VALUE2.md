# PROTOCOL_VALUE2: replications, deep research, four more codebases (fixed before any request of this batch)

The setup, prices, ALONE, MODEL D, scoring, statistics, M1 and M2 are exactly those of PROTOCOL_VALUE.md. Value 1's
results were known while this was written: E1, E3, E4 and E6 had finished, E2 and E5 had not. This batch exists to
confirm or refute them on new runs and new data.

**Budget:** the runner stops this batch once the shared ledger passes $120 for both batches together. This replaces
value 1's $150 for everything after this point.

## F1: E1 replicated twice
- Runs 2 and 3: ALONE and MODEL D on the 114 django reports, fresh workspaces, same order.
- P1: in each run, MODEL D needs fewer requests than ALONE (interval above 1.0).
- P2: over the three runs, MODEL D's mean right per run is within 5 of ALONE's.
- P3: over the three runs pooled (issue × run), MODEL D's list-price cost is lower than ALONE's (interval above 1.0).
- M1 and M2 on each run, with value 1's 20% criteria.

## F2: E4 (names removed) replicated once
- Run 2: ALONE and MODEL D on the 114 masked reports, fresh workspaces.
- P4: MODEL D is again right on more than 5 fewer reports than ALONE.
  - This checks that value 1's failure (V8) is real, not noise.
  - If MODEL D is within 5, the run-1 accuracy loss is called not replicated.

## F3: deep research (code + docs + web)
- Questions: 30 django settings, sampled with seed 20261009 from value 1's 165 candidates. A setting is excluded if
  it was among E6's 30, or if no file in the django code reads it.
  - "Reads it" means a file other than conf/global_settings.py contains `settings.<S>` or `settings, "<S>"`.
- Pass 1: "Where in Django's source code is the `<SETTING>` setting used, and what is its default value?"
- Pass 2: "Which part of Django reads `<SETTING>`, and what value does it have when a project does not set it?"
- Both arms have web search (at most 5 uses) and the code tools. MODEL D works as in E6.
- Right means both:
  - the answer contains the documented default (E6's rule);
  - it names at least one file that reads the setting, by path or by the module path written with dots.
- P5: pass 1, MODEL D is at least 1.5x cheaper than ALONE.
- P6: pass 1, MODEL D's accuracy is within 3 questions of ALONE's.
- P7: pass 2, MODEL D is at least 4x cheaper than ALONE.

## F4: four more codebases
- Data: SWE-bench Lite's matplotlib (23), sphinx (16), requests (6) and flask (3) issues, 48 in all.
- Workspaces as in E5: built by the compiled package at each repository's latest base commit; created_at order.
- P8: pooled over the 48, MODEL D needs fewer requests than ALONE (interval above 1.0), and its accuracy is within 5
  points of ALONE's.
- M1 and M2 on F4.

## Order and honesty
- F1, F2 and F3 run in parallel, each on its own workspaces and ports. F4 runs when its workspaces are built.
- Deviations go in PROTOCOL_VALUE2.md.deviations before the affected numbers are read.
- Every prediction is reported held or failed.
