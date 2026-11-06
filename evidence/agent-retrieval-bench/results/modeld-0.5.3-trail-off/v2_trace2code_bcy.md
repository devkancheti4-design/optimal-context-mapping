# BCY Budget Curve

- Generated at: `2026-11-05T14:14:23+00:00`
- Corpus manifest: `data/corpus/v2_trace2code/corpus_manifest.jsonl`
- Tokenizer: `regex_code_tokenizer_v1`
- Protocol: file-deduplicate ranked results, render canonical corpus file text with a path header, greedily pack by rank, and prefix-truncate at the budget boundary.
- Canonical coverage: a gold file counts when at least one non-header content token is packed.
- Sensitivity coverage: at threshold tau, require at least min(tau, available file-content tokens).
- Caveat: this report uses released corpus `kind=file` text and stored top-20 file lists.

## Overall Curve

| Rank | Method | Family | Samples | BCY@4k | BCY@8k | BCY@16k | BCY@32k |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | modeld-0.5.3-trail-off | modeld | 101 | 0.2244 | 0.3152 | 0.4142 | 0.4785 |

## trace2code

| Rank | Method | Family | Samples | BCY@4k | BCY@8k | BCY@16k | BCY@32k |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | modeld-0.5.3-trail-off | modeld | 101 | 0.2244 | 0.3152 | 0.4142 | 0.4785 |

## Packing Diagnostics

| Method | Used@8k | Packed files@8k | Partial files@8k | Missing ranked files@8k |
|---|---:|---:|---:|---:|
| modeld-0.5.3-trail-off | 8000.0000 | 5.9208 | 1.0000 | 0.0000 |

## Minimum-content Threshold Sensitivity at 8k

| Method | tau=1 | tau=16 | tau=32 | tau=64 | tau=128 |
|---|---:|---:|---:|---:|---:|
| modeld-0.5.3-trail-off | 0.3152 | 0.3152 | 0.3152 | 0.3152 | 0.3152 |
