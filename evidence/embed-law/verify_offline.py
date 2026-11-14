"""verify_offline.py -- does the branch stay off the network with OCM_OFFLINE=1? A local listener stands in for the Hub
(HF_ENDPOINT points at it); every connection attempt is counted. Old reader vs fixed reader, then the fixed code end to
end (a gate run that calibrates, and an L1 reference): connections, and outputs against the record."""
import json, os, socket, subprocess, sys, threading
SCR = os.path.dirname(os.path.abspath(__file__)); HARN = os.path.expanduser('~/neos/sandbox/embed_law')
BR = os.path.expanduser('~/optimal-context-mapping-embed-law')
hits = []


def listen(sock):
    while True:
        try:
            c, addr = sock.accept()
        except OSError:
            return
        try:
            hits.append(c.recv(200).split(b'\r\n')[0].decode(errors='replace'))
        except OSError:
            hits.append('?')
        c.close()                                           # refuse to answer: an online path errors or falls back


s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('127.0.0.1', 0)); s.listen(64)
PORT = s.getsockname()[1]; threading.Thread(target=listen, args=(s,), daemon=True).start()
ENV = dict(os.environ, OCM_OFFLINE='1', HF_ENDPOINT=f'http://127.0.0.1:{PORT}')
for k in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE'):
    ENV.pop(k, None)
REC = json.load(open(os.path.join(HARN, 'results.json')))['e_checks']['E5']['traced']
MODELS = {'bge-base': 'BAAI/bge-base-en-v1.5', 'all-MiniLM-L6-v2': 'sentence-transformers/all-MiniLM-L6-v2'}
KEYS = ('pooling', 'normalize', 'query_prompt', 'document_prompt', 'max_length', 'sources')
READ = r'''
import importlib.util, json, sys, site
sys.path.append(site.getusersitepackages())
spec = importlib.util.spec_from_file_location("embed_under_test", sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
out = {}
for name in sys.argv[2:]:
    try:
        s = m.read_spec(name); out[name] = {k: s[k] for k in %r}
    except m.Refused as e:
        out[name] = "refused: " + str(e)[:60]
print(json.dumps(out))
''' % (KEYS,)


def run(label, cmd):
    hits.clear()
    r = subprocess.run(cmd, env=ENV, capture_output=True, text=True, timeout=900)
    n, first = len(hits), list(hits[:2])
    warn = sum('unauthenticated' in l or 'connect' in l.lower() for l in r.stderr.splitlines())
    return dict(label=label, connections=n, first_requests=first, hub_warnings=warn, rc=r.returncode, out=r.stdout.strip().splitlines()[-1:] if r.stdout.strip() else [], err=r.stderr.strip().splitlines()[-2:])


res = []
for label, path in (('old reader (before the fix)', os.path.join(SCR, 'embed_before_offline_fix.py')),
                    ('fixed reader', os.path.join(BR, 'ocm/cmlm_vector/embed.py'))):
    r = run(label, [sys.executable, '-I', '-c', READ, path, *MODELS.values(), 'gpt2'])
    got = json.loads(r['out'][0]) if r['out'] else {}
    r['specs_equal_record'] = {short: got.get(name) == REC[short] for short, name in MODELS.items()}
    r['gpt2'] = got.get('gpt2'); r.pop('out'); res.append(r)
S2 = os.path.join(SCR, 'offline_gate_minilm_DeepInfer_L2.json')
r = run('fixed code, gate run (MiniLM DeepInfer, L2: loads the model, calibrates)',
        [sys.executable, '-I', os.path.join(HARN, 'gates.py'), '--code', 'branch', '--workspace', os.path.join(HARN, 'maps/all-MiniLM-L6-v2/read/DeepInfer'),
         '--facts', os.path.expanduser('~/coldsession/fresh/data/DeepInfer/facts.jsonl'), '--arm', 'L2', '--out', S2])
r['digest_equals_record'] = json.load(open(S2))['digest'] == json.load(open(os.path.join(HARN, 'runs/all-MiniLM-L6-v2_DeepInfer_L2.json')))['digest'] if os.path.exists(S2) else None
r.pop('out'); res.append(r)
L1 = os.path.join(SCR, 'offline_l1_minilm.json')
r = run('fixed code, L1 reference (MiniLM: reads its files, embeds 20,000 sentences)',
        [sys.executable, '-I', os.path.join(HARN, 'l1_reference.py'), MODELS['all-MiniLM-L6-v2'], L1])
if os.path.exists(L1):
    a, b = json.load(open(L1)), json.load(open(os.path.join(HARN, 'l1_all-MiniLM-L6-v2.json')))
    r['geometry_equals_record'] = {k: a[k] == b[k] for k in ('sigma0', 'lift84', 'lift98', 'median', 'n_units', 'n_queries')}
r.pop('out'); res.append(r)
for r in res:
    print(json.dumps(r))
json.dump(res, open(os.path.join(SCR, 'verify_offline.json'), 'w'), indent=1)
