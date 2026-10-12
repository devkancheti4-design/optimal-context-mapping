"""PROTOCOL_API.md: the kit through a raw model API. Vertex AI gemini-2.5-flash, billed to project cmlm-bench.
CMLM and ALONE arms, 3 runs x 6 tasks of 10 questions over transformers (10.8M tokens). Every request and its billed
usage is logged.

    ~/.venvs/cmlm-live/bin/python api_bench.py run [runs=3]     -> runs/<arm>_r<k>/{requests,answers,readouts}.jsonl
    ~/.venvs/cmlm-live/bin/python api_bench.py smoke             -> one ALONE question, to check the wiring"""
import json, os, shutil, subprocess, sys, threading, time, urllib.error, urllib.request, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
A = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(A); L = f"{B}/large"
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping")); sys.path.insert(0, L)
import tools                                                      # large/tools.py: the kit's /search, /read, /list formats

PROJECT, LOCATION, MODEL = "cmlm-bench", "global", os.environ.get("API_MODEL", "gemini-2.5-flash")
REGIONS = {0: "us-east4", 1: "us-east4", 2: "europe-west4", 3: "us-east1"}     # D1: the global endpoint was out of shared capacity
url_for = lambda run: f"https://{REGIONS[run]}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGIONS[run]}/publishers/google/models/{MODEL}:generateContent"
QS = json.load(open(os.path.expanduser("~/cmlm-bench5/questions.json")))
STREAM = [{"qid": q["qid"], "question": q["question"]} for q in QS] + [{"qid": q["qid"] + "b", "question": q["question2"]} for q in QS]
MAX_CALLS, MAX_REQ = 15, 250
import re as _re
NON_ANSWER = _re.compile(r"waiting for|awaiting|no (new )?question|provide the (next )?question|have not (been )?(given|provided)", _re.I)
LOCK = threading.Lock(); TOKEN = {"t": None, "at": 0}

INTRO = ("You are an engineer working on the Hugging Face transformers library (its Python source: models, tokenizers, "
         "feature extractors, pipelines, generation and utilities). In this session you will answer 10 questions about this "
         "codebase, one at a time. Answer each from the code, not from general knowledge of transformers. Do not guess: if "
         "you cannot find an answer, say not found.\n\n")
TOOLS_TXT = ("Tools for researching each question: search (case-insensitive regular expression over every line of every file; at "
             "most 40 matching lines as file:line: text, and the total count), read_file (lines of one file, at most 200 per "
             "call) and list_files (the files under a folder prefix, e.g. 'corpus/models/bert'; '' for all). File paths start "
             "with corpus/. At most 15 tool calls per question.")
SYSTEM = {
    "alone": INTRO + "When you have the answer to the current question, call submit_answer; it records it and gives you the "
             "next question. Keep going until it says DONE.\n\n" + TOOLS_TXT,
    "cmlm": INTRO + "When you have the answer to the current question, call submit_answer with the answer, its source files, and "
            "a TEACH pair: teach_question (the question) and teach_at (the one line your answer is on, as <path>:<line>, for "
            "example corpus/models/bert/modeling_bert.py:120). It records the answer, teaches the team's workspace and gives you "
            "the next question. Keep going until it says DONE. Each question comes with the code and docs the team workspace "
            "ranked for it before it reached you (there is nothing to call): if they answer it, answer from them without "
            "searching; if not, search.\n\n" + TOOLS_TXT}


