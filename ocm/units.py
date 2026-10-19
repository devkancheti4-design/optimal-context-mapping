"""What goes into a workspace: the files of one or more repositories, cut into units the memory stores.

Code files are cut into blocks (split at blank lines, at most 400 characters, each prefixed with its path, so copied
code in two files stays two units); documentation is cut into sentences, each with the lines it spans, so a taught
question can point at a doc line as it can at a code line. Build files with no extension (Dockerfile, Makefile and the
like), server configs (.conf), email templates (.mjml) and editor launch settings (.vscode) are code. Skipped, always:
Model D's and Graphify's own output folders (modeld-out, graphify-out), version control, dependency and build folders,
lockfiles, binaries, minified bundles (*.min.js, *.min.css), .json data files over 2 MB, and anything that looks like a
secret (.env files, keys, certificates, credential files). Every other code file is read, whatever its size (since
0.5.2; before, anything over 512 KB was skipped). OCM_MAX_FILE_KB, or `modeld build --max-file-kb N`, sets a limit.
Nothing is read outside the folders you pass."""
import os

from .cmlm_vector.chunk import units as sentences

CODE = {".py", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".astro", ".java", ".kt", ".kts", ".go", ".rs", ".rb", ".php", ".cs",
        ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".swift", ".scala", ".sql", ".sh", ".bash", ".ps1", ".css", ".scss", ".less",
        ".html", ".vue", ".svelte", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".gradle", ".tf", ".proto", ".graphql", ".json",
        ".conf", ".mjml"}
NAMED = {"Dockerfile", "Containerfile", "Makefile", "GNUmakefile", "Procfile", "Jenkinsfile", "Vagrantfile", "Rakefile", "Gemfile"}
DOT_DIRS = {".github", ".vscode", ".devcontainer", ".circleci", ".gitlab"}
DOCS = {".md", ".mdx", ".rst", ".txt", ".adoc"}
TOOL_OUT = ("modeld-out", "graphify-out")         # tools' own output folders (a workspace, a graph): never indexed
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "bower_components", "dist", "build", "out", ".next", ".nuxt", ".output",
             "venv", ".venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache", "target", "vendor", ".idea",
             "coverage", ".cache", ".gradle", ".terraform", "Pods", "DerivedData"}
LOCKS = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "Gemfile.lock", "composer.lock",
         "go.sum", "Pipfile.lock"}
JSON_MAX_BYTES = 2_000_000          # a .json file larger than this is a data dump, not code


def max_bytes():
    """The optional per-file limit, read at call time: OCM_MAX_FILE_KB (kilobytes), unset for no limit."""
    v = os.environ.get("OCM_MAX_FILE_KB", "").strip()
    return int(v) * 1000 if v else None
MAXC, MINC = 400, 20


def looks_secret(name):
    n = name.lower()
    return (n.startswith(".env") or n.endswith((".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".crt", ".der"))
            or n.startswith("id_rsa") or n.startswith("id_ed25519") or "secret" in n or "credential" in n or n == ".npmrc"
            or n == ".pypirc" or n == ".netrc")


def named(f):
    return f in NAMED or f.split(".")[0] in ("Dockerfile", "Containerfile")


def files(roots):
    """[(name, rel, path)] for every file kept, in a stable order; roots is {name: folder}."""
    out, limit = [], max_bytes()
    for name, root in sorted(roots.items()):
        for d, dirs, fs in os.walk(root):
            dirs[:] = sorted(x for x in dirs if (x not in SKIP_DIRS and not x.startswith(".") or x in DOT_DIRS)
                             and not x.startswith(TOOL_OUT))
            for f in sorted(fs):
                ext = os.path.splitext(f)[1].lower(); p = os.path.join(d, f)
                if not (ext in CODE or ext in DOCS or named(f)) or f in LOCKS or looks_secret(f) or ".min." in f.lower():
                    continue
                try:
                    size = os.path.getsize(p)
                except OSError:
                    continue
                if (limit is not None and size > limit) or (ext == ".json" and size > JSON_MAX_BYTES):
                    continue
                out.append((name, f"{name}/{os.path.relpath(p, root)}", p))
    return out


def blocks(rel, text):
    out, block, start = [], [], None
    def flush():
        if block and len("".join(block).replace(" ", "").replace("\n", "")) >= MINC:
            out.append((f"# {rel}\n" + "\n".join(block), start))
    for i, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            flush(); block, start = [], None; continue
        piece = line[:MAXC]
        if block and len("\n".join(block)) + 1 + len(piece) > MAXC:
            flush(); block, start = [], None
        if start is None:
            start = i
        block.append(piece)
    flush()
    return out


def doc_lines(text, us):
    """The first and last line of each sentence in the text it came from, found in order (a sentence's words, whitespace
    aside, appear in the text as they do in the sentence)."""
    flat, line_of = [], []
    for i, line in enumerate(text.split("\n"), 1):
        for ch in line + " ":
            if not ch.isspace() or (flat and flat[-1] != " "):
                flat.append(" " if ch.isspace() else ch); line_of.append(i)
    flat = "".join(flat); out, at = [], 0
    for u in us:
        k = flat.find(u, at)
        if k < 0:
            k = flat.find(u[:40], at)
        if k < 0:
            out.append((0, 0)); continue
        end = min(len(line_of) - 1, k + len(u) - 1)
        out.append((line_of[k], line_of[end])); at = k + 1
    return out


def units(rel, text):
    """[(unit text, first line, last line)] for one file: blocks for code, sentences for documentation."""
    if os.path.splitext(rel)[1].lower() in DOCS:
        us = sentences(text)
        return [(u, a, b) for u, (a, b) in zip(us, doc_lines(text, us))]
    return [(t, a, a + t.count("\n") - 1) for t, a in blocks(rel, text)]
