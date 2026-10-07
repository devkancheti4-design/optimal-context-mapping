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
    assert any(p.endswith("/Dockerfile") for p in ws.files)                    # build files with no extension are code
    assert ws.unit_at("docs/README.md:4") is not None                           # doc sentences keep their lines
    first = ws.handle("ask", {"question": "How many times do we retry a failed card charge?"})
    assert "MAX_CHARGE_RETRIES = 3" in first
    units = len(ws.mem.texts)
    taught = ws.handle("teach", {"pairs": [{"question": "How many times do we retry a failed card charge?", "at": "src/config.py:4"},
                                           {"question": "Who owns refunds?", "at": "nowhere.py:3"}]})
    assert taught.startswith("taught 1 question vectors onto code; 1 not placed") and "(1 examples)" in taught, taught
    assert len(ws.mem.texts) == units                                           # teaching stores vectors, never text
    again = ws.handle("ask", {"question": "what is the retry limit when a payment to a card fails?"})
    assert again.startswith("(readout: the code a taught question") and "MAX_CHARGE_RETRIES = 3" in again, again
    assert "src/config.py:3" in again                                           # the code block itself, with its place
    assert "ChargeDeclined" in ws.handle("search", {"pattern": "class ChargeDeclined"})
    st = json.loads(ws.handle("stats", {}))
    assert st["question vectors taught"] == 1 and st["learned law"]["examples"] == 1
    again2 = Workspace(out)                                                     # taught vectors persist on disk
    assert json.loads(again2.handle("stats", {}))["question vectors taught"] == 1


def test_mcp_protocol():
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert init["protocolVersion"] == "2025-06-18" and "tools" in init["capabilities"]
    names = [t["name"] for t in handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]]
    assert names == ["workspace_ask", "workspace_next", "workspace_recall", "workspace_teach"]


def test_loop_teach_lines():
    from ocm.loop import teach_lines
    reply = """The token lasts 8 days.
ANSWER: 8 days | SOURCE: backend/app/core/config.py
TEACH: How long does a login token stay valid? | backend/app/core/config.py:36
- TEACH: Where do emails go locally? | compose.override.yml:84
TEACH: no separator here
"""
    got = teach_lines(reply)
    assert got == [("How long does a login token stay valid?", "backend/app/core/config.py:36"),
                   ("Where do emails go locally?", "compose.override.yml:84")], got


def test_loop_compact_readout():
    from ocm.loop import compact_readout
    many = "(readout: meaning)\n\n" + "\n\n".join(f"{i}. [corpus/a.py:{i}]\nline {i}" for i in range(1, 11))
    small = compact_readout(many)
    assert "3. [corpus/a.py:3]" in small and "4. [corpus/a.py:4]" not in small, small


def test_loop_readout_advances_after_the_taught_lane():
    from ocm.loop import readout
    calls = []
    def taught(path, **kw):
        calls.append(path)
        return "(readout: the code a taught question's vector points to)\n\n1. [a.py:3]\nX = 3" if path == "ask" else "(readout: meaning)\n\n1. [b.py:9]\nY = 4"
    out = readout(taught, "q")
    assert calls == ["ask", "next"] and "X = 3" in out and "Y = 4" in out
    calls.clear()
    plain = readout(lambda path, **kw: calls.append(path) or "(readout: meaning)\n\n1. [b.py:9]\nY = 4", "q")
    assert calls == ["ask"] and "Y = 4" in plain
