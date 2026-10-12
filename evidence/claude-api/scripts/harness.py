"""PROTOCOL_VALUE harness: the Claude API with a shared spend ledger and cap, ALONE, MODEL D (the compiled package),
workspace servers. Run everything with the package's venv (~/ocm-eval/venvs/t312/bin/python)."""
import json, os, re, shutil, subprocess, sys, threading, time, urllib.request

H = os.path.expanduser("~/cmlm-bench10")
V = f"{H}/value"
if not os.path.exists(os.path.expanduser("~/.ocm_run_token")):
    sys.exit("refused: no ~/.ocm_run_token (orchestrator only)")
os.environ["ANTHROPIC_API_KEY"] = open(os.path.expanduser("~/.ocm_anthropic_key")).read().strip()   # never printed
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")

import anthropic
from ocm.hybrid import run as md_run, provider, Workspace, TOOLS, TEACH, READ, MAX_CALLS
from ocm.loop import readout, TAUGHT

SONNET, HAIKU = "claude-sonnet-5-5", "claude-haiku-5-5"
PRICE = {"sonnet": (2.00, 2.50, 0.20, 10.00), "haiku": (0.10, 0.125, 0.01, 0.50)}   # per 1M: in, write, read, out
WEB_SEARCH = 0.01                                                                     # $10 per 1,000 searches
CAP = 150.0
LEDGER = f"{V}/ledger.jsonl"
ALONE_SYS = TEACH.replace(" The code the team's workspace ranked for the question comes with it; if it holds the answer, "
                          "submit from it without searching.", "")
assert ALONE_SYS != TEACH, "teach prompt changed: ALONE prompt not derived"
WEB_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}

_lock = threading.Lock()
_spent = [sum(json.loads(l)["usd"] for l in open(LEDGER)) if os.path.exists(LEDGER) else 0.0]
_tl = threading.local()


class Capped(Exception):
    pass


def spent():
    return _spent[0]


def _cost(model, u, web):
    p = PRICE["haiku" if "haiku" in model else "sonnet"]
    return (u["input"] * p[0] + u["write"] * p[1] + u["read"] * p[2] + u["output"] * p[3]) / 1e6 + web * WEB_SEARCH


def begin():
    _tl.rec = []


def took():
    return list(getattr(_tl, "rec", []))


def wrap(client, tag):
    """Every request: refused past the cap, retried on rate limits and overloads, recorded in the ledger."""
    orig = client.messages.create

    def create(**kw):
        if _spent[0] > CAP:
            raise Capped(f"program spend ${_spent[0]:.2f} passed the ${CAP} cap")
        for attempt in range(10):
            try:
                r = orig(**kw); break
            except anthropic.APIStatusError as e:
                if e.status_code in (429, 500, 502, 503, 529) and attempt < 9:
                    time.sleep(min(90, 3 * 2 ** attempt)); continue
                raise
            except anthropic.APIConnectionError:
                if attempt < 9:
                    time.sleep(min(90, 3 * 2 ** attempt)); continue
                raise
        u = r.usage
        st = getattr(u, "server_tool_use", None)
        web = (getattr(st, "web_search_requests", 0) or 0) if st else 0
        row = {"model": kw["model"], "input": u.input_tokens, "output": u.output_tokens,
               "write": u.cache_creation_input_tokens or 0, "read": u.cache_read_input_tokens or 0, "web": web}
        row["usd"] = round(_cost(kw["model"], row, web), 6)
        with _lock:
            _spent[0] += row["usd"]
            with open(LEDGER, "a") as f:
                f.write(json.dumps({"tag": tag, "t": round(time.time(), 1), **row}) + "\n")
        if not hasattr(_tl, "rec"):
            _tl.rec = []
        _tl.rec.append(row)
        return r

    client.messages.create = create
    return client


CLIENT = wrap(anthropic.Anthropic(max_retries=4), "direct")
MD = provider("claude")
wrap(MD.client, "modeld")


