"""Cortex D against Graphify's knowledge graph on the same Django commit (0ab58c1209): how many of Cortex D's meaning
edges join files that Graphify's graph links directly.
    python overlap.py <cortex.json> <graphify graph.json> > overlap.json
cortex.json: `modeld cortex` on the Django workspace that learned the codebase once (vs-graphify, dj_cover).
graph.json: Graphify 0.9.92's own output for the same commit (built_at_commit 0ab58c12)."""
import collections, json, sys
C, G = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
sf = {n["id"]: n.get("source_file") for n in G["nodes"]}
pairs, rel = set(), collections.defaultdict(set)
for l in G["links"]:
    a, b = sf.get(l["source"]), sf.get(l["target"])
    if a and b and a != b:
        k = tuple(sorted((a, b))); pairs.add(k); rel[k].add(l["relation"])
covered = {v for v in sf.values() if v}
N = {n["id"]: n for n in C["nodes"]}
M = [(N[e["source"]]["path"], N[e["target"]]["path"]) for e in C["edges"] if e["kind"] == "meaning"]
both = [m for m in M if m[0] in covered and m[1] in covered]
linked = [m for m in both if tuple(sorted(m)) in pairs]
out = {"graphify": {"nodes": len(G["nodes"]), "links": len(G["links"]), "files": len(covered), "file_pairs_linked": len(pairs),
                    "relations": collections.Counter(l.get("relation") for l in G["links"]).most_common(),
                    "built_at_commit": G.get("built_at_commit")},
       "cortex": C["stats"],
       "meaning_edges_both_files_covered": len(both), "graphify_links_them": len(linked),
       "graphify_does_not": len(both) - len(linked),
       "their_relations_where_linked": collections.Counter(r for m in linked for r in rel[tuple(sorted(m))]).most_common()}
json.dump(out, sys.stdout, indent=1)
