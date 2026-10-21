"""Tool-free baselines on the same snapshots:
- grep: files ranked by how many distinct question words they contain (what a quick agent grep does);
- bm25: classic BM25 over code files, identifiers split on camelCase and snake_case;
- prior: files ranked by how many earlier fix commits touched them (no question at all, a floor)."""
import collections, json, math, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
from common import snapshot, ranked_code_files, score, CODE

STOP = set("the and for with from that this when into not are was were has have had but its use using used should would "
           "could can will fix fixes fixed bug issue make makes made allow allows add adds added when which".split())


def words(text):
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3 and w not in STOP]


def code_files(root):
    for d, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in (".git", "node_modules", "dist", "build")]
        for f in fs:
            if f.endswith(CODE):
                p = os.path.join(d, f)
                yield os.path.relpath(p, root), p


def run(repo, Q, work):
    rows = {"grep": [], "bm25": [], "prior": []}
    snap = os.path.join(work, "snap")
    for q in Q:
        snapshot(repo, q["parent"], snap)
        docs = {}
        for rel, p in code_files(snap):
            try:
                docs[rel] = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                pass
        terms = list(dict.fromkeys(words(q["question"])))
        low = {r: t.lower() for r, t in docs.items()}
        g = sorted(((-sum(1 for w in terms if w in t), -sum(t.count(w) for w in terms), r) for r, t in low.items()))
        grep = [r for a, b, r in g if a < 0]
        toks = {r: collections.Counter(words(t)) for r, t in docs.items()}
        N = len(toks); avg = sum(sum(c.values()) for c in toks.values()) / max(N, 1)
        df = collections.Counter(w for c in toks.values() for w in set(c))
        def bm25(c, k1=1.2, b=0.75):
            L = sum(c.values())
            return sum(math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * c[w] * (k1 + 1) / (c[w] + k1 * (1 - b + b * L / avg))
                       for w in terms if c.get(w))
        bm = [r for s, r in sorted(((-bm25(c), r) for r, c in toks.items())) if s < 0]
        log = subprocess.run(["git", "-C", repo, "log", "--no-merges", "--format=@@%s", "--name-only", q["parent"], "-n", "3000"],
                             capture_output=True, text=True).stdout
        cnt, fixing = collections.Counter(), False
        for line in log.split("\n"):
            if line.startswith("@@"):
                fixing = bool(re.search(r"^(fix|bug ?fix|hotfix)", line[2:], re.I))
            elif fixing and line in docs:
                cnt[line] += 1
        prior = [r for r, _ in cnt.most_common(20)]
        for name, files in (("grep", grep), ("bm25", bm), ("prior", prior)):
            files = ranked_code_files(files)
            rows[name].append({"hash": q["hash"][:10], "question": q["question"], "gold": q["gold"], "files": files[:10],
                               **score(files, q["gold"])})
    return rows


if __name__ == "__main__":
    repo, qfile, out, work = sys.argv[1:5]
    rows = run(repo, json.load(open(qfile)), work)
    json.dump(rows, open(out, "w"), indent=1)
    for k, v in rows.items():
        print(k, "top1", sum(r["top1"] for r in v), "top5", sum(r["top5"] for r in v), "of", len(v))
