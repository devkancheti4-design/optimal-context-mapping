"""Every table, from the answers in results/. A program grades each answer against the code at that commit (grade.py); tokens and dollars are the API's own counts.

    <modeld python> -I score.py [repo ...]"""
import glob, json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import grade as G  # noqa: E402

ARMS = ("alone", "notes", "map", "modeld")
mean = lambda v: sum(v) / len(v) if v else 0.0


def boot(v, n=10000, seed=0):
    rng, N = random.Random(seed), len(v)
    ms = sorted(sum(rng.choices(v, k=N)) / N for _ in range(n))
    return ms[int(.025 * n)], ms[int(.975 * n)]


def load(repo):
    """Every answer with its grade: [{repo, arm, session, fact fields..., grade, tokens}]"""
    facts = {f["id"]: f for f in C.rows(C.data(repo, "facts.jsonl"))}
    out = []
    for p in sorted(glob.glob(C.results(repo, "*_S?.jsonl"))):
        arm, session = os.path.basename(p)[:-6].rsplit("_S", 1)
        session = int(session)
        for r in C.rows(p):
            f = facts[r["id"]]
            late = session == 4
            truth = f["new_path"] if late and f["kind"] == "where" else f["new_value"] if late else f["value"]
            old = f["value"] if late and f["status"] == "changed" else None
            out.append({**r, "repo": repo, "arm": arm, "session": session, "kind": f["kind"], "role": f["role"], "status": f["status"], "grade": G.grade(f["kind"], truth, r["answer"], old), "tokens": r["tokens_in"] + r["tokens_out"]})
    return out


def line(name, rows):
    n = len(rows)
    if not n:
        return f"{name:<34} (none)"
    right = sum(r["grade"] == "right" for r in rows)
    tokens = sum(r["tokens"] for r in rows)
    return (f"{name:<34} n={n:<4} right {100 * right / n:5.1f}%  stale {100 * mean([r['grade'] == 'stale' for r in rows]):5.1f}%  hedged {100 * mean([r['grade'] == 'hedged' for r in rows]):4.1f}%  "
            f"requests {mean([r['requests'] for r in rows]):5.2f}  tokens {tokens / n:8.0f}  ${mean([r['usd'] for r in rows]):.5f}  tokens per right {tokens / right if right else float('inf'):8.0f}")


def paired(rows, a, b, session):
    """b's tokens as a multiple of a's cost, and a's right minus b's, on the same facts in the same session."""
    x = {(r["repo"], r["id"]): r for r in rows if r["arm"] == a and r["session"] == session}
    y = {(r["repo"], r["id"]): r for r in rows if r["arm"] == b and r["session"] == session}
    keys = sorted(set(x) & set(y))
    if not keys:
        return f"{a} vs {b} S{session}: no pairs"
    rng = random.Random(0)
    ratios = []
    for _ in range(5000):
        s = rng.choices(keys, k=len(keys))
        ratios.append(sum(y[k]["tokens"] for k in s) / max(1, sum(x[k]["tokens"] for k in s)))
    ratios.sort()
    d = [(x[k]["grade"] == "right") - (y[k]["grade"] == "right") for k in keys]
    lo, hi = boot(d)
    return (f"{a} vs {b} S{session}, n={len(keys)}: {b} uses {sum(y[k]['tokens'] for k in keys) / max(1, sum(x[k]['tokens'] for k in keys)):.2f}x {a}'s tokens ({ratios[125]:.2f} to {ratios[4875]:.2f}); "
            f"right, {a} minus {b}: {100 * mean(d):+.1f} points ({100 * lo:+.1f} to {100 * hi:+.1f})")


