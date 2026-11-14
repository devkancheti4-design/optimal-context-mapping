"""verify_wiring.py -- after RELATION_LIMIT, GAP and TAU moved to the sphere's whole laws (ocm/embed_laws.py RLIM, GAPW,
TAUW): every threshold this study recorded recomputes identically from its recorded geometry, and the Python meaning of
each law equals what it replaces.
    python3 -I verify_wiring.py"""
import glob, json, math, os, site, sys
sys.path.append(site.getusersitepackages()); sys.path.insert(0, os.path.expanduser('~/optimal-context-mapping-embed-law'))
import numpy as np
from ocm.calibrate import thresholds
from ocm.embed_laws import SEL, RLIM, GAPW, TAUW, XF
HERE = os.path.dirname(os.path.abspath(__file__))

# 1. every recorded calibration (L1 and L2 arms of both models, and E4's CPU run)
recs = []
for f in sorted(glob.glob(os.path.join(HERE, 'runs', '*.json'))):
    d = json.load(open(f)); c = d.get('calibration') if isinstance(d, dict) else None
    if isinstance(c, dict) and 'geometry' in c:
        recs.append((os.path.basename(f), c['geometry'], c['N'], c['thresholds']))
e4 = json.load(open(os.path.join(HERE, 'runs', 'e4_e3.json')))
recs.append(('e4_e3.json', e4['geometry'], e4['geometry']['n_units'], e4['thresholds']))
bad = [(f, thresholds(g, n), t) for f, g, n, t in recs if thresholds(g, n) != t]
frac = sorted({g['lift98'] for _, g, _, _ in recs if g['lift98'] != int(g['lift98'])})
print('recorded calibrations: %d, recomputed identically: %d%s' % (len(recs), len(recs) - len(bad), (' DIFFER: %s' % bad[:3]) if bad else ''))
print('  of them with a fractional lift98 (where TAU now reads round(lift98)): %s' % frac)

# 2. RLIM and GAPW against the joins they replace, every packed input
p, q = np.meshgrid(np.arange(1024), np.arange(1024), indexing='ij')
join_bad = sum(RLIM(int(s) | int(a) << 10) != int(s) + SEL(int(a) - int(s)) for s, a in zip(p.ravel(), q.ravel()))
gapw_bad = sum(GAPW(int(s) | int(a) << 10) != int(s) + SEL(int(a) - int(s)) for s, a in zip(p.ravel(), q.ravel()))
print('RLIM vs s + SEL(a84 - s) on all 1,048,576 inputs: %d differ; GAPW vs s2 + SEL(a98 - s2): %d differ' % (join_bad, gapw_bad))

# 3. TAUW's Python meaning against the integer definition (64-bit, written separately)
def tau_int(a, n):
    return (a * XF(n) + 2097152) >> 22


rng = np.random.default_rng(0)
pairs = [(a, n) for a in (68, 117, 1023) for n in range(30, 1 << 21)]
pairs += list(zip(rng.integers(0, 1024, 1000000).tolist(), rng.integers(30, 1 << 21, 1000000).tolist()))
tau_bad = sum(TAUW(a | n << 10) != tau_int(a, n) for a, n in pairs)
print('TAUW vs (a98 * XF(N) + 2^21) >> 22 on %s inputs (every N at a98 = 68, 117, 1023; 1,000,000 random): %d differ'
      % (format(len(pairs), ','), tau_bad))
ok = not bad and not join_bad and not gapw_bad and not tau_bad
print('WIRING VERIFIED' if ok else 'WIRING NOT VERIFIED')
sys.exit(0 if ok else 1)
