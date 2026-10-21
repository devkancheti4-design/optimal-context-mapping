"""Reproduce the independent evaluation from nothing, and check every answer against the published rows.

    python3 reproduce.py                         # everything: 120 fixes + Saleor's 200 as a team (about 4 hours)
    python3 reproduce.py --repos aiohttp         # one repository, both tools and the baselines (about 15 minutes)
    python3 reproduce.py --repos saleor --tools modeld

What it does, in order:
1. Installs Model D and Graphify into their own Python 3.12 environments, at the exact commits the evaluation used
   (Model D 0.5.3, tag v0.5.3, ec440d7; Graphify 0.9.93, tag v0.9.93, b90b9df), with every library pinned to the
   evaluation's versions (env/*.lock.txt) and Model D's embedding model pinned to the revision it used.
2. Clones aiohttp, fastify, zod and Saleor, and checks that every fix commit in the question sets is present.
3. Re-runs the evaluation's own runners (bench/run_*.py) on the published question sets (bench/q_*.json), writing
   to <work>/results.
4. Compares every answer with bench/results: how many ranked file lists are identical, and whether right-file-first
   and top-5 counts match. Then prints the report's tables from the new rows (bench/analyze*.py).

It exits 0 when every count matches. No API key and no model calls. The first run needs the network: the packages,
four repositories and Model D's embedding model (BAAI/bge-base-en-v1.5, 440 MB). Needs git, and uv or python3.12.
- The evaluation ran on Apple Silicon, where Model D embeds on the GPU (MPS). Other hardware (CUDA, or CPU) can round
  a few floats differently, which can move a handful of answers; counts should match or come within a few.
- The agent tests (Claude sessions) are not part of it: model answers vary from run to run."""
import argparse, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "bench")
PUBLISHED = os.path.join(BENCH, "results")
MODELD = "model-d @ git+https://github.com/devkancheti4-design/optimal-context-mapping@ec440d7b4f7f0e1b42906efd60ec352e5a029229"
GRAPHIFY = "graphifyy @ git+https://github.com/Graphify-Labs/graphify@b90b9df7949bd04a15b40a1624af85d0a9cfdf04"
TARGETS = {"aiohttp": "https://github.com/aio-libs/aiohttp", "fastify": "https://github.com/fastify/fastify",
           "zod": "https://github.com/colinhacks/zod", "saleor": "https://github.com/saleor/saleor"}
SALEOR_SPLITS = 3                                   # Graphify's Saleor builds run as three parallel parts, as published
LOCKS = os.path.join(HERE, "env")
EMBED_MODEL, EMBED_REVISION = "BAAI/bge-base-en-v1.5", "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a"
EMBED_FILES = ["config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"]


def sh(cmd, log=None, **kw):
    print("  $", " ".join(cmd), flush=True)
    if log:
        with open(log, "w") as f:
            return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, **kw)
    return subprocess.run(cmd, check=True, **kw)


def venv(work, name, spec, check):
    """A Python 3.12 environment with the evaluation's pinned libraries (env/<name>.lock.txt), then `spec` itself
    without dependencies. uv when present (it fetches Python 3.12 if needed), else python3.12 -m venv + pip."""
    env = os.path.join(work, "envs", name)
    py = os.path.join(env, "bin", "python")
    lock = os.path.join(LOCKS, f"{name}.lock.txt")
    if not os.path.exists(py):
        if shutil.which("uv"):
            sh(["uv", "venv", "-q", "-p", "3.12", env])
            sh(["uv", "pip", "install", "-q", "-p", py, "-r", lock])
            sh(["uv", "pip", "install", "-q", "-p", py, "--no-deps", spec])
        else:
            base = shutil.which("python3.12") or sys.exit("needs uv, or python3.12 on PATH")
            sh([base, "-m", "venv", env])
            sh([py, "-m", "pip", "install", "-q", "--upgrade", "pip"])
            sh([py, "-m", "pip", "install", "-q", "-r", lock])
            sh([py, "-m", "pip", "install", "-q", "--no-deps", spec])
    version = subprocess.run([py, "-c", check], capture_output=True, text=True, check=True).stdout.strip()
    print(f"  {name}: {version}")
    return env


