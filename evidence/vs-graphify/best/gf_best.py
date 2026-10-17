"""Graphify 0.9.92's own ranking, three readings per question (METHOD_BEST.md). Run with Graphify's environment:
    gfvenv/bin/python best/gf_best.py <graph.json> <questions.json> <out.json>"""
import json, sys
from graphify.serve import _read_graph, _query_terms, _score_query, _pick_seeds, _RELATIONAL_INTENT_TERMS
from graphify.paths import _is_test_path
TEST_TERMS = {"test", "tests", "testing", "pytest", "unittest", "fixture", "fixtures", "spec", "specs"}
gp, qf, out = sys.argv[1:4]
G = _read_graph(gp); Q = json.load(open(qf)); res = {}
src = lambda n: (G.nodes[n].get("source_file") or "") if n in G else ""


def fill(first, ranked):
    files = list(dict.fromkeys(f for f in first if f))
    for _, n in ranked:
        if len(files) >= 30:
            break
        f = src(n)
        if f and f not in files:
            files.append(f)
    return files


for it in Q:
    r = {}
    for name, q in it["queries"].items():
        terms = _query_terms(q)
        qs = _score_query(G, terms, collect_per_term_seeds=True)
        best = qs.best_seed_by_term
        intent = {t for t in best if t in _RELATIONAL_INTENT_TERMS}
        if intent and any(t not in _RELATIONAL_INTENT_TERMS for t in terms):
            best = {t: n for t, n in best.items() if t not in intent}
        seeds = _pick_seeds(qs.ranked, G=G, best_seed_by_term=best, term_order=qs.term_order) or []
        totals = {}
        for score, n in qs.ranked[:50]:
            f = src(n)
            if f:
                totals[f] = totals.get(f, 0.0) + score
        byfile = sorted(totals, key=lambda f: (-totals[f], f))
        norm = [t.lower() for t in terms]
        if not set(norm) & TEST_TERMS:
            byfile = [f for f in byfile if not _is_test_path(f)] or byfile
        r[name] = {"seeds": fill([src(n) for n in seeds], qs.ranked), "by file": fill(byfile, qs.ranked)}
    res[str(it["id"])] = r
json.dump(res, open(out, "w"))
print(f"{gp.split('/')[-3] if 'graphify-out' in gp else gp.split('/')[-2]}: {len(res)} questions", flush=True)
