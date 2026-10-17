"""PROTOCOL_OSS_COMPREHENSION judge: blind, the PROTOCOL_VALUE4 rubric verbatim, Sonnet 5.5; both arms shuffled together.

    python comp_judge.py comp_questions.json "rows_md*.jsonl" "rows_alone*.jsonl" judged.jsonl --cap USD"""
import glob, json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import team_year as T  # noqa: E402
SYS = ("You grade an engineer's answer about a codebase against the reference answer. Reply with exactly one word: RIGHT if "
       "the answer states the reference's key facts with no contradiction, PARTIAL if it states some of them and contradicts "
       "none, WRONG otherwise. End with a final line exactly: VERDICT: RIGHT, VERDICT: PARTIAL or VERDICT: WRONG.")
qf, md_g, al_g, out, cap = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[6])
Q = {q["k"]: q for q in json.load(open(qf))}
items = [{"key": f"{arm}|{r['k']}", "k": r["k"], "answer": r["answer"]} for arm, g in (("md", md_g), ("alone", al_g))
         for f in sorted(glob.glob(g)) for r in map(json.loads, open(f))]
random.Random(20261017).shuffle(items)
done = {json.loads(l)["key"] for l in open(out)} if os.path.exists(out) else set()
prov = T.Claude(); meter = T.Meter(prov.client)
def one(it):
    if it["key"] in done or meter.usd >= cap: return
    q = Q[it["k"]]
    r = prov.client.messages.create(model="claude-sonnet-5-5", max_tokens=2000, system=SYS, messages=[{"role": "user", "content":
        f"Question: {q['question']}\n\nReference answer: {q['gold']}\n\nAnswer to grade: {it['answer'] or '(no answer)'}"}])
    t = "".join(b.text for b in r.content if b.type == "text").strip()
    m = re.findall(r"VERDICT:\s*\**\s*(RIGHT|PARTIAL|WRONG)", t.upper())
    with open(out, "a") as f: f.write(json.dumps({"key": it["key"], "verdict": m[-1] if m else "UNPARSED", "reply": t[-400:]}) + "\n")
with ThreadPoolExecutor(4) as ex: list(ex.map(one, items))
print(f"judged {sum(1 for _ in open(out))} | judge spend ${meter.usd:.3f}")
