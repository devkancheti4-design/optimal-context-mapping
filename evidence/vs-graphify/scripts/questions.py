"""The question files: Django 2022 (the 288 kept fixes of PROTOCOL_TEAM_YEAR) and SWE-bench Lite (the 285 issues whose
fixed file exists in the repository snapshot, by repository)."""
import ast, json, os
TY = os.path.expanduser("~/neos/outreach/team-year"); LITE = os.path.expanduser("~/neos/outreach/graphify-seed-study/lite")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "questions"); os.makedirs(OUT, exist_ok=True)
keep = set(json.load(open(f"{TY}/keep.json")))
dj = [{"id": x["k"], "queries": {"q": f"Where is the code behind this change: {x['raw']}", "raw": x["raw"]}, "gold": x["gold"], "date": x["date"]}
      for x in json.load(open(f"{TY}/window_2022.json")) if x["k"] in keep]
json.dump(dj, open(f"{OUT}/django2022.json", "w"), indent=0)
D = json.load(open(f"{LITE}/swebench_lite_by_repo.json")); n = 0
for slug, v in sorted(D.items()):
    name = slug.split("/")[1]; repo = f"{LITE}/repos/{name}"
    items = []
    for it in v["issues"]:
        g = it["gold_files"]; gold = ast.literal_eval(g) if isinstance(g, str) else list(g)
        if any(os.path.exists(os.path.join(repo, f)) for f in gold):
            items.append({"id": it["instance_id"], "queries": {"title": it["query_title"], "q400": it["query_400"]}, "gold": gold})
    json.dump(items, open(f"{OUT}/lite_{name}.json", "w"), indent=0); n += len(items)
print(f"django 2022: {len(dj)}; lite: {n} issues in {len(D)} repositories")
