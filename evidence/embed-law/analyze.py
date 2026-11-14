"""analyze.py -- Stage 3 and Stage 4 as PROTOCOL.md states them: E1-E8, the gates pooled over the six ColdSession-Fresh
repositories with 95% bootstrap intervals over facts (10,000 resamples, seed 0), and predictions P1-P5.
    python3 -I analyze.py   (reads runs/*.json, l1_*.json, laws/*.json; writes results.json and prints the tables)"""
import glob, json, os, site, subprocess, sys
sys.path.append(site.getusersitepackages()); sys.path.insert(0, os.path.expanduser('~/optimal-context-mapping-embed-law'))
os.environ['OCM_OFFLINE'] = '1'; os.environ.setdefault('HF_HUB_OFFLINE', '1')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, 'runs')
REPOS = ['artemis', 'FrontierAgent', 'DeepInfer', 'sphinx', 'textual', 'celery']
ARMS = ['frozen', 'read', 'L1', 'L2']
MODELS = {'bge-base': 'BAAI/bge-base-en-v1.5', 'all-MiniLM-L6-v2': 'sentence-transformers/all-MiniLM-L6-v2'}
TODAY = {'tau': 8, 'near': 8, 'delta': 8, 'gap': 74, 'relation_limit': 37, 'cert_gap': 41, 'cert_near': 10}


def run(model, r, arm):
    """One gate run. bge-base's frozen and read arms are the same map and code path (part A is bit-identical): E2's control."""
    if model == 'bge-base':
        p = f'E2_{r}_control.json' if arm in ('frozen', 'read') else f'bge_{r}_{arm}.json'
    else:
        p = f'{model}_{r}_{arm}.json'
    p = os.path.join(R, p)
    return json.load(open(p)) if os.path.exists(p) else None


def load(model, arm):
    """per fact: (repo, id, {g1l, g1f, g2: [lead per wording], g3: [wrong per wording]}) pooled; None if a repo is missing."""
    facts = []
    for r in REPOS:
        d = run(model, r, arm)
        if d is None:
            return None
        by = {}
        for x in d['g1']: by.setdefault(x['id'], {}).update(g1l=int(x['line_in']), g1f=int(x['file_first']))
        for x in d['g2']: by.setdefault(x['id'], {}).setdefault('g2', []).append(int(x['lead']))
        for x in d['g3']: by.setdefault(x['id'], {}).setdefault('g3', []).append(int(x['wrong_pull']))
        facts += [(r, k, v) for k, v in by.items()]
    return facts


def totals(facts):
    return dict(g1_line=sum(v['g1l'] for _, _, v in facts), g1_file=sum(v['g1f'] for _, _, v in facts), g1_n=len(facts),
                g2_lead=sum(sum(v.get('g2', [])) for _, _, v in facts), g2_n=sum(len(v.get('g2', [])) for _, _, v in facts),
                g3_wrong=sum(sum(v.get('g3', [])) for _, _, v in facts), g3_n=sum(len(v.get('g3', [])) for _, _, v in facts))


def boot_diff(a, b, key, reps=10000, seed=0):
    """(b - a) in a gate's count and its 95% interval, resampling facts (the same facts in both arms, paired)."""
    ka = {(r, k): v for r, k, v in a}; kb = {(r, k): v for r, k, v in b}; ids = sorted(set(ka) & set(kb))
    val = lambda v: sum(v.get(key, [])) if isinstance(v.get(key), list) else v.get(key, 0)
    d = np.array([val(kb[i]) - val(ka[i]) for i in ids], dtype=float)
    rng = np.random.default_rng(seed); s = d[rng.integers(0, len(d), (reps, len(d)))].sum(axis=1)
    return [int(d.sum()), float(np.quantile(s, 0.025)), float(np.quantile(s, 0.975))]


