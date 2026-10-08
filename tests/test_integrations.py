"""Integration tests: `ocm init` writes each agent's config into a repo (merged, idempotent), and the hybrid routes a
question the kit knows to one read and anything new to teaching, then teaches the kit. No network, no model calls: the
workspace runs in process and the model is a stub. Run: python -m pytest -q tests"""
import json, os, tempfile

from ocm import init, hybrid
from ocm.build import build
from ocm.server import Workspace

HERE = os.path.dirname(os.path.abspath(__file__))


def test_init_writes_every_agent_config_and_keeps_existing_settings():
    repo = tempfile.mkdtemp()
    os.makedirs(os.path.join(repo, ".gemini"))
    json.dump({"theme": "dark", "mcpServers": {"other": {"command": "x"}}}, open(os.path.join(repo, ".gemini", "settings.json"), "w"))
    open(os.path.join(repo, "AGENTS.md"), "w").write("# Our rules\n\nKeep this line.\n")
    for _ in range(2):                                                          # running twice changes nothing more
        init.main(["all", repo, "--url", "http://ws.internal:7700"])
    claude = json.load(open(os.path.join(repo, ".claude", "settings.json")))
    assert claude["env"]["OCM_URL"] == "http://ws.internal:7700"
    assert [h["command"] for g in claude["hooks"]["UserPromptSubmit"] for h in g["hooks"]] == ["python -m ocm hook prompt"]
    assert [h["command"] for g in claude["hooks"]["Stop"] for h in g["hooks"]] == ["python -m ocm hook stop"]
    kiro = json.load(open(os.path.join(repo, ".kiro", "settings", "mcp.json")))["mcpServers"]["ocm"]
    assert kiro["args"] == ["-m", "ocm", "mcp"] and "workspace_teach" in kiro["autoApprove"]
    assert open(os.path.join(repo, ".kiro", "steering", "ocm.md")).read().startswith("---\ninclusion: always\n---")
    toml = open(os.path.join(repo, ".codex", "config.toml")).read()
    assert toml.count("[mcp_servers.ocm]") == 1 and 'OCM_URL = "http://ws.internal:7700"' in toml
    gem = json.load(open(os.path.join(repo, ".gemini", "settings.json")))
    assert gem["theme"] == "dark" and "other" in gem["mcpServers"] and gem["mcpServers"]["ocm"]["env"]["OCM_URL"] == "http://ws.internal:7700"
    agents = open(os.path.join(repo, "AGENTS.md")).read()
    assert "Keep this line." in agents and agents.count(init.BEGIN) == 1 and "workspace_ask" in agents
    assert open(os.path.join(repo, "GEMINI.md")).read().count(init.BEGIN) == 1


class Stub:
    """A model stub: reads by quoting the first code line, teaches by citing a fixed line."""
    def __init__(self):
        self.reads = self.teaches = 0

    def read(self, system, question, code):
        self.reads += 1
        return "MAX_CHARGE_RETRIES = 3" if "MAX_CHARGE_RETRIES" in code else "NEED_SEARCH"

    def teach(self, system, question, code, tools, run_tool, max_calls):
        self.teaches += 1
        assert "class ChargeDeclined" in run_tool("search", {"pattern": "class ChargeDeclined"})
        return "3 retries", "src/config.py:4", 2


class LocalWorkspace(hybrid.Workspace):
    def __init__(self, ws):
        self.ws = ws

    def call(self, path, **kw):
        return self.ws.handle(path, kw)


def test_hybrid_reads_what_the_kit_knows_and_teaches_what_is_new():
    out = os.path.join(tempfile.mkdtemp(), "ws")
    build([os.path.join(HERE, "fixture_repo")], out, log=lambda *a: None)
    ws, model = LocalWorkspace(Workspace(out)), Stub()
    first = hybrid.run("How many times do we retry a failed card charge?", model, ws)
    assert first["path"] == "teach" and first["at"] == "src/config.py:4" and model.teaches == 1 and model.reads == 0
    again = hybrid.run("what is the retry limit when a payment to a card fails?", model, ws)
    assert again["path"] == "read" and again["requests"] == 1 and "MAX_CHARGE_RETRIES" in again["answer"], again
    assert model.teaches == 1                                                   # the second question never reached teaching


if __name__ == "__main__":
    test_init_writes_every_agent_config_and_keeps_existing_settings()
    test_hybrid_reads_what_the_kit_knows_and_teaches_what_is_new()
    print("integration tests passed")
