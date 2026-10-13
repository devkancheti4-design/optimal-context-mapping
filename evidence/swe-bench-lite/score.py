"""Score both tools on SWE-bench Lite with the same rule: an issue counts when one of its fixed files exists in the
repo snapshot; hit@k = a fixed file is among the first k files the tool lists."""
import json, os, sys
from statistics import mean
L = os.path.dirname(os.path.abspath(__file__)); D = json.load(open(f"{L}/swebench_lite_by_repo.json"))
M = json.load(open(f"{L}/modeld_ranked.json")); G = json.load(open(f"{L}/" + (sys.argv[1] if len(sys.argv) > 1 else "graphify_ranked_087.json")))
rows = []; tot = {k: {"md": [0, 0, 0], "gf": [0, 0, 0], "n": 0, "mdc": [], "gfc": []} for k in ("query_title", "query_400")}
for slug, v in sorted(D.items(), key=lambda kv: -len(kv[1]["issues"])):
    if slug not in M or slug not in G: continue
    name = slug.split("/")[1]; repo = f"{L}/repos/{name}"
    issues = [it for it in v["issues"] if any(os.path.exists(os.path.join(repo, f)) for f in it["gold_files"])]
    line = {"repo": slug, "n": len(issues), "dropped": len(v["issues"]) - len(issues)}
    for key in ("query_title", "query_400"):
        for tool, R in (("md", M), ("gf", G)):
            hits = [sum(any(f in it["gold_files"] for f in R[slug][it["instance_id"]][key]["files"][:k]) for it in issues) for k in (1, 3, 5)]
            line[f"{tool}_{key}"] = hits
            for j in range(3): tot[key][tool][j] += hits[j]
            tot[key][f"{tool}c"] += [R[slug][it["instance_id"]][key]["chars"] / 4 for it in issues]
        tot[key]["n"] += len(issues)
    rows.append(line)
for key, label in (("query_title", "issue title"), ("query_400", "title + 400 characters")):
    print(f"\n#### Query: {label}\n\n| repo | issues | Model D top-1 / 3 / 5 | Graphify top-1 / 3 / 5 |\n|---|---|---|---|")
    for r in rows:
        print(f"| {r['repo']} | {r['n']} | {' / '.join(map(str, r['md_' + key]))} | {' / '.join(map(str, r['gf_' + key]))} |")
    t = tot[key]
    print(f"| **all** | **{t['n']}** | **{' / '.join(map(str, t['md']))}** | **{' / '.join(map(str, t['gf']))}** |")
    print(f"\ntokens handed to the model per issue: Model D {mean(t['mdc']):,.0f}, Graphify {mean(t['gfc']):,.0f}")
print("\nissues dropped (no fixed file in the snapshot):", {r["repo"]: r["dropped"] for r in rows if r["dropped"]})
