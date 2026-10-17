"""Score Graphify's Python import edges against Python's own parser (METHOD.md).

    python3 check_imports.py <name> ...      reads repos/<name> and graphs/<name>/graph.json, writes results/<name>.json"""
import ast, collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def py_files(repo):
    out = []
    for d, dirs, files in os.walk(repo):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        out += [os.path.relpath(os.path.join(d, f), repo) for f in files if f.endswith(".py")]
    return sorted(out)


class Repo:
    def __init__(self, root):
        self.root = root; self.files = set(py_files(root)); self.trees = {}

    def tree(self, f):
        if f not in self.trees:
            try:
                self.trees[f] = ast.parse(open(os.path.join(self.root, f), encoding="utf-8", errors="replace").read())
            except SyntaxError:
                self.trees[f] = None
        return self.trees[f]

    def module_file(self, base, dotted):
        """The file for module `dotted` under folder `base` (relative to the repo), or None."""
        p = os.path.normpath(os.path.join(base, *dotted.split("."))) if dotted else os.path.normpath(base)
        for cand in (p + ".py", os.path.join(p, "__init__.py")):
            if cand in self.files:
                return cand
        return None

    def bases(self, f):
        """sys.path-like roots: the repository, src/, and each ancestor folder outside a package (D1)."""
        out, d = ["", "src"], os.path.dirname(f)
        while d:
            if os.path.join(d, "__init__.py") not in self.files and d not in out:
                out.append(d)
            d = os.path.dirname(d)
        return out

    def resolve_abs(self, f, dotted):
        for b in self.bases(f):
            hit = self.module_file(b, dotted)
            if hit:
                return hit, b
        return None, None

    def defining_file(self, mod_file, name, hops=3):
        """Follow `from .x import name` re-exports from mod_file to the file that defines name."""
        seen = mod_file
        for _ in range(hops):
            t = self.tree(seen)
            if t is None:
                return seen
            nxt = None
            for node in t.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
                    return seen
                if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == name for x in node.targets):
                    return seen
                if isinstance(node, ast.ImportFrom) and any((a.asname or a.name) == name for a in node.names):
                    tgt = self.from_base(seen, node)
                    if tgt:
                        nxt = tgt
            if not nxt:
                return seen
            seen = nxt
        return seen

    def from_base(self, f, node):
        """The file of the module a `from ... import` statement names, or None (external)."""
        if node.level:
            pkg = os.path.dirname(f)
            for _ in range(node.level - 1):
                pkg = os.path.dirname(pkg)
            return self.module_file(pkg, node.module or "")
        return self.resolve_abs(f, node.module)[0] if node.module else None

    def statements(self, f):
        """{line: set of acceptable target files} for internal imports, and the set of external import lines."""
        t = self.tree(f); internal, external = collections.defaultdict(set), set()
        if t is None:
            return internal, external
        for node in ast.walk(t):
            if isinstance(node, ast.Import):
                for a in node.names:
                    hit, _ = self.resolve_abs(f, a.name)
                    if not hit:                                   # import a.b: the package a may still be internal
                        hit, _ = self.resolve_abs(f, a.name.split(".")[0])
                    (internal[node.lineno].add(hit) if hit else external.add(node.lineno))
            elif isinstance(node, ast.ImportFrom):
                base = self.from_base(f, node)
                if not base:
                    external.add(node.lineno); continue
                internal[node.lineno].add(base)
                for a in node.names:
                    if a.name == "*":
                        continue
                    sub = self.module_file(os.path.dirname(base), a.name) if base.endswith("__init__.py") else None
                    internal[node.lineno].add(sub or self.defining_file(base, a.name))
        for ln in list(external):
            if ln in internal:
                external.discard(ln)
        return internal, external


