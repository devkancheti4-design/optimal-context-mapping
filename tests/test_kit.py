"""Smoke tests: build a workspace over the fixture repo, ask, teach in one batch, ask again in other words, and speak
MCP. Needs the embedding model (downloaded once). Run: python -m pytest -q tests"""
import json, os, shutil, tempfile

from ocm.build import build
from ocm.mcp import handle
from ocm.server import Workspace

HERE = os.path.dirname(os.path.abspath(__file__))


def test_workspace_end_to_end():
    out = os.path.join(tempfile.mkdtemp(), "ws")
    build([os.path.join(HERE, "fixture_repo")], out, log=lambda *a: None)
    ws = Workspace(out)
    assert all(".env" not in p for p in ws.files) and not any("should-never" in t for t in ws.mem.texts)
    first = ws.handle("ask", {"question": "How many times do we retry a failed card charge?"})
    assert "MAX_CHARGE_RETRIES = 3" in first
    shutil.copytree(out, out + "_code")
    note = {"question": "How many times do we retry a failed card charge?", "note": "3 retries (MAX_CHARGE_RETRIES in src/config.py:4)."}
    taught = ws.handle("teach", {"notes": [note]})
    assert taught.startswith("taught 1 notes; 0 cues on cited code") and "(1 examples)" in taught, taught
    again = ws.handle("ask", {"question": "what is the retry limit when a payment to a card fails?"})
    assert "nearest match" in again and "3 retries" in again
    assert "ChargeDeclined" in ws.handle("search", {"pattern": "class ChargeDeclined"})
    st = json.loads(ws.handle("stats", {}))
    assert st["notes taught"] == 1 and st["cues"] == 1 and st["learned law"]["examples"] == 1
    full = Workspace(out + "_code", teach="note+code+law")                  # the question also cues the cited code
    assert full.handle("teach", {"notes": [note]}).startswith("taught 1 notes; 1 cues on cited code")
    assert json.loads(full.handle("stats", {}))["cues"] == 2


def test_mcp_protocol():
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert init["protocolVersion"] == "2025-06-18" and "tools" in init["capabilities"]
    names = [t["name"] for t in handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]]
    assert names == ["workspace_ask", "workspace_next", "workspace_recall", "workspace_teach"]


def test_loop_teach_lines():
    from ocm.loop import teach_lines
    reply = """The token lasts 8 days.
ANSWER: 8 days | SOURCE: backend/app/core/config.py
TEACH: How long does a login token stay valid? | 8 days (ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*8, backend/app/core/config.py:36)
- TEACH: Where do emails go locally? | Mailcatcher at http://localhost:1080 (compose.override.yml)
TEACH: no separator here
"""
    got = teach_lines(reply)
    assert got == [("How long does a login token stay valid?", "8 days (ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*8, backend/app/core/config.py:36)"),
                   ("Where do emails go locally?", "Mailcatcher at http://localhost:1080 (compose.override.yml)")], got
