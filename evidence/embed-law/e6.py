"""E6: what calibration costs on the largest map (sphinx, 41,641 units), bge-base on the Apple GPU: wall time and memory."""
import json, os, site, sys, time, resource
sys.path.append(site.getusersitepackages()); sys.path.insert(0, os.path.expanduser('~/optimal-context-mapping-embed-law'))
os.environ['OCM_OFFLINE'] = '1'
from ocm.cmlm_vector.memory import Memory
from ocm.calibrate import geometry, thresholds
m = Memory(os.path.expanduser('~/coldsession-fresh-work/sphinx/maps/modeld/memory'))
_ = m.embedder; r0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
t0 = time.time(); g = geometry(m); dt = time.time() - t0
r1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(json.dumps({'units': g['n_units'], 'pseudo_queries': g['n_queries'], 'seconds': round(dt, 1), 'device': m.man['device'],
                  'max_rss_mb_model_loaded': round(r0 / 1e6), 'max_rss_mb_after': round(r1 / 1e6), 'tokens': 0, 'thresholds': thresholds(g)}))
