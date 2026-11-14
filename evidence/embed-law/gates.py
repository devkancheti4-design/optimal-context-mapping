"""gates.py -- one arm of the embedding law on one ColdSession-Fresh repository, offline (no model calls but embedding).

  G1 cold     wording a of every fact, nothing taught: is the gold line in the first readout, and is the gold file first?
  G2 memory   teach wording a of each taught fact onto its gold line (the /teach call the Stop hook makes), then ask b, c, d:
              does the taught line lead the readout?
  G3 wrong    after teaching, every wording of the facts never taught: how often does a TAUGHT line lead the readout
              when it is not this fact's answer?
Every readout is kept verbatim (E1/E2 compare them byte for byte). Teaching stays in RAM: no map on disk changes.

    python3 -I gates.py --code control|branch --workspace DIR --facts FILE [--arm frozen|read|L1|L2 --l1 GEO.json] --out OUT.json"""
import argparse, hashlib, json, os, re, site, sys, time
sys.path.append(site.getusersitepackages())
ap = argparse.ArgumentParser()
ap.add_argument('--code', choices=['control', 'branch'], required=True)
ap.add_argument('--workspace', required=True); ap.add_argument('--facts', required=True)
ap.add_argument('--arm', default='frozen', choices=['frozen', 'read', 'L1', 'L2']); ap.add_argument('--l1')
ap.add_argument('--out', required=True)
args = ap.parse_args()
sys.path.insert(0, os.path.expanduser('~/eval/repos/modelD' if args.code == 'control' else '~/optimal-context-mapping-embed-law'))
os.environ['OCM_OFFLINE'] = '1'
import numpy as np                                                          # noqa: E402
from ocm import server as S                                                  # noqa: E402
from ocm.cmlm_vector import memory as MM                                     # noqa: E402
from ocm import life as LIFE                                                 # noqa: E402
MM.Memory.save = lambda self: None                                           # teaching stays in RAM
LIFE.Life.save = lambda self, path=None: None

w = S.Workspace(args.workspace)
cal = None
if args.arm in ('L1', 'L2'):
    from ocm import calibrate as CAL
    ref = json.load(open(args.l1)) if args.arm == 'L1' else None
    cal = CAL.calibrate(w.mem, args.arm, reference=ref, save=False)
    w.lanes = S.L.Lanes(w.mem, np.arange(w.meta['units']), os.path.join(args.workspace, 'keyword.db'), S.RL)
facts = [json.loads(l) for l in open(args.facts)]
CITE = re.compile(r'^\d+\. \[([^\]]+?)(?::(\d+))?\]', re.M)


def rows(readout):
    """(path, first, last) of every row, read from the readout and the workspace's spans."""
    out = []
    for path, pos in CITE.findall(readout):
        first = int(pos) if pos else 0
        span = next(((f, l) for f, l, _j in w.spans.get(path, []) if f == first), (first, first))
        out.append((path, span[0], span[1]))
    return out


def covers(row, path, line):
    p, f, l = row
    return (p == path or p.endswith('/' + path)) and f <= line <= l


def ask(q):
    return w.handle('ask', {'question': q})


rec = {'arm': args.arm, 'code': args.code, 'workspace': args.workspace, 'calibration': cal, 'g1': [], 'g2': [], 'g3': []}
t0 = time.time()
for f in facts:                                                              # G1: cold
    r = ask(f['wordings']['a']); rs = rows(r)
    rec['g1'].append({'id': f['id'], 'readout': r, 'line_in': any(covers(x, f['path'], f['line']) for x in rs),
                      'file_first': bool(rs) and (rs[0][0] == f['path'] or rs[0][0].endswith('/' + f['path']))})
taught = [f for f in facts if f.get('role') == 'taught']
untaught = [f for f in facts if f.get('role') != 'taught']
rec['teach'] = w.handle('teach', {'pairs': [{'question': f['wordings']['a'], 'at': '%s:%d' % (f['path'], f['line'])} for f in taught]})
for f in taught:                                                             # G2: does the taught line lead?
    for k in ('b', 'c', 'd'):
        r = ask(f['wordings'][k]); rs = rows(r)
        rec['g2'].append({'id': f['id'], 'w': k, 'readout': r, 'lead': bool(rs) and covers(rs[0], f['path'], f['line'])})
for f in untaught:                                                           # G3: does a taught line lead when it is wrong?
    for k in ('a', 'b', 'c', 'd'):
        r = ask(f['wordings'][k]); rs = rows(r)
        wrong = bool(rs) and not covers(rs[0], f['path'], f['line']) and any(covers(rs[0], t['path'], t['line']) for t in taught)
        rec['g3'].append({'id': f['id'], 'w': k, 'readout': r, 'wrong_pull': wrong})
rec['seconds'] = round(time.time() - t0, 1)
rec['digest'] = hashlib.sha256(json.dumps([x['readout'] for g in ('g1', 'g2', 'g3') for x in rec[g]]).encode()).hexdigest()
rec['summary'] = {'g1_line': sum(x['line_in'] for x in rec['g1']), 'g1_file': sum(x['file_first'] for x in rec['g1']), 'g1_n': len(rec['g1']),
                  'g2_lead': sum(x['lead'] for x in rec['g2']), 'g2_n': len(rec['g2']),
                  'g3_wrong': sum(x['wrong_pull'] for x in rec['g3']), 'g3_n': len(rec['g3'])}
json.dump(rec, open(args.out, 'w'), indent=1)
print(json.dumps({'arm': args.arm, 'code': args.code, **rec['summary'], 'digest': rec['digest'][:16], 's': rec['seconds']}))
