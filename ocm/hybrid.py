"""The hybrid (Model D): the kit takes every decision; a language model only reads, or teaches what is new.

    python -m ocm hybrid "<question>" --provider claude|openai|gemini [--url http://127.0.0.1:7700]

For each question, the kit's laws decide (no model call, no tokens):
  - a question near one it was taught: the model READS the code the kit chose, once, with no tools, and answers;
    if that code does not hold the answer it says NEED_SEARCH and the question goes on to be taught
  - anything new: the model TEACHES, exploring with search / read / list just enough to find the one line the answer is
    on; the kit learns that line, so the next question like it costs one read
The tools reach the team's workspace server (python -m ocm serve). Providers live in ocm/providers/ and take their keys
from the environment (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY or a Vertex project)."""
import argparse, json, os
from ocm.loop import _call, readout, TAUGHT

MAX_CALLS = 15
READ = ("You read code for an engineering team. Answer the question from the code below only, in one or two sentences. "
        "If the code below does not contain the answer, reply exactly NEED_SEARCH.")
TEACH = ("You are an engineer on this codebase. Find the answer to the question in the code: search (a case-insensitive "
         "regular expression over every line), read_file (lines of one file) and list_files reach it. The code the team's "
         "workspace ranked for the question comes with it; if it holds the answer, submit from it without searching. When "
         "you have the answer, call submit with the answer and the one line it is on, as path:line. At most 15 tool calls.")
TOOLS = [  # neutral tool specs; each provider renders them in its own format
    {"name": "search", "description": "case-insensitive regular-expression search over every line of every file",
     "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "read_file", "description": "read lines of one file (at most 200 lines per call)",
     "parameters": {"type": "object", "properties": {"file": {"type": "string"}, "start_line": {"type": "integer"},
                                                     "num_lines": {"type": "integer"}}, "required": ["file", "start_line"]}},
    {"name": "list_files", "description": "list the files under a folder prefix ('' for all)",
     "parameters": {"type": "object", "properties": {"prefix": {"type": "string"}}}},
    {"name": "submit", "description": "the final answer and the one line it is on",
     "parameters": {"type": "object", "properties": {"answer": {"type": "string"}, "at": {"type": "string", "description": "path:line"}},
                    "required": ["answer", "at"]}},
]


class Workspace:
    """The team's workspace, over HTTP: the kit's decisions, its tools for the teaching model, and teaching."""
    def __init__(self, url=None):
        self.url = url

    def call(self, path, **kw):
        return _call(path, self.url, **kw)

    def tool(self, name, args):
        if name == "search": return self.call("search", pattern=args.get("pattern", ""))
        if name == "read_file": return self.call("read", file=args.get("file", ""), start=args.get("start_line", 1), num=args.get("num_lines", 80))
        if name == "list_files": return self.call("list", prefix=args.get("prefix", ""))
        return f"unknown tool {name}"


def run(question, provider, ws=None):
    """One question through the hybrid. Returns {"path": "read" | "teach", "answer", "at", "requests"}."""
    ws = ws or Workspace()
    code = readout(ws.call, question)
    if code.startswith(TAUGHT):                                   # the kit knows this code: one read
        text = provider.read(READ, question, code)
        if "NEED_SEARCH" not in text:
            return {"path": "read", "answer": text.strip(), "at": None, "requests": 1}
        extra = 1
    else:
        extra = 0
    answer, at, n = provider.teach(TEACH, question, code, TOOLS, ws.tool, MAX_CALLS)
    if at:
        ws.call("teach", pairs=[{"question": question, "at": at}])   # the kit learns it; next time it is one read
    return {"path": "teach", "answer": answer, "at": at, "requests": n + extra}


def provider(name, **kw):
    if name == "claude":
        from ocm.providers.claude_api import Claude; return Claude(**kw)
    if name == "openai":
        from ocm.providers.openai_api import OpenAIProvider; return OpenAIProvider(**kw)
    if name == "gemini":
        from ocm.providers.gemini_api import Gemini; return Gemini(**kw)
    raise SystemExit(f"unknown provider {name}: claude, openai or gemini")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ocm hybrid")
    ap.add_argument("question"); ap.add_argument("--provider", default="claude", choices=["claude", "openai", "gemini"])
    ap.add_argument("--url", default=os.environ.get("OCM_URL"))
    ap.add_argument("--reader"); ap.add_argument("--teacher")
    a = ap.parse_args(argv)
    kw = {k: v for k, v in (("reader", a.reader), ("teacher", a.teacher)) if v}
    print(json.dumps(run(a.question, provider(a.provider, **kw), Workspace(a.url)), indent=2))


if __name__ == "__main__":
    main()
