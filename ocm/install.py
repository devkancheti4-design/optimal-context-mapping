"""Register Model D with the coding assistants on this machine, once per person.

    modeld install                 every assistant found: Claude Code, Codex, Gemini CLI, Kiro
    modeld install --team URL      the same, pointed at the team's workspace server
    modeld install --all           write for all four, found or not
    modeld install --dry-run       print what would be written, write nothing

What it writes (in your home folder; a rerun replaces only Model D's own block):
  Claude Code  ~/.claude/skills/modeld/SKILL.md   the /modeld skill
  Codex        ~/.codex/AGENTS.md                 Model D's block in the global instructions
  Gemini CLI   ~/.gemini/GEMINI.md                the same
  Kiro         ~/.kiro/steering/modeld.md         the same, included always
Per repository, `modeld init <agent>` wires hooks and MCP to a team server instead."""
import argparse, os, shutil

from .init import BEGIN, END, _block

SKILL_HEAD = """---
name: modeld
description: Ask Model D where the answer is before searching the code, and teach it what you found. Use it for
  questions about this codebase, bug reports, and finding which file to change. `/modeld <path>` maps a repository.
---
"""


def instructions(url=None):
    flag = f" --url {url}" if url else ""
    build = ("The team's server already holds the map, so there is nothing to build."
             if url else "**Map the repository** once, and again after large changes: `modeld build .` (writes `modeld-out/`).\n"
                          "If this skill is invoked with a path (`/modeld <path>`), run `modeld build <path>` and report the result.")
    return f"""# Model D

Model D maps a repository on this machine and ranks the code that answers a question. It learns from each answer
you teach it, so a later question in other words lands on the same code.

{build}

**Before searching the code**, ask it in plain words:
`modeld ask "<the question>" --scope code{flag}`
- Use `--scope code` for bug reports and code questions. Drop it when the docs may hold the answer.
- If the code it returns answers the question, answer from it without searching.
- If not, run `modeld next "<the same question>"{' --scope code' + flag} once, then search as usual.

**After answering**, teach it the one line the answer is on:
`modeld teach "<the question>" <path>:<line>{flag}`
"""


def found(name, home):
    marks = {"claude": (".claude", "claude"), "codex": (".codex", "codex"), "gemini": (".gemini", "gemini"), "kiro": (".kiro", "kiro")}
    folder, exe = marks[name]
    return os.path.isdir(os.path.join(home, folder)) or shutil.which(exe) is not None


def write(name, home, text, dry):
    if name == "claude":
        path = os.path.join(home, ".claude", "skills", "modeld", "SKILL.md")
        if not dry:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w").write(SKILL_HEAD + "\n" + text)
        return path
    path = {"codex": os.path.join(home, ".codex", "AGENTS.md"), "gemini": os.path.join(home, ".gemini", "GEMINI.md"),
            "kiro": os.path.join(home, ".kiro", "steering", "modeld.md")}[name]
    if not dry:
        _block(path, text.replace("# Model D", "## Model D", 1),
               front="---\ninclusion: always\n---\n\n" if name == "kiro" else None)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="modeld install")
    ap.add_argument("--team", metavar="URL", help="the team's workspace server, e.g. http://ws.internal:7700")
    ap.add_argument("--all", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    home = os.path.expanduser("~")
    names = [n for n in ("claude", "codex", "gemini", "kiro") if a.all or found(n, home)]
    if not names:
        print("no coding assistant found (Claude Code, Codex, Gemini CLI, Kiro); `modeld install --all` writes for all four")
        return
    text = instructions(a.team.rstrip("/") if a.team else None)
    for n in names:
        print(("would write " if a.dry_run else "wrote ") + write(n, home, text, a.dry_run))
    if not shutil.which("modeld"):
        print("note: `modeld` is not on PATH; install it with `uv tool install model-d` or `pipx install model-d`")
    print("next: modeld build ." if not a.team else f"agents will ask the team server at {a.team}")


if __name__ == "__main__":
    main()
