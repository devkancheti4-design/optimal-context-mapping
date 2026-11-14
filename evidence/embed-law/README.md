# The embedding law: the record

This is the record of the offline study behind `ocm/calibrate.py`, `ocm/embed_laws.py` and the `read_spec` part of
`ocm/cmlm_vector/embed.py`, run on 14 November 2026. It made no Claude or API calls; only embeddings were computed.

| file | what it is |
|---|---|
| `REPORT.md` | the results: who authored each threshold, Stage 1 (where 37 and 8 come from), checks E1 to E8, the gates, predictions P1 to P5, and the offline flaw E8 found |
| `PROTOCOL.md` | the pre-registration, written before any model other than bge-base was measured |
| `HASHES.txt` | its SHA-256 (recorded 18:17:15 IST), plus Amendments 1 to 4: the whole laws, the E8 runner, the offline fix, the comparator |
| `results.json` | every E check, prediction, total and bootstrap interval |
| `analyze.log` | the printed tables `analyze.py` produced from the runs |
| `stage1*_results.json`, `stage1.log` | Stage 1: the chance spread of bge-base on the 20 Newsgroups sample and on the six code maps |
| `l1_*.json` | the L1 reference geometry of each model, which `calibrate(mem, "L1", reference=...)` takes |
| `laws/*.json` | the machine-authored integer laws (SEL, CGAP, CNEAR, RLIM, GAPW, TAUW), each with its proof |
| `e8/` | E8, the whole study rerun from one command in a fresh folder (19:00:06 to 19:40:16): `E8_COMPARE.md` (it held: every number came back exactly, and all 48 gate runs gave byte-identical readouts), `e8_compare.json`, and the run's `reproduce.log` and `stderr.log` |
| `verify_offline.py`, `verify_offline.json` | the check behind Amendment 3: a local stand-in for the Hugging Face Hub counted connections. The old reader made 6; the fixed reader, a gate run and an L1 reference each made 0, with outputs identical to the record |
| `*.py`, `*.sh` | the harness: `reproduce.sh` runs the whole study, `e8.sh` reruns it in a fresh folder, and `e8_compare.py` compares the two |

Each file here that `HASHES.txt` lists matches its recorded hash. So do the branch's `ocm/` files, at their latest
entries.

## Not included

- **`runs/`**: the 48 gate runs, 6.5 MB, and E8's regenerated copies of them. Each holds every readout verbatim: code
  from the ColdSession-Fresh repositories, the IDs of their unpublished facts, and local paths. `results.json` has
  every number computed from them, and `e8/e8_compare.json` has the digest checks.
- **The maps**: 302 MB of MiniLM maps. `reproduce.sh` rebuilds them.
- **`ng20k_*.npy`**: binary fingerprints of the 20,000-sentence sample. `stage1.py` rebuilds them.
- **`laws/*.py` and their logs**: the scripts that ran the integer program-synthesis engine from a local folder. The
  laws they authored, with their proofs, are in `laws/*.json` and `ocm/embed_laws.py`.
- **E8's interim comparison** (`E8_PARTIAL_COMPARE.md`), taken during the run. `e8/E8_COMPARE.md` replaces it.

Home-folder paths in `HASHES.txt`, `stage1_results.json`, `e8/E8_COMPARE.md` and `e8/reproduce.log` are shown as `~`.
These are labels only: no hash changes.

The harness reads inputs that are not in this repository: the 0.5.3 control checkout, the ColdSession-Fresh facts and
maps, and the 20 Newsgroups collection (`fts9m.db`). It records how each number was made, but it does not run from this
folder alone. In `verify_offline.py`, the old reader is `ocm/cmlm_vector/embed.py` as of commit 949fdab, before the
offline fix.