def main(name):
    repo = os.path.join(HERE, "repos", name); R = Repo(repo)
    g = json.load(open(os.path.join(HERE, os.environ.get("GRAPHS", "graphs"), name, "graph.json"))); N = {n["id"]: n for n in g["nodes"]}
    rel = lambda p: os.path.relpath(p, os.path.relpath(repo, os.getcwd())) if p else None
    src_of = lambda n: (lambda p: p[len(f"repos/{name}/"):] if p and p.startswith(f"repos/{name}/") else p)(n.get("source_file"))
    GT = {f: R.statements(f) for f in R.files}
    counts, examples, found, reach = collections.Counter(), collections.defaultdict(list), set(), {}
    for e in g["links"]:
        if e["relation"] not in ("imports", "imports_from", "re_exports"):
            continue
        f = src_of(N[e["source"]])
        if not f or not f.endswith(".py") or f not in GT:
            continue
        line = int(re.sub(r"\D", "", str(e.get("source_location") or "0")) or 0)
        internal, external = GT[f]
        tgt = src_of(N[e["target"]])
        if line not in internal and line not in external:
            k = "wrong line"
        elif tgt:
            k = "right (internal)" if tgt in internal.get(line, ()) else "wrong target"
            if k == "right (internal)":
                found.add((f, line))
        if tgt:
            reach.setdefault(f, set()).add(tgt)
        else:
            k = "wrong, missed internal" if line in internal else "right (external)"
        counts[k] += 1
        if k.startswith("wrong") and len(examples[k]) < 8:
            examples[k].append(f"{f}:{line} -> {N[e['target']].get('label')} [{tgt}] (truth: {sorted(internal.get(line, [])) or 'external'})")
    gt_internal = {(f, ln) for f, (internal, _) in GT.items() for ln in internal}
    found = {(f, ln) for f, ln in gt_internal if GT[f][0][ln] & reach.get(f, set())}      # one edge per file pair (D1)
    def src_line(f, ln):
        try:
            return open(os.path.join(repo, f), encoding="utf-8", errors="replace").read().split("\n")[ln - 1].strip()
        except (OSError, IndexError):
            return ""
    missed = sorted(gt_internal - found)
    examples["missed (not found)"] = [f"{f}:{ln}  {src_line(f, ln)[:90]}" for f, ln in missed[:12]]
    calls = collections.Counter()
    for e in g["links"]:
        if e["relation"] != "calls":
            continue
        f = src_of(N[e["source"]]); line = int(re.sub(r"\D", "", str(e.get("source_location") or "0")) or 0)
        tname = re.sub(r"[()]", "", str(N[e["target"]].get("label", ""))).lstrip(".").split(".")[-1]
        try:
            text = open(os.path.join(repo, f), encoding="utf-8", errors="replace").read().split("\n")[line - 1] if f and line else ""
        except (OSError, IndexError):
            text = ""
        ok = bool(tname) and re.search(rf"\b{re.escape(tname)}\s*(\.\s*\w+\s*)*\(", text) is not None   # name( or module.attr( (D1)
        calls[(e.get("confidence"), ok)] += 1
        if not ok and len(examples["calls failing the name check"]) < 10:
            examples["calls failing the name check"].append(f"{f}:{line} -> {tname}  |  {text.strip()[:90]}")
    edges = sum(counts.values()); wrong = sum(v for k, v in counts.items() if k.startswith("wrong"))
    res = {"repo": name, "py files": len(R.files), "import edges scored": edges, "by verdict": dict(counts),
           "wrong share": round(wrong / edges, 3) if edges else None,
           "internal import statements (truth)": len(gt_internal), "found by graphify": len(found & gt_internal),
           "recall": round(len(found & gt_internal) / len(gt_internal), 3) if gt_internal else None,
           "calls: name on the line (confidence, ok) ": {f"{c} {ok}": n for (c, ok), n in sorted(calls.items(), key=str)},
           "examples": dict(examples)}
    os.makedirs(os.path.join(HERE, os.environ.get("RESULTS", "results")), exist_ok=True)
    json.dump(res, open(os.path.join(HERE, os.environ.get("RESULTS", "results"), f"{name}.json"), "w"), indent=1)
    return res


if __name__ == "__main__":
    for n in sys.argv[1:]:
        r = main(n)
        print(json.dumps({k: v for k, v in r.items() if k != "examples"}))
        for k, v in r["examples"].items():
            print("  ", k); [print("     ", x) for x in v[:4]]