def embedding_model(work, py):
    """Model D's embedding model at the revision the evaluation used, in a Hugging Face cache of its own, made the
    default there so Model D's offline load picks exactly it."""
    hf = os.path.join(work, "hf")
    ref = os.path.join(hf, "hub", "models--" + EMBED_MODEL.replace("/", "--"), "refs", "main")
    if not os.path.exists(ref) or open(ref).read().strip() != EMBED_REVISION:
        code = ("import sys; from huggingface_hub import snapshot_download; "
                "snapshot_download(sys.argv[1], revision=sys.argv[2], allow_patterns=sys.argv[3:])")
        sh([py, "-c", code, EMBED_MODEL, EMBED_REVISION, *EMBED_FILES], env={**os.environ, "HF_HOME": hf})
        os.makedirs(os.path.dirname(ref), exist_ok=True)
        open(ref, "w").write(EMBED_REVISION)
    print(f"  {EMBED_MODEL} at {EMBED_REVISION[:7]}")
    return hf


def target(work, name, questions):
    """A full clone of the target repository holding every commit the questions need."""
    repo = os.path.join(work, "targets", name)
    if not os.path.isdir(os.path.join(repo, ".git")):
        sh(["git", "clone", "-q", TARGETS[name], repo])
    need = sorted({q[k] for q in questions for k in ("parent", "hash") if k in q})
    missing = [c for c in need if subprocess.run(["git", "-C", repo, "cat-file", "-e", c + "^{commit}"],
                                                 capture_output=True).returncode]
    if missing:
        sh(["git", "-C", repo, "fetch", "-q", "origin", *missing])
    return repo


def compare(name):
    """(identical lists, rows, (top1, top5) published, (top1, top5) now) for one result file; baselines per method."""
    old, new = json.load(open(os.path.join(PUBLISHED, name))), json.load(open(os.path.join(RESULTS, name)))
    pairs = [(f"{name}:{k}", old[k], new[k]) for k in old] if isinstance(old, dict) else [(name, old, new)]
    out = []
    for label, a, b in pairs:
        same = sum(x["files"] == y["files"] for x, y in zip(a, b))
        score = lambda rows: (sum(r["top1"] for r in rows), sum(r["top5"] for r in rows))
        out.append((label, same, len(a), len(b), score(a), score(b)))
    return out


