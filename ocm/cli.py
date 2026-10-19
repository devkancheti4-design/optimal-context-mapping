"""modeld: map a repository once, ask it where the answer is, teach it what was found.

  modeld build [path] [--out DIR]       map the repository into <path>/modeld-out (alias: modeld .)
  modeld ask "question" [--scope code]  the ranked places to look; --scope code leaves documentation out
  modeld next "question"                the next readout for the same question
  modeld teach "question" path:line     teach the line the answer is on
  modeld stats                          units, files, questions taught
  modeld forecast [repo]                how much Model D would cut an agent's bill here, from git history alone
  modeld prove [repo] [--fixes 50]      check it on your own recent bug fixes, at zero tokens, against grep
  modeld cover [--cap USD] [--yes]      teach it the whole codebase once: Claude Haiku writes one question per piece of
                                        code, each taught as a pointer to that code (about $1 for Django's 24k pieces)
  modeld install [--team URL]           register Model D with the coding assistants found on this machine
  modeld init <claude|kiro|codex|gemini|all> [repo] [--url URL]
                                        wire one repository's agent to a team server
  modeld serve [workspace] [--port 7700] [--host 127.0.0.1] [--build REPO ...]
                                        the team's shared workspace server (--build maps the repos first if empty)
  modeld mcp                            the MCP server over stdio (a local workspace, or $OCM_URL)
  modeld fetch-model [--to DIR]         download the embedding model once, for offline and air-gapped machines
  modeld hybrid | measure | calc | hook ...
                                        as in `python -m ocm` (see README)

ask, next, teach and stats use the nearest modeld-out folder (this folder or a parent), $MODELD_WORKSPACE, or
--workspace; with --url (or $OCM_URL) they ask a team server instead."""
import argparse, json, os, sys, urllib.request

OUT = "modeld-out"


