# Results: teach the whole codebase once, then ask real questions (PROTOCOL_COVERAGE.md)

Claude Haiku 5.5 wrote one question for each of Django's 23,976 non-test code units: 23,951 written, for $0.97. All of
them were taught once onto their units with the product's `teach_at`, in 590 seconds on a laptop. Then the 288 real
Django 2022 fix questions, never seen, went to the cold workspace and to the covered one. No model calls were made
after the generation.

| | cold | covered |
|---|---|---|
| right file first | 111 | **142** |
| right file in the top 5 of the first readout | 197 | 193 |
| readouts led by taught code | 0 | 153 of 288 (53%) |
| the learned law | off ("the vector order") | **switched itself on**: it beat the vector order 16 to 9 in its prequential check, over 23,948 examples |

- **Right file first, paired:** covered only 69, cold only 38, exact McNemar p = 0.0035.
- **Top 5, paired:** 42 against 46, p = 0.75, so no real change. When taught code leads, the first readout is one item.
  The shipped product also sends the next readout then (`ocm.loop.readout`).
- **Questions led by taught code (153):** right first 83, against 64 cold. **The other 135:** 59 against 47, so
  coverage also improved the untaught readouts.

## The threshold: right-first precision of taught-led readouts, by margin m

| m (bits) | n | right first | 95% interval | cold, same questions |
|---|---|---|---|---|
| 0–20 | 6 | 50% | 19–81% | 3 |
| 20–37 | 12 | 42% | 19–68% | 6 |
| 37–50 | 16 | 50% | 28–72% | 8 |
| 50–74 | 40 | 52% | 37–67% | 21 |
| 74+ | 79 | 58% | 47–68% | 26 |

There is no sharp threshold. Precision rises slowly with the margin, and at m ≥ 74 bits (2σ), taught code is right
first 58% of the time, against 33% for cold on the same questions.

## Predictions
- **V1 failed:** top 5, 193 against 197. The paired difference is not significant (p = 0.75).
- **V2 failed:** right first at m ≥ 37 was 56%, against a bar of 60%.
- **V3 held:** 53% of readouts were led by taught code, against a bar of 30%.

## What it means
- Teaching the whole codebase once does generalize to new real questions. The right file comes first 28% more often
  (111 → 142, p = 0.0035), and the learned law switches itself on.
- A taught answer is right about half the time, so the cheap read still needs the reader's check (it says NEED_SEARCH
  when the code does not answer). That is the product's design, and E/K ≈ 1% makes it pay at this precision.
- **Cost:** about $1 of Haiku, and 10 minutes on a laptop, for a 24k-unit codebase.
