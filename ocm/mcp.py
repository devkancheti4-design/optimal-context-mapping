"""The MCP plugin: gives any MCP-capable agent (Claude Code, Cursor, Windsurf, others) the workspace as four tools.

    modeld mcp      (or modeld-mcp, python -m ocm mcp)

With $OCM_URL set it forwards to the team's workspace server. Without it, it serves a local workspace in this process:
$MODELD_WORKSPACE, or the nearest modeld-out folder (see `modeld build`); with neither, the server at
http://127.0.0.1:7700.

Speaks the Model Context Protocol over stdio (JSON-RPC 2.0, one message per line) with no extra dependencies. The tools
forward to the team's workspace server, so every person's agent shares one memory:
  workspace_ask      the first readout for a question (call before searching)
  workspace_next     the next readout for the same question
  workspace_recall   the k nearest units for a query in other words
  workspace_teach    at the end of a session, every question answered and the line its answer is on, at once"""
import json, os, sys, urllib.request

from . import __version__ as VERSION                                   # the package version, never a copy
URL = os.environ.get("OCM_URL", "http://127.0.0.1:7700").rstrip("/")
LOCAL = None                                                     # a Workspace served in this process (no OCM_URL)
Q = {"type": "object", "properties": {"question": {"type": "string", "description": "the question, as you would ask a colleague"},
                                     "scope": {"type": "string", "enum": ["all", "code"],
                                               "description": "code: leave documentation out, for a bug report or a question "
                                                              "whose answer is in code; all (default): code, config and docs"}},
     "required": ["question"]}
TOOLS = [
    {"name": "workspace_ask", "inputSchema": Q,
     "description": "Ask the team's shared workspace FIRST, before searching the code. Returns the code its laws rank for the "
                    "question: the code a taught question's vector points to, or the nearest code blocks and doc sentences (ranked, "
                    "not verified). If it answers the question, answer from it without searching."},
    {"name": "workspace_next", "inputSchema": Q,
     "description": "The workspace's next readout for the same question (a different lane), when the first did not answer it."},
    {"name": "workspace_recall",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer", "minimum": 1, "maximum": 10}},
                     "required": ["query"]},
     "description": "Ask the workspace in other words: the k code blocks or doc sentences nearest in meaning."},
    {"name": "workspace_teach",
     "inputSchema": {"type": "object", "properties": {"pairs": {"type": "array", "items": {"type": "object", "properties": {
         "question": {"type": "string"}, "at": {"type": "string", "description": "path:line, the one line the answer is on"}},
         "required": ["question", "at"]}}}, "required": ["pairs"]},
     "description": "Call ONCE at the end of your work: for each question you answered, the question and the one line its answer "
                    "is on (path:line). Each question's vector is put on that code, so a teammate's question near it in meaning "
                    "is drawn there instead of repeating the research."},
]
PATH = {"workspace_ask": "ask", "workspace_next": "next", "workspace_recall": "recall", "workspace_teach": "teach"}


def post(path, body):
    if LOCAL is not None:
        return LOCAL.handle(path, body)
    req = urllib.request.Request(f"{URL}/{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=300).read().decode()


def handle(msg):
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if method == "initialize":
        return {"protocolVersion": params.get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}},
                "serverInfo": {"name": "model-d", "version": VERSION}}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in PATH:
            return {"content": [{"type": "text", "text": f"unknown tool {name}"}], "isError": True}
        try:
            return {"content": [{"type": "text", "text": post(PATH[name], args)}], "isError": False}
        except Exception as e:                                           # noqa: BLE001 -- the agent sees the reason
            where = "the local workspace" if LOCAL is not None else f"the workspace server at {URL}"
            return {"content": [{"type": "text", "text": f"{where} failed: {e}"}], "isError": True}
    if mid is not None:
        raise LookupError(method)
    return None


def main(argv=None):
    global LOCAL
    if not os.environ.get("OCM_URL"):
        from .cli import find_workspace
        ws = find_workspace()
        if ws:
            os.environ.setdefault("OCM_OFFLINE", "1")
            from .server import Workspace
            LOCAL = Workspace(ws)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in msg:                                              # a notification: no reply
            continue
        try:
            out = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg)}
        except LookupError as e:
            out = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": f"method not found: {e}"}}
        sys.stdout.write(json.dumps(out) + "\n"); sys.stdout.flush()
