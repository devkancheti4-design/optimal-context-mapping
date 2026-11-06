# BCY Budget Curve

- Generated at: `2026-11-05T22:34:50+00:00`
- Corpus manifest: `data/corpus/v2_code2test/corpus_manifest.jsonl`
- Tokenizer: `regex_code_tokenizer_v1`
- Protocol: file-deduplicate ranked results, render canonical corpus file text with a path header, greedily pack by rank, and prefix-truncate at the budget boundary.
- Canonical coverage: a gold file counts when at least one non-header content token is packed.
- Sensitivity coverage: at threshold tau, require at least min(tau, available file-content tokens).
- Caveat: this report uses released corpus `kind=file` text and stored top-20 file lists.

## Overall Curve

| Rank | Method | Family | Samples | BCY@4k | BCY@8k | BCY@16k | BCY@32k |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | modeld-0.5.3 | modeld | 106 | 0.1321 | 0.2107 | 0.3459 | 0.4610 |

## code2test

| Rank | Method | Family | Samples | BCY@4k | BCY@8k | BCY@16k | BCY@32k |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | modeld-0.5.3 | modeld | 106 | 0.1321 | 0.2107 | 0.3459 | 0.4610 |

## Packing Diagnostics

| Method | Used@8k | Packed files@8k | Partial files@8k | Missing ranked files@8k |
|---|---:|---:|---:|---:|
| modeld-0.5.3 | 8000.0000 | 7.0000 | 1.0000 | 0.0000 |

## Minimum-content Threshold Sensitivity at 8k

| Method | tau=1 | tau=16 | tau=32 | tau=64 | tau=128 |
|---|---:|---:|---:|---:|---:|
| modeld-0.5.3 | 0.2107 | 0.2107 | 0.2107 | 0.2107 | 0.2107 |
