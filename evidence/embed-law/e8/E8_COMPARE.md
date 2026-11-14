# E8: one command, end to end

- Record: `~/neos/sandbox/embed_law`; regeneration: `~/neos/sandbox/embed_law_e8`, made by `zsh e8.sh`, which copied the harness there byte for byte and ran its `reproduce.sh`.
- Started 2026-11-14 19:00:06, finished 2026-11-14 19:40:16.
- Code: 17 files are listed in HASHES.txt; 0 differ from their latest recorded hash now.
- **E8 HOLDS**: every number that must come back came back exactly. Gate readouts: 48 of 48 runs byte-identical by digest.

| what | compared | identical | value differences |
|---|---|---|---|
| Stage 1 | 3 | 3 | — |
| L1 geometries | 2 | 2 | — |
| gate runs (every readout) | 48 | 48 | — |
| E3/E4, E6, E7 | 3 | 3 | — |
| laws: expressions and proofs | 3 | 3 | — |
| results.json | 1 | 1 | — |
| MiniLM maps (byte for byte) | 12 | 12 | — |

## Set aside, and why

- **Fields only the regeneration has** (the record's file was written by an earlier version of its script; every field the record has was compared):
  - L1 geometries: l1_bge-base.json: /device, /model, /pooling, /query_prompt
  - gate runs (every readout): bge_DeepInfer_L1.json: /calibration/geometry/device, /calibration/geometry/model, /calibration/geometry/pooling, /calibration/geometry/query_prompt
  - gate runs (every readout): bge_FrontierAgent_L1.json: /calibration/geometry/device, /calibration/geometry/model, /calibration/geometry/pooling, /calibration/geometry/query_prompt
  - gate runs (every readout): bge_artemis_L1.json: /calibration/geometry/device, /calibration/geometry/model, /calibration/geometry/pooling, /calibration/geometry/query_prompt
  - gate runs (every readout): bge_celery_L1.json: /calibration/geometry/device, /calibration/geometry/model, /calibration/geometry/pooling, /calibration/geometry/query_prompt
  - gate runs (every readout): bge_sphinx_L1.json: /calibration/geometry/device, /calibration/geometry/model, /calibration/geometry/pooling, /calibration/geometry/query_prompt
  - gate runs (every readout): bge_textual_L1.json: /calibration/geometry/device, /calibration/geometry/model, /calibration/geometry/pooling, /calibration/geometry/query_prompt
  - laws: expressions and proofs: laws.json: /SEL/exact_by
- **Free-text labels that differ:**
  - L1 geometries: l1_bge-base.json: [('/reference', 'fts9m.db 20,000-sentence sample (seed 0), bge-base, mps', 'fts9m.db 20,000-sentence sample (seed 0)')]
  - gate runs (every readout): bge_DeepInfer_L1.json: [('/calibration/geometry/reference', 'fts9m.db 20,000-sentence sample (seed 0), bge-base, mps', 'fts9m.db 20,000-sentence sample (seed 0)')]
  - gate runs (every readout): bge_FrontierAgent_L1.json: [('/calibration/geometry/reference', 'fts9m.db 20,000-sentence sample (seed 0), bge-base, mps', 'fts9m.db 20,000-sentence sample (seed 0)')]
  - gate runs (every readout): bge_artemis_L1.json: [('/calibration/geometry/reference', 'fts9m.db 20,000-sentence sample (seed 0), bge-base, mps', 'fts9m.db 20,000-sentence sample (seed 0)')]
  - gate runs (every readout): bge_celery_L1.json: [('/calibration/geometry/reference', 'fts9m.db 20,000-sentence sample (seed 0), bge-base, mps', 'fts9m.db 20,000-sentence sample (seed 0)')]
  - gate runs (every readout): bge_sphinx_L1.json: [('/calibration/geometry/reference', 'fts9m.db 20,000-sentence sample (seed 0), bge-base, mps', 'fts9m.db 20,000-sentence sample (seed 0)')]
  - gate runs (every readout): bge_textual_L1.json: [('/calibration/geometry/reference', 'fts9m.db 20,000-sentence sample (seed 0), bge-base, mps', 'fts9m.db 20,000-sentence sample (seed 0)')]
- **MiniLM maps, bytes that differ but carry no number** (every other file byte-identical): manifest.json (build timestamp, hash of the .gz); rows.jsonl.gz (gzip header time); workspace.json (build timestamp)

## Reported, not required

### MiniLM build times (s)

| map | record | regenerated |
|---|---|---|
| branch DeepInfer | 39.1 | 53.8 |
| branch FrontierAgent | 65.8 | 92.4 |
| branch artemis | 76.9 | 103.3 |
| branch celery | 73.1 | 98.1 |
| branch sphinx | 79.8 | 118.5 |
| branch textual | 61.9 | 95.6 |
| control DeepInfer | 37.2 | 43.2 |
| control FrontierAgent | 62.1 | 87.2 |
| control artemis | 90.4 | 94.6 |
| control celery | 70.1 | 132.6 |
| control sphinx | 80.6 | 101.4 |
| control textual | 59.1 | 69.6 |

### Each colony's own clock (it runs on real time, so it varies run to run)

| law | record: rung, generation, evaluations, ticks | regenerated: rung, generation, evaluations, ticks |
|---|---|---|
| SEL | 3, gen 2, 496 evals, ticks [1302, 1364, 516, 1302] | 3, gen 2, 496 evals, ticks [1302, 1364, 516, 1302] |
| CGAP | 3, gen 2, 8499 evals, ticks [10731, 10742, 5361, 10731] | 3, gen 2, 8499 evals, ticks [11475, 11640, 5520, 11475] |
| CNEAR | 3, gen 2, 6891 evals, ticks [8187, 8235, 3783, 8187] | 3, gen 2, 6891 evals, ticks [9483, 9590, 4385, 9483] |
| RLIM | 4, gen 3, 811 evals, ticks [1517, 1559, 586, 1517] | 4, gen 3, 811 evals, ticks [1517, 1813, 586, 1517] |
| GAPW | 4, gen 3, 807 evals, ticks [1304, 1729, 472, 1304] | 4, gen 3, 807 evals, ticks [1513, 1728, 569, 1513] |
| TAU | 5, gen 3, 31007 evals, ticks [56287, 56360, 21053, 56287] | 5, gen 3, 31007 evals, ticks [55468, 55480, 21012, 55468] |
