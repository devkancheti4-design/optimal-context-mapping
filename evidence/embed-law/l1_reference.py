"""l1_reference.py -- L1: one reference geometry per model, from the fixed 20,000-sentence sample (seed 0) of the 20 Newsgroups
memory's corpus (fts9m.db), embedded the way the model's own files say (part A), centred on the sample's mean, measured
by the branch's own calibrate.geometry (2,000 pseudo-queries, seed 0, each against every other sentence).
    python3 -I l1_reference.py MODEL OUT.json [--device mps|cpu]"""
import json, os, site, sqlite3, sys, time
sys.path.append(site.getusersitepackages()); sys.path.insert(0, os.path.expanduser('~/optimal-context-mapping-embed-law'))
os.environ['OCM_OFFLINE'] = '1'
import numpy as np
from ocm.cmlm_vector.embed import read_spec, Embedder
from ocm.calibrate import geometry, thresholds, N_REFERENCE

model, out = sys.argv[1], sys.argv[2]
device = sys.argv[sys.argv.index('--device') + 1] if '--device' in sys.argv else 'mps'
FTS = os.path.expanduser('~/cmlm-bench4/fts9m.db')


class Reference:
    """What calibrate.geometry reads from a map, for a bare sample: each sentence is its own file."""
    def __init__(self, texts, spec, device):
        self.bits, self.texts, self.spec = 1024, texts, spec
        self.emb = Embedder(model, device=device, spec=spec)
        E = self.emb([spec['document_prompt'] + t for t in texts])
        self.mean = E.mean(axis=0).astype(np.float32)
        self.planes = np.random.default_rng(0).standard_normal((E.shape[1], 1024)).astype(np.float32)
        self.fshards, self.src = [self._pack(E)], list(range(len(texts)))

    def _pack(self, E):
        b = np.packbits((E - self.mean) @ self.planes > 0, axis=1)
        return b.view('>u8').astype(np.uint64)

    def measure(self, texts, query=False):
        return self._pack(self.emb([(self.spec['query_prompt'] if query else '') + t for t in texts]))


t0 = time.time()
con = sqlite3.connect(f'file:{FTS}?mode=ro', uri=True)
allt = [r[0] for r in con.execute('select c0 from s_content order by id')]
sample = [allt[i] for i in np.sort(np.random.default_rng(0).choice(len(allt), 20000, replace=False))]
spec = read_spec(model)
geo = geometry(Reference(sample, spec, device))
geo.update(reference='fts9m.db 20,000-sentence sample (seed 0)', model=model, device=device, pooling=spec['pooling'],
           query_prompt=spec['query_prompt'], seconds=round(time.time() - t0, 1))
json.dump(geo, open(out, 'w'), indent=1)
print(json.dumps({k: geo[k] for k in ('model', 'sigma0', 'lift84', 'lift98', 'n_queries', 'seconds')}), '| L1 thresholds:', thresholds(geo, N_REFERENCE))
