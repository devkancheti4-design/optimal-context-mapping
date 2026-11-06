"""Every number in RESULTS.md, from results/ (see pack.py). Published scores are typed in from the benchmark at 9e4d689: README.md, paper/main.tex
and docs/community_results.md.

    <modeld python> -I report.py > report.txt"""
import collections, gzip, json, os, random

from ocm.units import is_test

H = os.path.dirname(os.path.abspath(__file__))
TRACKS = ("trace2code", "edit2ripple", "comment2context", "code2test")
MAIN, OFF = "modeld-0.5.3", "modeld-0.5.3-trail-off"
OFFICIAL = {"Qwen3-Embedding-4B": (.6306, .2379, .3409), "Qwen3-Embedding-8B": (.7029, .2336, .3732), "pplx-embed-v1-4b": (.6072, .2267, .3549),
            "RepoMap": (.6333, .2158, .3788), "nomic-embed-code": (.5244, .1986, .2781), "jina-code-embeddings-0.5b": (.4823, .1914, .2783),
            "Lexical": (.4940, .1574, .2650), "BM25": (.4452, .1520, .2051)}                      # Recall@20, MRR, BCY@8k
COMMUNITY = {"Oko 0.9.1": (.7019, .4043, .5326), "CodeNib dense": (.5736, .2425, .3355), "CodeNib hybrid": (.5972, .2144, .3101),
             "CodeNib Zoekt": (.4400, .1605, .2569), "CodeNib BM25": (.3889, .1211, .1659), "CodeNib graph expansion": (.3498, .1197, .1659)}
BEST_MRR = {"trace2code": .2742, "comment2context": .3043, "code2test": .3225, "edit2ripple": .2877}
OKO_MRR = {"trace2code": .736, "comment2context": .280, "code2test": .279, "edit2ripple": .226}
LANG = {"caddyserver/caddy": "Go", "gin-gonic/gin": "Go", "etcd-io/etcd": "Go", "tokio-rs/tokio": "Rust", "clap-rs/clap": "Rust", "astral-sh/ruff": "Rust",
        "vitejs/vite": "TypeScript/JavaScript", "vuejs/core": "TypeScript/JavaScript", "microsoft/playwright": "TypeScript/JavaScript",
        "eslint/eslint": "TypeScript/JavaScript", "spring-projects/spring-boot": "Java", "mockito/mockito": "Java"}


def load(label):
    return [json.loads(l) for l in gzip.open(f"{H}/results/{label}.jsonl.gz", "rt")]


def bcy(label, t):
    return json.load(open(f"{H}/results/{label}/v2_{t}_bcy.json"))["runs"][0]["overall"]


def score(gold, files):
    pos = {f: i + 1 for i, f in enumerate(files)}
    ranks = [pos[g] for g in gold if g in pos]
    return {"MRR": 1 / min(ranks) if ranks else 0, **{f"Recall@{k}": sum(r <= k for r in ranks) / len(gold) for k in (5, 10, 20)}}


def boot(v, n=10000, seed=7):
    rng, N = random.Random(seed), len(v)
    ms = sorted(sum(rng.choices(v, k=N)) / N for _ in range(n))
    return ms[int(.025 * n)], ms[int(.975 * n)]


mean = lambda v: sum(v) / len(v)
ci = lambda v: "%.4f (%.4f to %.4f)" % (mean(v), *boot(v))
dci = lambda v: "%+.4f (%+.4f to %+.4f)" % (mean(v), *boot(v))
m = lambda rows, k: mean([r["metrics"][k] for r in rows])
main, off = load(MAIN), load(OFF)
of = lambda rows, t: [r for r in rows if r["task_type"] == t]
print("# Agent Retrieval Bench, Model D 0.5.3\n\n## Integrity")
for label, rows in ((MAIN, main), (OFF, off)):
    assert len({r["sample_id"] for r in rows}) == len(rows) == 345
    assert all(abs(score(r["gold_files"], r["ranked_files"])[k] - r["metrics"][k]) < 1e-9 for r in rows for k in ("MRR", "Recall@5", "Recall@10", "Recall@20"))
    print(label, "345 distinct samples; MRR and Recall recomputed from the stored list match the benchmark's own sample_metrics")
gold_all = [g for r in main for g in r["gold_files"]]
print("gold files %d, not in Model D's list %d" % (len(gold_all), sum(v is None for r in main for v in r["gold_ranks"].values())))

