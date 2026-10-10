"""Copy the kit into src/, strip docstrings and comments, swap usage texts for neutral ones, and list every string
literal left that could describe the method's internals (for review before compiling)."""
import ast, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "ocm")
DST = os.path.join(HERE, "build", "ocm")
USAGE = {  # modules that print their own __doc__ as usage: neutral text instead
    "__main__.py": "python -m ocm <build | serve | hook | mcp | init | hybrid | measure | calc> ...  (see README.md)",
    "loop.py": "python -m ocm hook prompt   (Claude Code UserPromptSubmit hook)\npython -m ocm hook stop     (Claude Code Stop hook)",
    "life.py": "Internal: the workspace's record of what was taught.",
    "cmlm_vector/cli.py": "cmlm-vector: internal tool.",
}
# runtime strings that name internals: replaced in the build copy only
REPLACE = [
    ("the code and docs its laws ranked for this request", "the code and docs it ranked for this request"),
    # readout labels: generic names instead of the internal ones (client and server changed together)
    ("NAMES = {0: \"the code a taught question's vector points to (ranked by meaning, not verified: use it only if it answers the question)\",\n         1: \"meaning\", 2: \"keyword matches\", 3: \"meaning and keyword matches\", 4: \"meaning, wider\"}",
     "NAMES = {0: \"learned match: code a teammate's question was answered from (not verified: use it only if it answers the question)\",\n         1: \"ranked matches\", 2: \"ranked matches\", 3: \"ranked matches\", 4: \"ranked matches, wider\"}"),
    ('TAUGHT = "(readout: the code a taught question"', 'TAUGHT = "(readout: learned match"'),
    # 0.2.0: the strict reader (PROTOCOL_VALUE7), and the version
    ('"If the code below does not contain the answer, reply exactly NEED_SEARCH.")',
     '"If the code below does not contain everything the question asks for, reply exactly NEED_SEARCH.")'),
    ('Answer the question from the code below only, in one or two sentences. "',
     'Answer the question from the code below only, completely, in one to three sentences. "'),
    ('__version__ = "0.1.0"', '__version__ = "0.2.1"'),
    ('VERSION = "0.1.0"', 'VERSION = "0.2.1"'),
    # law modules renamed so file names say nothing
    ("from .router import router as RL", "from ._r import _a as RL"),
    ("from .router import lanes as L", "from ._r import _b as L"),
    ("from .lawsearch import", "from ._c import"),
    # user-visible texts
    ('f"learned law: {st[\'law\']}, {\'active\' if st[\'active\'] else \'not yet active\'} ({st[\'examples\']} examples)"',
     'f"learned ranking: {\'active\' if st[\'active\'] else \'not yet active\'} ({st[\'examples\']} examples)"'),
    ('"learned law": m.law.state()', '"learned ranking": m.law.state()'),
    ("Returns the code its laws rank for the \"\n                    \"question: the code a taught question's vector points to, or the nearest code blocks and doc sentences (ranked, \"\n                    \"not verified).",
     "Returns the code it ranks for the \"\n                    \"question: a learned match, or the nearest code blocks and doc sentences (ranked, \"\n                    \"not verified)."),
    ("(a different lane), when", "when"),
    ("Each question's vector is put on that code, so a teammate's question near it in meaning \"\n                    \"is drawn there",
     "The workspace learns each one, so a teammate's similar question \"\n                    \"goes straight there"),
    ("This repository is mapped by the team's workspace: a small model with laws that turns a question into a vector and ranks\nthe code it points to, and that learns from every question a teammate answered.",
     "This repository is mapped by the team's workspace (the CMLM method): it ranks the code for a question before you search,\nand it learns from every question a teammate answered."),
]
RENAME = {"router/router.py": "_r/_a.py", "router/lanes.py": "_r/_b.py", "router/__init__.py": "_r/__init__.py",
          "cmlm_vector/lawsearch.py": "cmlm_vector/_c.py"}
DROP = {"cmlm_vector/cli.py"}
NO_MAIN = {"_r/_a.py", "_r/_b.py", "cmlm_vector/_c.py", "cmlm_vector/memory.py", "life.py"}
WORDS = re.compile(r"\b(law|laws|router|lane|lanes|advance|kernel|hamming|popcount|bits?|cue|cues|fingerprint|eight|check|checks|learned|vector law)\b", re.I)


class Strip(ast.NodeTransformer):
    def _body(self, node):
        b = node.body
        if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) and isinstance(b[0].value.value, str):
            node.body = b[1:] or [ast.Pass()]
        return node

    def visit_FunctionDef(self, n): self.generic_visit(n); return self._body(n)
    def visit_AsyncFunctionDef(self, n): self.generic_visit(n); return self._body(n)
    def visit_ClassDef(self, n): self.generic_visit(n); return self._body(n)


def main():
    if os.path.exists(DST):
        shutil.rmtree(DST)
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    os.makedirs(os.path.join(DST, "_r"), exist_ok=True)
    for a, b in RENAME.items():
        os.rename(os.path.join(DST, a), os.path.join(DST, b))
    os.rmdir(os.path.join(DST, "router"))
    for d in DROP:
        os.remove(os.path.join(DST, d))
    used = {a: 0 for a, _ in REPLACE}; missed = False
    flagged = []
    for root, _, fs in os.walk(DST):
        for f in fs:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f); rel = os.path.relpath(p, DST)
            src = open(p).read()
            for a, b in REPLACE:
                if a in src:
                    used[a] += 1
                src = src.replace(a, b)
            tree = ast.parse(src)
            if rel in NO_MAIN:
                tree.body = [n for n in tree.body if not (isinstance(n, ast.If) and "__main__" in ast.unparse(n.test))]
            Strip().visit(tree)
            body = tree.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                body = body[1:]
            if rel in USAGE:
                body = [ast.Expr(ast.Constant(USAGE[rel]))] + body
            tree.body = body or [ast.Pass()]
            out = ast.unparse(ast.fix_missing_locations(tree)) + "\n"
            open(p, "w").write(out)
            for node in ast.walk(ast.parse(out)):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and WORDS.search(node.value):
                    flagged.append((rel, node.lineno, node.value[:160].replace("\n", " | ")))
    for a, n in used.items():
        if not n:
            print("REPLACEMENT NOT APPLIED:", a[:90], file=sys.stderr); missed = True
    for r in flagged:
        print("%s:%d  %r" % r)
    print(len(flagged), "strings to review", file=sys.stderr)
    if missed:
        sys.exit("a replacement was not applied: the build copy would leak internal names")


main()
