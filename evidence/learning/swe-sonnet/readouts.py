"""PROTOCOL_SWE_SONNET.md: the kit's readout for each of the 114 issues, before it reaches the agent. Teaching after each
issue is the gold location (PROTOCOL_SWE.md), never an agent's answer, so the sequence is fixed in advance.
    ~/.venvs/cmlm-live/bin/python readouts.py [out=readouts.json]"""
import json, os, shutil, sys, tempfile, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
from ocm.server import Workspace
from ocm.loop import readout
ISSUES = json.load(open(f"{B}/swe/issues.json"))["issues"]
ws_dir = os.path.join(tempfile.mkdtemp(), "ws"); shutil.copytree(f"{B}/swe/ws_base", ws_dir); w = Workspace(ws_dir)
out = {}
for k, i in enumerate(ISSUES):
    out[i["id"]] = readout(lambda path, **kw: w.handle(path, kw), i["issue"][:4000])
    w.handle("teach", {"pairs": [{"question": i["issue"][:4000], "at": f"corpus/{i['file']}:{i['line']}"}]})
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "readouts.json", "w"), indent=1)
shutil.rmtree(os.path.dirname(ws_dir))
print(len(out), "readouts;", sum(v.startswith("(readout: the code a taught question") for v in out.values()), "on the taught lane")