print("\n## Per track, and all 345 (BCY over all 345 is the sample-weighted mean of the tracks)")
print("track n MRR(95%) R@5 R@10 R@20 BCY@4k BCY@8k BCY@16k BCY@32k first-readout-has-gold first-readout-tokens best-official-MRR Oko-MRR")
BUDGETS = (4000, 8000, 16000, 32000)
for t in TRACKS:
    r, b = of(main, t), bcy(MAIN, t)
    print(t, len(r), ci([x["metrics"]["MRR"] for x in r]), *["%.4f" % m(r, f"Recall@{k}") for k in (5, 10, 20)], *["%.4f" % b[f"BCY@{k}"] for k in BUDGETS],
          "%.3f" % mean([x["gold_in_first_readout"] for x in r]), "%.0f" % mean([x["first_readout_tokens"] for x in r]), BEST_MRR[t], OKO_MRR[t])
ALLB = {k: sum(bcy(MAIN, t)[f"BCY@{k}"] * len(of(main, t)) for t in TRACKS) / 345 for k in BUDGETS}
print("all", 345, ci([x["metrics"]["MRR"] for x in main]), *["%.4f" % m(main, f"Recall@{k}") for k in (5, 10, 20)], *["%.4f" % ALLB[k] for k in BUDGETS],
      "%.3f" % mean([x["gold_in_first_readout"] for x in main]), "%.0f" % mean([x["first_readout_tokens"] for x in main]), .2379, .4043)
print("R@20 over all 345:", ci([x["metrics"]["Recall@20"] for x in main]))

print("\n## Rank on each measure")
ours = (m(main, "Recall@20"), m(main, "MRR"), ALLB[8000])
for i, name in enumerate(("Recall@20", "MRR", "BCY@8k")):
    table = sorted([(v[i], k) for k, v in OFFICIAL.items()] + [(ours[i], "MODEL D")], reverse=True)
    wider = sorted([(v[i], k) for k, v in {**OFFICIAL, **COMMUNITY}.items()] + [(ours[i], "MODEL D")], reverse=True)
    print(name, "rank among 8 official + Model D: %d of 9; with Oko 0.9.1 and CodeNib: %d of 15" % ([k for _, k in table].index("MODEL D") + 1, [k for _, k in wider].index("MODEL D") + 1))
    print("   ", ", ".join("%s %.4f" % (k, v) for v, k in table))

print("\n## Predictions")
t2c, c2t = m(of(main, "trace2code"), "MRR"), m(of(main, "code2test"), "MRR")
per = {t: m(of(main, t), "MRR") for t in TRACKS}
print("R1 trace2code MRR > .2742:", "%.4f" % t2c, "HELD" if t2c > .2742 else "FAILED")
print("R2 trace2code MRR < .736:", "%.4f" % t2c, "HELD" if t2c < .736 else "FAILED")
print("R3 all 345 MRR > .2379 and < .4043:", "%.4f" % m(main, "MRR"), "HELD" if .2379 < m(main, "MRR") < .4043 else "FAILED")
print("R4 code2test weakest and < .3225:", {k: round(v, 4) for k, v in per.items()}, "HELD" if min(per, key=per.get) == "code2test" and c2t < .3225 else "FAILED")

print("\n## Diagnostic: the tests-after-code rule off (OCM_TESTS_TRAIL=off). The rule works inside one readout, on queries it doesn't read as about tests")
offs = {r["sample_id"]: r for r in off}
print("track rule-off-MRR queries-about-tests samples-changed better-with-rule-off worse-with-rule-off MRR(off-on)")
for t in TRACKS + ("all",):
    rows = main if t == "all" else of(main, t)
    d = [offs[r["sample_id"]]["metrics"]["MRR"] - r["metrics"]["MRR"] for r in rows]
    print(t, "%.4f" % mean([offs[r["sample_id"]]["metrics"]["MRR"] for r in rows]), "%d/%d" % (sum(r["query_about_tests"] for r in rows), len(rows)),
          sum(abs(x) > 1e-9 for x in d), sum(x > 1e-9 for x in d), sum(x < -1e-9 for x in d), dci(d))