def first_time(rows):
    """Model D's first time against an agent alone, which never has anything but a first time: the same facts, in the wordings each arm got."""
    x = {(r["repo"], r["id"]): r for r in rows if r["arm"] == "alone" and r["session"] == 2 and r["role"] == "taught"}
    y = {(r["repo"], r["id"]): r for r in rows if r["arm"] == "modeld" and r["session"] == 1 and r["role"] == "taught"}
    keys = sorted(set(x) & set(y))
    if not keys:
        return "alone S2 vs modeld S1: no pairs"
    d = [(y[k]["grade"] == "right") - (x[k]["grade"] == "right") for k in keys]
    lo, hi = boot(d)
    return (f"first time: modeld S1 uses {sum(y[k]['tokens'] for k in keys) / max(1, sum(x[k]['tokens'] for k in keys)):.2f}x the tokens of alone, n={len(keys)}; "
            f"right, modeld minus alone: {100 * mean(d):+.1f} points ({100 * lo:+.1f} to {100 * hi:+.1f})")


def main(repos):
    rows = [r for repo in repos for r in load(repo)]
    print(f"repositories: {', '.join(repos)}; answers: {len(rows)}; failed calls, counted as not right: {sum(bool(r.get('error')) for r in rows)}; spent so far ${C.spent():.3f}\n")
    labels = {1: "S1 the first time", 2: "S2 the next day", 3: "S3 a teammate", 4: "S4 a year later", 5: "S5 the next day, with 200 more lessons on disk"}
    for session in (1, 2, 3, 4, 5):
        print(labels[session] + " (the taught facts)")
        for arm in ARMS:
            print("  " + line(arm, [r for r in rows if r["arm"] == arm and r["session"] == session and r["role"] == "taught"]))
        print()
    print("S4 by what happened to the fact")
    for status in ("same", "moved", "changed"):
        for arm in ARMS:
            print("  " + line(f"{status}, {arm}", [r for r in rows if r["arm"] == arm and r["session"] == 4 and r["status"] == status and r["role"] == "taught"]))
    print("\nS4 at each repository's own mix of same, moved and changed, from all its checkable facts")
    for arm in ARMS:
        per = []
        for repo in repos:
            rates = json.load(open(C.data(repo, "rates.json")))
            live = {s: sum(k.get(s, 0) for k in rates.values()) for s in ("same", "moved", "changed")}
            v = {s: [r for r in rows if r["repo"] == repo and r["arm"] == arm and r["session"] == 4 and r["status"] == s and r["role"] == "taught"] for s in live}
            total = sum(live[s] for s in live if v[s])
            if total:
                per.append((sum(live[s] / total * mean([r["grade"] == "right" for r in v[s]]) for s in live if v[s]), sum(live[s] / total * mean([r["grade"] == "stale" for r in v[s]]) for s in live if v[s]),
                            sum(live[s] / total * mean([r["tokens"] for r in v[s]]) for s in live if v[s])))
        if per:
            right, stale, tokens = (mean([p[i] for p in per]) for i in range(3))
            print(f"  {arm:<8} right {100 * right:5.1f}%  stale {100 * stale:5.1f}%  tokens {tokens:7.0f}  tokens per right {tokens / right if right else float('inf'):7.0f}")
    print("\nS2 new questions, never asked before")
    for role in ("sibling", "unrelated"):
        for arm in ARMS:
            print("  " + line(f"{role}, {arm}", [r for r in rows if r["arm"] == arm and r["session"] == 2 and r["role"] == role]))
    print("\nThe named control: the question gives the code's exact name")
    for session in (1, 2):
        for arm in ARMS:
            print("  " + line(f"S{session}, {arm}", [r for r in rows if r["arm"] == arm and r["session"] == session and r["role"] == "named"]))
    print("\nWhat the model already knows, with no code and no tools")
    print("  " + line("guess, first wording", [r for r in rows if r["arm"] == "guess"]))
    print("\nModel D and the others, same facts")
    for b in ("modeld",):
        for a in ("alone", "notes", "map"):
            for s in (1, 2, 3, 4, 5):
                if (s in (1, 3, 5) and a == "notes") or (s in (2, 4) and a in ("alone", "notes", "map")):
                    print("  " + paired([r for r in rows if r["role"] == "taught"], a, b, s))
    print("  " + first_time(rows))
    print("\nHow Model D answered")
    for s in (1, 2, 3, 4, 5):
        v = [r for r in rows if r["arm"] == "modeld" and r["session"] == s and r["role"] == "taught"]
        if v:
            print(f"  S{s}: one read {sum(r['path'] == 'read' for r in v)} of {len(v)}, explored {sum(r['path'] != 'read' for r in v)}")
    return rows


