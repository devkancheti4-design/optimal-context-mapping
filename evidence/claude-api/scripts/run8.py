"""PROTOCOL_VALUE8 runner: the kit names the code; Claude writes the fix from it alone (no search).
    python run8.py <run | score>"""
import json, os, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run as R1
import run5 as W
from harness import V

Hn.CAP = 175.0
ARMS = {"KH": Hn.HAIKU, "KS": Hn.SONNET}
TOOLS8 = [t for t in W.TOOLS if t["name"] in ("read_file", "edit_file", "finish")]
SYS8 = ("You fix an issue in this repository (Django). The team's workspace has already found the code that matters for "
        "it; that code is below. Work from it: read_file reads more lines of a file the workspace named (no other files), "
        "and edit_file changes code in those files (exact string replacement: old_string must match the file exactly and "
        "occur once). There is no search. Change only the source code needed to resolve the issue; do not edit or add tests. "
        "When the fix is complete, call finish. At most 8 tool calls.")
MAX = 8


def named_files(readout):
    return sorted({p.split(":")[0].removeprefix("corpus/") for p in re.findall(r"(?m)^\d+\. \[([^\]]+)\]", readout)})


def gold_files(patch):
    return sorted(set(re.findall(r"^diff --git a/(\S+) b/", patch, re.M)))


def agent8(model, first, repo, allowed):
    messages, calls, n = [{"role": "user", "content": first}], 0, 0
    while n < MAX + 6:
        r = Hn.CLIENT.messages.create(model=model, max_tokens=16000, system=SYS8, tools=TOOLS8, messages=messages)
        n += 1
        if r.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": r.content}); continue
        uses = [b for b in r.content if b.type == "tool_use"]
        if not uses:
            return "".join(b.text for b in r.content if b.type == "text").strip()
        messages.append({"role": "assistant", "content": r.content}); results, done = [], None
        for u in uses:
            if u.name == "finish":
                done = u.input.get("summary", ""); results.append({"type": "tool_result", "tool_use_id": u.id, "content": "ok"}); continue
            calls += 1
            if calls > MAX:
                out = "Tool limit reached: call finish now."
            elif u.input.get("file") not in allowed:
                out = "Not one of the files the workspace named. Those are: " + ", ".join(allowed)
            else:
                out = repo.tool(u.name, u.input)
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": out})
        if done is not None:
            return done
        messages.append({"role": "user", "content": results})
    return ""


def run():
    p, url = Hn.serve(R1.WS_BASE, f"{V}/ws_v8", 7990)
    try:
        ro = {}
        for iid in W.ORDER:                                      # the kit's readout, cold, learning off: every bug novel
            ro[iid] = Hn.readout(Hn.WS(url, False).call, W.ISS[iid]["issue"])
        info = {iid: {"named": named_files(ro[iid]), "gold": gold_files(W.ISS[iid]["patch"])} for iid in W.ORDER}
        for v in info.values():
            v["hit"] = bool(set(v["named"]) & set(v["gold"]))
        json.dump(info, open(f"{V}/v8_readouts.json", "w"), indent=1)
        print(f"kit named a gold file on {sum(v['hit'] for v in info.values())} of {len(info)} bugs", flush=True)

        def one(job):
            arm, iid = job; out = f"{V}/v8_{arm}.jsonl"
            if iid in Hn.done_ids(out) or R1.STOP.is_set():
                return
            repo = W.Repo(W.workdir(iid, f"v8{arm}")); Hn.begin(); err = summary = None
            first = f"Issue:\n{W.ISS[iid]['issue']}\n\nThe code the team's workspace ranked for it:\n{ro[iid]}"
            try:
                summary = agent8(ARMS[arm], first, repo, info[iid]["named"])
            except Hn.Capped as e:
                err = str(e); R1.STOP.set()
            except Exception as e:
                err = f"{type(e).__name__}: {e}"[:300]
            diff = subprocess.run(["git", "diff"], cwd=repo.root, capture_output=True, text=True).stdout
            row = {"arm": arm, "id": iid, "edits": repo.edits, "patch": diff, "summary": (summary or "")[:300], "error": err,
                   "kit named gold": info[iid]["hit"]}
            row.update(Hn.summarise(Hn.took()))
            Hn.write(out, row)
            print(f"v8 {arm} {iid:<24} edits={len(repo.edits)} req={row['requests']} ${row['usd']:.4f} total ${Hn.spent():.2f}" + (f" ERR {err}" if err else ""), flush=True)
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(one, [(a, i) for i in W.ORDER for a in ARMS]))
    finally:
        p.terminate()


def score():
    for arm in ARMS:
        scored = f"{V}/v8_scored_{arm}.jsonl"; done = Hn.done_ids(scored)
        for r in [json.loads(l) for l in open(f"{V}/v8_{arm}.jsonl")]:
            if r["id"] in done:
                continue
            it = W.ISS[r["id"]]; tmp = f"{V}/wt/{r['id']}/score_v8{arm}"
            shutil.rmtree(tmp, ignore_errors=True); subprocess.run(["cp", "-cR", f"{V}/wt/{r['id']}/base", tmp], check=True)
            ok_model = (not r["patch"]) or W.P.apply(tmp, r["patch"])[0]
            tests = re.findall(r"^diff --git a/(\S+) b/", it["test_patch"], re.M)
            subprocess.run(["git", "checkout", "--", *[t for t in tests if os.path.exists(os.path.join(tmp, t))]], cwd=tmp, capture_output=True)
            ok_test = W.P.apply(tmp, it["test_patch"])[0]
            st, _ = W.P.run_tests(tmp, W.P.modules(it["test_patch"])) if (ok_model and ok_test and r["patch"]) else ({}, 1)
            resolved = bool(r["patch"]) and ok_model and ok_test and W.P.judge(st, it)
            shutil.rmtree(tmp, ignore_errors=True)
            Hn.write(scored, {"id": r["id"], "arm": arm, "resolved": resolved})
            print(f"score {arm} {r['id']:<24} resolved={resolved}", flush=True)


if __name__ == "__main__":
    {"run": run, "score": score}[sys.argv[1]]()
    print(f"DONE {sys.argv[1]}: spend ${Hn.spent():.2f}", flush=True)