def e_checks():
    E = {}
    # E1: L1 with bge-base gives today's numbers, and every readout is byte for byte the control's.
    per = {}
    for r in REPOS:
        d, c = run('bge-base', r, 'L1'), run('bge-base', r, 'frozen')
        if d and c:
            th = d['calibration']['thresholds']
            per[r] = dict(off={k: [th[k], v] for k, v in TODAY.items() if th[k] != v}, same_readouts=d['digest'] == c['digest'])
    if per:
        off = next(iter(per.values()))['off']
        E['E1'] = dict(held=all(not p['off'] and p['same_readouts'] for p in per.values()), numbers_off_today=off,
                       repos_with_identical_readouts=sum(p['same_readouts'] for p in per.values()), repos=len(per))
    # E2: a 0.5.3 map with no calibration gives byte-identical readouts on the branch.
    same = [run_file(f'E2_{r}_control.json')['digest'] == run_file(f'E2_{r}_branch.json')['digest'] for r in REPOS
            if run_file(f'E2_{r}_control.json') and run_file(f'E2_{r}_branch.json')]
    E['E2'] = dict(held=bool(same) and all(same), identical=sum(same), repos=len(same))
    # E3, E4: no labels; deterministic on CPU.
    if os.path.exists(os.path.join(R, 'e4_e3.json')):
        x = json.load(open(os.path.join(R, 'e4_e3.json')))
        E['E3'] = dict(held=bool(x['E3_with_lessons_identical']), note='same numbers on the map with 12 lessons as without; '
                       'calibrate() reads units and model files only')
        E['E4'] = dict(held=bool(x['E4_twice_identical']), device=x['device'], geometry=x['geometry'], thresholds=x['thresholds'])
    # E5: part A traced to each model's files; the only use of a name is the declared prompt table.
    from ocm.cmlm_vector.embed import read_spec, Refused
    traced = {}
    for short, name in MODELS.items():
        s = read_spec(name); traced[short] = {k: s[k] for k in ('pooling', 'normalize', 'query_prompt', 'document_prompt', 'max_length', 'sources')}
    try:
        read_spec('gpt2'); refused = 'NOT refused'
    except Refused as e:
        refused = str(e)
    except Exception as e:                                          # not cached: cannot be read offline
        refused = f'not readable offline ({type(e).__name__})'
    src = open(os.path.expanduser('~/optimal-context-mapping-embed-law/ocm/cmlm_vector/embed.py')).read()
    name_tests = [l.strip() for l in src.splitlines() if l.strip().startswith(('if ', 'elif ')) and 'name' in l]
    E['E5'] = dict(held=all(t == 'elif name in PROMPT_TABLE:' for t in name_tests), traced=traced, gpt2=refused, name_tests=name_tests)
    # E6: free.
    if os.path.exists(os.path.join(R, 'e6.json')):
        x = json.load(open(os.path.join(R, 'e6.json')))
        cal = {m: [run(m, r, 'L2')['calibration']['seconds'] for r in REPOS if run(m, r, 'L2')] for m in MODELS}
        E['E6'] = dict(held=x['tokens'] == 0, sphinx=x, l2_calibration_seconds=cal)
    # E7: the carried lessons are identical under every model.
    if os.path.exists(os.path.join(R, 'e7.json')):
        x = json.load(open(os.path.join(R, 'e7.json')))
        E['E7'] = dict(held=bool(x['identical']), carries={k: {kk: v[kk] for kk in v if kk != 'life'} for k, v in x['carries'].items()})
    # E8: one command.
    E['E8'] = dict(command='zsh ~/neos/sandbox/embed_law/reproduce.sh', exists=os.path.exists(os.path.join(HERE, 'reproduce.sh')))
    return E


def run_file(f):
    p = os.path.join(R, f)
    return json.load(open(p)) if os.path.exists(p) else None


def sigma0s(model):
    """L1: the model's one reference geometry. L2: each code map's own."""
    l1 = os.path.join(HERE, f'l1_{model}.json')
    return dict(L1=json.load(open(l1))['sigma0'] if os.path.exists(l1) else None,
                L2={r: run(model, r, 'L2')['calibration']['geometry']['sigma0'] for r in REPOS if run(model, r, 'L2')})


