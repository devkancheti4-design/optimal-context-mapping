# Results: the kit live on a large codebase (a closed domain), and the map it absorbed

Protocol ../PROTOCOL_LARGE.md, hashed before any agent ran. The kit at 8002a4e, unchanged. The codebase is transformers
5.8.1: 2,347 files, 43 MB, about 10.8M tokens, 183,830 units (the build took 28 minutes on an M-series Mac). The 30
facts and their second wordings come from cmlm-bench5. Two chains of 6 fresh sessions ran together. Two blind judges
graded all 120 answers. Reproduce: `~/.venvs/cmlm-live/bin/python report.py report`.

| | right | requests | cache-weighted input | search/read/list |
|---|---|---|---|---|
| **L-CMLM** | **60/60** | **132** | **1,056,232** | **64** |
| L-ALONE | 60/60 | 226 | 1,705,546 | 172 |
| saving | same | **1.71x** | **1.61x** | **2.69x** |

| task | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| L-CMLM requests | 23 | 25 | 18 | 21 | 22 | 23 |
| L-ALONE requests | 37 | 39 | 35 | 38 | 39 | 38 |

- First wordings (tasks 1-3): 66 against 111 requests, **1.68x**.
- Repeats (tasks 4-6): 66 against 115, **1.74x**.

## The absorbed map, checked against the truth
For each of the 30 second wordings, the readout logged before it reached the agent was compared with the unit holding
the fact's line:

| right | junk (wrong unit) | not absorbed |
|---|---|---|
| **30** | **0** | **0** |

Every fact taught once was found again under a new wording, on the exact code, with no junk. This is neo4d's closed-
domain topology result seen in context mapping: the learned map equals the true map on every fact taught.

## Predictions: G1 to G4 all held
- **G1.** 1.71x is more than the 1.25x on the FastAPI template.
- **G2.** Repeats saved 1.74x, at least 1.5x.
- **G3.** Right: 60 against 60.
- **G4.** The taught lane opened on the right unit 30 times and on a wrong unit 0 times.

## The scale, the same kit live
| codebase | tokens | fewer requests | fewer searches and reads |
|---|---|---|---|
| FastAPI template (results section 12) | about 148k | 1.25x | 1.58x |
| **transformers** | **about 10.8M** | **1.71x** | **2.69x** |

The saving grew with the codebase: the more there is to search, the more a readout saves. On repeats the CMLM agents
made one read per question, to confirm the exact line for the TEACH rule, and no search. That read is most of what is
left.

## Rule breaks, counted
- The CMLM arm had 2 sessions with a `| cat`. It changed no output.
- The alone arm had 3 calls with a pipe (`| cat`, or `| head -0`, which errored before any output).
- All are kept in the transcripts.