def serve(ws_src, ws_dir, port, fresh=True):
    if fresh:
        if os.path.exists(ws_dir):
            shutil.rmtree(ws_dir)
        shutil.copytree(ws_src, ws_dir)
    log = open(f"{ws_dir}.serve.log", "w")
    p = subprocess.Popen([os.path.join(os.path.dirname(sys.executable), "ocm"), "serve", ws_dir, "--port", str(port)],
                         stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    for _ in range(300):
        try:
            urllib.request.urlopen(urllib.request.Request(f"{url}/stats", data=b"{}"), timeout=5).read(); return p, url
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"workspace server on {port} did not start")


class WS(Workspace):
    """The workspace over HTTP, keeping the readouts it gave; learn=False drops teaching."""
    def __init__(self, url, learn=True):
        super().__init__(url); self.seen = []; self.learn = learn

    def call(self, path, **kw):
        if path == "teach" and not self.learn:
            return "not taught (learning off)"
        out = super().call(path, **kw)
        if path in ("ask", "next"):
            self.seen.append(out)
        return out


def _loop(system, first, url, extra_tools=None):
    """The agent loop, as the Claude provider's teach runs it: tools until submit."""
    ws = Workspace(url)
    spec = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in TOOLS] + (extra_tools or [])
    messages = [{"role": "user", "content": first}]
    calls = n = 0
    while n < MAX_CALLS + 10:
        r = CLIENT.messages.create(model=SONNET, max_tokens=8000, system=system, tools=spec, messages=messages)
        n += 1
        if r.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": r.content}); continue
        uses = [b for b in r.content if b.type == "tool_use"]
        if not uses:
            return "".join(b.text for b in r.content if b.type == "text").strip(), None
        messages.append({"role": "assistant", "content": r.content})
        results = []
        for u in uses:
            if u.name == "submit":
                return u.input.get("answer", ""), u.input.get("at") or None
            calls += 1
            out = ws.tool(u.name, u.input) if calls <= MAX_CALLS else "Tool limit reached: call submit now."
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": out})
        messages.append({"role": "user", "content": results})
    return "", None


def alone(question, url, web=False):
    return _loop(ALONE_SYS, f"Question: {question}", url, [WEB_TOOL] if web else None)


def modeld(question, url, learn=True):
    """MODEL D exactly as shipped (ocm.hybrid.run, the compiled package)."""
    ws = WS(url, learn)
    res = md_run(question, MD, ws)
    return res, ws.seen


def modeld_web(question, url, learn=True):
    """E6: the same decision as ocm.hybrid.run, with web search added to the teach step (the shipped provider has none)."""
    ws = WS(url, learn)
    code = readout(ws.call, question)
    if code.startswith(TAUGHT):
        r = CLIENT.messages.create(model=HAIKU, max_tokens=1024, system=READ,
                                   messages=[{"role": "user", "content": f"Question: {question}\n\nCode:\n{code}"}])
        text = "".join(b.text for b in r.content if b.type == "text")
        if "NEED_SEARCH" not in text:
            return {"path": "read", "answer": text.strip(), "at": None}, ws.seen
    first = f"Question: {question}\n\nThe code the team's workspace ranked for it:\n{code}"
    answer, at = _loop(TEACH, first, url, [WEB_TOOL])
    if at:
        ws.call("teach", pairs=[{"question": question, "at": at}])
    return {"path": "teach", "answer": answer, "at": at}, ws.seen


def same_file(path, gold):
    path = (path or "").split(":")[0].lstrip("./")
    return bool(path) and (path == gold or path.endswith("/" + gold))


def first_file(readout_text):
    m = re.search(r"(?m)^1\. \[([^\]]+)\]", readout_text or "")
    return m.group(1) if m else ""


def summarise(rec):
    return {"requests": len(rec), "models": [x["model"] for x in rec], "web": sum(x["web"] for x in rec),
            "tokens": sum(x["input"] + x["output"] + x["write"] + x["read"] for x in rec),
            "first tokens": (rec[0]["input"] + rec[0]["write"] + rec[0]["read"] + rec[0]["output"]) if rec else 0,
            "per request tokens": [x["input"] + x["write"] + x["read"] + x["output"] for x in rec],
            "usd": round(sum(x["usd"] for x in rec), 6)}


def done_ids(path):
    return {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()


def write(path, row):
    with _lock:
        with open(path, "a") as f:
            f.write(json.dumps(row) + "\n")
