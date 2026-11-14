# THE EMBEDDING LAW: results, 14 November 2026

Model D's router thresholds are derived from each embedding model's own measured geometry, instead of staying frozen at bge-base's numbers.

- **Branch:** `embed-law`, in the worktree `~/optimal-context-mapping-embed-law`. Not committed.
- **Offline:** no Claude, no API. Embeddings only.
- **Panel:** bge-base (the control) and all-MiniLM-L6-v2, the two models already cached. The disk was below the 2.5 GB floor for downloads.
- **Pre-registration:** PROTOCOL.md was hashed at 18:17 IST, before MiniLM was measured. Amendments 1–4 are at the end of HASHES.txt: the whole laws, the E8 runner, the offline fix, the comparator.
- **E8:** held. One command regenerated every number exactly, in a fresh folder.

## Verdict

- **Part A carries the result for a swapped model.** Reading how to embed from the model's own files raises MiniLM's memory hits (G2) from 42 to 101 of 216. That's +59, with a 95% interval of +43 to +76.
- **L1 thresholds add a little.** L1 uses one reference geometry per model. MiniLM gains +7 (+3 to +12) over Part A alone, and bge-base gains +6 (+1 to +12) over the control. Wrong pulls don't change.
- **L2 thresholds lose hits.** L2 uses each map's own geometry. MiniLM drops −20 (−29 to −12) against Part A alone, and bge-base −1 (−3 to 0). Code maps spread wider than the reference corpus, so per-map thresholds come out stricter. They cost hits and removed no wrong pulls.
- **Predictions:**
  - P3 held.
  - P1 and P5 failed exactly where PROTOCOL.md said they would, before a second model was measured.
  - P2 failed on two wrong pulls, which Part A caused, not the thresholds.
  - P4 failed on the reference corpus but holds on code maps.

## Who authored each threshold

Every threshold is now an integer law that the engine authored, each with a fresh colony that finished strictly alive (generation ≥ 1, all four organisms alive and ticked). Each was then proven on every input of its domain: 3 translation units, -O3 and -O1, `-fwrapv`, volatile sink.

