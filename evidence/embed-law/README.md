# The embedding law: the record

This is the record of the offline study behind `ocm/calibrate.py`, `ocm/embed_laws.py` and the `read_spec` part of
`ocm/cmlm_vector/embed.py`, run on 14 November 2026. It made no Claude or API calls; only embeddings were computed.

| file | what it is |
|---|---|
| `REPORT.md` | the results: who authored each threshold, Stage 1 (where 37 and 8 come from), checks E1 to E8, the gates, predictions P1 to P5 |
| `PROTOCOL.md` | the pre-registration, written before any model other than bge-base was measured |
| `HASHES.txt` | its SHA-256 (recorded 18:17:15 IST), plus Amendments 1 and 2 |
| `results.json` | every E check, prediction, total and bootstrap interval |
| `analyze.log` | the printed tables `analyze.py` produced from the runs |
| `stage1*_results.json`, `stage1.log` | Stage 1: the chance spread of bge-base on the 20 Newsgroups sample and on the six code maps |
| `l1_*.json` | the L1 reference geometry of each model, which `calibrate(mem, "L1", reference=...)` takes |
| `laws/*.json` | the machine-authored integer laws (SEL, CGAP, CNEAR, RLIM, GAPW, TAUW), each with its proof |
| `*.py`, `*.sh` | the harness: `reproduce.sh` runs the whole study, `e8.sh` runs it again in a fresh folder, and `e8_compare.py` compares the two |

Each file here that `HASHES.txt` lists matches its recorded hash. So do the branch's `ocm/` files, at their latest
entries.

## Not included

- **`runs/`**: the 48 gate runs, 6.5 MB. Each holds every readout verbatim: code from the ColdSession-Fresh
  repositories, the IDs of their unpublished facts, and local paths. `results.json` has every number computed from them.
- **The maps**: 302 MB of MiniLM maps. `reproduce.sh` rebuilds them.
- **`ng20k_*.npy`**: binary fingerprints of the 20,000-sentence sample. `stage1.py` rebuilds them.
- **`laws/*.py` and their logs**: the scripts that ran the integer program-synthesis engine from a local folder. The
  laws they authored, with their proofs, are in `laws/*.json` and `ocm/embed_laws.py`.

Home-folder paths in `HASHES.txt` and `stage1_results.json` are shown as `~`. These are labels only: no hash
changes.

The harness reads inputs that are not in this repository: the 0.5.3 control checkout, the ColdSession-Fresh facts and
maps, and the 20 Newsgroups collection (`fts9m.db`). It records how each number was made, but it does not run from this
folder alone.

E8, the whole study from one command end to end, was still running when this folder was committed.
