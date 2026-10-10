"""Leak audit for built wheels: the only Python source shipped is the five stub modules, and no docstring or comment
from the kit's source survives in any compiled module.   python packaging/audit.py dist/*.whl"""
import ast, io, os, re, sys, tokenize, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(os.path.dirname(HERE), "ocm")
KEEP_PY = {"ocm/__init__.py", "ocm/__main__.py", "ocm/_r/__init__.py", "ocm/cmlm_vector/__init__.py", "ocm/providers/__init__.py"}
BANNED_PATHS = re.compile(r"(^|/)(router|lawsearch|lanes)(/|\.|$)")


def phrases():
    out = set()
    for root, _, fs in os.walk(SRC):
        for f in fs:
            if not f.endswith(".py"):
                continue
            src = open(os.path.join(root, f), encoding="utf-8").read()
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    d = ast.get_docstring(node, clean=False)
                    if d and len(d.strip()) >= 40:
                        out.add(d.strip()[:40])
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                if tok.type == tokenize.COMMENT and len(tok.string.lstrip("# ").strip()) >= 40:
                    out.add(tok.string.lstrip("# ").strip()[:40])
    return out


def main(wheels):
    ph = [p.encode() for p in phrases()]; bad = 0
    for w in wheels:
        z = zipfile.ZipFile(w); names = z.namelist()
        py = {n for n in names if n.endswith(".py")}
        if py != KEEP_PY:
            print(w, "python files differ from the stubs:", sorted(py ^ KEEP_PY)); bad += 1
        for n in names:
            if BANNED_PATHS.search(n):
                print(w, "internal module name in the wheel:", n); bad += 1
            if n.endswith(".so"):
                data = z.read(n)
                hits = [p.decode() for p in ph if p in data]
                if hits:
                    print(w, n, "keeps source text:", hits[:3]); bad += 1
        print(f"{os.path.basename(w)}: {len(names)} files, {len(py)} stub .py, {sum(n.endswith('.so') for n in names)} compiled modules")
    print(f"checked {len(ph)} docstring/comment phrases")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
