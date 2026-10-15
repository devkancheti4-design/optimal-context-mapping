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
        init.main(["all", repo, "--url", "http://ws.internal:7700", "--python", "python"])
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


def test_init_runs_the_modeld_command_when_it_is_installed(monkeypatch):
    repo = tempfile.mkdtemp()
    monkeypatch.setattr(init.shutil, "which", lambda name: "/opt/bin/modeld" if name == "modeld" else None)
    init.main(["claude", repo, "--url", "http://ws.internal:7700"])
    init.main(["kiro", repo, "--url", "http://ws.internal:7700"])
    claude = json.load(open(os.path.join(repo, ".claude", "settings.json")))
    assert [h["command"] for g in claude["hooks"]["Stop"] for h in g["hooks"]] == ["/opt/bin/modeld hook stop"]
    kiro = json.load(open(os.path.join(repo, ".kiro", "settings", "mcp.json")))["mcpServers"]["ocm"]
    assert kiro["command"] == "/opt/bin/modeld" and kiro["args"] == ["mcp"]


def test_install_registers_each_assistant_found_and_reruns_cleanly(monkeypatch):
    from ocm import install
    home = tempfile.mkdtemp()
    for d in (".claude", ".codex"):
        os.makedirs(os.path.join(home, d))
    open(os.path.join(home, ".codex", "AGENTS.md"), "w").write("# Mine\n\nKeep.\n")
    monkeypatch.setenv("HOME", home)
    monkeypatch.setattr(install.shutil, "which", lambda name: None)
    for _ in range(2):
        install.main([])
    skill = open(os.path.join(home, ".claude", "skills", "modeld", "SKILL.md")).read()
    assert skill.startswith("---\nname: modeld") and "modeld ask" in skill and "--scope code" in skill
    agents = open(os.path.join(home, ".codex", "AGENTS.md")).read()
    assert "Keep." in agents and agents.count(init.BEGIN) == 1 and "modeld teach" in agents
    assert not os.path.exists(os.path.join(home, ".gemini")) and not os.path.exists(os.path.join(home, ".kiro"))
    install.main(["--team", "http://ws.internal:7700"])
    assert "--url http://ws.internal:7700" in open(os.path.join(home, ".claude", "skills", "modeld", "SKILL.md")).read()


def test_cli_builds_asks_with_scope_and_teaches(monkeypatch, capsys):
    from ocm import cli
    import shutil as sh
    repo = os.path.join(tempfile.mkdtemp(), "repo")
    sh.copytree(os.path.join(HERE, "fixture_repo"), repo)
    cli.main([repo])                                                            # modeld <path> == modeld build <path>
    out = os.path.join(repo, "modeld-out")
    assert os.path.exists(os.path.join(out, "workspace.json")) and open(os.path.join(out, ".gitignore")).read() == "*\n"
    monkeypatch.chdir(repo)
    capsys.readouterr()
    cli.main(["ask", "Who owns refunds?", "--scope", "code"])
    assert "docs/README.md" not in capsys.readouterr().out
    cli.main(["teach", "How many times do we retry a failed card charge?", "src/config.py:4"])
    assert capsys.readouterr().out.startswith("taught 1 question vectors")
    cli.main([repo])                                                            # a rebuild in place keeps what was taught
    assert not any("modeld-out" in p for p in Workspace(out).files)              # its own output is never indexed
    assert json.loads(Workspace(out).handle("stats", {}))["question vectors taught"] == 1
