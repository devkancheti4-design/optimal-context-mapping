"""E7: the lessons carried across a rebuild are identical under every model. Lessons follow their code by line text, not by
vectors: teach DeepInfer's 12 taught facts (wording a, at their gold lines) into a scratch copy of the bge map, then carry
that Life into fresh copies of the bge map and of the MiniLM maps (frozen and read), and compare what each carry returns
(entries, carried, moved, reformatted, abstained, the Life's sha) and the carried Life itself.
    python3 -I e7.py"""
import json, os, shutil, site, sys
sys.path.append(site.getusersitepackages()); sys.path.insert(0, os.path.expanduser('~/optimal-context-mapping-embed-law'))
os.environ['OCM_OFFLINE'] = '1'
from ocm import server as S
HERE = os.path.dirname(os.path.abspath(__file__)); E = os.path.join(HERE, 'e7'); shutil.rmtree(E, ignore_errors=True); os.makedirs(E)
SRC = {'bge-base': os.path.expanduser('~/coldsession-fresh-work/DeepInfer/maps/modeld'),
       'MiniLM frozen': os.path.join(HERE, 'maps/all-MiniLM-L6-v2/frozen/DeepInfer'),
       'MiniLM read': os.path.join(HERE, 'maps/all-MiniLM-L6-v2/read/DeepInfer')}


def fresh_copy(src, name):
    d = os.path.join(E, name)
    shutil.copytree(src, d, ignore=shutil.ignore_patterns('calls.jsonl', '*.log', 'taught.life.json', 'carry_misses.json'))
    if os.path.isdir(os.path.join(src, 'memory_at_build')):            # untaught: the memory as built
        shutil.rmtree(os.path.join(d, 'memory')); shutil.copytree(os.path.join(src, 'memory_at_build'), os.path.join(d, 'memory'))
    return d


old = fresh_copy(SRC['bge-base'], 'taught')
facts = [json.loads(l) for l in open(os.path.expanduser('~/coldsession/fresh/data/DeepInfer/facts.jsonl'))]
print(S.Workspace(old).handle('teach', {'pairs': [{'question': f['wordings']['a'], 'at': '%s:%d' % (f['path'], f['line'])} for f in facts if f['role'] == 'taught']}))
out = {}
for name, src in SRC.items():
    w = S.Workspace(fresh_copy(src, name.replace(' ', '_')))
    r = w.carry(old); r['life'] = json.loads(w.life.dumps()); out[name] = r
    print('%-14s %s' % (name, json.dumps({k: r[k] for k in r if k != 'life'})))
first = next(iter(out.values()))
same = all({k: v for k, v in r.items() if k != 'vectors taught'} == {k: v for k, v in first.items() if k != 'vectors taught'} for r in out.values())
print('E7: carried lessons identical under every model:', same)
json.dump({'identical': same, 'carries': out}, open(os.path.join(HERE, 'runs', 'e7.json'), 'w'), indent=1)
shutil.rmtree(E, ignore_errors=True)
