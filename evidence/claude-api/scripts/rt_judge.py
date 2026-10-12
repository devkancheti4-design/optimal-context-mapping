"""PROTOCOL_RETEST R2: grade the finished pairs (both arms answered without error), blind and shuffled. $2 cap."""
import json, os, random, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run_qa as QA
from harness import V
Hn.CAP = Hn.spent() + 2.0
md = {r["id"]: r for r in map(json.loads, open(f"{V}/rt_qa_md.jsonl"))}
al = {r["id"]: r for r in map(json.loads, open(f"{V}/rt_qa_alone.jsonl"))}
ids = [i for i in md if not md[i]["error"] and i in al and not al[i]["error"]]
items = {it["id"]: it for repo in ("sqlfluff", "sphinx", "requests") for it in QA.items(repo)}
out = f"{V}/rt_qa_judge.jsonl"
done = {json.loads(l)["key"] for l in open(out)} if os.path.exists(out) else set()
todo = [r for i in ids for r in (md[i], al[i]) if f"{r['arm']}|{r['id']}" not in done]
random.Random(20261014).shuffle(todo)
with ThreadPoolExecutor(4) as ex:
    list(ex.map(lambda r: QA.judge_one(items[r["id"]], r, out), todo))
print("judged", len(todo), "spend", round(Hn.spent(), 2))
