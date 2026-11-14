# THE EMBEDDING LAW: protocol and predictions

Written 14 November 2026, before any embedding model other than BAAI/bge-base-en-v1.5 was measured. Its SHA-256 is in
HASHES.txt. Spec: ~/neos/PROMPT_EMBED_LAW.md.

## Code and data

- Control: ~/eval/repos/modelD, Model D 0.5.3, commit ec440d7 (never modified).
- Branch: embed-law off main (d452c9a), in the git worktree ~/optimal-context-mapping-embed-law. Not committed.
- Harness: ~/neos/sandbox/embed_law (stage1*.py, laws/, gates.py). Everything runs offline: no Claude, no API.
- Panel, as the owner chose on 14 November: **bge-base** (the control) and **sentence-transformers/all-MiniLM-L6-v2**
  (mean pooling, no prompt), the two models already cached. The disk had 1.7 GB free, below the spec's 2.5 GB floor
  for any download, so bge-small, bge-large, e5-base-v2, arctic-embed-m-v1.5 and Qwen3-Embedding-0.6B are not run.

## The law, fixed before any other model is measured

Part A, read from the model's own files (ocm/cmlm_vector/embed.py, read_spec): pooling from the Pooling module's
config.json, normalisation from modules.json, prompts from config_sentence_transformers.json `prompts`, otherwise from
the declared PROMPT_TABLE (each entry quoting its model card), max length min(128, the model's own limit). A model with
no pooling config, or needing trust_remote_code, is refused. bge-base reads as first token, normalised, bge's
instruction, 128: the part-A path is bit-identical to 0.5.3's on CPU and on the Apple GPU (checked).

Part B, measured once per map (ocm/calibrate.py): 2,000 pseudo-queries (seed 0) from the map's own units, embedded with
the query prompt, each against every unit outside its own file. sigma0 = the median per-query spread; lift84/lift98 =
the median 84.13%/97.72% quantile over the median. With s = round(sigma0), s2 = round(2 sigma0), a84/a98 the rounded lifts:

    RELATION_LIMIT = s + SEL(a84 - s)            GAP = Cortex D GAP = s2 + SEL(a98 - s2)
    TAU = NEAR = DELTA = round((lift98 / 2) * (sqrt(2 ln N) - sqrt(2 ln N/3)))
    certifier gap = CGAP(s) = round(41 s / 37)    certifier near = learned-law near = CNEAR(s) = round(10 s / 37)

SEL, CGAP and CNEAR were authored by the integer program-synthesis engine, each by a fresh colony checked strictly alive
(generation >= 1, all four organisms alive and ticked), and proven on every input of their domains against the
derivation (3 translation units, -O3 and -O1, -fwrapv, volatile sink): SEL on [-1024, 1024], CGAP and CNEAR on [0, 511].
CGAP and CNEAR use multiply-shift constants found by brute force and declared, as earlier division lanes were.
TAU's root-of-log factor is float64 arithmetic, rounded once.

Why TAU takes the tail spread (lift98 / 2), fixed from Stage 1 alone: at the 20 Newsgroups collection where 8 bits per
tripling was measured (N/3 -> N = 92,560 -> 277,681), the Gaussian form with sigma0 = 30.9 gives 6.9 (7); the same form
with the tail spread 34 gives 7.6 (8). On nested subsets of the 20,000-sentence sample the measured shift (+14.0, +10.5)
exceeds the Gaussian prediction (+8.3, +7.8): the tail is heavier than Gaussian.

L1: one geometry per model, from the fixed 20,000-sentence sample (seed 0) of ~/cmlm-bench4/fts9m.db, with
N = 277,681 for TAU. Stage 1 could not confirm where 37 was measured, so this is the spec's fallback corpus.
L2: every map's own geometry, N = its unit count. A map with no calibration (any 0.5.3 map) uses today's numbers.

## Arms, per model

- frozen: the 0.5.3 control code with the model swapped in (first-token pooling for every model, bge's numbers).
- read: the branch with part A, bge's numbers.
- L1 and L2: the branch with part A and the thresholds above.

For bge-base, frozen and read are the same map (part A is bit-identical); its L1/L2 arms calibrate copies in memory.

## Gates (ColdSession-Fresh: artemis, FrontierAgent, DeepInfer, sphinx, textual, celery; 15 facts each)

- G1 cold: wording a of every fact, nothing taught. Gold line in the first readout; gold file first.
- G2 memory: teach wording a of the 12 taught facts onto their gold lines (the /teach call the Stop hook makes),
  then ask wordings b, c, d. Does the taught line lead the first readout?
- G3 wrong pulls: after teaching, all four wordings of the 3 facts never taught. How often does a taught line lead
  the readout when it is not the answer?
- G4 (ColdSession, after its later rebuilds): not run in this round; reported as not run.

Statistics: pooled over the six repositories; 95% bootstrap intervals over facts (10,000 resamples, seed 0).

## Predictions

- P1: E1 to E8 hold. **Expected from Stage 1, stated before any other model: E1 will fail on RELATION_LIMIT, GAP and
  the certifier, because L1 on fts9m.db gives sigma0 = 31 (RELATION_LIMIT 31, GAP 68, certifier 34/8) where today
  says 37/74/41/10; it holds on TAU (8).**
- P2: for every model other than bge-base, pooled over repositories with bootstrap intervals over facts: L1 scores at
  least as high as frozen on G2, and has at most as many wrong pulls as frozen on G3.
- P3: the spread of G2 between models is smaller under L1 than under frozen.
- P4: sigma0 differs between models by at least 20%.
- P5: bge-base's sigma0 on code maps is within 10% of 37 (measured in Stage 1: 34.9 to 38.7 on the six maps, so P5's
  first half holds), so L2 changes nothing for bge-base (expected to fail: L2 moves GAP to 77-82 and TAU to 10).

## Not tested

Live token savings, collections over about 100,000 units, questions longer than 128 tokens, languages other than English.
