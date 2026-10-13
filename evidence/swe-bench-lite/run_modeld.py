"""Model D's kit on SWE-bench Lite: ranked files per issue (title, and title + 400 chars), readout size.
Run with the Model D package: ~/ocm-eval/venvs/t021/bin/python run_modeld.py"""
import json, os, re
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
from ocm.server import Workspace
L = os.path.dirname(os.path.abspath(__file__)); D = json.load(open(f"{L}/swebench_lite_by_repo.json")); out = {}
for slug, v in D.items():
    name = slug.split("/")[1]; ws = f"{L}/ws/{name}"
    if not os.path.exists(f"{ws}/workspace.json"):
        continue
    w = Workspace(ws); rows = {}
    for it in v["issues"]:
        r = {}
        for key in ("query_title", "query_400"):
            text = w.handle("ask", {"question": it[key]}); files = []
            for p in re.findall(r"(?m)^\d+\. \[([^\]:]+):\d+\]", text):
                p = p.split("/", 1)[1] if "/" in p else p          # drop the indexed folder's name
                if p not in files: files.append(p)
            r[key] = {"files": files[:10], "chars": len(text)}
        rows[it["instance_id"]] = r
    out[slug] = rows; print(slug, len(rows), flush=True)
json.dump(out, open(f"{L}/modeld_ranked.json", "w"))
