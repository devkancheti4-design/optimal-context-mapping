# Results: 114 real django issues (SWE-bench Lite) on Claude Sonnet 5.5, Haiku 5.5 as the eyes

- **Protocol:** PROTOCOL_SWE_SONNET.md, sha256 a2e9d04c…33c8, fixed before any agent ran. Deviations DS1 and DS2 were
  written before the bulk run.
- **Run:** 2026-10-08. 229 Claude Code subagents: 114 ALONE, 114 KIT and 7 eyes.
- **Data:** every number below comes from the subagents' own transcripts (report.py → report_swe_sonnet.json).
- **Model check:** ALONE 114/114 and KIT 114/114 sessions ran on claude-sonnet-5-5. The eyes ran on claude-haiku-5-5,
  7/7.
- **Off-script calls:** 2 in 229 sessions, neither touching the django files:
  - one call to read.sh under a lowercase tool name;
  - one empty, failed tool call by an eyes agent before it answered NEED_SEARCH.

## All 114 issues

| | ALONE | KIT | MODEL D |
|---|---|---|---|
| right (named the file the real fix changed) | 111 | 112 | 112 |
| requests per issue, measured | 5.52 | 3.76 | 3.75 |
| requests per issue, API-equivalent (DS1/DS2) | 3.52 | 1.76 | 1.76 |
| list-price dollars per issue, measured | $0.0976 | $0.0802 | $0.0779 |
| list-price dollars per issue, API-equivalent | $0.0468 | $0.0292 | $0.0281 |

Factors against ALONE, with 95% paired bootstrap intervals over issues:

| | KIT | MODEL D |
|---|---|---|
| requests, measured | **1.47x** [1.38, 1.56] | **1.47x** [1.38, 1.57] |
| requests, API-equivalent | **2.00x** [1.77, 2.26] | **2.00x** [1.77, 2.28] |
| dollars, measured | 1.22x [1.17, 1.27] | 1.25x [1.19, 1.32] |
| dollars, API-equivalent | 1.60x [1.45, 1.78] | 1.67x [1.49, 1.87] |

- **The measured dollars** include Claude Code's own system prompt and tool definitions: about 45k cached tokens in every
  session, in every arm. That overhead shrinks the dollar factor.
- **The API-equivalent figures** remove only the task-read and hand-back requests that a bare API harness does not have
  (DS1, DS2).

## Predictions

| | prediction | result |
|---|---|---|
| S1 | KIT fewer requests than ALONE (interval above 1.0), right within 5 | **holds**: 1.47x [1.38, 1.56]; 112 vs 111 right |
| S2 | MODEL D fewer requests than KIT, right within 5 of ALONE | **holds, but only just**: 3.75 vs 3.76 per issue; 112 right |
| S3 | MODEL D dollar factor's interval above 1.0 | **holds**: 1.25x [1.19, 1.32] |
| S4 | MODEL D saving larger in the second half | **fails**: first half 1.58x, second half 1.38x |
| S5 | MODEL D saving larger on repeat-file issues | **fails**: repeat file 1.44x, new file 1.49x |

## What this shows, and what it does not

- **Accuracy:** on Claude Sonnet 5.5, the kit halves the work per real issue in API-equivalent requests, 2.00x
  [1.77, 2.26]. It does so without losing accuracy: 112 right with the kit, 111 alone.
- **Model D is no better than KIT here.** The eyes fired on only 7 of the 114 issues: the taught lane needs an issue close
  to an earlier one.
  - Haiku answered 4 of the 7, and all 4 were right, at 1 request each.
  - It handed the other 3 to the agent with NEED_SEARCH, as designed.
  - On this stream the hybrid's extra saving over KIT is small. On the Gemini 2.5 Flash run of the same stream it was
    larger.
- **The learning-curve predictions failed on Sonnet** (S4, S5). Sonnet alone is already efficient at about 3.5
  API-equivalent requests per issue. The kit's saving is about the same in both halves and on new and repeat files.
  - On Flash, where the agent alone needed 7.25 requests, the saving grew over the stream (W3, W4 held).
- **Flash on the same issues:** right 84 / 94 / 93 for ALONE / KIT / MODEL D; requests 7.25 / 4.21 / 3.75; factors 1.72x
  and 1.94x. The stronger the agent, the smaller the absolute saving. The saving is still about 2x in API-equivalent
  requests.
- **Caveats:**
  - one run per arm;
  - one django snapshot;
  - a "file-localisation" task, not the full patch-and-test task;
  - the dollars are list-price equivalents, since the subagents ran on the Claude Code subscription, not on a billed
    API key.

## Gemini 3.1 Pro (PROTOCOL_PRO.md) did not complete

- **Rate limits:** the preview model's endpoint rate-limited project cmlm-bench on almost every request. In about an hour
  it finished 2 issues per arm (all 6 right, $2.22).
- **Stopped:** at that pace the run would take more than two days, so it was stopped (DP2). No Pro prediction is scored.
