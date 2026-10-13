"""Model D on SWE-bench Lite with a readout scope: ranked files per issue (title, and title + 400 chars), readout size.
    PYTHONPATH=<optimal-context-mapping checkout> python run_modeld_scope.py <scope: all|code> <out json>"""
import json, os, re, sys
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
from ocm.server import Workspace
SCOPE, OUT = sys.argv[1], sys.argv[2]
L = os.path.dirname(os.path.abspath(__file__)); D = json.load(open(f"{L}/swebench_lite_by_repo.json")); out = {}
for slug, v in D.items():
    name = slug.split("/")[1]; ws = f"{L}/ws/{name}"
    w = Workspace(ws); rows = {}
    for it in v["issues"]:
        r = {}
        for key in ("query_title", "query_400"):
            text = w.handle("ask", {"question": it[key], "scope": SCOPE}); files = []
            for p in re.findall(r"(?m)^\d+\. \[([^\]:]+):\d+\]", text):
                p = p.split("/", 1)[1] if "/" in p else p          # drop the indexed folder's name
                if p not in files: files.append(p)
            r[key] = {"files": files[:10], "chars": len(text)}
        rows[it["instance_id"]] = r
    out[slug] = rows; print(slug, len(rows), flush=True)
json.dump(out, open(f"{L}/{OUT}", "w"))
