"""PROTOCOL_MODEL_D_E2E.md: Model D end to end on gemini-2.5-flash (Vertex). The kit decides every path; the eyes read
once; the body works only what is new to the kit, and what it learns is taught back.

    ~/.venvs/cmlm-live/bin/python model_d_e2e.py [runs=3]      -> e2e/qa_r<k>/, e2e/bugs_r<k>/"""
import json, os, shutil, sys, threading, time, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
H = Path(os.path.dirname(os.path.abspath(__file__))); B = H.parent
for p in (B / "api", B / "fix", B / "reports", Path(os.path.expanduser("~/optimal-context-mapping"))):
    sys.path.insert(0, str(p))
sys.argv = sys.argv[:2]
import api_bench as AB
import agent_fix as AF
from common import usd

TAUGHT = "(readout: the code a taught question"
EYES_Q = ("You answer questions about the Hugging Face transformers codebase. Answer the question from the code below only, "
          "in one short sentence. If the code below does not contain the answer, reply exactly NEED_SEARCH.")


def eyes(run, item, ro, out):
    body = {"systemInstruction": {"parts": [{"text": EYES_Q}]},
            "contents": [{"role": "user", "parts": [{"text": f"Question: {item['question']}\n\nCode:\n{ro}"}]}]}
    r, dt, tries = AB.call(body, AB.url_for(run))
    u = r.get("usageMetadata", {}); parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    text = " ".join(p.get("text", "") for p in parts).strip()
    out["requests"].write(json.dumps({"path": "eyes", "run": run, "qid": item["qid"], "seconds": round(dt, 3), "retries": tries,
                                      "prompt": u.get("promptTokenCount", 0), "cached": u.get("cachedContentTokenCount", 0),
                                      "output": u.get("candidatesTokenCount", 0), "thoughts": u.get("thoughtsTokenCount", 0)}) + "\n"); out["requests"].flush()
    return text


def qa_chain(run):
    d = H / "e2e" / f"qa_r{run}"
    if d.exists(): shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copytree(B / "large/ws_L_base", d / "ws"); hook = AB.Hook(str(d / "ws"))
    out = {k: open(d / f"{k}.jsonl", "a") for k in ("requests", "answers", "readouts", "decisions")}
    for item in AB.STREAM:
        t0 = time.time()
        ro = hook.readout(item["question"])
        path = "body"
        if ro.startswith(TAUGHT):                                    # the kit decides: it knows this code
            text = eyes(run, item, ro, out)
            if "NEED_SEARCH" not in text:
                path = "eyes"
                out["answers"].write(json.dumps({"qid": item["qid"], "answer": f"ANSWER: {text} | SOURCE: (the kit's readout)", "path": "eyes",
                                                 "seconds": round(time.time() - t0, 2)}) + "\n"); out["answers"].flush()
            else:
                path = "eyes -> body"
        if path != "eyes":                                           # new to the kit: the body works it, and the kit learns it
            AB.session("cmlm", run, 0, hook, out, items=[item])
        out["decisions"].write(json.dumps({"qid": item["qid"], "taught lane": ro.startswith(TAUGHT), "path": path, "seconds": round(time.time() - t0, 2)}) + "\n")
        out["decisions"].flush()
        print("qa", run, item["qid"], path, flush=True)
    shutil.rmtree(d / "ws")


def bugs_chain(run):
    d = H / "e2e" / f"bugs_r{run}"
    if d.exists(): shutil.rmtree(d)
    d.mkdir(parents=True)
    work = d / "qb"; shutil.copytree(AF.QBSRC, work, ignore=shutil.ignore_patterns(".git", "java_*", "correct_java_programs", "*.class"))
    out = open(d / "requests.jsonl", "a"); res = open(d / "results.jsonl", "a")
    for name in AF.PROGRAMS:
        row = AF.ROWS[name]; o = row.get("outcome")
        if o == "not red": continue
        t0 = time.time()
        if o in ("repaired", "ambiguous"):                           # the kit decides: its first verified candidate in law order
            g = row["greens"][0]; prog = (work / "python_programs" / f"{name}.py").read_text()
            lines = prog.split("\n"); ind = lines[g["line"] - 1][:len(lines[g["line"] - 1]) - len(lines[g["line"] - 1].lstrip())]
            lines[g["line"] - 1] = ind + g["after"]; fixed = AF.tests(work, name, "\n".join(lines))[0]
            if fixed:
                res.write(json.dumps({"program": name, "path": "kit", "requests": 0, "fixed": True, "seconds": round(time.time() - t0, 1), "neo4d": o}) + "\n"); res.flush()
                print("bugs", run, name, "kit", flush=True); continue
        r = AF.session("neo4d", run, name, work, out); r["path"] = "body"
        res.write(json.dumps(r) + "\n"); res.flush()
        print("bugs", run, name, "body", r["requests"], r["fixed"], flush=True)
    shutil.rmtree(work)


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    th = [threading.Thread(target=f, args=(k,)) for k in range(1, runs + 1) for f in (qa_chain, bugs_chain)]
    for x in th: x.start()
    for x in th: x.join()
    print("all chains done")


if __name__ == "__main__":
    main()
