# Protocol: 114 real django issues (SWE-bench Lite) on Claude Sonnet 5.5, with Claude Haiku 5.5 as the eyes

Fixed before any agent runs; its SHA-256 goes in prereg_hashes.json. This is PROTOCOL_SWE.md with the model changed to
Claude: the agents are Claude Code subagents, the same way PROTOCOL_SONNET.md ran (Vertex Claude quota is 0 and there is
no Anthropic API key).

## Unchanged from PROTOCOL_SWE.md
- **Data and codebase:** the 114 issues (swe/issues.json), the django snapshot, and swe/tools.py's search / read /
  list over it.
- **The task:** name the one source file the real fix changed. Right means the named file is the gold file.
- **Prompts:** the system text (SYSTEM, SYSTEM_KIT, EYES) and the issue text (the first 6,000 characters), word for
  word from swe/swe_bench.py.
- **Limit:** at most 15 tool calls per issue, enforced by the tool scripts.
- **Learning:** after each issue, the kit is taught the issue text at the gold line, in the order the issues were
  opened.
  - The teaching never uses an agent's answer, so the kit's readout for every issue is fixed in advance.
  - The readouts are computed once (swe_sonnet/readouts.py, kit at main 2b5d99e, law files unchanged since 1d0008e).
  - The computation ran twice with byte-identical results: 7 of the 114 readouts are on the taught lane.
  - Because the readouts are fixed, the issues can run in parallel without changing what any agent sees.

## Arms (each issue a fresh subagent)
- **ALONE:** Claude Sonnet 5.5 with the issue and the three tools, run as shell scripts. It answers with submit.sh.
- **KIT:** the same, with the kit's readout and RULE before the issue.
- **MODEL D:** the kit decides the path.
  - **Taught-lane issues:** one call to Claude Haiku 5.5, as a subagent with model "haiku", with the EYES text, the issue
    and the readout. It has no tools and replies once. A file path ends the issue.
  - **NEED_SEARCH, or not on the taught lane:** the body runs. The body is the KIT session for that issue, and its
    measured result is used. The body's input is identical to KIT's, so running it a second time would only add
    sampling noise and cost.
  - **MODEL D's cost per issue** is the eyes call, if any, plus the KIT session, if it ran.

## Measures (from each subagent's transcript)
- **Requests:** the assistant messages with usage (distinct message ids).
- **Tokens:** input, cache write, cache read and output.
- **Dollars at list price, per 1M tokens:**

  | Model | Input | Cache write | Cache read | Output |
  |---|---|---|---|---|
  | Sonnet 5.5 | $2.00 | $2.50 | $0.20 | $10 |
  | Haiku 5.5 | $0.10 | $0.125 | $0.01 | $0.50 |

  Cache write is 1.25x input and cache read is 0.1x input.
- **The tokens include Claude Code's own system prompt and tool definitions,** the same for every arm. Absolute dollars
  are therefore higher than a bare API harness would bill. The factors compare like with like.
- **Model check:** every transcript's model is checked: Sonnet 5.5 for ALONE and KIT, Haiku 5.5 for the eyes.
- **Off-script tool use is counted and reported.** Any tool call other than the four scripts counts, such as reading
  the django files directly.
- **Factors:** ALONE / KIT and ALONE / MODEL D for requests and dollars. Each comes with a 95% paired bootstrap interval
  over issues (20,000 resamples, seed 20261008).
  - The same factors are given for the first and second half of the stream, and for repeat-file vs new-file issues, as
    in PROTOCOL_SWE.md.

## Predictions
- **S1 (W1).** KIT makes fewer requests than ALONE, with the 95% interval above 1.0. Its right count is within 5 of
  ALONE's.
- **S2 (W2).** MODEL D makes fewer requests than KIT. Its right count is within 5 of ALONE's.
- **S3.** MODEL D's dollars are lower than ALONE's, with the 95% interval of the dollar factor above 1.0.
- **S4 (W3).** MODEL D's request saving against ALONE is larger in the second half of the stream than in the first.
- **S5 (W4).** MODEL D's request saving against ALONE is larger on the issues whose gold file was fixed before.
