"""What goes into a workspace: the files of one or more repositories, cut into units the memory stores.

Code files are cut into blocks (split at blank lines, at most 400 characters, each prefixed with its path, so copied
code in two files stays two units); documentation is cut into sentences. Skipped, always: version control, dependency
and build folders, lockfiles, binaries, anything over 512 KB, and anything that looks like a secret (.env files, keys,
certificates, credential files). Nothing is read outside the folders you pass."""
import os

from .cmlm_vector.chunk import units as sentences

CODE = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".java", ".kt", ".kts", ".go", ".rs", ".rb", ".php", ".cs",
        ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".swift", ".scala", ".sql", ".sh", ".bash", ".ps1", ".css", ".scss", ".less",
        ".html", ".vue", ".svelte", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".gradle", ".tf", ".proto", ".graphql", ".json"}
DOCS = {".md", ".mdx", ".rst", ".txt", ".adoc"}
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "bower_components", "dist", "build", "out", ".next", ".nuxt", ".output",
             "venv", ".venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache", "target", "vendor", ".idea", ".vscode",
             "coverage", ".cache", ".gradle", ".terraform", "Pods", "DerivedData"}
LOCKS = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "Gemfile.lock", "composer.lock",
         "go.sum", "Pipfile.lock"}
MAX_BYTES = 512_000
MAXC, MINC = 400, 20


def looks_secret(name):
    n = name.lower()
    return (n.startswith(".env") or n.endswith((".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".crt", ".der"))
            or n.startswith("id_rsa") or n.startswith("id_ed25519") or "secret" in n or "credential" in n or n == ".npmrc"
            or n == ".pypirc" or n == ".netrc")


def files(roots):
    """[(name, rel, path)] for every file kept, in a stable order; roots is {name: folder}."""
    out = []
    for name, root in sorted(roots.items()):
        for d, dirs, fs in os.walk(root):
            dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith(".") or x in (".github",))
            for f in sorted(fs):
                ext = os.path.splitext(f)[1].lower(); p = os.path.join(d, f)
                if (ext not in CODE and ext not in DOCS) or f in LOCKS or looks_secret(f):
                    continue
                try:
                    if os.path.getsize(p) > MAX_BYTES:
                        continue
                except OSError:
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


def units(rel, text):
    """[(unit text, first line)] for one file: blocks for code, sentences for documentation."""
    if os.path.splitext(rel)[1].lower() in DOCS:
        return [(u, 0) for u in sentences(text)]
    return blocks(rel, text)