def main():
    global RESULTS
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", default=os.path.abspath("repro-work"))
    ap.add_argument("--repos", default="aiohttp,fastify,zod,saleor")
    ap.add_argument("--tools", default="modeld,graphify,baselines")
    a = ap.parse_args()
    work, repos, tools = os.path.abspath(a.work), a.repos.split(","), a.tools.split(",")
    RESULTS = os.path.join(work, "results"); os.makedirs(RESULTS, exist_ok=True)
    logs = os.path.join(work, "logs"); os.makedirs(logs, exist_ok=True)
    t0 = time.time()

    print("1. Tools at the evaluated commits")
    envs = {}
    if "modeld" in tools:
        envs["modeld"] = venv(work, "modeld", MODELD, "import ocm; print('model-d', ocm.__version__)")
        hf = embedding_model(work, os.path.join(envs["modeld"], "bin", "python"))
    if "graphify" in tools:
        envs["graphify"] = venv(work, "graphify", GRAPHIFY, "from importlib.metadata import version; print('graphifyy', version('graphifyy'))")

    print("2. Target repositories")
    qfile = lambda r: os.path.join(BENCH, f"q_{r}.json")
    targets = {r: target(work, r, json.load(open(qfile(r)))) for r in repos}

    print("3. Runs")
    env = {**os.environ, "GRAPHIFY": os.path.join(envs.get("graphify", ""), "bin", "graphify")}
    if "modeld" in tools:                                                # the pinned model, and nothing fetched
        env.update({"HF_HOME": hf, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "OCM_OFFLINE": "1"})
    mdpy = os.path.join(envs.get("modeld", ""), "bin", "python")
    run = lambda script: os.path.join(BENCH, script)
    jobs, produced = [], []
    for r in repos:
        scratch = lambda tool: os.path.join(work, "run", f"{tool}_{r}")
        if r == "saleor":                                                  # the team replay
            if "modeld" in tools:
                jobs.append(([mdpy, run("run_modeld_team.py"), targets[r], qfile(r), os.path.join(RESULTS, "team_modeld.json"),
                              os.path.join(work, "run", "saleor_embed.sqlite")], "team_modeld.json"))
            if "graphify" in tools:
                for i in range(SALEOR_SPLITS):
                    jobs.append(([sys.executable, run("run_graphify.py"), targets[r], os.path.join(BENCH, f"q_saleor_g{i}.json"),
                                  os.path.join(RESULTS, f"team_graphify_{i}.json"), scratch(f"graphify{i}")], f"team_graphify_{i}.json"))
            if "baselines" in tools:
                jobs.append(([sys.executable, run("run_baselines.py"), targets[r], qfile(r), os.path.join(RESULTS, "team_baselines.json"),
                              scratch("baselines")], "team_baselines.json"))
            continue
        if "modeld" in tools:
            jobs.append(([mdpy, run("run_modeld.py"), targets[r], qfile(r), os.path.join(RESULTS, f"modeld_{r}.json"), scratch("modeld")],
                         f"modeld_{r}.json"))
        if "graphify" in tools:
            jobs.append(([sys.executable, run("run_graphify.py"), targets[r], qfile(r), os.path.join(RESULTS, f"graphify_{r}.json"),
                          scratch("graphify")], f"graphify_{r}.json"))
        if "baselines" in tools:
            jobs.append(([sys.executable, run("run_baselines.py"), targets[r], qfile(r), os.path.join(RESULTS, f"baselines_{r}.json"),
                          scratch("baselines")], f"baselines_{r}.json"))
    for cmd, _ in jobs:
        os.makedirs(cmd[-1] if not cmd[-1].endswith(".sqlite") else os.path.dirname(cmd[-1]), exist_ok=True)
    # Graphify's parts run side by side (as published); everything else one at a time.
    procs = []
    for cmd, name in jobs:
        print("  $", " ".join(cmd), flush=True)
        procs.append((subprocess.Popen(cmd, stdout=open(os.path.join(logs, name + ".log"), "w"), stderr=subprocess.STDOUT, env=env), name))
        if "run_graphify.py" not in cmd[1] or not name.startswith("team_graphify"):
            procs[-1][0].wait()
    failed = [name for p, name in procs if p.wait() != 0]
    produced = [name for _, name in jobs if name not in failed]
    for name in failed:
        print(f"  FAILED: {name} (see {os.path.join(logs, name + '.log')})")

    print("4. Against the published rows")
    ok = not failed
    for name in produced:
        for label, same, n_old, n_new, s_old, s_new in compare(name):
            match = s_old == s_new and n_old == n_new
            ok &= match
            print(f"  {'same ' if match else 'DIFF '} {label:<26} identical answers {same}/{n_old}   "
                  f"right first, top 5: published {s_old[0]}, {s_old[1]}   now {s_new[0]}, {s_new[1]}")
    if any(not n.startswith("team_") for n in produced) and set(repos) >= {"aiohttp", "fastify", "zod"}:
        sh([sys.executable, run("analyze.py")], env={**os.environ, "RESULTS": RESULTS})
    if any(n.startswith("team_") for n in produced) and {"modeld", "graphify", "baselines"} <= set(tools):
        sh([sys.executable, run("analyze_team.py")], env={**os.environ, "RESULTS": RESULTS})
    print(f"\n{'REPRODUCED' if ok else 'NOT REPRODUCED'}: every right-first and top-5 count "
          f"{'matches' if ok else 'does not match'} the published rows ({(time.time() - t0) / 60:.0f} min).")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
