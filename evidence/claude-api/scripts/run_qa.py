"""PROTOCOL_SWEQA runner: SWE-QA (12 repositories x 48 questions), MODEL D (0.2.1 as shipped, learning on) against
Claude Sonnet alone with the same tools, both answers graded blind with SWE-QA's own judge rubric.
    python run_qa.py <run | stats>        (resumable: done ids are skipped)"""
import json, os, random, re, sys, threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
from harness import V, H

Q = f"{H}/sweqa"
REPOS = [l.split()[0].split("/")[1] for l in open(f"{Q}/shas.txt")]
ORDER = sorted(REPOS); random.Random(20261009).shuffle(ORDER)          # pre-registered repository order
BUDGET = 35.0                                                            # this program's own spend, dollars
BF = f"{V}/sweqa_budget.json"
if not os.path.exists(BF):
    json.dump({"start": Hn.spent(), "budget": BUDGET}, open(BF, "w"))
Hn.CAP = json.load(open(BF))["start"] + BUDGET
STOP = threading.Event()
JUDGE_SRC = open(f"{Q}/bench/Benchmark construction/score/llm-as-a-judge.py").read()
JUDGE = re.search(r'prompt = f"""(.*?)"""', JUDGE_SRC, re.S).group(1)   # SWE-QA's rubric, verbatim
DIMS = ("correctness", "completeness", "relevance", "clarity", "reasoning")


def items(repo):
    rows = [json.loads(l) for l in open(f"{Q}/bench/Benchmark/{repo}.jsonl")]
    return [{"id": f"{repo}-{k:02d}", "repo": repo, "question": r["question"], "reference": r["answer"]} for k, r in enumerate(rows, 1)]


def record(out, arm, it, res, err):
    row = {"id": it["id"], "repo": it["repo"], "arm": arm, "path": (res or {}).get("path"), "answer": (res or {}).get("answer") or "",
           "at": (res or {}).get("at"), "error": err}
    row.update(Hn.summarise(Hn.took()))
    Hn.write(out, row)
    print(f"qa {arm[:2].upper()} {it['id']:<18} {str(row['path']):<5} req={row['requests']:>2} ${row['usd']:.4f}  total ${Hn.spent():.2f}" + (f"  ERR {err}" if err else ""), flush=True)


def answer(arm, it, url, out):
    if STOP.is_set():
        return
    Hn.begin(); res = err = None
    try:
        if arm == "modeld":
            res, _ = Hn.modeld(it["question"], url)
        else:
            a, at = Hn.alone(it["question"], url); res = {"path": "alone", "answer": a, "at": at}
    except Hn.Capped as e:
        err = str(e); STOP.set()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:300]
    record(out, arm, it, res, err)


def judge_one(it, row, out):
    prompt = (JUDGE.replace("{question}", it["question"]).replace("{reference}", it["reference"])
              .replace("{candidate}", row["answer"] or "(no answer)").replace("{{", "{").replace("}}", "}"))
    Hn.begin(); scores = None; err = None
    try:
        r = Hn.CLIENT.messages.create(model=Hn.SONNET, max_tokens=400, messages=[{"role": "user", "content": prompt}])
        t = "".join(b.text for b in r.content if b.type == "text")
        m = re.search(r"\{[^{}]*\}", t, re.S)
        js = json.loads(m.group(0)) if m else {}
        if all(isinstance(js.get(d), int) for d in DIMS):
            scores = {d: js[d] for d in DIMS}
    except Hn.Capped as e:
        err = str(e); STOP.set()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:300]
    usd = sum(x["usd"] for x in Hn.took())
    Hn.write(out, {"key": f"{row['arm']}|{row['id']}", "id": row["id"], "arm": row["arm"], "scores": scores,
                   "total": sum(scores.values()) if scores else None, "usd": round(usd, 6), "error": err})


def rows_of(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def repo_cost(repo, paths):
    """What one repository cost: both arms' answers and their grading, from the records."""
    return sum(r["usd"] for p in paths for r in rows_of(p) if r["id"].rsplit("-", 1)[0] == repo)


def run():
    md_out, al_out, j_out = f"{V}/qa_md.jsonl", f"{V}/qa_alone.jsonl", f"{V}/qa_judge.jsonl"
    for n, repo in enumerate(ORDER):
        its = items(repo); ids = {i["id"] for i in its}
        before = Hn.spent()
        done_md, done_al = Hn.done_ids(md_out), Hn.done_ids(al_out)
        if not (ids <= done_md and ids <= done_al):
            est = max((repo_cost(r, (md_out, al_out, j_out)) for r in ORDER[:n]), default=0.0)
            if est and Hn.spent() + 1.15 * est > Hn.CAP:
                print(f"STOP before {repo}: ${Hn.spent():.2f} spent, a repository costs up to ${est:.2f}, cap ${Hn.CAP:.2f}", flush=True)
                break
            while not os.path.exists(f"{Q}/ws/{repo}/workspace.json"):   # its index may still be building
                threading.Event().wait(30)
            pm, um = Hn.serve(f"{Q}/ws/{repo}", f"{Q}/run/{repo}_md", 7960 + n, fresh=not (ids & done_md))
            pa, ua = Hn.serve(f"{Q}/ws/{repo}", f"{Q}/run/{repo}_alone", 7980 + n)
            try:
                t = threading.Thread(target=lambda: [answer("modeld", it, um, md_out) for it in its if it["id"] not in done_md])
                t.start()
                with ThreadPoolExecutor(3) as ex:
                    list(ex.map(lambda it: answer("alone", it, ua, al_out), [it for it in its if it["id"] not in done_al]))
                t.join()
            finally:
                pm.terminate(); pa.terminate()
        if STOP.is_set():
            break
        rows = [json.loads(l) for f in (md_out, al_out) for l in open(f)]
        rows = [r for r in rows if r["id"] in ids]
        judged = {json.loads(l)["key"] for l in open(j_out)} if os.path.exists(j_out) else set()
        todo = [r for r in rows if f"{r['arm']}|{r['id']}" not in judged]
        random.Random(20261012 + n).shuffle(todo)                       # blind: the judge never sees the arm
        byid = {i["id"]: i for i in its}
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(lambda r: None if STOP.is_set() else judge_one(byid[r["id"]], r, j_out), todo))
        print(f"REPO DONE {repo}: ${Hn.spent() - before:.2f} this repository, total ${Hn.spent():.2f}", flush=True)
        if STOP.is_set():
            break


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
    print(f"DONE {sys.argv[1]}: spend ${Hn.spent():.2f}", flush=True)
