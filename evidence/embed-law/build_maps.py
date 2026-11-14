"""build_maps.py -- a ColdSession-Fresh workspace for one model, with the control's build (frozen: 0.5.3's way for every
model) or the branch's (read: part A). Same snapshot and relative paths as the bge maps; no float cache.
    python3 -I build_maps.py control|branch MODEL REPO OUT"""
import os, site, sys, time
sys.path.append(site.getusersitepackages())
code, model, repo, out = sys.argv[1:5]
sys.path.insert(0, os.path.expanduser('~/eval/repos/modelD' if code == 'control' else '~/optimal-context-mapping-embed-law'))
os.environ['OCM_OFFLINE'] = '1'
from ocm import build as B
t0 = time.time()
kw = dict(read=True) if code == 'branch' else {}
B.build([os.path.expanduser(f'~/coldsession-fresh-work/{repo}/snap/repo')], out, model=model, device='mps', log=lambda s: None, **kw)
print('%s %s %s built in %.1fs' % (code, model.split('/')[-1], repo, time.time() - t0))
