"""stage1d.py -- the per-tripling shift measured directly where it is cheap: the 244 questions' best WRONG agreement on
nested random subsets (seed 0) of the 20,000-sentence sample (2,222 / 6,666 / 20,000), against the Gaussian
extreme-value form sigma * (sqrt(2 ln 3N) - sqrt(2 ln N)) with sigma = each query's own spread. Archaeology only."""
import json, os, site, sys
sys.path.append(site.getusersitepackages()); sys.path.insert(0, os.path.expanduser('~/eval/repos/modelD')); os.environ['OCM_OFFLINE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqlite3
import numpy as np
from ocm.cmlm_vector.embed import Embedder, QUERY_PREFIX
from stage1 import pack, agree, MODEL, FTS, HERE
U = np.load(os.path.join(HERE, 'ng20k_bits.npy')); mu = np.load(os.path.join(HERE, 'ng20k_mean.npy'))
con = sqlite3.connect(f'file:{FTS}?mode=ro', uri=True)
texts = [r[0] for r in con.execute('select c0 from s_content order by id')]
idx = np.sort(np.random.default_rng(0).choice(len(texts), 20000, replace=False)); sample = [texts[i] for i in idx]; pos = {t: k for k, t in enumerate(sample)}
planes = np.random.default_rng(0).standard_normal((768, 1024)).astype(np.float32)
Q = json.load(open(os.path.expanduser('~/neos/sandbox/bench2/questions.json')))['questions']
qb = pack(Embedder(MODEL, device='mps')([QUERY_PREFIX[MODEL] + q['question'] for q in Q]) - mu, planes)
N = len(U); sizes = [N // 9, N // 3, N]; perm = np.random.default_rng(0).permutation(N)
best = np.zeros((len(Q), 3)); evt = np.zeros((len(Q), 2)); sds = []
for i, (q, b) in enumerate(zip(Q, qb)):
    a = agree(b, U).astype(float); wrong = np.ones(N, bool); k = pos.get(q['sentence'])
    if k is not None: wrong[k] = False
    sd = a[wrong].std(); sds.append(sd)
    for j, n in enumerate(sizes):
        m = np.zeros(N, bool); m[perm[:n]] = True; best[i, j] = a[m & wrong].max()
    for j in range(2): evt[i, j] = sd * (np.sqrt(2 * np.log(sizes[j + 1])) - np.sqrt(2 * np.log(sizes[j])))
med = np.median(best, axis=0)
r = dict(sizes=sizes, best_wrong_median=med.tolist(), measured_shift=[float(med[1] - med[0]), float(med[2] - med[1])],
         measured_shift_mean=[float(np.mean(best[:, 1] - best[:, 0])), float(np.mean(best[:, 2] - best[:, 1]))],
         gaussian_evt_shift=[float(np.median(evt[:, 0])), float(np.median(evt[:, 1]))], sd_median=float(np.median(sds)))
json.dump(r, open(os.path.join(HERE, 'stage1d_results.json'), 'w'), indent=1); print(json.dumps(r))
