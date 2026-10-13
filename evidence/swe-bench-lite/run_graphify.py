"""graphify query on SWE-bench Lite: printed files per issue (title, and title + 400 chars), answer size.
Run from a graphify checkout: uv run --no-sync python run_graphify.py [graphs dir, default graphs087] [out json]"""
import json, os, re, sys
from networkx.readwrite import json_graph
from graphify import serve as S
L = os.path.dirname(os.path.abspath(__file__)); D = json.load(open(f"{L}/swebench_lite_by_repo.json")); out = {}
GR = sys.argv[1] if len(sys.argv) > 1 else "graphs087"; OUT = sys.argv[2] if len(sys.argv) > 2 else "graphify_ranked.json"
def load(p):
    raw = json.load(open(p)); raw = dict(raw, links=raw.get("links", raw.get("edges", [])))
    raw["links"] = [{**l, "_src": l.get("_src", l.get("source")), "_tgt": l.get("_tgt", l.get("target"))} for l in raw["links"]]
    return json_graph.node_link_graph(raw, edges="links")
for slug, v in D.items():
    name = slug.split("/")[1]; gp = f"{L}/{GR}/{name}/graphify-out/graph.json"
    if not os.path.exists(gp):
        continue
    G = load(gp); rows = {}
    for it in v["issues"]:
        r = {}
        for key in ("query_title", "query_400"):
            text = S._query_graph_text(G, it[key], mode="bfs", depth=2, token_budget=2000); files = []
            for p in re.findall(r"(?m)^NODE .*?\[src=([^ \]]+)", text):
                if p not in files: files.append(p)
            r[key] = {"files": files[:10], "chars": len(text)}
        rows[it["instance_id"]] = r
    out[slug] = rows; print(slug, len(rows), G.number_of_nodes(), "nodes", flush=True)
json.dump(out, open(f"{L}/{OUT}", "w"))
