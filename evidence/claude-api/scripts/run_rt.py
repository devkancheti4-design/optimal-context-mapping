"""PROTOCOL_RETEST runner: SWE-ContextBench and SWE-QA again, with prompt caching on every request and (SWE-QA) the
same answer standard for both arms.   python run_rt.py <cb | cbscore | qa | stats>"""
import json, os, random, re, shutil, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
from statistics import mean

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
from harness import V, H

MODE = sys.argv[1]


def cached(client):
    """Automatic prompt caching on every request (top-level cache_control)."""
    orig = client.messages.create
    client.messages.create = lambda **kw: orig(**{"cache_control": {"type": "ephemeral"}, **kw})


cached(Hn.CLIENT); cached(Hn.MD.client)


def budget(name, usd):
    bf = f"{V}/rt_{name}_budget.json"
    if not os.path.exists(bf):
        json.dump({"start": Hn.spent(), "budget": usd}, open(bf, "w"))
    Hn.CAP = json.load(open(bf))["start"] + usd


STOP = threading.Event()

# ---------- R1: SWE-ContextBench, ALONE and COLD ----------
if MODE in ("cb", "cbscore"):
    import run5 as W
    sys.path.insert(0, f"{H}/swecb")
    import cb_prep as P
    from ocm.server import Workspace
    C = f"{H}/swecb"
    EVAL = json.load(open(f"{C}/cb_eval.json"))
    ITEMS = [it for it in P.REL if EVAL.get(it["id"], {}).get("keep")]
    BY = {it["id"]: it for it in ITEMS}
    _kit = threading.Lock()


def cb_one(job):
    iid, arm = job; out = f"{V}/rt_cb_{arm}.jsonl"
    if STOP.is_set() or iid in Hn.done_ids(out):
        return
    it = BY[iid]; wd = f"{C}/wt/{iid}/rt_{arm}"
    shutil.rmtree(wd, ignore_errors=True); subprocess.run(["cp", "-cR", f"{C}/wt/{iid}/base", wd], check=True)
    repo = W.Repo(wd); Hn.begin(); err = None; code = ""
    try:
        if arm == "alone":
            W.agent(W.SYS, f"Issue:\n{it['issue']}", repo)
        else:
            with _kit:
                w = Workspace(f"{C}/ws/{iid}_cold")
                code = Hn.readout(lambda path, **kw: w.handle(path, kw), it["issue"])
            W.agent(W.SYS_D, f"Issue:\n{it['issue']}\n\nThe code the team's workspace ranked for it:\n{code}", repo)
    except Hn.Capped as e:
        err = str(e); STOP.set()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:300]
    diff = subprocess.run(["git", "diff"], cwd=wd, capture_output=True, text=True).stdout
    row = {"arm": arm, "id": iid, "edits": repo.edits, "patch": diff, "error": err}
    row.update(Hn.summarise(Hn.took()))
    row["cache read"] = sum(x["read"] for x in Hn.took()); row["cache write"] = sum(x["write"] for x in Hn.took())
    Hn.write(out, row)
    print(f"rt cb {arm:<5} {iid:<22} edits={len(repo.edits)} req={row['requests']:>2} ${row['usd']:.4f} total ${Hn.spent():.2f}" + (f" ERR {err}" if err else ""), flush=True)
    shutil.rmtree(wd, ignore_errors=True)


def cb():
    budget("cb", 5.0)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(cb_one, [(it["id"], a) for it in ITEMS for a in ("alone", "cold")]))


