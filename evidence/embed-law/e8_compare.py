"""e8_compare.py -- E8: does one command regenerate every recorded number?
    python3 -I e8_compare.py --precheck RECORD_DIR    every file HASHES.txt lists still has its latest recorded hash
    python3 -I e8_compare.py RECORD_DIR REGEN_DIR     -> REGEN_DIR/E8_COMPARE.md and REGEN_DIR/e8_compare.json
Must come back exactly: Stage 1; both L1 geometries; all 48 gate runs (every readout, byte for byte) with their
calibrations; E3/E4, E6's counts and thresholds, E7; the laws' expressions and proofs; results.json; the MiniLM maps
(fingerprints, planes, mean, spans, keyword index). Reported beside them, not required: wall time and memory, and each
colony's own clock (generation, ticks, windows, evaluations, the rung and path it was found on), which runs on real time."""
import glob, hashlib, json, os, re, sqlite3, sys

TIMING = {'seconds', 's', 'embed_s', 'secs', 'max_rss_mb_model_loaded', 'max_rss_mb_after', 'created', 'built',
          'l2_calibration_seconds'}
COLONY = {'generation', 'alive', 'ticks', 'windows', 'evals', 'note', 'minimal', 'ladder'}
REPOS = ['artemis', 'FrontierAgent', 'DeepInfer', 'sphinx', 'textual', 'celery']
N = 'all-MiniLM-L6-v2'


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def precheck(src):
    latest = {}
    for line in open(os.path.join(src, 'HASHES.txt')):
        m = re.match(r'^([0-9a-f]{64})  (.+)$', line.rstrip('\n'))
        if m:
            latest[m.group(2)] = m.group(1)                      # a later entry supersedes an earlier one
    bad = []
    for path, h in latest.items():
        p = path if os.path.isabs(path) else os.path.join(src, path)
        got = sha(p) if os.path.exists(p) else 'missing'
        if got != h:
            bad.append((path, h[:12], got[:12]))
    return latest, bad


def norm(x, drop):
    if isinstance(x, dict):
        return {k: norm(v, drop) for k, v in x.items() if k not in drop}
    if isinstance(x, list):
        return [norm(v, drop) for v in x]
    if isinstance(x, str):
        return re.sub(r'\d+\.\d+ s\b', '<t> s', x)                # proof logs carry their own run time
    return x


def diff(a, b, path='', out=None, limit=12):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append((path + '/' + str(k), a.get(k, '<absent>'), b.get(k, '<absent>')))
            else:
                diff(a[k], b[k], path + '/' + str(k), out, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'length %d' % len(a), 'length %d' % len(b)))
        for i, (u, v) in enumerate(zip(a, b)):
            diff(u, v, '%s[%d]' % (path, i), out, limit)
    elif a != b:
        out.append((path, a, b))
    return out


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


def cmp_json(rec, reg, drop):
    a, b = load(rec), load(reg)
    if b is None:
        return False, [('', 'present', 'NOT REGENERATED')]
    d = diff(norm(a, drop), norm(b, drop))
    return not d, d


def map_files(root):
    out = {}
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            out[os.path.relpath(os.path.join(dp, fn), root)] = os.path.join(dp, fn)
    return out


def cmp_map(rec, reg):
    """Byte for byte, except the two build timestamps (manifest 'created', workspace 'built'); a keyword index whose
    bytes differ is compared row by row."""
    A, B = map_files(rec), map_files(reg)
    notes = []
    if set(A) != set(B):
        notes.append(('files', sorted(set(A) - set(B))[:5], sorted(set(B) - set(A))[:5]))
    for rel in sorted(set(A) & set(B)):
        if sha(A[rel]) == sha(B[rel]):
            continue
        if rel.endswith('manifest.json') or rel == 'workspace.json':
            d = diff(norm(load(A[rel]), TIMING), norm(load(B[rel]), TIMING))
            if d:
                notes.append((rel, d[:3], ''))
        elif rel.endswith('keyword.db'):
            q = lambda p: sqlite3.connect(f'file:{p}?mode=ro', uri=True).execute('select rowid, t from s order by rowid').fetchall()
            if q(A[rel]) != q(B[rel]):
                notes.append((rel, 'rows differ', ''))
        else:
            notes.append((rel, 'bytes differ', ''))
    return not notes, notes, len(A)


def build_times(text):
    return {(m.group(1), m.group(2)): float(m.group(3)) for m in re.finditer(r'(control|branch) all-MiniLM-L6-v2 (\S+) built in ([\d.]+)s', text)}