if __name__ == '__main__':
    models = [m for m in MODELS if load(m, 'frozen')]
    res, out = {}, {}
    for m in models:
        for a in ARMS:
            f = load(m, a)
            if f: res[f'{m}|{a}'] = totals(f)
    print('%-18s %-6s  %9s %9s %9s %9s' % ('model', 'arm', 'G1 line', 'G1 file', 'G2 lead', 'G3 wrong'))
    for key, t in res.items():
        m, a = key.split('|')
        print('%-18s %-6s  %3d / %-3d  %3d / %-3d %3d / %-3d %3d / %-3d' % (m, a, t['g1_line'], t['g1_n'], t['g1_file'], t['g1_n'], t['g2_lead'], t['g2_n'], t['g3_wrong'], t['g3_n']))
    E = e_checks()
    S = {m: sigma0s(m) for m in models}
    P = {}
    P['P1'] = dict(held=all(E.get(k, {}).get('held', False) for k in ('E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7')) and E['E8']['exists'],
                   expected='fail on E1 (stated before any other model was measured)', failing=[k for k, v in E.items() if not v.get('held', v.get('exists'))])
    for m in models:
        if m == 'bge-base' or not load(m, 'L1'):
            continue
        fz, rd, l1, l2 = (load(m, a) for a in ARMS)
        g2, g3 = boot_diff(fz, l1, 'g2'), boot_diff(fz, l1, 'g3')
        P[f'P2 {m}'] = dict(held=g2[0] >= 0 and g3[0] <= 0, g2_L1_minus_frozen=g2, g3_L1_minus_frozen=g3,
                            interval_rules_out_loss=g2[1] >= 0 and g3[2] <= 0,
                            note='held on the point estimates; [sum, 2.5%, 97.5%] over 10,000 fact resamples')
        out[f'decomposition {m} (not a prediction)'] = {
            'read - frozen (part A alone)': {g: boot_diff(fz, rd, g) for g in ('g1l', 'g2', 'g3')},
            'L1 - read (thresholds alone)': {g: boot_diff(rd, l1, g) for g in ('g1l', 'g2', 'g3')},
            'L2 - read (thresholds alone)': {g: boot_diff(rd, l2, g) for g in ('g1l', 'g2', 'g3')} if l2 else None}
    if 'bge-base|frozen' in res:
        rate = lambda k: res[k]['g2_lead'] / res[k]['g2_n']
        for m in models[1:]:
            if f'{m}|frozen' in res and f'{m}|L1' in res:
                sf, sl = abs(rate('bge-base|frozen') - rate(f'{m}|frozen')), abs(rate('bge-base|L1') - rate(f'{m}|L1'))
                P[f'P3 bge-base vs {m}'] = dict(held=sl < sf, g2_spread_frozen=round(sf, 4), g2_spread_L1=round(sl, 4))
    if len(S) > 1 and S['bge-base']['L1']:
        b = S['bge-base']
        for m in models[1:]:
            if S[m]['L1']:
                rel = abs(S[m]['L1'] - b['L1']) / b['L1']
                l2 = [abs(S[m]['L2'][r] - b['L2'][r]) / b['L2'][r] for r in REPOS if r in S[m]['L2'] and r in b['L2']]
                P[f'P4 bge-base vs {m}'] = dict(held=rel >= 0.20, sigma0_L1={'bge-base': b['L1'], m: S[m]['L1']}, rel_diff_L1=round(rel, 4),
                                                rel_diff_L2_per_map=[round(x, 4) for x in l2], note='relative to bge-base, the control')
    if S.get('bge-base', {}).get('L2'):
        l2 = S['bge-base']['L2']; within = {r: 33.3 <= v <= 40.7 for r, v in l2.items()}
        th = {r: run('bge-base', r, 'L2')['calibration']['thresholds'] for r in l2}
        moved = {r: {k: [t[k], v] for k, v in TODAY.items() if t[k] != v} for r, t in th.items()}
        same = {r: run('bge-base', r, 'L2')['digest'] == run('bge-base', r, 'frozen')['digest'] for r in l2}
        P['P5'] = dict(held=all(within.values()) and not any(moved.values()), first_half_sigma0_within_10pct_of_37=all(within.values()),
                       sigma0_L2=l2, second_half_L2_changes_nothing=not any(moved.values()), thresholds_moved=moved,
                       repos_with_identical_readouts=sum(same.values()), expected='fail on the second half (stated before measuring)')
    out.update(totals=res, e_checks=E, sigma0=S, predictions=P)
    json.dump(out, open(os.path.join(HERE, 'results.json'), 'w'), indent=1)
    for k, v in list(E.items()) + list(P.items()):
        print(k, json.dumps(v)[:400])
    for k, v in out.items():
        if k.startswith('decomposition'):
            print(k, json.dumps(v))
