"""PROTOCOL_SWECB runner: SWE-ContextBench Lite, its Django related tasks that validate locally. Three arms write the
fix with the same tools (V5's): ALONE (no kit), COLD (the kit's readout, nothing taught) and EXP (the kit's readout
after it was taught the experience pool). Scored by Django's own tests.
    python run_cb.py <run | score>        (resumable)"""
import json, os, re, shutil, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run5 as W
from harness import V, H

sys.path.insert(0, f"{H}/swecb")
import cb_prep as P
from ocm.server import Workspace

C = f"{H}/swecb"
BUDGET = 15.0
BF = f"{V}/swecb_budget.json"
if not os.path.exists(BF):
    json.dump({"start": Hn.spent(), "budget": BUDGET}, open(BF, "w"))
Hn.CAP = json.load(open(BF))["start"] + BUDGET
STOP = threading.Event()
EVAL = json.load(open(f"{C}/cb_eval.json"))
ITEMS = [it for it in P.REL if EVAL.get(it["id"], {}).get("keep")]            # chronological
BY = {it["id"]: it for it in ITEMS}
ARMS = ("exp", "alone", "cold")
_kit = threading.Lock()


def readout(iid, arm, issue):
    with _kit:                                       # one embedding at a time
        w = Workspace(f"{C}/ws/{iid}_{arm}")
        return Hn.readout(lambda path, **kw: w.handle(path, kw), issue)


def workdir(iid, arm):
    wd = f"{C}/wt/{iid}/{arm}"
    shutil.rmtree(wd, ignore_errors=True)
    subprocess.run(["cp", "-cR", f"{C}/wt/{iid}/base", wd], check=True)
    return wd


def one(job):
    iid, arm = job; out = f"{V}/cb_{arm}.jsonl"
    if STOP.is_set() or iid in Hn.done_ids(out):
        return
    while not any(l.startswith(iid + " {") for l in open(f"{C}/build.log")):     # cb_prep logs a task once its kits are ready
        threading.Event().wait(30)                   # its kit may still be building
    it = BY[iid]; repo = W.Repo(workdir(iid, arm)); Hn.begin(); err = summary = None; code = ""
    try:
        if arm == "alone":
            summary = W.agent(W.SYS, f"Issue:\n{it['issue']}", repo)
        else:
            code = readout(iid, arm, it["issue"])
            summary = W.agent(W.SYS_D, f"Issue:\n{it['issue']}\n\nThe code the team's workspace ranked for it:\n{code}", repo)
    except Hn.Capped as e:
        err = str(e); STOP.set()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:300]
    diff = subprocess.run(["git", "diff"], cwd=repo.root, capture_output=True, text=True).stdout
    named = sorted({p.split(":")[0] for p in re.findall(r"(?m)^\d+\. \[([^\]]+)\]", code)})
    gold = sorted(set(re.findall(r"^diff --git a/(\S+) b/", it["patch"], re.M)))
    row = {"arm": arm, "id": iid, "edits": repo.edits, "patch": diff, "summary": (summary or "")[:300], "error": err,
           "learned": code.startswith(Hn.TAUGHT), "named gold": bool(set(named) & set(gold)), "readout": code[:600]}
    row.update(Hn.summarise(Hn.took()))
    Hn.write(out, row)
    print(f"cb {arm:<5} {iid:<22} learned={row['learned']!s:<5} gold={row['named gold']!s:<5} edits={len(repo.edits)} req={row['requests']:>2} ${row['usd']:.4f} total ${Hn.spent():.2f}" + (f" ERR {err}" if err else ""), flush=True)
    shutil.rmtree(repo.root, ignore_errors=True)


def run():
    jobs = [(it["id"], a) for it in ITEMS for a in ARMS]
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, jobs))


def score():
    for arm in ARMS:
        scored = f"{V}/cb_scored_{arm}.jsonl"; done = Hn.done_ids(scored)
        for r in [json.loads(l) for l in open(f"{V}/cb_{arm}.jsonl")]:
            if r["id"] in done or r["error"]:
                continue
            it = BY[r["id"]]; tmp = f"{C}/wt/{r['id']}/score_{arm}"
            shutil.rmtree(tmp, ignore_errors=True); subprocess.run(["cp", "-cR", f"{C}/wt/{r['id']}/base", tmp], check=True)
            ok_model = bool(r["patch"]) and P.apply(tmp, r["patch"])
            tests = re.findall(r"^diff --git a/(\S+) b/", it["test_patch"], re.M)
            subprocess.run(["git", "checkout", "--", *[t for t in tests if os.path.exists(os.path.join(tmp, t))]], cwd=tmp, capture_output=True)
            ok_test = P.apply(tmp, it["test_patch"])
            st = P.run_tests(tmp, P.modules(it["test_patch"]), P.py_for(it["version"])) if (ok_model and ok_test) else {}
            res = ok_model and ok_test and P.resolved(st, it)
            shutil.rmtree(tmp, ignore_errors=True)
            Hn.write(scored, {"id": r["id"], "arm": arm, "resolved": res})
            print(f"score {arm:<5} {r['id']:<22} resolved={res}", flush=True)


if __name__ == "__main__":
    {"run": run, "score": score}[sys.argv[1]]()
    print(f"DONE {sys.argv[1]}: spend ${Hn.spent():.2f}", flush=True)
