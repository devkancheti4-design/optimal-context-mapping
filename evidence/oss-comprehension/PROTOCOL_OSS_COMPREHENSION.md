# Proof on real comprehension questions: bluesky-social/atproto (written 2026-10-17, before any model call)

## Why this work
Understanding existing code (reading, navigating, finding where things are) takes about 58% of a professional
developer's working time (Xia et al., IEEE TSE 2018: 78 developers, 3,148 tracked hours). It is Model D's main use.

## Why this project
bluesky-social/atproto (TypeScript, about 9.7k stars) runs `anthropics/claude-code-action` on its own repository. Its
GitHub Discussions hold real people's questions about how the AT Protocol code works, each with an accepted answer from
the maintainers.

## Data
- **Questions:** every answered discussion created on or after 2023-07-01 (115), oldest first: categories "How to do
  it?", 'Clarifications and "Why?"' and "Dev Debugging". Each is the title, then the body, cut to 1,500 characters
  (`comp_questions.json`).
- **Gold:** the accepted answer.
- **Code:** atproto at `2e4a11437` (2023-06-30), the last commit before the window, frozen for the whole stream.

## Arms (the PROTOCOL_TEAM_YEAR harness: `ocm.hybrid` and the same alone loop)
- **Model D:** the product as shipped.
  - Haiku 5.5 reads learned code with the strict prompt; Sonnet 5.5 explores and teaches (MAX_CALLS 15).
  - One workspace server over the snapshot, default scope ("all": the docs count for these questions), cold.
  - It learns only from its own explorations, in question order.
- **Alone:** Sonnet 5.5 with the same tools, never taught. It may run in parallel shards.

## Grading
- A blind judge, Claude Sonnet 5.5, with the PROTOCOL_VALUE4 rubric verbatim (`evidence/claude-api/scripts/judge4.py`):
  RIGHT if the answer states the reference's key facts with no contradiction, PARTIAL if it states some and
  contradicts none, WRONG otherwise.
- Answers from both arms are shuffled with a fixed seed. The judge sees no arm label.

## Measures
- Per arm:
  - RIGHT, PARTIAL and WRONG counts;
  - requests, tokens and dollars at list price;
  - the read share (questions answered by one read of learned code).
- By half of the stream: the saving and the read share.

## Predictions (fixed now)
- **C1, the bill:** alone / Model D ≥ 1.5x. Earlier comprehension evidence: 1.90x on SWE-QA, 2.3–2.8x for a team.
- **C2, the work:** Model D's RIGHT + PARTIAL ≥ alone's − 5% of the questions.
- **C3, learning over time:** the saving on the second half > on the first.
- **C4, novelty falls:** Model D's read share on the second half > on the first.

## Caps and reporting
- Caps: alone $12, Model D $7, judge $3.
- Every number is reported whichever way it comes out. Deviations go in `PROTOCOL_OSS_COMPREHENSION.md.deviations`.
