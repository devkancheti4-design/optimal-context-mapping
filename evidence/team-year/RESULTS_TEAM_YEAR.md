# Results: a team's year on one codebase (PROTOCOL_TEAM_YEAR.md, PROTOCOL_TEAM_YEAR_GATE.md)

Django's 288 real "Fixed #" commits from 2022, in commit order. The product as it ships (`ocm.hybrid`: Haiku 5.5 reads
learned code, Sonnet 5.5 explores and teaches) ran against the same Sonnet agent working alone, on the same tools and
the same code (Django at 0ab58c1209, 2022-01-03). Model D started cold and learned only from its own explorations. The
plans were hashed before the first model call (PREREG_HASHES.txt). The deviations, D0–D7, are listed at the end.

## The bill bends as novelty falls

| quarter | novelty ν | Model D, $ per fix | alone, $ per fix | saving | right, cited (D4): Model D / alone |
|---|---|---|---|---|---|
| Q1 | 0.89 | 0.032 | 0.061 | 1.88x | 67 / 67 of 73 |
| Q2 | 0.93 | 0.049 | 0.083 | 1.70x | 62 / 62 of 69 |
| Q3 | 0.84 | 0.050 | 0.112 | 2.23x | 67 / 71 of 80 |
| Q4 | **0.78** | 0.041 | 0.105 | **2.57x** | 56 / 53 of 63 |
| **year** | 0.86 | **$12.32** | **$25.72** | **2.09x** | **252 / 253 of 285** |

- **Requests:** 1,162 against 1,597.
- **The read path:** 40 fixes were answered by one cheap read, at $0.0004 each. Of those, 36 cited a changed file;
  the agent alone got 37 of the same 40, at about 100 times the cost.
- **Explored fixes:** 216 right against the agent alone's 216, on the same 245 questions.

## Predictions

| | prediction | result |
|---|---|---|
| T1 | the bill: alone / Model D ≥ 1.5x | **held: 2.09x** |
| T2 | the work: right ≥ alone − 3% (as pre-registered) | **failed: 227 vs 253.** All 25 of the gap are read-path answers that the pre-registered rule (the readout's first file) marks wrong while the answer cites the changed file (D4). Cited: 252 vs 253. |
| T3 | novelty falls: ν(Q4) < ν(Q1) | **held: 0.78 < 0.89** |
| T4 | the saving grows: Q4 > Q1 | **held: 2.57x > 1.88x** |
| T5 | the law, as written | an identity, not a test (D2) |
| T5′ | the law forecasts each quarter from the earlier ones, within 15% | **held:** Q2 +6.3%, Q3 −13.8%, Q4 −13.7% |

## The gate (OCM_CERT_MIN_OVER_OWN = 37)

| | gated | ungated |
|---|---|---|
| saving over the year | 2.14x ($11.90 vs $25.44, 281 paired) | 2.09x |
| Q4 saving | 2.79x | 2.57x |
| read-path answers citing a changed file | 27 of 31 (87%) | 36 of 40 (90%) |
| right, cited, against alone | 245 vs 249 | 252 vs 253 |

- **G1 failed:** read precision is not higher with the gate.
- **G2 failed** on the pre-registered rule (227 vs 249).
- **G3 held:** 2.14x.
- **G4 held:** the gate cost no more than ungated.
- **T5′ for the gated arm failed:** Q4 −23%.
- **Conclusion:** on this stream the gate buys nothing. The default stays off.

## What it means
- On real team work, where nearly every fix is genuinely new, Model D gives the same work for about half the bill.
- Most of the saving is the kit's first readout: an exploration with it costs $0.050 against $0.090 alone.
- As the year goes on and novelty falls, more fixes are answered by one read, and the saving rises from 1.88x to 2.57x.
- The learning law forecast each quarter from the earlier ones within 14%.

## Deviations (PROTOCOL_TEAM_YEAR.md.deviations)
- **D0:** code scope on the Model D server.
- **D1, D5, D7:** caps raised, each recorded before the arm ran out, because the agent alone cost more than planned.
- **D2:** T5 is an identity; T5′ replaces it before Q2.
- **D3:** the alone arm ran in 3 parallel shards. It never learns, so order cannot matter.
- **D4:** the cited measure, added after 49 questions.
- **D6:** one gated question lost to an HTTP 500; the product fix is in 0.4.0.

Three alone questions and five gated ones did not complete, so every comparison is paired.

**Total spend:** Model D $12.32, gated $11.90, alone $25.72.
