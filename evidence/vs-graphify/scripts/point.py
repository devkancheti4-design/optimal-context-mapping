"""Pointing, offline: each tool's first readout for every question, the files it lists in order, and its size.

    python point.py md <workspace> <questions.json> <out.json>     Model D: ask, scope code
    python point.py gf <graph.json> <questions.json> <out.json>    Graphify: query_graph through its MCP server, defaults

questions.json: [{"id", "queries": {name: text}, "gold": [...]}]. out: {id: {name: {files (first 10), chars, taught}}}."""
import json, os, re, sys
arm, src, qfile, out = sys.argv[1:5]
Q = json.load(open(qfile)); res = {}
if arm == "md":
    sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
    os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import ocm
    assert ocm.__file__.startswith(os.path.expanduser("~/optimal-context-mapping")), ocm.__file__
    from ocm.server import Workspace
    from ocm.loop import TAUGHT
    w = Workspace(src)
    ask = lambda q: w.handle("ask", {"question": q, "scope": "code"})
    CITE = re.compile(r"(?m)^\s*\d+\.\s*\[([^\]]+?):\d+\]")
    files_of = lambda t: [p.split("/", 1)[1] if "/" in p else p for p in CITE.findall(t)]   # drop the indexed folder
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gf_mcp import Graphify
    G = Graphify(src, int(os.environ.get("GF_PORT", "8092")), log=out + ".serve.log")
    ask = lambda q: G.call("query_graph", {"question": q})
    TAUGHT = None
    SRC = re.compile(r"(?m)^NODE .*?\[src=([^ \]]+)")
    files_of = lambda t: SRC.findall(t)
try:
    for it in Q:
        r = {}
        for name, q in it["queries"].items():
            t = ask(q); files = list(dict.fromkeys(files_of(t)))
            r[name] = {"files": files[:10], "chars": len(t), "taught": bool(TAUGHT and t.startswith(TAUGHT))}
        res[it["id"]] = r
finally:
    if arm == "gf":
        G.close()
json.dump(res, open(out, "w"))
print(f"{arm} {os.path.basename(src.rstrip('/'))}: {len(res)} questions", flush=True)
