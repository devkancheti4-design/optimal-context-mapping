"""PROTOCOL_VALUE4.md.addendum: blind judge of every V4 answer against the gold answer."""
import json, os, random, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
from harness import V, H
Hn.CAP = 175.0
Q = {q["qid"]: q for q in json.load(open(f"{H}/questions_100.json"))}
SYS = ("You grade an engineer's answer about a codebase against the reference answer. Reply with exactly one word: RIGHT if "
       "the answer states the reference's key facts with no contradiction, PARTIAL if it states some of them and contradicts "
       "none, WRONG otherwise. End with a final line exactly: VERDICT: RIGHT, VERDICT: PARTIAL or VERDICT: WRONG.")
items = []
for n in (1, 2, 3):
    for arm, f in (("alone", f"v4_r{n}_alone.jsonl"), ("modeld", f"v4_r{n}_md.jsonl")):
        for l in open(f"{V}/{f}"):
            r = json.loads(l)
            items.append({"key": f"{n}|{arm}|{r['id']}", "qid": r["id"], "answer": r["answer"]})
random.Random(20261011).shuffle(items)
out = f"{V}/v4_judge.jsonl"; done = {json.loads(l)["key"] for l in open(out)} if os.path.exists(out) else set()


def one(it):
    if it["key"] in done:
        return
    q = Q[it["qid"]]
    r = Hn.CLIENT.messages.create(model=Hn.SONNET, max_tokens=2000, system=SYS, messages=[{"role": "user", "content":
        f"Question: {q['question']}\n\nReference answer: {q['answer']}\n\nAnswer to grade: {it['answer'] or '(no answer)'}"}])
    t = "".join(b.text for b in r.content if b.type == "text").strip()
    import re
    m = re.findall(r"VERDICT:\s*\**\s*(RIGHT|PARTIAL|WRONG)", t.upper())
    v = m[-1] if m else "UNPARSED"
    Hn.write(out, {"key": it["key"], "verdict": v, "reply": t[-600:]})


with ThreadPoolExecutor(4) as ex:
    list(ex.map(one, items))
print("judged", sum(1 for _ in open(out)), "spend", round(Hn.spent(), 2))