def cbscore():
    def sc(args):
        arm, r = args; it = BY[r["id"]]; tmp = f"{C}/wt/{r['id']}/rtscore_{arm}"
        shutil.rmtree(tmp, ignore_errors=True); subprocess.run(["cp", "-cR", f"{C}/wt/{r['id']}/base", tmp], check=True)
        ok_m = bool(r["patch"]) and P.apply(tmp, r["patch"]); ok_t = P.apply(tmp, it["test_patch"])
        st = P.run_tests(tmp, P.modules(it["test_patch"]), P.py_for(it["version"])) if (ok_m and ok_t) else {}
        res = ok_m and ok_t and P.resolved(st, it)
        shutil.rmtree(tmp, ignore_errors=True)
        Hn.write(f"{V}/rt_cb_scored_{arm}.jsonl", {"id": r["id"], "arm": arm, "resolved": res})
        print(f"rt score {arm:<5} {r['id']:<22} resolved={res}", flush=True)
    jobs = []
    for arm in ("alone", "cold"):
        done = Hn.done_ids(f"{V}/rt_cb_scored_{arm}.jsonl")
        jobs += [(arm, r) for r in map(json.loads, open(f"{V}/rt_cb_{arm}.jsonl")) if r["id"] not in done and not r["error"]]
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(sc, jobs))


# ---------- R2: SWE-QA, same answer standard ----------
COMPLETE = " Answer completely: name the files, classes and functions involved and explain how they work."
READER = ("You read code for an engineering team. Answer the question from the code below only, completely: name the files, "
          "classes and functions involved and explain how they work. If the code below does not contain everything the "
          "question asks for, reply exactly NEED_SEARCH.")
QA_REPOS = ["sqlfluff", "sphinx", "requests"]


def qa_md(question, url):
    ws = Hn.WS(url, True)
    code = Hn.readout(ws.call, question)
    if code.startswith(Hn.TAUGHT):
        r = Hn.CLIENT.messages.create(model=Hn.HAIKU, max_tokens=4000, system=READER,
                                      messages=[{"role": "user", "content": f"Question: {question}\n\nCode:\n{code}"}])
        text = "".join(b.text for b in r.content if b.type == "text")
        if "NEED_SEARCH" not in text:
            return {"path": "read", "answer": text.strip(), "at": None}
    answer, at = Hn._loop(Hn.TEACH + COMPLETE, f"Question: {question}\n\nThe code the team's workspace ranked for it:\n{code}", url)
    if at:
        ws.call("teach", pairs=[{"question": question, "at": at}])
    return {"path": "teach", "answer": answer, "at": at}


def qa_answer(arm, it, url, out):
    if STOP.is_set():
        return
    Hn.begin(); res = err = None
    try:
        if arm == "modeld":
            res = qa_md(it["question"], url)
        else:
            a, at = Hn._loop(Hn.ALONE_SYS + COMPLETE, f"Question: {it['question']}", url); res = {"path": "alone", "answer": a, "at": at}
    except Hn.Capped as e:
        err = str(e); STOP.set()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:300]
    row = {"id": it["id"], "repo": it["repo"], "arm": arm, "path": (res or {}).get("path"), "answer": (res or {}).get("answer") or "", "error": err}
    row.update(Hn.summarise(Hn.took()))
    Hn.write(out, row)
    print(f"rt qa {arm[:2].upper()} {it['id']:<16} {str(row['path']):<5} req={row['requests']:>2} ${row['usd']:.4f}  total ${Hn.spent():.2f}" + (f"  ERR {err}" if err else ""), flush=True)