print("\n## After the fact: what kind of file the task needs, and what Model D's top 5 holds")
for t in TRACKS:
    r = of(main, t)
    g = [bool(is_test(x)) for s in r for x in s["gold_files"]]
    print(t, "gold files that are tests %d/%d;" % (sum(g), len(g)), "tests in Model D's top 5: %.0f%%" % (100 * mean([mean([bool(is_test(x)) for x in s["ranked_files"][:5]]) for s in r])))

print("\n## After the fact: the saved lists reordered, not a run of Model D. Same files, tests moved to the end or the front of the whole list")
last = lambda f: [x for x in f if not is_test(x)] + [x for x in f if is_test(x)]
first = lambda f: [x for x in f if is_test(x)] + [x for x in f if not is_test(x)]
EST = {}
for t, name, move in (("trace2code", "tests last", last), ("code2test", "tests first", first)):
    r = of(main, t)
    moved = [score(s["gold_files"], move(s["ranked_files"])) for s in r]
    EST[t] = mean([x["MRR"] for x in moved])
    print(t, name, "MRR %.4f R@5 %.4f R@10 %.4f R@20 %.4f" % (EST[t], *[mean([x[f"Recall@{k}"] for x in moved]) for k in (5, 10, 20)]),
          "MRR change", dci([x["MRR"] - s["metrics"]["MRR"] for x, s in zip(moved, r)]))
n = {t: len(of(main, t)) for t in TRACKS}
print("all 345 with trace2code changed only: MRR %.4f" % (sum(EST.get(t, per[t]) * n[t] for t in TRACKS if t != "code2test") / 345 + per["code2test"] * n["code2test"] / 345))
print("all 345 with both changed: MRR %.4f" % (sum(EST.get(t, per[t]) * n[t] for t in TRACKS) / 345))
print("code2test queries name no task: the fields are changed_file, pr_title and pr_body, so tests-first needs the task from outside the query")

print("\n## After the fact: query length (the embedder reads 128 tokens including 2 special ones; run.py passes the whole query)")
print("queries over 126 tokens: %d of 345" % sum(r["query_tokens"] > 126 for r in main))
for t in TRACKS + ("all",):
    rows = main if t == "all" else of(main, t)
    for name, f in (("up to 126", lambda r: r["query_tokens"] <= 126), ("longer", lambda r: r["query_tokens"] > 126)):
        v = [r for r in rows if f(r)]
        if v:
            print(t, name, "n=%d MRR %.3f R@20 %.3f" % (len(v), m(v, "MRR"), m(v, "Recall@20")))

print("\n## After the fact: by language and repository, against a random order of the same list")


def random_mrr(n, g):
    total, none_yet = 0, 1.0
    for k in range(1, n - g + 2) if g else ():
        total += none_yet * g / (n - k + 1) / k
        none_yet *= (n - k + 1 - g) / (n - k + 1)
    return total


groups = collections.defaultdict(list)
for r in main:
    groups[LANG.get(r["repo"], "Python")].append(r)
for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    print(k, "n=%d MRR %.3f R@20 %.3f" % (len(v), m(v, "MRR"), m(v, "Recall@20")))
nogin = [r for r in main if r["repo"] != "gin-gonic/gin"]
print("without gin-gonic/gin: n=%d MRR %.4f R@20 %.4f" % (len(nogin), m(nogin, "MRR"), m(nogin, "Recall@20")))
rand = {r["sample_id"]: random_mrr(len(r["ranked_files"]), sum(v is not None for v in r["gold_ranks"].values())) for r in main}
print("all 345: MRR %.4f, random order %.4f; samples below their random-order expectation: %d" % (m(main, "MRR"), mean(list(rand.values())), sum(r["metrics"]["MRR"] < rand[r["sample_id"]] for r in main)))
repos = collections.defaultdict(list)
for r in main:
    repos[r["repo"]].append(r)
for k, v in sorted(repos.items(), key=lambda kv: -len(kv[1])):
    print(k, "n=%d MRR %.3f random %.3f R@20 %.3f" % (len(v), m(v, "MRR"), mean([rand[r["sample_id"]] for r in v]), m(v, "Recall@20")))

print("\n## Cost")
print("model calls: none. ask, next and the ranking per sample: mean %.2f s. index builds, all snapshots: %.0f s (includes a paused and resumed run, so indicative)" % (mean([r["ask_s"] for r in main]), sum(r["build_s"] for r in main)))
