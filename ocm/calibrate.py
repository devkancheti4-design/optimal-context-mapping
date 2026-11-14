"""THE EMBEDDING LAW, part B: the model's geometry, measured once per map from the map's own units, and every threshold
the router compares agreement with, derived from it.

Pseudo-queries: a deterministic sample (seed 0) of the map's own units, embedded the way questions are (with the query
prompt). Each one's agreement with every unit outside its own file is the chance distribution the router reads. No
question, gold line, lesson or result is read; nothing is called but the embedding the build already does.

  sigma0          the spread of one pseudo-query's agreement over the units (median over pseudo-queries)
  lift84, lift98  the 84.13% and 97.72% quantiles over the median (median over pseudo-queries)
  RELATION_LIMIT  = RLIM(s | a84 << 10)   sigma0, or the 84.13% lift when it departs by more than 4 bits
  GAP             = GAPW(s2 | a98 << 10)  2 sigma0, or the 97.72% lift likewise (Cortex D's gap is the same number)
  TAU = NEAR = DELTA  = TAUW(a98 | N << 10): the extreme-value shift of the best chance match per tripling of the
                  collection, at its size N, derived as (lift98 / 2) * (sqrt(2 ln N) - sqrt(2 ln N/3)). The tail's own
                  spread (half the 97.72% lift) carries the extremes: the Gaussian sigma0 under-predicts the measured
                  shift. The root-of-log factor is the declared table XF(N), float64, rounded once at 2^-21.
  certifier gap, near, and the learned law's near: never derived; written in sigma0 units, CGAP(s) and CNEAR(s).
s = round(sigma0), s2 = round(2 sigma0), a84/a98 = the rounded lifts: the geometry is rounded once to whole bits and
every threshold is then an authored integer law of it (ocm/embed_laws.py).

L2 measures every map on its own units. L1 uses one reference geometry per model (a fixed 20,000-sentence sample of the
corpus the router's numbers were set on) with N = 277,681, the size of the collection the 8 bits were measured at."""
import math
import time

import numpy as np

from .embed_laws import CGAP, CNEAR, RLIM, GAPW, TAUW

TODAY = {"tau": 8, "near": 8, "delta": 8, "gap": 74, "relation_limit": 37, "cert_gap": 41, "cert_near": 10, "cortex_gap": 74,
         "learned_near": 10}                                   # 0.5.3's numbers, measured once on bge-base and frozen
Q84, Q98 = 0.8413447460685429, 0.9772498680518208               # Phi(1), Phi(2)
N_REFERENCE = 277681                                           # the 9M-token collection, where 8 bits per tripling was measured


def _round(x):
    return int(math.floor(x + 0.5))


def geometry(mem, n_queries=2000, seed=0):
    """Measured from the map's own units only. Returns sigma0, the median, the two lifts, N and the sample size."""
    U = np.concatenate([np.asarray(s) for s in mem.fshards]).astype(np.uint64)
    n = len(U)
    src = np.asarray(mem.src[:n])
    q = np.random.default_rng(seed).permutation(n)[:min(n_queries, n)]
    Q = mem.measure([mem.texts[i] for i in q], query=True)
    sds, meds, l84, l98 = [], [], [], []
    for k, i in enumerate(q):
        a = (mem.bits - np.bitwise_count(U ^ Q[k]).sum(axis=1, dtype=np.int64)).astype(np.float64)
        keep = (src != src[i]) if src[i] >= 0 else (np.arange(n) != i)        # its own file, which holds its own unit
        x = a[keep]
        if len(x) < 2:
            continue
        qs = np.quantile(x, [0.5, Q84, Q98])
        sds.append(float(x.std())); meds.append(float(qs[0])); l84.append(float(qs[1] - qs[0])); l98.append(float(qs[2] - qs[0]))
    if not sds:
        raise ValueError("too few units in other files to measure the geometry")
    return {"sigma0": float(np.median(sds)), "median": float(np.median(meds)), "lift84": float(np.median(l84)),
            "lift98": float(np.median(l98)), "n_units": int(n), "n_queries": len(sds), "seed": seed}


def thresholds(geo, N=None):
    """Every geometry-dependent number, from the geometry alone: each an authored integer law of the geometry rounded
    once to whole bits (TAU through its declared collection-size table)."""
    N = int(N or geo["n_units"])
    s, s2 = _round(geo["sigma0"]), _round(2 * geo["sigma0"])
    a84, a98 = _round(geo["lift84"]), _round(geo["lift98"])
    if not (0 <= s <= 511 and all(0 <= v <= 1023 for v in (s2, a84, a98))):
        raise ValueError(f"geometry outside the laws' domains: sigma0 {geo['sigma0']}, lifts {geo['lift84']} / {geo['lift98']}")
    if not 30 <= N < 1 << 21:
        raise ValueError(f"N = {N:,} units: TAU's law covers collections of 30 to 2,097,151 units")
    tau, gap = TAUW(a98 | N << 10), GAPW(s2 | a98 << 10)
    return {"tau": tau, "near": tau, "delta": tau, "gap": gap, "relation_limit": RLIM(s | a84 << 10),
            "cert_gap": CGAP(s), "cert_near": CNEAR(s), "cortex_gap": gap, "learned_near": CNEAR(s)}


def calibrate(mem, mode="L2", reference=None, n_queries=2000, seed=0, save=True):
    """Measure (L2) or take the model's reference geometry (L1), derive the thresholds and store both in the manifest,
    where the router reads them. The certifier's gap and near go into the manifest's own gap/near fields."""
    t0 = time.time()
    if mode == "L2":
        geo, N = geometry(mem, n_queries, seed), None
    elif mode == "L1":
        if not reference:
            raise ValueError("L1 needs the model's reference geometry")
        geo, N = dict(reference), N_REFERENCE
    else:
        raise ValueError(f"mode {mode!r}: L1 or L2")
    th = thresholds(geo, N)
    cal = {"mode": mode, "geometry": geo, "N": int(N or geo["n_units"]), "thresholds": th, "today": TODAY,
           "device": mem.man.get("device"), "seconds": round(time.time() - t0, 2), "law": "ocm/calibrate.py + ocm/embed_laws.py"}
    mem.man["calibration"] = cal
    mem.man["gap"], mem.man["near"] = th["cert_gap"] / mem.bits, th["cert_near"] / mem.bits
    mem.calibration, mem.gap, mem.near, mem.learned_near_bits = cal, mem.man["gap"], mem.man["near"], th["learned_near"]
    if save:
        mem.save()
    return cal
