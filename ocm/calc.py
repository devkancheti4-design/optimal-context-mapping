"""The savings calculator: expected model requests with and without the workspace, from per-question costs measured in
live tests (ocm/data/pools.json), with a 95% bootstrap interval.

    python -m ocm calc --repeat 0.5 --deep 0.3 [--questions-per-month 16800]

  --repeat   share of questions that repeat something a teammate already asked (in any words)
  --deep     share of questions that are multi-file deep dives (the rest are lookups and short scans)
Requests per question = search-and-read calls + a fixed session overhead per question (both arms) + batched teaching
(one call per session of about six questions, workspace arm). This arithmetic predicted a held-out live run before it
ran: 83 requests predicted, 84 measured; 1.66x predicted, 1.66x measured (results/RESULTS.md)."""
import argparse, json, os, random

POOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pools.json")      # shipped inside the package


def expect(P, p, d, over, teach, rng=None):
    pick = (lambda xs: [rng.choice(xs) for _ in xs]) if rng else (lambda xs: xs)
    m = {k: sum(x) / len(x) for k, x in ((k, pick(v)) for k, v in P.items())}
    def arm(a):
        look = (1 - p) * m[f"lookup first {a}"] + p * m[f"lookup repeat {a}"]
        deep = (1 - p) * m[f"deep first {a}"] + p * m[f"deep repeat {a}"]
        return (1 - d) * look + d * deep + over + (teach if a == "memory" else 0)
    return arm("tools"), arm("memory")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ocm calc")
    ap.add_argument("--repeat", type=float); ap.add_argument("--deep", type=float, default=0.0)
    ap.add_argument("--questions-per-month", type=int, default=0); ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--table", action="store_true", help="the published table: repeats 0 to 90%%, with and without 30%% deep dives")
    a = ap.parse_args(argv)
    D = json.load(open(POOLS)); P = D["pools"]; over, teach = D["overhead per question"], D["teach per question, batched"]
    if a.table:                                     # one generator over every row, in this order, as the published table
        rng = random.Random(a.seed); q = a.questions_per_month or 16800
        print(f"{'deep dives':>10} {'repeats':>8} {'without':>8} {'with':>6} {'saving':>7}  95% interval   fewer per month at {q:,} questions")
        for d in (0.0, 0.3):
            for p in (0.0, 0.25, 0.5, 0.75, 0.9):
                t, m = expect(P, p, d, over, teach)
                bs = sorted(x / y for x, y in (expect(P, p, d, over, teach, rng) for _ in range(5000)))
                print(f"{d:>10.0%} {p:>8.0%} {t:>8.2f} {m:>6.2f} {t / m:>6.2f}x  [{bs[125]:.2f}, {bs[4875]:.2f}]   {q * (t - m):>9,.0f}")
        return
    if a.repeat is None:
        ap.error("--repeat is required (or use --table)")
    t, m = expect(P, a.repeat, a.deep, over, teach)
    rng = random.Random(a.seed); boots = sorted(x / y for x, y in (expect(P, a.repeat, a.deep, over, teach, rng) for _ in range(5000)))
    print(f"requests per question: without the workspace {t:.2f}, with it {m:.2f}")
    print(f"saving: {t / m:.2f}x fewer requests (95% interval {boots[125]:.2f} to {boots[4875]:.2f})")
    if a.questions_per_month:
        q = a.questions_per_month
        print(f"per month at {q:,} questions: {q * t:,.0f} requests without, {q * m:,.0f} with, {q * (t - m):,.0f} fewer")
    print("billed input falls less than requests (measured: 1.40x when requests fell 1.66x), because readouts add reading.")
