"""stage1c.py -- the 8 bits, measured: every 20 Newsgroups sentence (277,681) embedded with bge-base and centred on the
same 20,000-sentence mean (as the paper did), then each of the 244 questions' best WRONG agreement on nested random
subsets of N/9, N/3 and N sentences (seed 0; the answer sentence, and any identical copy of it, left out). The paper's
Table 4 shows +8 and +9 bits per tripling. Archaeology only: the law never reads questions."""
import json, os, site, sqlite3, sys, time
sys.path.append(site.getusersitepackages()); sys.path.insert(0, os.path.expanduser('~/eval/repos/modelD')); os.environ['OCM_OFFLINE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from ocm.cmlm_vector.embed import Embedder, QUERY_PREFIX
from stage1 import pack, agree, MODEL, FTS, HERE
con = sqlite3.connect(f'file:{FTS}?mode=ro', uri=True)
texts = [r[0] for r in con.execute('select c0 from s_content order by id')]; N = len(texts)
mu = np.load(os.path.join(HERE, 'ng20k_mean.npy'))
emb = Embedder(MODEL, device='mps')
planes = np.random.default_rng(0).standard_normal((768, 1024)).astype(np.float32)
t0 = time.time(); U = np.concatenate([pack(emb(texts[s:s + 20000]) - mu, planes) for s in range(0, N, 20000)]); t_emb = time.time() - t0
np.save(os.path.join(HERE, 'ng277k_bits.npy'), U)
Q = json.load(open(os.path.expanduser('~/neos/sandbox/bench2/questions.json')))['questions']
qb = pack(emb([QUERY_PREFIX[MODEL] + q['question'] for q in Q]) - mu, planes)
perm = np.random.default_rng(0).permutation(N); sizes = [N // 9, N // 3, N]
inset = [np.zeros(N, bool) for _ in sizes]
for m, n in zip(inset, sizes): m[perm[:n]] = True
by_text = {}
for k, t in enumerate(texts): by_text.setdefault(t, []).append(k)
best = np.zeros((len(Q), 3)); gold = np.full(len(Q), np.nan); sd_full = []
for i, (q, b) in enumerate(zip(Q, qb)):
    a = agree(b, U); wrong = np.ones(N, bool); g = by_text.get(q['sentence'], [])
    wrong[g] = False
    if g: gold[i] = a[g].max()
    for j, m in enumerate(inset): best[i, j] = a[m & wrong].max()
    sd_full.append(float(a[wrong].std()))
med = np.median(best, axis=0)
r = dict(sentences=N, sizes=sizes, embed_s=round(t_emb, 1), questions=len(Q), best_wrong_median=med.tolist(),
         shift_per_tripling=[float(med[1] - med[0]), float(med[2] - med[1])], answer_median=float(np.nanmedian(gold)),
         answers_found=int(np.isfinite(gold).sum()), sd_full_median=float(np.median(sd_full)),
         gaussian_evt_shift=[float(np.median(sd_full) * (np.sqrt(2 * np.log(sizes[k + 1])) - np.sqrt(2 * np.log(sizes[k])))) for k in range(2)])
json.dump(r, open(os.path.join(HERE, 'stage1c_results.json'), 'w'), indent=1); print(r)
