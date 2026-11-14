"""stage1.py -- Stage 1 of the embedding law: where Model D's 37 bits come from, measured with bge-base.

The chance distribution of agreement (A = 1024 - popcount(xor) of two 1,024-bit fingerprints), two ways:
  (a) per query: one pseudo-query's agreement with every unit (its own unit and, on code maps, its own file left out):
      the list whose median and best the router reads. Reported: the sd of each query's list, median over queries.
  (b) random pairs of units (as statements, no prompt).
Pseudo-queries are units embedded the way questions are, with the model's query prompt. No real questions, no gold
lines, no results are read.

Where: (1) the 20 Newsgroups memory's own corpus (cmlm-bench4/fts9m.db, 277,681 sentences: the corpus the paper's
"sd 34" and "8 bits per tripling" were measured on), a deterministic sample of 20,000 sentences, centred on its own
mean as the paper did; (2) the six ColdSession-Fresh code maps, as built (their own mean, planes and device).

Embedding and fingerprints use the 0.5.3 control's code (~/eval/repos/modelD) unchanged.
    python3 -I stage1.py [--device mps|cpu] [--queries 2000]"""
import argparse, json, os, site, sqlite3, sys, time
sys.path.append(site.getusersitepackages())            # -I drops the user site, where torch's typing_extensions lives
CONTROL = os.path.expanduser('~/eval/repos/modelD')
sys.path.insert(0, CONTROL)
os.environ['OCM_OFFLINE'] = '1'
import numpy as np
from ocm.cmlm_vector.embed import Embedder, QUERY_PREFIX
from ocm.cmlm_vector.memory import Memory

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = 'BAAI/bge-base-en-v1.5'
REPOS = ['artemis', 'FrontierAgent', 'DeepInfer', 'sphinx', 'textual', 'celery']
FTS = os.path.expanduser('~/cmlm-bench4/fts9m.db')


def pack(c, planes, W=16):
    b = np.packbits(c @ planes > 0, axis=1)
    b = np.pad(b, ((0, 0), (0, W * 8 - b.shape[1])))
    return b.view('>u8').astype(np.uint64)


def agree(q, U, bits=1024):
    return bits - np.bitwise_count(U ^ q).sum(axis=1, dtype=np.int64)


def stats(a):
    a = np.asarray(a, dtype=np.float64)
    q = np.quantile(a, [0.5, 0.8413, 0.9772])
    return dict(mean=float(a.mean()), sd=float(a.std()), median=float(q[0]), q84=float(q[1]), q98=float(q[2]), max=float(a.max()))


def per_query(Q, U, exclude):
    """Each query's agreement with all units except its excluded set: the per-query sd, median, best (max)."""
    out = []
    for i in range(len(Q)):
        a = agree(Q[i], U)
        keep = np.ones(len(U), bool); keep[exclude(i)] = False
        s = stats(a[keep]); out.append(s)
    sds = np.array([s['sd'] for s in out]); med = np.array([s['median'] for s in out])
    lift84 = np.array([s['q84'] - s['median'] for s in out]); lift98 = np.array([s['q98'] - s['median'] for s in out])
    return dict(n_queries=len(Q), sd_median=float(np.median(sds)), sd_mean=float(sds.mean()), sd_p10=float(np.quantile(sds, .1)),
                sd_p90=float(np.quantile(sds, .9)), median_of_medians=float(np.median(med)),
                q84_minus_median=float(np.median(lift84)), q98_minus_median=float(np.median(lift98)))


def random_pairs(U, n=200000, seed=0):
    rng = np.random.default_rng(seed)
    i = rng.integers(0, len(U), n); j = rng.integers(0, len(U), n); ok = i != j
    a = 1024 - np.bitwise_count(U[i[ok]] ^ U[j[ok]]).sum(axis=1, dtype=np.int64)
    return dict(n_pairs=int(ok.sum()), **stats(a))


def corpus_part(device, nq):
    con = sqlite3.connect(f'file:{FTS}?mode=ro', uri=True)
    texts = [r[0] for r in con.execute('select c0 from s_content order by id')]
    N = len(texts)
    idx = np.sort(np.random.default_rng(0).choice(N, 20000, replace=False))
    sample = [texts[i] for i in idx]
    emb = Embedder(MODEL, device=device)
    t0 = time.time(); E = emb(sample); t_emb = time.time() - t0
    mu = E.mean(axis=0).astype(np.float32)
    planes = np.random.default_rng(0).standard_normal((E.shape[1], 1024)).astype(np.float32)
    U = pack(E - mu, planes)
    qi = np.random.default_rng(0).permutation(len(sample))[:nq]
    Eq = emb([QUERY_PREFIX.get(MODEL, '') + sample[i] for i in qi])
    Q = pack(Eq - mu, planes)
    a = per_query(Q, U, lambda k: [qi[k]])
    return dict(corpus='20 Newsgroups (fts9m.db)', sentences=N, sample=len(sample), device=device, embed_s=round(t_emb, 1),
                per_query=a, random_pairs=random_pairs(U))


def map_part(repo, nq):
    path = os.path.expanduser(f'~/coldsession-fresh-work/{repo}/maps/modeld/memory')
    m = Memory(path)
    U = np.concatenate([np.asarray(s) for s in m.fshards]).astype(np.uint64)
    src = np.array(m.src)
    qi = np.random.default_rng(0).permutation(len(m.texts))[:nq]
    Q = m.measure([m.texts[i] for i in qi], query=True)
    a = per_query(Q, U, lambda k: np.nonzero(src == src[qi[k]])[0])      # its own file, which holds its own unit
    return dict(repo=repo, units=len(m.texts), files=len(m.sources), device=m.man.get('device'), per_query=a, random_pairs=random_pairs(U))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--device', default='mps'); ap.add_argument('--queries', type=int, default=2000)
    args = ap.parse_args()
    res = dict(model=MODEL, control=CONTROL, corpus=corpus_part(args.device, args.queries), maps=[map_part(r, args.queries) for r in REPOS])
    json.dump(res, open(os.path.join(HERE, 'stage1_results.json'), 'w'), indent=1)
    c = res['corpus']
    print('%-26s %7s  %9s %8s %8s  %9s %8s' % ('where', 'units', 'query sd', 'q84-med', 'q98-med', 'pairs sd', 'pairs mu'))
    rows = [('20 Newsgroups sample', c['sample'], c['per_query'], c['random_pairs'])] + [(m['repo'], m['units'], m['per_query'], m['random_pairs']) for m in res['maps']]
    for name, n, pq, rp in rows:
        print('%-26s %7d  %9.1f %8.1f %8.1f  %9.1f %8.1f' % (name, n, pq['sd_median'], pq['q84_minus_median'], pq['q98_minus_median'], rp['sd'], rp['mean']))