def fdecl(arm):
    sub = {"answer": {"type": "string", "description": "the answer, short"}, "source": {"type": "string", "description": "the files it came from"}}
    req = ["answer", "source"]
    if arm == "cmlm":
        sub.update({"teach_question": {"type": "string"}, "teach_at": {"type": "string", "description": "<path>:<line>"}}); req += ["teach_question", "teach_at"]
    return [{"functionDeclarations": [
        {"name": "search", "description": "case-insensitive regex search over every line of every file",
         "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
        {"name": "read_file", "description": "read lines of one file (at most 200 per call)",
         "parameters": {"type": "object", "properties": {"file": {"type": "string"}, "start_line": {"type": "integer"}, "num_lines": {"type": "integer"}}, "required": ["file", "start_line"]}},
        {"name": "list_files", "description": "list the files under a folder prefix",
         "parameters": {"type": "object", "properties": {"prefix": {"type": "string"}}}},
        {"name": "submit_answer", "description": "record the answer to the current question and get the next one",
         "parameters": {"type": "object", "properties": sub, "required": req}}]}]


def token(force=False):
    with LOCK:
        if force or time.time() - TOKEN["at"] > 300:                      # D4: gcloud can hand out a nearly expired token
            TOKEN["t"] = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip(); TOKEN["at"] = time.time()
        return TOKEN["t"]


POOL = ["us-east1", "us-west1", "asia-northeast1", "europe-west1", "us-south1", "northamerica-northeast1", "us-east4"]
_rot = {"i": 0}


def call(body, url):
    """D3: on 429, 5xx or a dropped connection, move to the next region in POOL (the same model) and retry; never give up.
    Returns (response, seconds, attempts, region)."""
    r0 = url.split("//")[1].split("-aiplatform")[0]
    region = r0
    for attempt in range(400):
        u = url.replace(f"//{r0}-aiplatform", f"//{region}-aiplatform").replace(f"locations/{r0}/", f"locations/{region}/")
        req = urllib.request.Request(u, data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read()), time.time() - t0, attempt
        except urllib.error.HTTPError as e:
            msg = e.read()[:300]
            if e.code == 401:
                token(force=True); continue                                   # D4: refresh and retry on an expired token
            if e.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {e.code}: {msg}")
        except (TimeoutError, urllib.error.URLError, ConnectionError, OSError):
            pass
        with LOCK:
            _rot["i"] += 1
            region = POOL[_rot["i"] % len(POOL)]
        time.sleep(min(30, 2 + attempt))
    raise RuntimeError("no region answered in 400 attempts")


def run_tool(name, args):
    try:
        if name == "search": return tools.search(str(args.get("pattern", "")))
        if name == "read_file": return tools.read(args.get("file", ""), int(args.get("start_line") or 1), int(args.get("num_lines") or 80))
        if name == "list_files": return tools.listing(args.get("prefix", "") or "")
    except Exception as e:
        return f"error: {e}"
    return f"unknown tool {name}"


class Hook:
    """The CMLM arm's workspace, resident in this process: readout before each question, TEACH after each answer."""
    def __init__(self, ws):
        from ocm.server import Workspace
        self.w = Workspace(ws)

    def readout(self, question):
        from ocm.loop import readout
        with LOCK:
            return readout(lambda path, **kw: self.w.handle(path, kw), question)

    def teach(self, q, at):
        with LOCK:
            return self.w.handle("teach", {"pairs": [{"question": q, "at": at}]})


def present(arm, hook, item, k, n, out):
    text = f"Question {item['qid']} ({k} of {n}): {item['question']}"
    if arm == "cmlm":
        from ocm.loop import HEADER, RULE
        t0 = time.time(); ro = hook.readout(item["question"]); dt = time.time() - t0
        out["readouts"].write(json.dumps({"qid": item["qid"], "readout": ro, "seconds": round(dt, 3)}) + "\n"); out["readouts"].flush()
        text = text + "\n\n" + HEADER + "\n\n" + ro + "\n\n" + RULE          # D5: the question first, the ranked code after
    return text


def session(arm, run, t, hook, out, items=None):
    items = items or STREAM[(t - 1) * 10:t * 10]; i = 0; calls = 0; t_q = time.time()
    contents = [{"role": "user", "parts": [{"text": present(arm, hook, items[0], 1, len(items), out)}]}]
    nreq = 0; nudges = 0; qnudge = 0
    while nreq < MAX_REQ:
        force = calls >= MAX_CALLS or qnudge >= 3                                # D2: the 15-call limit, enforced by the API's function-calling mode
        fcc = {"mode": "ANY", "allowedFunctionNames": ["submit_answer"]} if force else {"mode": "AUTO"}
        sysmsg = SYSTEM[arm] if len(items) > 1 else SYSTEM[arm].replace("10 questions about this codebase, one at a time", "one question about this codebase").replace("; it records it and gives you the next question. Keep going until it says DONE.", "; it records it and ends the session.").replace("It records the answer, teaches the team's workspace and gives you the next question. Keep going until it says DONE.", "It records the answer and teaches the team's workspace, and ends the session.")
        body = {"systemInstruction": {"parts": [{"text": sysmsg}]}, "contents": contents, "tools": fdecl(arm),
                "toolConfig": {"functionCallingConfig": fcc}}
        resp, dt, retries = call(body, url_for(run)); nreq += 1
        u = resp.get("usageMetadata", {}); cand = (resp.get("candidates") or [{}])[0]
        parts = (cand.get("content") or {}).get("parts") or []
        qid = items[i]["qid"] if i < len(items) else None
        out["requests"].write(json.dumps({"arm": arm, "run": run, "task": t, "qid": qid, "seconds": round(dt, 3), "retries": retries,
                                          "prompt": u.get("promptTokenCount", 0), "cached": u.get("cachedContentTokenCount", 0),
                                          "output": u.get("candidatesTokenCount", 0), "thoughts": u.get("thoughtsTokenCount", 0),
                                          "finish": cand.get("finishReason"), "forced": force,
                                          "calls": [[p["functionCall"].get("name"), json.dumps(p["functionCall"].get("args"))[:160]] for p in parts if "functionCall" in p]}) + "\n"); out["requests"].flush()
        contents.append({"role": "model", "parts": parts or [{"text": ""}]})
        fcs = [p["functionCall"] for p in parts if "functionCall" in p]
        if not fcs:
            nudges += 1; qnudge += 1
            contents.append({"role": "user", "parts": [{"text": "Use the tools; when you have the answer, call submit_answer."}]}); continue
        responses = []; done = False
        for fc in fcs:
            name, args = fc.get("name"), fc.get("args") or {}
            if done:
                responses.append({"functionResponse": {"name": name, "response": {"content": "DONE: all questions are answered."}}}); continue
            if name == "submit_answer" and NON_ANSWER.search(str(args.get("answer", ""))):
                responses.append({"functionResponse": {"name": name, "response": {"content": "That is not an answer. The question is: " + items[i]["question"]}}}); continue   # D5
            if name == "submit_answer":
                item = items[i]; taught = None
                if arm == "cmlm" and args.get("teach_question") and args.get("teach_at"):
                    try: taught = hook.teach(args["teach_question"], args["teach_at"])
                    except Exception as e: taught = f"error: {e}"
                out["answers"].write(json.dumps({"qid": item["qid"], "answer": f"ANSWER: {args.get('answer', '')} | SOURCE: {args.get('source', '')}",
                                                 "teach": f"TEACH: {args.get('teach_question', '')} | {args.get('teach_at', '')}" if arm == "cmlm" else None,
                                                 "taught": taught, "calls": calls, "seconds": round(time.time() - t_q, 2)}) + "\n"); out["answers"].flush()
                i += 1; calls = 0; qnudge = 0; t_q = time.time()
                if i >= len(items):
                    done = True; content = f"DONE: all {len(items)} questions are answered."
                else:
                    content = present(arm, hook, items[i], i + 1, len(items), out)
                responses.append({"functionResponse": {"name": name, "response": {"content": content}}})
            else:
                calls += 1
                content = run_tool(name, args) if calls <= MAX_CALLS else "Tool limit reached for this question: call submit_answer now."
                responses.append({"functionResponse": {"name": name, "response": {"content": content}}})
        contents.append({"role": "user", "parts": responses})
        if done:
            return {"requests": nreq, "nudges": nudges, "answered": i}
    return {"requests": nreq, "nudges": nudges, "answered": i, "capped": True}


def chain(arm, run):
    d = f"{A}/runs/{arm}_r{run}"
    if os.path.exists(d): shutil.rmtree(d)
    os.makedirs(d)
    hook = None
    if arm == "cmlm":
        shutil.copytree(f"{L}/ws_L_base", f"{d}/ws"); hook = Hook(f"{d}/ws")
    out = {k: open(f"{d}/{k}.jsonl", "a") for k in ("requests", "answers", "readouts")}
    summary = []
    for t in range(1, 7):
        s = session(arm, run, t, hook, out); s["task"] = t; summary.append(s)
        print(arm, run, t, s, flush=True)
    json.dump(summary, open(f"{d}/sessions.json", "w"), indent=1)
    if hook: shutil.rmtree(f"{d}/ws")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "smoke":
        d = f"{A}/runs/smoke"; os.makedirs(d, exist_ok=True)
        out = {k: open(f"{d}/{k}.jsonl", "w") for k in ("requests", "answers", "readouts")}
        global STREAM; STREAM = STREAM[:1] + STREAM[1:10]
        r = session("alone", 0, 1, None, out); print(r); return
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    th = [threading.Thread(target=chain, args=(arm, k)) for k in range(1, runs + 1) for arm in ("cmlm", "alone")]
    for x in th: x.start()
    for x in th: x.join()
    print("all chains done")


if __name__ == "__main__":
    main()
