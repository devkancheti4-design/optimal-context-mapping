"""PROTOCOL_VALUE7 runner: python run7.py <S | N | NS | judge>"""
import json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run as R1
import run2  # noqa: F401
import run3 as R3
from harness import V, H

Hn.CAP = 175.0
Q = json.load(open(f"{H}/questions_100.json")); QD = {q["qid"]: q for q in Q}
BASE = f"{V}/ws_v4_base"
STRICT = ("You read code for an engineering team. Answer the question from the code below only, completely, in one to three "
          "sentences. If the code below does not contain everything the question asks for, reply exactly NEED_SEARCH.")
VAR = {"S": (Hn.HAIKU, STRICT), "N": (Hn.SONNET, Hn.READ), "NS": (Hn.SONNET, STRICT)}
PORT = {"S": 7931, "N": 7932, "NS": 7933}


def md(question, url, reader, prompt):
    ws = Hn.WS(url, True)
    code = Hn.readout(ws.call, question)
    if code.startswith(Hn.TAUGHT):
        r = Hn.CLIENT.messages.create(model=reader, max_tokens=4000, system=prompt,
                                      messages=[{"role": "user", "content": f"Question: {question}\n\nCode:\n{code}"}])
        text = "".join(b.text for b in r.content if b.type == "text")
        if "NEED_SEARCH" not in text:
            return {"path": "read", "answer": text.strip(), "at": None}, ws.seen
    answer, at = R3.loop(Hn.TEACH, f"Question: {question}\n\nThe code the team's workspace ranked for it:\n{code}", url)
    if at:
        ws.call("teach", pairs=[{"question": question, "at": at}])
    return {"path": "teach", "answer": answer, "at": at}, ws.seen


def run(v):
    reader, prompt = VAR[v]; out = f"{V}/v7_{v}.jsonl"
    p, url = Hn.serve(BASE, f"{V}/ws_v7_{v}", PORT[v], fresh=not R1.resume(out))
    items = [{"id": q["qid"], "text": q["question"], "gold": None} for q in Q]
    try:
        done = Hn.done_ids(out)
        for it in items:
            if it["id"] not in done and not R1.STOP.is_set():
                R3.one(f"v7{v}", "modeld", it, lambda it: md(it["text"], url, reader, prompt), out)
    finally:
        p.terminate()


JSYS = ("You grade an engineer's answer about a codebase against the reference answer. Reply with exactly one word: RIGHT if "
        "the answer states the reference's key facts with no contradiction, PARTIAL if it states some of them and contradicts "
        "none, WRONG otherwise. End with a final line exactly: VERDICT: RIGHT, VERDICT: PARTIAL or VERDICT: WRONG.")


def judge():
    items = [{"key": f"{v}|{r['id']}", "qid": r["id"], "answer": r["answer"]} for v in VAR for r in (json.loads(l) for l in open(f"{V}/v7_{v}.jsonl"))]
    random.Random(20261012).shuffle(items)
    out = f"{V}/v7_judge.jsonl"; done = {json.loads(l)["key"] for l in open(out)} if os.path.exists(out) else set()

    def one(it):
        if it["key"] in done:
            return
        q = QD[it["qid"]]
        r = Hn.CLIENT.messages.create(model=Hn.SONNET, max_tokens=2000, system=JSYS, messages=[{"role": "user", "content":
            f"Question: {q['question']}\n\nReference answer: {q['answer']}\n\nAnswer to grade: {it['answer'] or '(no answer)'}"}])
        t = "".join(b.text for b in r.content if b.type == "text").strip()
        m = re.findall(r"VERDICT:\s*\**\s*(RIGHT|PARTIAL|WRONG)", t.upper())
        Hn.write(out, {"key": it["key"], "verdict": m[-1] if m else "UNPARSED", "reply": t[-400:]})
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(one, items))


if __name__ == "__main__":
    judge() if sys.argv[1] == "judge" else run(sys.argv[1])
    print(f"DONE {sys.argv[1]}: spend ${Hn.spent():.2f}", flush=True)
