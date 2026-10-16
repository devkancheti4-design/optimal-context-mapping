"""Model D pricing from measured cost parameters (PROTOCOL_TEAM_YEAR and the published evidence).

    python pricing.py [--A 0.033 --K 0.024 --E 0.0005] [--nu 0.6 0.4 0.3]

The learning law (the site's form, nu = novelty): S = A / ((1 - nu) * E + nu * K).
- A: the agent alone, $ per question. K: Model D on a new question. E: a learned question (one read).
- Spend per engineer per month: Scale VP's startup survey, $577 median, $1,040 mean (code generation).
- Saving per engineer per month = spend * (1 - 1/S): every dollar of agent spend is assumed to be the kind Model D
  serves. For mixed work, scale by the share of spend that is codebase questions and search.
- The price is set so that a customer at the floor (all-new work, nu = 1) and median spend still keeps at least 3x
  what they pay."""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--A", type=float, default=0.033); ap.add_argument("--K", type=float, default=0.024)
ap.add_argument("--E", type=float, default=0.0005); ap.add_argument("--nu", type=float, nargs="+", default=[1.0, 0.6, 0.4, 0.3])
ap.add_argument("--share", type=float, default=1.0, help="share of agent spend that is codebase questions and search")
a = ap.parse_args()
SPEND = {"median": 577.0, "mean": 1040.0}
print(f"A ${a.A}  K ${a.K}  E ${a.E}  share of spend served {a.share:.0%}\n")
print(f"{'novelty nu':>10} {'saving S':>9} {'bill cut':>9} {'saved / eng / mo (median)':>27} {'(mean)':>8}")
floor = None
for nu in a.nu:
    s = a.A / ((1 - nu) * a.E + nu * a.K)
    cut = 1 - 1 / s
    m, mean = SPEND["median"] * a.share * cut, SPEND["mean"] * a.share * cut
    floor = m if floor is None else floor
    print(f"{nu:>10.2f} {s:>8.2f}x {cut:>8.0%} {m:>26,.0f} {mean:>8,.0f}")
print(f"\nfloor saving (nu = {a.nu[0]}, median spend): ${floor:,.0f} per engineer per month")
for price in (29, 49, 79, 99):
    print(f"  at ${price}/seat/month the customer keeps {floor / price:.1f}x what they pay, at the floor")
