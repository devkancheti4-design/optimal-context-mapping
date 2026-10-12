# Protocol: company-scale replay. Ten years of Django engineers' fixes through one shared kit (offline, no model calls)

Fixed before running; its SHA-256 goes in prereg_hashes.json.

## Question
Does a shared kit put the right code in front of the agent:
- with its laws alone (frozen, never taught);
- more often as it learns from every engineer's finished work (learning);
- and how much would that save in agent cost?

## Stream
- **Source:** histories/django, every non-merge commit from 2013-01-01 to 4a72da7 (2023-07-17), in commit order.
- **Kept:** commits whose subject starts "Fixed #<n>" and that touch at most 20 django/*.py files, at least one of which
  exists in the snapshot workspace (swe/files.json). That is 5,333 questions by many contributors over ten years.
- **Question:** the subject with the "Fixed #<n>[, #<m>...] -- " prefix removed.
- **Gold files:** the touched django/*.py files that exist in the snapshot.
- **Offline:** the clone is blob-less, so only file names per commit are used, not line diffs. Nothing is downloaded.

## Two forms of each question
- **RAW:** the subject as written.
- **MASKED:** every token that looks like code is removed. That means tokens containing any of . _ ( ) [ ] ` ' " = < > /
  or ::, CamelCase or inner-capital tokens, and all-caps tokens of 2+ letters. This is a conservative stand-in for a
  symptom-style ticket that names no code.

## Kits (the snapshot workspace swe/ws_base, kit at main 2b5d99e)
- **FROZEN:** never taught. The readout for each question.
- **LEARNING:** one workspace per form, taught as the stream goes.
  - For each question, the readout is taken first.
  - Then the question, in that form, is taught at one line of a gold file. This is the line the engineer's finished work
    points to, standing in for the TEACH line an agent would emit.
  - **The line:** the snapshot line, across the gold files, whose lowercase word tokens (3+ letters, the stop-word list
    in the script) overlap most with the RAW subject's. Ties go to the earlier file in git's order, then the earlier
    line.
  - If nothing overlaps, it is the first line of the first gold file. If the chosen line is one the workspace does not
    hold, the nearest held line within ±8 is used.

## Measures (per question, before it is taught)
- **File hit:** a gold file's path appears in the readout. This is the rule the earlier SWE reports used.
- **Lane opened** (LEARNING only): the readout opens with "(readout: the code a taught question".
- **Lane right:** the first corpus path after the lane header is a gold file.
- **History repeat:** some gold file was a gold file of an earlier question (no kit involved).
- **Grouping:** every measure is reported by decile of the stream (about 533 questions each) and overall.

## Cost projection (calibration fixed here, computed from data that already exists)
- **Source:** the PROTOCOL_SWE_SONNET.md sessions. Claude Sonnet 5.5, API-equivalent requests and API-equivalent list
  dollars as defined there.
- **The rates:**
  - c_A: ALONE's mean per issue.
  - c_K_hit and c_K_miss: KIT's mean per issue, split by whether the gold file is in that issue's KIT readout
    (readouts.json).
  - c_E: the eyes' mean per call.
  - p_NS: the share of eyes replies that were NEED_SEARCH (3 of 7).
- **Per-question cost:**
  - ALONE = c_A.
  - LAWS (frozen kit + agent) = c_K_hit or c_K_miss, by FROZEN's file hit.
  - LAWS + LEARNING (kit + agent) = the same, by LEARNING's file hit.
  - MODEL D = c_E + p_NS × (c_K_hit or c_K_miss) when the lane opens, otherwise LAWS + LEARNING.
- **Saving:** factor = ALONE / arm, by decile and overall.
- **This is a projection:** measured hit rates times measured conditional costs. It is not a measured bill.

## Predictions
- **R1.** LAWS alone: FROZEN's file hit on RAW questions is at least 60% over the stream.
- **R2.** LEARNING's file hit beats FROZEN's over the stream, on RAW. The advantage in the last decile is larger than in
  the first.
- **R3.** Novelty dies:
  - the lane-opened rate in the last decile is larger than in the first (RAW);
  - when the lane opens, its first item is right at least 50% of the time.
- **R4.** The saving scales: MODEL D's projected cost per question is lower in the last decile than in the first, and its
  saving against ALONE is at least 2.0x overall (RAW, requests).
- **R5.** MASKED questions show the same direction as R2 and R3: a larger learning advantage and lane rate in the last
  decile than in the first.
