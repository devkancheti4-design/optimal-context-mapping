# Results: real comprehension questions on bluesky-social/atproto (PROTOCOL_OSS_COMPREHENSION.md)

115 answered GitHub Discussions (2023-07-03 → 2026-05-10), real people asking how the AT Protocol code works, against
atproto at 2e4a11437 (2023-06-30). The product as it ships ran against the same Sonnet 5.5 agent working alone, with
the same tools. A blind judge (Sonnet 5.5, the PROTOCOL_VALUE4 rubric, both arms shuffled together) graded every answer
against the maintainers' accepted answer. The plan was hashed before the first model call; deviation D1 raised the
alone cap after the smoke test.

| | Model D | alone |
|---|---|---|
| cost | **$4.39** | $10.37 |
| requests | 428 | 551 |
| RIGHT / PARTIAL / WRONG | 33 / 38 / 44 | 35 / 42 / 38 |
| right or partial | 71 | 77 |
| quality points (RIGHT 2, PARTIAL 1) | 104 | 112 |

- **Paired, right or partial:** Model D alone gets 6; the agent alone gets 12; 97 are the same. The exact McNemar p is
  0.24, so the gap is not significant at this size.
- **Quality:** Model D reached 93% of the agent alone's points, at 2.36x less cost. That is 2.19x cheaper per point of
  quality.
- **By half:** the saving was 2.55x on the first 57 questions and 2.23x on the last 58. Accuracy fell for both arms on
  the later questions, because they ask about code newer than the 2023 snapshot.
- **Learning:** one question in 115 was answered by one read of learned code. These are different people's questions
  across three years, and they almost never repeat.

## Predictions
- **C1 held:** the bill was 2.36x lower, against a bar of 1.5x.
- **C2 failed:** right or partial was 71 against 77, a margin of 5.8 allowed. The paired gap is not significant
  (p = 0.24).
- **C3 failed:** the saving fell from 2.55x to 2.23x.
- **C4 failed:** reads went from 1 to 0.

## What it means
- On real comprehension questions about a codebase, Model D's first readout makes the agent's exploring cheaper:
  2.36x, at 93% of the quality.
- Learning adds nothing on a stream where every question is new (ν ≈ 1). The law then says S = A / K, and that is what
  was measured. The learning saving belongs to teams that re-ask about the same code, not to a public Q&A forum.

**Spend:** Model D $4.39, alone $10.37, judge $1.14.
