"""Smoke tests: build a workspace over the fixture repo, ask, teach in one batch, ask again in other words, and speak
MCP. Needs the embedding model (downloaded once). Run: python -m pytest -q tests"""
import json, os, tempfile

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
    assert ws.handle("teach", {"notes": [{"question": "How many times do we retry a failed card charge?",
                                          "note": "3 retries (MAX_CHARGE_RETRIES in src/config.py)."}]}) == "taught 1 notes"
    again = ws.handle("ask", {"question": "what is the retry limit when a payment to a card fails?"})
    assert "certified" in again and "3 retries" in again
    assert "ChargeDeclined" in ws.handle("search", {"pattern": "class ChargeDeclined"})
    assert json.loads(ws.handle("stats", {}))["notes taught"] == 1


def test_mcp_protocol():
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert init["protocolVersion"] == "2025-06-18" and "tools" in init["capabilities"]
    names = [t["name"] for t in handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]]
    assert names == ["workspace_ask", "workspace_next", "workspace_recall", "workspace_teach"]