def find_workspace(start=None):
    """--workspace, else $MODELD_WORKSPACE, else the nearest modeld-out above the current folder, else None."""
    env = os.environ.get("MODELD_WORKSPACE")
    if env:
        return env
    d = os.path.abspath(start or os.getcwd())
    while True:
        cand = os.path.join(d, OUT)
        if os.path.exists(os.path.join(cand, "workspace.json")):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _post(url, path, body):
    req = urllib.request.Request(f"{url.rstrip('/')}/{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=300).read().decode()


def _call(args, path, body, then=None):
    """Run one workspace call (or two, for `next`) locally or on the team server; print the result."""
    url = args.url or os.environ.get("OCM_URL")
    if url:
        print(_post(url, then or path, body)); return
    ws = args.workspace or find_workspace()
    if not ws:
        sys.exit(f"no {OUT} folder here or above: run `modeld build .` first, or pass --workspace or --url")
    os.environ.setdefault("OCM_OFFLINE", "1")
    from .server import Workspace
    w = Workspace(ws)
    out = w.handle(path, body)
    if then:                                   # a local process has no earlier readout to advance from: ask, then next
        out = w.handle(then, body)
    print(out)


def _common(ap):
    ap.add_argument("--workspace"); ap.add_argument("--url")


def build_cmd(argv):
    ap = argparse.ArgumentParser(prog="modeld build")
    ap.add_argument("path", nargs="*", default=["."]); ap.add_argument("--out")
    ap.add_argument("--model"); ap.add_argument("--device"); ap.add_argument("--carry")
    ap.add_argument("--cache", help="an embedding cache file ($MODELD_CACHE): a rebuild embeds only changed code")
    a = ap.parse_args(argv)
    roots = [os.path.abspath(p) for p in a.path]
    out = os.path.abspath(a.out or os.path.join(roots[0], OUT))
    carry = a.carry or (out if os.path.exists(os.path.join(out, "workspace.json")) else None)
    from .build import build
    if carry and os.path.abspath(carry) == out:                # a rebuild in place carries what was taught
        import shutil, tempfile
        tmp = tempfile.mkdtemp(prefix="modeld-out.new-")
        build(roots, tmp, a.model, a.device, carry=out, cache=a.cache)
        for name in os.listdir(out):                           # replace the contents, not the folder: it may be a mount
            p = os.path.join(out, name)
            shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
        for name in os.listdir(tmp):
            shutil.move(os.path.join(tmp, name), os.path.join(out, name))
        os.rmdir(tmp)
    else:
        build(roots, out, a.model, a.device, carry=carry, cache=a.cache)
    open(os.path.join(out, ".gitignore"), "w").write("*\n")    # the workspace never lands in git by accident
    print(f"\nmapped into {out}\nnext: modeld ask \"your question\" --scope code")


def ask_cmd(argv, path="ask"):
    ap = argparse.ArgumentParser(prog=f"modeld {path}"); ap.add_argument("question")
    ap.add_argument("--scope", choices=["all", "code"]); _common(ap)
    a = ap.parse_args(argv)
    body = {"question": a.question, **({"scope": a.scope} if a.scope else {})}
    if path == "next":
        _call(a, "ask", body, then="next")
    else:
        _call(a, "ask", body)


def teach_cmd(argv):
    ap = argparse.ArgumentParser(prog="modeld teach"); ap.add_argument("question"); ap.add_argument("at")
    _common(ap)
    a = ap.parse_args(argv)
    _call(a, "teach", {"pairs": [{"question": a.question, "at": a.at}]})


def stats_cmd(argv):
    ap = argparse.ArgumentParser(prog="modeld stats"); _common(ap)
    _call(ap.parse_args(argv), "stats", {})


def serve_cmd(argv):
    ap = argparse.ArgumentParser(prog="modeld serve"); ap.add_argument("workspace", nargs="?")
    ap.add_argument("--port", type=int, default=7700); ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--build", nargs="+", metavar="REPO", help="map these repositories into the workspace first, if it is empty")
    a = ap.parse_args(argv)
    ws = a.workspace or find_workspace()
    if a.build and ws and not os.path.exists(os.path.join(ws, "workspace.json")):
        build_cmd([*a.build, "--out", ws])
    if not ws or not os.path.exists(os.path.join(ws, "workspace.json")):
        sys.exit(f"no workspace at {ws or 'a ' + OUT + ' folder here or above'}: run `modeld build <repo>` first, or pass --build")
    os.environ.setdefault("OCM_OFFLINE", "1")
    from .server import serve
    print(f"serving {ws} at http://{a.host}:{a.port}"); sys.stdout.flush()
    serve(ws, a.port, a.host)


def fetch_model_cmd(argv):
    ap = argparse.ArgumentParser(prog="modeld fetch-model")
    ap.add_argument("--to", help="a folder to hold the model (used as HF_HOME); default: the normal Hugging Face cache")
    a = ap.parse_args(argv)
    if a.to:
        os.environ["HF_HOME"] = os.path.abspath(a.to)
    os.environ.pop("HF_HUB_OFFLINE", None); os.environ.pop("TRANSFORMERS_OFFLINE", None)
    from .cmlm_vector.embed import DEFAULT_MODEL
    from huggingface_hub import snapshot_download
    path = snapshot_download(DEFAULT_MODEL, allow_patterns=["*.json", "*.txt", "model.safetensors"])   # weights + tokenizer only
    print(f"{DEFAULT_MODEL} is at {path}")
    if a.to:
        print(f"on the offline machine: export HF_HOME={os.path.abspath(a.to)} OCM_OFFLINE=1")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__); return
    cmd, rest = argv[0], argv[1:]
    if cmd == "--version":
        from . import __version__
        print(f"modeld {__version__}"); return
    if cmd not in COMMANDS and os.path.isdir(cmd):            # modeld .  ==  modeld build .
        cmd, rest = "build", argv
    if cmd not in COMMANDS:
        print(__doc__); sys.exit(2)
    COMMANDS[cmd](rest)


def _module(name):
    def run(rest):
        import importlib
        importlib.import_module(f"ocm.{name}").main(rest)
    return run


def install_cmd(argv):
    from .install import main as install_main
    install_main(argv)


COMMANDS = {"build": build_cmd, "ask": ask_cmd, "next": lambda r: ask_cmd(r, "next"), "teach": teach_cmd,
            "stats": stats_cmd, "serve": serve_cmd, "fetch-model": fetch_model_cmd, "install": install_cmd,
            "cover": _module("cover"), "forecast": _module("forecast"), "prove": _module("prove"), "init": _module("init"), "mcp": _module("mcp"), "hybrid": _module("hybrid"), "measure": _module("measure"),
            "calc": _module("calc"), "hook": _module("loop")}


if __name__ == "__main__":
    main()