| threshold | law | the engine's part | supplied | proof |
|---|---|---|---|---|
| RELATION_LIMIT | `RLIM(s \| a84 << 10)` | the whole expression; generation 3, 4/4 alive, 811 evaluations | 10-bit field readers; its own proven SEL as material; no constants | all 1,048,576 inputs, and all 2^32 int32 |
| GAP (= Cortex D's GAP) | `GAPW(s2 \| a98 << 10)` | the whole expression; same as RLIM, from a separate fresh colony (807 evaluations): one rule at k = 1 and k = 2 | the same | the same |
| TAU = NEAR = DELTA | `TAUW(a98 \| N << 10)` | the whole expression `(2^21 + a98 * XF(N)) >> 22`; size 5, minimal; generation 3, 4/4 alive, 31,007 evaluations, 0.83 s | the declared table XF(N) = round(2^21 (√(2 ln N) − √(2 ln N/3))) and its scale (2^21, >> 22) | all 2,147,452,928 inputs of its domain |
| SEL (the 4-bit rule inside RLIM and GAP) | `SEL(d)` | found alone, from the intent "mask" and the constant 4 | nothing else | d in [−1024, 1024] |
| certifier gap and near, learned-law near | `CGAP(s)`, `CNEAR(s)` | composed the multiply and shift | the constants 4539/1990/12 and 1107/2006/12 (brute-force search) | s in [0, 511] |

**TAU:**
- **Integers only (pose 1).** The engine got the N field, an exact integer square root, the multiply and the scale. It found no expression up to size 5; the search space closed empty at sizes 3, 4 and 5. An integer engine has no logarithm, and that abstention names the missing piece.
- **With the factor as one declared table (pose 2).** Found in 0.83 s. In the earlier crashed run, a separate fresh colony found the same expression.
- **Change of definition (Amendment 1).**
  - TAU now reads round(lift98), as GAP already did, and the factor is rounded once at 2^-21.
  - It differs from PROTOCOL.md's float formula on 65,589 of the 2,147,452,928 domain inputs (0.003%). Each difference is one bit, at a near-tie within 0.00012 of a half.
  - On all 25 calibrations this study recorded, TAU is unchanged. One of them, MiniLM on celery, has a fractional lift98 of 116.90.
  - Two L2 arms re-run on the wired code gave byte-identical readouts.
- **Domain:** 30 to 2,097,151 units. A map outside that range is left uncalibrated and keeps today's numbers, instead of failing the build.

**Still mine:**
- measuring the geometry (σ₀ and the two lifts, from 2,000 pseudo-queries), rounding it once, and packing the inputs
- the XF table
- the CGAP and CNEAR constants
- Part A's file reader, the router wiring, and the harness

The rules themselves (σ₀, 2σ₀, the 4-bit tolerance, the extreme-value form) came from your spec. TAU's use of the tail spread (lift98 / 2) came from Stage 1.

## Stage 1: where 37 and 8 come from (bge-base)

| where | units | per-query σ | q84 − median | q98 − median | random-pair σ |
|---|---|---|---|---|---|
| 20 Newsgroups sample (fts9m.db) | 20,000 | 30.9 | 32 | 68 | 34.5 |
| artemis | 33,411 | 38.7 | 38 | 82 | 44.0 |
| FrontierAgent | 27,517 | 34.9 | 36 | 77 | 41.3 |
| DeepInfer | 11,339 | 35.7 | 37 | 80 | 40.9 |
| sphinx | 41,641 | 36.1 | 37 | 80 | 42.0 |
| textual | 35,389 | 36.5 | 37 | 81 | 41.6 |
| celery | 38,549 | 37.0 | 39 | 82 | 40.6 |

- **37 isn't reproduced on the 20 Newsgroups corpus.** The per-query spread there is 30.9 for pseudo-queries and 30.8 for the 244 real questions. Random pairs give 34.5, which matches the paper's 34. On the six code maps the per-query spread is 34.9 to 38.7, so 37 fits code, not the corpus it was said to come from.
- **8 is the paper's Table 4.** The best wrong match is 670, 678 and 687 at 1M, 3M and 9M tokens. On nested subsets of the sample, the best-wrong shift per tripling measured +14.0 and +10.5 bits. The Gaussian extreme-value form predicts +8.3 and +7.8 (σ₀ = 30.8). The tail is heavier than Gaussian, which is why TAU uses the tail spread.
- **0.04 and 0.01 (the certifier) were never derived.** They are kept as the same numbers, expressed in σ₀ units.

## Stage 3: E1 to E8

| check | result |
|---|---|
| E1 same for bge | **failed, as predicted.** L1 gives TAU 8 but GAP 68, RELATION_LIMIT 31, certifier 34/8, where today's are 74/37/41/10. Readouts identical on 2 of 6 repositories. |
| E2 old maps | held: 6 of 6 byte-identical |
| E3 no labels | held: the same numbers with the 12 lessons taught as without |
| E4 deterministic | held: twice identical on CPU (DeepInfer: σ₀ 35.725, RL 36, GAP 80, TAU 10, certifier 40/10). The device is recorded, because CPU and Apple GPU bits can differ. |
| E5 from the files | held. bge reads as first token, normalised, bge's instruction (from the declared table quoting its card), 128 tokens. MiniLM reads as mean pooling, normalised, no prompt, 128 tokens (its own limit is 256). gpt2 is refused for having no pooling config. The only use of a model's name is the declared prompt table. |
| E6 free | held. 0 tokens. L2 calibration takes 13–16 s per map for bge and 5–7 s for MiniLM. On sphinx (41,641 units): 24.6 s, with memory going from 600 to 724 MB. |
| E7 lessons | held: 12 of 12 carried under bge, MiniLM frozen and MiniLM read, all with the identical Life (sha `aedd4b9bf73cedbb`) |
| E8 reproducible | **held.** `zsh e8.sh` copied the harness byte for byte into a fresh folder (`~/neos/sandbox/embed_law_e8`) and ran its one command, `reproduce.sh`, from 19:00:06 to 19:40:16. Every number came back exactly: Stage 1; both L1 geometries; all 48 gate runs, readouts byte-identical; E3–E7; results.json; all 12 MiniLM maps, byte for byte apart from timestamps. All six laws came back with the same expressions, proofs and even evaluation counts; only the colonies' clocks (ticks) differ. See E8_COMPARE.md. |

## Stage 4: the gates

Six ColdSession-Fresh repositories, 15 facts each, pooled.

| model | arm | G1 line | G1 file | G2 lead | G3 wrong |
|---|---|---|---|---|---|
| bge-base | frozen | 50/90 | 41/90 | 135/216 | 8/72 |
| bge-base | read | 50/90 | 41/90 | 135/216 | 8/72 |
| bge-base | L1 | 50/90 | 41/90 | 141/216 | 8/72 |
| bge-base | L2 | 50/90 | 41/90 | 134/216 | 8/72 |
| all-MiniLM-L6-v2 | frozen | 39/90 | 20/90 | 42/216 | 2/72 |
| all-MiniLM-L6-v2 | read | 41/90 | 20/90 | 101/216 | 4/72 |
| all-MiniLM-L6-v2 | L1 | 41/90 | 20/90 | 108/216 | 4/72 |
| all-MiniLM-L6-v2 | L2 | 41/90 | 20/90 | 81/216 | 4/72 |

The differences below are paired over facts, with 95% bootstrap intervals (10,000 resamples, seed 0). In bge's rows, "frozen" means the control.

| comparison | G1 line | G2 lead | G3 wrong |
|---|---|---|---|
| MiniLM: read − frozen (Part A alone) | +2 (−4, +8) | **+59 (+43, +76)** | +2 (0, +5) |
| MiniLM: L1 − read (thresholds alone) | 0 | +7 (+3, +12) | 0 |
| MiniLM: L2 − read (thresholds alone) | 0 | **−20 (−29, −12)** | 0 |
| bge: L1 − frozen | 0 | +6 (+1, +12) | 0 |
| bge: L2 − frozen | 0 | −1 (−3, 0) | 0 |

### Predictions

- **P1, E1 to E8 hold: failed,** on E1 only, as stated before measuring.
- **P2, MiniLM under L1 scores at least as well as frozen on G2 and pulls no more wrong lines on G3: failed.** G2 gained +66 (+50 to +83), which held. G3 had +2 wrong pulls (0 to +5), which did not. Those two come from Part A (read − frozen +2), not from the thresholds (L1 − read: 0).
- **P3, the G2 spread between models is smaller under L1 than frozen: held.** It fell from 0.43 to 0.15 (share of taught-line leads).
- **P4, σ₀ differs by at least 20% between models: failed on the reference corpus.** Under L1 it's 30.9 against 32.1, a 3.6% difference. On code maps (L2) it differs by 17–43%, with 5 of 6 maps at 20% or more.
- **P5, bge's σ₀ on code is within 10% of 37, so L2 changes nothing: the second half failed, as predicted.** σ₀ is 34.9 to 38.7, all within 10%. But L2 moves GAP to 77–82 and TAU to 10, and readouts changed on 1 of 6 repositories.

### Geometry and thresholds per model

| model | where | N | σ₀ | lift84 | lift98 | RL | GAP | TAU | certifier |
|---|---|---|---|---|---|---|---|---|---|
| bge-base | L1 (20NG sample) | 277,681 | 30.9 | 32 | 68 | 31 | 68 | 8 | 34/8 |
| bge-base | L2 artemis | 33,411 | 38.7 | 38 | 82 | 39 | 82 | 10 | 43/11 |
| bge-base | L2 FrontierAgent | 27,517 | 34.9 | 36 | 77 | 35 | 77 | 10 | 39/9 |
| bge-base | L2 DeepInfer | 11,339 | 35.7 | 37 | 80 | 36 | 80 | 10 | 40/10 |
| bge-base | L2 sphinx | 41,641 | 36.1 | 37 | 80 | 36 | 80 | 10 | 40/10 |
| bge-base | L2 textual | 35,389 | 36.5 | 37 | 81 | 36 | 81 | 10 | 40/10 |
| bge-base | L2 celery | 38,549 | 37.0 | 39 | 82 | 37 | 82 | 10 | 41/10 |
| all-MiniLM-L6-v2 | L1 (20NG sample) | 277,681 | 32.1 | 33 | 73 | 32 | 73 | 8 | 35/9 |
| all-MiniLM-L6-v2 | L2 artemis | 33,411 | 48.5 | 50 | 106 | 49 | 106 | 13 | 54/13 |
| all-MiniLM-L6-v2 | L2 FrontierAgent | 27,517 | 42.3 | 44 | 97 | 42 | 97 | 12 | 47/11 |
| all-MiniLM-L6-v2 | L2 DeepInfer | 11,339 | 47.4 | 51 | 111 | 47 | 111 | 15 | 52/13 |
| all-MiniLM-L6-v2 | L2 sphinx | 41,641 | 51.6 | 54 | 111 | 52 | 111 | 14 | 58/14 |
| all-MiniLM-L6-v2 | L2 textual | 35,389 | 42.8 | 44 | 99 | 43 | 99 | 12 | 48/12 |
| all-MiniLM-L6-v2 | L2 celery | 38,549 | 51.8 | 58 | 116.90 | 58 | 117 | 14 | 58/14 |
| 0.5.3 today | frozen | | | | | 37 | 74 | 8 | 41/10 |

## Offline: a flaw E8 found, and its fix

The protocol says everything runs offline. Part A's reader (`read_spec`) didn't: it ran before the embedder turned the Hugging Face Hub off. So every read-mode map build and both L1 references sent metadata requests (HEAD) to huggingface.co, asking whether the model's config files had changed. This happened in the original runs too, where error output was discarded.

- **No downloads:** nothing was downloaded. No file in the model cache changed that day, and both models still point at the same cached commits. No number is affected.
- **Hidden fragility:** with the Hub unreachable, the old reader **refused** both models ("no pooling config") even though their files were cached.
- **Fix (Amendment 3):** with `OCM_OFFLINE=1`, the reader reads the local cache only and turns the Hub off before `huggingface_hub` is imported, so the model load that follows stays off too.
- **Test:** against a local stand-in for the Hub, the old reader made 6 connection attempts. The fixed reader, a full gate run and an L1 reference each made 0, with specs, readouts and geometry identical to the record.
- **In the live E8 run:** the steps that started before the fix sent the same 7 requests the original runs did. Every step after it sent none.

Amendment 4: E8's comparator was made to compare a gzip file decompressed. A gzip header stamps the time the file was written, which also changes the manifest's hash of it. Fields that only newer script versions write, and free-text labels, are reported instead of counted. Every field and every number the record has is still compared exactly.

## Cost

- **Build, MiniLM on the Apple GPU:** 37–90 s per map. The frozen and read builds are within 15% of each other.
- **Map size:** MiniLM 12–31 MB per map (302 MB for all 12); bge-base 15–34 MB.
- **Calibration:** 5–16 s per map, 0 tokens.
- **Engine runs for the laws:** under 1 s per find. Peak memory was 27 MB for RLIM/GAPW and 342 MB for TAU.

## Not run

- **Five panel models were not run:** bge-small, bge-large, e5-base-v2, arctic-embed-m-v1.5 and Qwen3-Embedding-0.6B. The disk was below the download floor. With two models, P3's spread rests on a single pair.
- **G4** (ColdSession, after its later rebuilds) was not run.
- **Outside the protocol's scope:** live token savings, collections over about 100,000 units, questions over 128 tokens, languages other than English.

## Files (all in ~/neos/sandbox/embed_law)

- **Pre-registration:** PROTOCOL.md; HASHES.txt (Amendment 1 at the end).
- **Results:** results.json (every E check, prediction, total and interval); runs/ (every gate run, with verbatim readouts).
- **Laws:** laws/laws.json (SEL, CGAP, CNEAR); laws/whole_laws.json (RLIM, GAPW); laws/tau_law.json (both TAU poses, the proof, the float comparison).
- **Scripts:** analyze.py, verify_wiring.py, reproduce.sh (the one command), e8.sh and e8_compare.py (E8: regenerate into a fresh folder, compare every number).
- **E8's regeneration:** `~/neos/sandbox/embed_law_e8`, with E8_COMPARE.md, e8_compare.json, reproduce.log and stderr.log.
- **Branch changes:** ocm/embed_laws.py, ocm/calibrate.py, ocm/cmlm_vector/embed.py, ocm/cmlm_vector/memory.py, ocm/router/{router,lanes}.py, ocm/graph.py, ocm/build.py. Not committed.