def qa():
    import run_qa as QA
    budget("qa", 8.0)
    md_out, al_out, j_out = f"{V}/rt_qa_md.jsonl", f"{V}/rt_qa_alone.jsonl", f"{V}/rt_qa_judge.jsonl"

    def repo_run(n, repo):
        its = QA.items(repo); dm, da = Hn.done_ids(md_out), Hn.done_ids(al_out)
        pm, um = Hn.serve(f"{H}/sweqa/ws/{repo}", f"{H}/sweqa/run/rt_{repo}_md", 7940 + n, fresh=not ({i["id"] for i in its} & dm))
        pa, ua = Hn.serve(f"{H}/sweqa/ws/{repo}", f"{H}/sweqa/run/rt_{repo}_alone", 7950 + n)
        try:
            t = threading.Thread(target=lambda: [qa_answer("modeld", it, um, md_out) for it in its if it["id"] not in dm])
            t.start()
            with ThreadPoolExecutor(2) as ex:
                list(ex.map(lambda it: qa_answer("alone", it, ua, al_out), [it for it in its if it["id"] not in da]))
            t.join()
        finally:
            pm.terminate(); pa.terminate()
        rows = [json.loads(l) for f in (md_out, al_out) for l in open(f)]
        ids = {i["id"] for i in its}; byid = {i["id"]: i for i in its}
        judged = {json.loads(l)["key"] for l in open(j_out)} if os.path.exists(j_out) else set()
        todo = [r for r in rows if r["id"] in ids and f"{r['arm']}|{r['id']}" not in judged]
        random.Random(20261013 + n).shuffle(todo)
        with ThreadPoolExecutor(3) as ex:
            list(ex.map(lambda r: None if STOP.is_set() else QA.judge_one(byid[r["id"]], r, j_out), todo))
        print(f"RT REPO DONE {repo}", flush=True)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda a: repo_run(*a), list(enumerate(QA_REPOS))))


def stats():
    out = {}
    if os.path.exists(f"{V}/rt_cb_scored_cold.jsonl"):
        run = {a: {r["id"]: r for r in map(json.loads, open(f"{V}/rt_cb_{a}.jsonl"))} for a in ("alone", "cold")}
        sc = {a: {r["id"]: r["resolved"] for r in map(json.loads, open(f"{V}/rt_cb_scored_{a}.jsonl"))} for a in ("alone", "cold")}
        ids = sorted(set(sc["alone"]) & set(sc["cold"]))
        out["R1 swe-contextbench"] = {a: {"resolved": sum(sc[a][i] for i in ids), "of": len(ids),
                                          "$ per task": round(mean(run[a][i]["usd"] for i in ids), 4),
                                          "requests per task": round(mean(run[a][i]["requests"] for i in ids), 2),
                                          "cache read tokens per task": round(mean(run[a][i]["cache read"] for i in ids))} for a in ("alone", "cold")}
    if os.path.exists(f"{V}/rt_qa_judge.jsonl"):
        md = {r["id"]: r for r in map(json.loads, open(f"{V}/rt_qa_md.jsonl"))}; al = {r["id"]: r for r in map(json.loads, open(f"{V}/rt_qa_alone.jsonl"))}
        jd = {j["key"]: j for j in map(json.loads, open(f"{V}/rt_qa_judge.jsonl"))}
        P2 = [(i, al[i]["usd"], md[i]["usd"], jd[f"alone|{i}"]["total"], jd[f"modeld|{i}"]["total"]) for i in md
              if i in al and jd.get(f"alone|{i}", {}).get("total") is not None and jd.get(f"modeld|{i}", {}).get("total") is not None]
        rng = random.Random(20261008); diffs = []
        for _ in range(20000):
            s = [P2[rng.randrange(len(P2))] for _ in P2]; diffs.append(mean(x[4] - x[3] for x in s))
        diffs.sort()
        out["R2 swe-qa"] = {"questions": len(P2), "alone $ per question": round(mean(x[1] for x in P2), 5),
                            "model d $ per question": round(mean(x[2] for x in P2), 5),
                            "cost ratio": round(sum(x[1] for x in P2) / sum(x[2] for x in P2), 3),
                            "alone score": round(mean(x[3] for x in P2), 2), "model d score": round(mean(x[4] for x in P2), 2),
                            "difference": round(mean(x[4] - x[3] for x in P2), 2), "difference 95% CI": [round(diffs[500], 2), round(diffs[19499], 2)],
                            "model d answers from the reader": sum(md[x[0]]["path"] == "read" for x in P2),
                            "answer chars alone / model d": [round(mean(len(al[x[0]]["answer"]) for x in P2)), round(mean(len(md[x[0]]["answer"]) for x in P2))]}
    json.dump(out, open(f"{V}/report_retest.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"cb": cb, "cbscore": cbscore, "qa": qa, "stats": stats}[MODE]()
    print(f"DONE {MODE}: spend ${Hn.spent():.2f}", flush=True)
