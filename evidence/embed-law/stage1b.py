"""stage1b.py -- candidate (a) with the benchmark's real questions: each of the 244 20 Newsgroups questions (with the
query prompt) against the same 20,000-sentence sample as stage1.py, its answer sentence left out. Archaeology only:
the law itself never reads questions. Also saves the sample's fingerprints for reuse."""
import json, os, site, sqlite3, sys
sys.path.append(site.getusersitepackages()); sys.path.insert(0, os.path.expanduser('~/eval/repos/modelD')); os.environ['OCM_OFFLINE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from ocm.cmlm_vector.embed import Embedder, QUERY_PREFIX
from stage1 import pack, agree, stats, MODEL, FTS, HERE
con = sqlite3.connect(f'file:{FTS}?mode=ro', uri=True)
texts = [r[0] for r in con.execute('select c0 from s_content order by id')]
idx = np.sort(np.random.default_rng(0).choice(len(texts), 20000, replace=False)); sample = [texts[i] for i in idx]
emb = Embedder(MODEL, device='mps'); E = emb(sample); mu = E.mean(axis=0).astype(np.float32)
planes = np.random.default_rng(0).standard_normal((E.shape[1], 1024)).astype(np.float32); U = pack(E - mu, planes)
np.save(os.path.join(HERE, 'ng20k_bits.npy'), U); np.save(os.path.join(HERE, 'ng20k_mean.npy'), mu)
Q = json.load(open(os.path.expanduser('~/neos/sandbox/bench2/questions.json')))['questions']
qb = pack(emb([QUERY_PREFIX[MODEL] + q['question'] for q in Q]) - mu, planes)
pos = {t: k for k, t in enumerate(sample)}
sds, l84, l98, best_minus_med = [], [], [], []
for q, b in zip(Q, qb):
    a = agree(b, U); keep = np.ones(len(U), bool)
    k = pos.get(q['sentence']); 
    if k is not None: keep[k] = False
    s = stats(a[keep]); sds.append(s['sd']); l84.append(s['q84'] - s['median']); l98.append(s['q98'] - s['median']); best_minus_med.append(s['max'] - s['median'])
r = dict(questions=len(Q), sd_median=float(np.median(sds)), sd_mean=float(np.mean(sds)), q84_minus_median=float(np.median(l84)),
         q98_minus_median=float(np.median(l98)), best_wrong_minus_median=float(np.median(best_minus_med)))
json.dump(r, open(os.path.join(HERE, 'stage1b_results.json'), 'w'), indent=1); print(r)
