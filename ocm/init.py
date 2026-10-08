"""Wire the team's workspace into a repository for the coding agent its engineers use.

    python -m ocm init claude [repo] [--url http://127.0.0.1:7700] [--python python]
    python -m ocm init kiro   [repo] ...
    python -m ocm init codex  [repo] ...      (OpenAI Codex)
    python -m ocm init gemini [repo] ...      (Gemini CLI)
    python -m ocm init all    [repo] ...

What each writes (merged into existing files, never overwriting other settings; safe to run again):
  claude  .claude/settings.json   two hooks: the readout before each request, TEACH lines taught after the reply
          CLAUDE.md               a short note on the TEACH line
  kiro    .kiro/settings/mcp.json the workspace as four MCP tools (auto-approved)
          .kiro/steering/ocm.md   when to ask the workspace and how to teach it (inclusion: always)
  codex   .codex/config.toml      [mcp_servers.ocm]
          AGENTS.md               the same instructions
  gemini  .gemini/settings.json   mcpServers.ocm
          GEMINI.md               the same instructions"""
import argparse, json, os

MCP_TOOLS = ["workspace_ask", "workspace_next", "workspace_recall", "workspace_teach"]
BEGIN, END = "<!-- ocm:begin -->", "<!-- ocm:end -->"
INSTRUCTIONS = """## Team workspace (Optimal Context Mapping)

This repository is mapped by the team's workspace: a small model with laws that turns a question into a vector and ranks
the code it points to, and that learns from every question a teammate answered.

1. Before searching the code for something, call `workspace_ask` with the question in plain words. If the code it returns
   answers the question, answer from it: no search needed. If not, call `workspace_next` once, then search as usual.
2. For every question you answered, keep the one line its answer is on, as path:line.
3. At the end of your work, call `workspace_teach` once with every question and its path:line. One call for everything.
"""
CLAUDE_NOTE = """## Team workspace (Optimal Context Mapping)

Each request arrives with the code the team's workspace ranked for it. If it answers the question, answer from it
without searching. End each reply with one line per question you answered, so the workspace learns it:
`TEACH: <the question> | <path>:<line>` (the one line your answer is on).
"""


def _json(path, update):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = json.load(open(path)) if os.path.exists(path) and os.path.getsize(path) else {}
    update(data)
    json.dump(data, open(path, "w"), indent=2)
    open(path, "a").write("\n")


def _block(path, text, front=None):
    """Put text between the ocm markers in a Markdown file: replaced on a rerun, everything else kept."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    old = open(path).read() if os.path.exists(path) else (front or "")
    block = f"{BEGIN}\n{text.rstrip()}\n{END}\n"
    if BEGIN in old and END in old:
        new = old[:old.index(BEGIN)] + block + old[old.index(END) + len(END):].lstrip("\n")
    else:
        new = old + ("\n" if old and not old.endswith("\n") else "") + ("\n" if old else "") + block
    open(path, "w").write(new)


def _mcp_entry(url, python, extra=None):
    e = {"command": python, "args": ["-m", "ocm", "mcp"], "env": {"OCM_URL": url}}
    e.update(extra or {})
    return e


def claude(repo, url, python):
    def upd(d):
        d.setdefault("env", {})["OCM_URL"] = url
        hooks = d.setdefault("hooks", {})
        for event, cmd in (("UserPromptSubmit", f"{python} -m ocm hook prompt"), ("Stop", f"{python} -m ocm hook stop")):
            groups = hooks.setdefault(event, [])
            if not any(h.get("command") == cmd for g in groups for h in g.get("hooks", [])):
                groups.append({"hooks": [{"type": "command", "command": cmd}]})
    _json(os.path.join(repo, ".claude", "settings.json"), upd)
    _block(os.path.join(repo, "CLAUDE.md"), CLAUDE_NOTE)
    return [".claude/settings.json", "CLAUDE.md"]


def kiro(repo, url, python):
    _json(os.path.join(repo, ".kiro", "settings", "mcp.json"),
          lambda d: d.setdefault("mcpServers", {}).__setitem__("ocm", _mcp_entry(url, python, {"disabled": False, "autoApprove": MCP_TOOLS})))
    _block(os.path.join(repo, ".kiro", "steering", "ocm.md"), INSTRUCTIONS, front="---\ninclusion: always\n---\n\n")
    return [".kiro/settings/mcp.json", ".kiro/steering/ocm.md"]


def codex(repo, url, python):
    path = os.path.join(repo, ".codex", "config.toml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    old = open(path).read() if os.path.exists(path) else ""
    if "[mcp_servers.ocm]" not in old:
        add = (f'\n[mcp_servers.ocm]\ncommand = "{python}"\nargs = ["-m", "ocm", "mcp"]\n\n'
               f'[mcp_servers.ocm.env]\nOCM_URL = "{url}"\n')
        open(path, "a").write(add if old else add.lstrip("\n"))
    _block(os.path.join(repo, "AGENTS.md"), INSTRUCTIONS)
    return [".codex/config.toml", "AGENTS.md"]


def gemini(repo, url, python):
    _json(os.path.join(repo, ".gemini", "settings.json"),
          lambda d: d.setdefault("mcpServers", {}).__setitem__("ocm", _mcp_entry(url, python, {"trust": False})))
    _block(os.path.join(repo, "GEMINI.md"), INSTRUCTIONS)
    return [".gemini/settings.json", "GEMINI.md"]


TARGETS = {"claude": claude, "kiro": kiro, "codex": codex, "gemini": gemini}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ocm init")
    ap.add_argument("target", choices=sorted(TARGETS) + ["all"])
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--url", default=os.environ.get("OCM_URL", "http://127.0.0.1:7700"))
    ap.add_argument("--python", default="python")
    a = ap.parse_args(argv)
    written = []
    for name in (sorted(TARGETS) if a.target == "all" else [a.target]):
        written += TARGETS[name](os.path.abspath(a.repo), a.url.rstrip("/"), a.python)
    print("wrote: " + ", ".join(written))
    print(f"the workspace server must be reachable at {a.url} (python -m ocm serve <workspace> --port 7700)")


if __name__ == "__main__":
    main()