def compare(src, out):
    R = {}
    R['Stage 1'] = {f: cmp_json(os.path.join(src, f), os.path.join(out, f), TIMING) for f in ('stage1_results.json', 'stage1b_results.json', 'stage1d_results.json')}
    R['L1 geometries'] = {f: cmp_json(os.path.join(src, f), os.path.join(out, f), TIMING) for f in ('l1_bge-base.json', f'l1_{N}.json')}
    gates = sorted(os.path.basename(p) for p in glob.glob(os.path.join(src, 'runs', '*.json')) if not os.path.basename(p).startswith(('e4', 'e6', 'e7')))
    R['gate runs (every readout)'] = {f: cmp_json(os.path.join(src, 'runs', f), os.path.join(out, 'runs', f), TIMING) for f in gates}
    R['E3/E4, E6, E7'] = {f: cmp_json(os.path.join(src, 'runs', f), os.path.join(out, 'runs', f), TIMING) for f in ('e4_e3.json', 'e6.json', 'e7.json')}
    R['laws: expressions and proofs'] = {f: cmp_json(os.path.join(src, 'laws', f), os.path.join(out, 'laws', f), TIMING | COLONY) for f in ('laws.json', 'whole_laws.json', 'tau_law.json')}
    R['results.json'] = {'results.json': cmp_json(os.path.join(src, 'results.json'), os.path.join(out, 'results.json'), TIMING)}
    maps = {}
    for arm in ('frozen', 'read'):
        for r in REPOS:
            ok, notes, n = cmp_map(os.path.join(src, 'maps', N, arm, r), os.path.join(out, 'maps', N, arm, r))
            maps[f'{arm}/{r} ({n} files)'] = (ok, notes)
    R[f'MiniLM maps (byte for byte)'] = maps
    digests = sum((load(os.path.join(src, 'runs', f)) or {}).get('digest') == (load(os.path.join(out, 'runs', f)) or {}).get('digest') for f in gates)
    clocks = {}
    for f, keys in (('laws.json', ('SEL', 'CGAP', 'CNEAR')), ('whole_laws.json', ('RLIM', 'GAPW')), ('tau_law.json', ('TAU',))):
        a, b = load(os.path.join(src, 'laws', f)) or {}, load(os.path.join(out, 'laws', f)) or {}
        for k in keys:
            clocks[k] = {w: {c: (d.get(k) or {}).get(c) for c in ('ladder', 'generation', 'evals', 'ticks', 'note', 'secs')} for w, d in (('record', a), ('regenerated', b))}
    log = open(os.path.join(out, 'reproduce.log')).read() if os.path.exists(os.path.join(out, 'reproduce.log')) else ''
    rec_log = open(os.path.join(src, 'runs', 'minilm.log')).read() if os.path.exists(os.path.join(src, 'runs', 'minilm.log')) else ''
    times = re.findall(r'reproduce\.sh (?:done )?(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)', log)
    return R, digests, len(gates), clocks, build_times(rec_log), build_times(log), times


def report(src, out, R, digests, ngates, clocks, bt_rec, bt_reg, times, pre):
    held = all(ok for sec in R.values() for ok, _ in sec.values())
    L = ['# E8: one command, end to end', '',
         f'- Record: `{src}`; regeneration: `{out}`, made by `zsh e8.sh`, which copied the harness there byte for byte and ran its `reproduce.sh`.',
         f'- Started {times[0] if times else "?"}, finished {times[-1] if len(times) > 1 else "?"}.',
         f'- Code: all {len(pre[0])} files HASHES.txt lists had their latest recorded hash before the run ({len(pre[1])} differed).',
         f'- **E8 {"HOLDS" if held else "DOES NOT HOLD"}**: every number that must come back {"came back exactly" if held else "did not; the differences are below"}. '
         f'Gate readouts: {digests} of {ngates} runs byte-identical by digest.', '',
         '| what | compared | identical | first differences |', '|---|---|---|---|']
    for name, sec in R.items():
        bad = [(k, d) for k, (ok, d) in sec.items() if not ok]
        first = '; '.join('%s: %s' % (k, str(d[:2])[:160]) for k, d in bad[:2]) or '—'
        L.append(f'| {name} | {len(sec)} | {len(sec) - len(bad)} | {first} |')
    L += ['', '## Reported, not required', '', '### MiniLM build times (s)', '', '| map | record | regenerated |', '|---|---|---|']
    for k in sorted(set(bt_rec) | set(bt_reg)):
        L.append(f'| {k[0]} {k[1]} | {bt_rec.get(k, "")} | {bt_reg.get(k, "")} |')
    L += ['', '### Each colony\'s own clock (found on real time, so it varies run to run)', '',
          '| law | record: rung, generation, evaluations, ticks | regenerated: rung, generation, evaluations, ticks |', '|---|---|---|']
    for k, v in clocks.items():
        f = lambda d: f"{d['ladder']}, gen {d['generation']}, {d['evals']} evals, ticks {d['ticks']}"
        L.append(f"| {k} | {f(v['record'])} | {f(v['regenerated'])} |")
    open(os.path.join(out, 'E8_COMPARE.md'), 'w').write('\n'.join(L) + '\n')
    json.dump(dict(held=held, digests_identical=digests, gate_runs=ngates, sections={n: {k: dict(identical=ok, differences=[list(map(str, x)) for x in d])
              for k, (ok, d) in s.items()} for n, s in R.items()}, colony_clocks=clocks, precheck_mismatches=pre[1], times=times),
              open(os.path.join(out, 'e8_compare.json'), 'w'), indent=1, default=str)
    return held


if __name__ == '__main__':
    if sys.argv[1] == '--precheck':
        latest, bad = precheck(sys.argv[2])
        print('precheck: %d files listed in HASHES.txt, %d differ from their latest recorded hash%s' % (len(latest), len(bad), (': %s' % bad) if bad else ''))
        sys.exit(1 if bad else 0)
    src, out = map(os.path.abspath, sys.argv[1:3])
    R, digests, ngates, clocks, bt_rec, bt_reg, times = compare(src, out)
    held = report(src, out, R, digests, ngates, clocks, bt_rec, bt_reg, times, precheck(src))
    print(open(os.path.join(out, 'E8_COMPARE.md')).read())
    sys.exit(0 if held else 1)
