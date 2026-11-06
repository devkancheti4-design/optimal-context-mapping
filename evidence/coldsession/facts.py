"""The facts of a Python repository at one commit, read by a program from the code itself, so the right answer to every question is known
without a judge. Comparing the facts of two commits says which stayed the same, which moved to another file and which changed.

Four kinds, each with one subject that is unique in the repository:
    default  the default value of a parameter           def send(self, request, timeout=30)
    const    the value of a named constant              MAX_RETRIES = 5
    base     the classes a class inherits from          class Session(SessionRedirectMixin)
    where    the file that defines a class or function  requests/sessions.py"""
import ast, json, os, re, sys
from collections import Counter

SKIP = re.compile(r"(^|/)(tests?|testing|docs?|doc_src|examples?|vendor|vendored|_vendor|third_party|extern|build|dist|benchmarks?|migrations|locale|"
                  r"__pycache__|\.[^/]+)(/|$)|(^|/)(test_[^/]*|[^/]*_test|conftest|setup|conf|_version|version)\.py$")
SIMPLE = (str, int, float, bool, type(None))
NOT = object()


def literal(node):
    """The value of a plain literal, or NOT."""
    if isinstance(node, ast.Constant) and isinstance(node.value, SIMPLE):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) and type(node.operand.value) in (int, float):
        return -node.operand.value
    return NOT


def usable(v):
    return not (isinstance(v, str) and (len(v) > 60 or "\n" in v))


def excerpt(lines, node, n=14):
    first = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return "\n".join(lines[first - 1:min(node.lineno + n, len(lines))])


def file_facts(path, text):
    """[{kind, subject, param, value, path, line, context}] for one file; no facts for a file Python can't parse."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return []
    lines, out = text.split("\n"), []

    def add(kind, subject, param, value, line, node):
        out.append({"kind": kind, "subject": subject, "param": param, "value": value, "path": path, "line": line, "context": excerpt(lines, node)})

    def visit(body, scope):
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = ".".join(scope + [n.name])
                add("where", q, None, path, n.lineno, n)
                a = n.args
                positional = a.posonlyargs + a.args
                pairs = list(zip(positional[len(positional) - len(a.defaults):], a.defaults)) + [(k, d) for k, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None]
                for arg, d in pairs:
                    v = literal(d)
                    if v is not NOT and usable(v):
                        add("default", q, arg.arg, v, d.lineno, n)
            elif isinstance(n, ast.ClassDef):
                q = ".".join(scope + [n.name])
                add("where", q, None, path, n.lineno, n)
                bases = [ast.unparse(b) for b in n.bases if isinstance(b, (ast.Name, ast.Attribute))]
                if bases and bases != ["object"] and len(bases) == len(n.bases):
                    add("base", q, None, bases, n.lineno, n)
                visit(n.body, scope + [n.name])
            elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                if len(targets) == 1 and isinstance(targets[0], ast.Name) and n.value is not None and n.lineno == n.end_lineno:
                    v = literal(n.value)
                    name = targets[0].id
                    if v is not NOT and usable(v) and not (name.startswith("__") and name.endswith("__")):
                        add("const", ".".join(scope + [name]), None, v, n.lineno, n)

    visit(tree.body, [])
    return out


def snapshot_facts(root):
    """Every fact of the Python source under root whose subject is unique in the repository. Test, doc, example, vendored and generated files are left out."""
    rows = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if not x.startswith("."))
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            p = os.path.join(d, f); rel = os.path.relpath(p, root).replace(os.sep, "/")
            if SKIP.search(rel) or os.path.getsize(p) > 400_000:
                continue
            rows += file_facts(rel, open(p, encoding="utf-8", errors="replace").read())
    key = lambda r: (r["kind"], r["subject"], r["param"])
    count = Counter(key(r) for r in rows)
    return {key(r): r for r in rows if count[key(r)] == 1}


def compare(old, new):
    """Each fact of the old commit with its status at the new one: same, moved (same value, another file), changed (another value), or gone."""
    out = []
    for k, r in old.items():
        n = new.get(k)
        if n is None:
            status = "gone"
        elif n["value"] != r["value"]:
            status = "changed"
        elif n["path"] != r["path"]:
            status = "moved"
        else:
            status = "same"
        out.append({**r, "status": status, "new_value": n["value"] if n else None, "new_path": n["path"] if n else None, "new_line": n["line"] if n else None})
    return out


def public(subject):
    return not any(part.startswith("_") for part in subject.split("."))


GUESSABLE = (None, True, False, 0, 1, -1, "")


def askable(r):
    """A fact a person could ask about and a program could check: a public subject and a value that isn't a likely guess."""
    if not public(r["subject"]) or (r["param"] or "x").startswith("_"):
        return False
    v = r["value"]
    if r["kind"] in ("default", "const"):
        if any(v is g or (type(v) is type(g) and v == g) for g in GUESSABLE):
            return False
        if isinstance(v, str) and len(v) < 3:
            return False
    return True


def rates(rows):
    """{kind: {status: how many}}, over the askable facts."""
    out = {}
    for r in rows:
        if askable(r):
            out.setdefault(r["kind"], Counter())[r["status"]] += 1
    return {k: dict(v) for k, v in out.items()}


if __name__ == "__main__":
    print(json.dumps(rates(compare(snapshot_facts(sys.argv[1]), snapshot_facts(sys.argv[2]))), indent=1))