def predictions(rows):
    """PROTOCOL.md's predictions, each held or failed. Anything about the notes file uses only the repositories where its arm finished."""
    done = {r["repo"] for r in rows if r["arm"] == "notes" and r["session"] == 5}
    t = [r for r in rows if r["role"] == "taught"]
    pick = lambda arm, s, test=lambda r: True, only=None: {(r["repo"], r["id"]): r for r in t if r["arm"] == arm and r["session"] == s and test(r) and (only is None or r["repo"] in only)}
    tokens = lambda d, keys: sum(d[k]["tokens"] for k in keys)
    right = lambda d, keys: mean([d[k]["grade"] == "right" for k in keys])
    reads = lambda d: mean([r["path"] == "read" for r in d.values()])
    stale = lambda d: mean([r["grade"] == "stale" for r in d.values()])

    def against(a, sa, b, sb, test=lambda r: True, only=None):
        x, y = pick(a, sa, test, only), pick(b, sb, test, only)
        keys = sorted(set(x) & set(y))
        return tokens(x, keys) / tokens(y, keys), right(x, keys) - right(y, keys), x, y, len(keys)

    show = lambda name, ok, text: print(f"  {name}: {'HELD' if ok else 'FAILED'}. {text}")
    print("\nPredictions")
    r, d, *_, n = against("modeld", 1, "alone", 2)
    show("P1 first time", r <= .5 and d >= -.05, f"{r:.2f}x alone's tokens (needs at most 0.50), right {100 * d:+.1f} points (needs at least -5), n={n}")
    r, d, x, _, n = against("modeld", 2, "alone", 2)
    show("P2 next day", reads(x) >= .6 and r <= .2 and d >= -.05, f"one read {100 * reads(x):.0f}% (needs at least 60%), {r:.2f}x alone's tokens (needs at most 0.20), right {100 * d:+.1f} points (needs at least -5), n={n}")
    r, d, *_, n = against("modeld", 3, "modeld", 2)
    show("P3 teammate", r <= 1.25 and d >= -.05, f"{r:.2f}x session 2's tokens (needs at most 1.25), right {100 * d:+.1f} points (needs at least -5), n={n}")
    kept = lambda f: f["status"] in ("same", "moved")
    r, d, x, _, n = against("modeld", 4, "alone", 4, kept)
    show("P4 a year later, facts that stayed true", reads(x) >= .4 and r <= .5 and d >= -.05, f"one read {100 * reads(x):.0f}% (needs at least 40%), {r:.2f}x alone's tokens (needs at most 0.50), right {100 * d:+.1f} points (needs at least -5), n={n}")
    changed = lambda f: f["status"] == "changed"
    m, o = pick("modeld", 4, changed), pick("notes", 4, changed, done)
    show("P5 facts that changed", stale(m) <= .1 and stale(o) >= .5, f"Model D stale {100 * stale(m):.1f}% of {len(m)} (needs at most 10%), notes stale {100 * stale(o):.1f}% of {len(o)} (needs at least 50%)")
    r, *_, n = against("modeld", 2, "notes", 2, only=done)
    show("P6 notes cheaper next day, a prediction against Model D", r > 1, f"Model D uses {r:.2f}x the notes file's tokens, n={n}")
    r, d, *_, n = against("modeld", 5, "notes", 5, only=done)
    show("P7 more on disk", r < 1 and d >= -.05, f"{r:.2f}x the notes file's tokens (needs under 1), right {100 * d:+.1f} points (needs at least -5), n={n}")
    r, d, *_, n = against("modeld", 2, "map", 2)
    show("P8 what memory adds", r <= .5, f"{r:.2f}x memory-off tokens (needs at most 0.50); right {100 * d:+.1f} points, n={n}")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(C.data("*", "facts.jsonl")))
    predictions(main(names))
