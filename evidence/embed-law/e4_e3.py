"""E4: the same model, map and seed give the same numbers twice on CPU. E3: the same numbers with and without lessons
taught (calibration reads only the map's units and the model's files)."""
import json, os, site, sys
sys.path.append(site.getusersitepackages()); sys.path.insert(0, os.path.expanduser('~/optimal-context-mapping-embed-law'))
os.environ['OCM_OFFLINE'] = '1'; os.environ['CMLM_DEVICE'] = 'cpu'
from ocm import server as S
from ocm.cmlm_vector import memory as MM
from ocm import life as LIFE
from ocm.calibrate import geometry, thresholds
MM.Memory.save = lambda self: None; LIFE.Life.save = lambda self, path=None: None
WS = os.path.expanduser('~/coldsession-fresh-work/DeepInfer/maps/modeld')
w = S.Workspace(WS)
g1 = geometry(w.mem); g2 = geometry(w.mem)
facts = [json.loads(l) for l in open(os.path.expanduser('~/coldsession/fresh/data/DeepInfer/facts.jsonl'))]
w.handle('teach', {'pairs': [{'question': f['wordings']['a'], 'at': '%s:%d' % (f['path'], f['line'])} for f in facts if f['role'] == 'taught']})
g3 = geometry(w.mem)
print(json.dumps({'device': 'cpu', 'E4_twice_identical': g1 == g2, 'E3_with_lessons_identical': g1 == g3, 'cues_after_teaching': len(w.mem.cue_texts),
                  'geometry': g1, 'thresholds': thresholds(g1)}))
