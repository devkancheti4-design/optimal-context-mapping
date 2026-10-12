# Results: the rebuilt kit (vectors only, the law's ADVANCE) live, clear between tasks, 100 questions

Protocol PROTOCOL_LIVE_VEC.md (hashed before any agent ran). The kit under test is the working tree, frozen as
kit_vec.diff (SHA-256 c849d10f...). Both arms ran 10 fresh sessions one after another, at the same time, on the
rebuilt index. Two blind judges graded all 200 answers. Reproduce: `python3 vec_report.py report`.

| | right | requests | cache-weighted input | context (fixed prompt out) | search/read/list |
|---|---|---|---|---|---|
| **VEC-CMLM** | **100/100** | **268** | **2,063,323** | **803,465** | **180** |
| VEC-ALONE | 100/100 | 335 | 2,455,955 | 917,518 | 285 |
| saving | same | 1.25x | 1.19x | 1.14x | 1.58x |

Per task, requests:

| task | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| VEC-CMLM | 27 | 27 | 23 | 25 | 30 | 22 | 29 | 30 | 27 | 28 |
| VEC-ALONE | 32 | 32 | 36 | 30 | 36 | 28 | 32 | 39 | 35 | 35 |

Per question, alone / CMLM:

| | requests | cache-weighted |
|---|---|---|
| first time, tasks 1-5 (35) | 1.19x | 1.15x |
| first time, tasks 6-10 (39) | **1.31x** | **1.26x** |
| asked before, tasks 1-5 (15) | 1.52x | 1.39x |
| asked before, tasks 6-10 (11) | 1.14x | 1.16x |

## Predictions
- **L1 held.** Fewer requests: 268 against 335.
- **L2 held.** Lower billed input: 1.19x.
- **L3 failed, narrowly.** The request saving was flat: 1.26x in tasks 1-5, 1.24x in tasks 6-10. It did not grow.
  Before the rebuild it fell, from 1.40x to 1.13x.
- **L4 held.** 100/100 both. The rebuilt index reached the answers the old one could not: Dockerfile, nginx.conf,
  .vscode and .mjml.
- **L5 failed.** Repeats cost 0.76 of alone's requests, against a 0.6 target.

## What the run shows
- **The saving no longer decays as teaching grows.** Tasks 6-10 kept the saving of tasks 1-5, and the saving on
  first-time questions rose, from 1.19x to 1.31x.
- **TEACH lines placed 98 of 100.** Each one became a question vector on code; no text was stored.
- **The repeats' saving was eaten by the oracle, again.**
  - The TEACH rule asks for "the one line your answer is on", so the agents read the file to confirm the exact line,
    even when the readout already held the answer. One agent said so.
  - Only 6 questions were answered with no search or read (2 repeats), against 16 (12 repeats) in the earlier kit's run.
  - Any line inside a unit maps to the same unit, so the readout item's own [path:line] label places the vector
    exactly as well.
  - Next: the TEACH rule says to cite the readout item's label when the answer came from it, with no need to read for
    line numbers.

## Reference (not the same index or alone run)
- **CLEAR-CMLM (the kit before the rebuild):** 273 requests, 2,067,417 warm-start cache-weighted, 98/100. Its saving
  fell from 1.40x to 1.13x across the tasks.
- **CLEAR-ALONE:** 341 requests, 98/100.
