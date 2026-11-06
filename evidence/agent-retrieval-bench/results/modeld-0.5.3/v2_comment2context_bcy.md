# BCY Budget Curve

- Generated at: `2026-11-05T21:03:07+00:00`
- Corpus manifest: `data/corpus/v2_comment2context/corpus_manifest.jsonl`
- Tokenizer: `regex_code_tokenizer_v1`
- Protocol: file-deduplicate ranked results, render canonical corpus file text with a path header, greedily pack by rank, and prefix-truncate at the budget boundary.
- Canonical coverage: a gold file counts when at least one non-header content token is packed.
- Sensitivity coverage: at threshold tau, require at least min(tau, available file-content tokens).
- Caveat: this report uses released corpus `kind=file` text and stored top-20 file lists.

## Overall Curve

| Rank | Method | Family | Samples | BCY@4k | BCY@8k | BCY@16k | BCY@32k |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | modeld-0.5.3 | modeld | 80 | 0.1062 | 0.2396 | 0.3604 | 0.4479 |

## comment2context

| Rank | Method | Family | Samples | BCY@4k | BCY@8k | BCY@16k | BCY@32k |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | modeld-0.5.3 | modeld | 80 | 0.1062 | 0.2396 | 0.3604 | 0.4479 |

## Packing Diagnostics

| Method | Used@8k | Packed files@8k | Partial files@8k | Missing ranked files@8k |
|---|---:|---:|---:|---:|
| modeld-0.5.3 | 7997.2750 | 8.1250 | 0.9750 | 0.0000 |

## Minimum-content Threshold Sensitivity at 8k

| Method | tau=1 | tau=16 | tau=32 | tau=64 | tau=128 |
|---|---:|---:|---:|---:|---:|
| modeld-0.5.3 | 0.2396 | 0.2396 | 0.2396 | 0.2396 | 0.2396 |
