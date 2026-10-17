"""Forecast Model D's saving on a repository from its own history (no model calls).

    python history.py <repo dir> [--since 2025-10-17] [--until 2026-10-17] [--out stream.json]

Fixes: non-merge commits whose subject starts with fix / fixes / fixed / bugfix, or cites "fix #N". Each fix's files are
the ones it changed, minus tests, docs, lockfiles, translations and snapshots (as in repo-proofs/METHOD.md).

From those it measures, in commit order:
- r: the share of fixes that touch a file an earlier fix in the window touched (file-level repetition);
- lam: fixes per month.

It forecasts with the learning law, S = A / ((1 - nu) E + nu K), calibrated on Django 2022 (evidence/team-year):
- nu = 1 - c * r, with c = 0.23 (range 0.13-0.38 across quarters): how much of the file-level repetition Model D
  turned into one-read answers;
- A / K = 1.80 (the saving with no learning at all), and E / A = 0.0044.
"""
import argparse, json, re, subprocess
from collections import OrderedDict

FIX = re.compile(r"^(fix(es|ed)?\b|bug ?fix|hotfix)|\bfix(es|ed)? #\d+", re.I)
SKIP = re.compile(r"(^|/)(tests?|__tests__|spec|specs|docs?|locales?|i18n|translations|__snapshots__|fixtures?)/"
                  r"|\.(md|mdx|rst|txt|adoc|snap|lock|min\.js)$|(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|go\.sum|"
                  r"Cargo\.lock|poetry\.lock|composer\.lock)$|(\.test\.|\.spec\.|_test\.go$|(^|/)test_[^/]*\.py$)", re.I)
A_OVER_K, E_OVER_A, C, C_LO, C_HI = 1.80, 0.0044, 0.23, 0.13, 0.38


def saving(nu):
    return 1 / ((1 - nu) * E_OVER_A + nu / A_OVER_K)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("repo"); ap.add_argument("--since", default="2025-10-17")
    ap.add_argument("--until", default="2026-10-17"); ap.add_argument("--out")
    a = ap.parse_args()
    log = subprocess.run(["git", "-C", a.repo, "log", "--no-merges", "--no-renames", "--reverse", f"--since={a.since}", f"--until={a.until}",
                          "--name-only", "--format=@@%H%x09%cs%x09%s"], capture_output=True, text=True, check=True).stdout
    fixes, cur = [], None
    for line in log.split("\n"):
        if line.startswith("@@"):
            h, d, subj = line[2:].split("\t", 2); cur = {"hash": h, "date": d, "raw": subj, "gold": []}
            if FIX.search(subj): fixes.append(cur)
        elif line.strip() and cur is not None and not SKIP.search(line.strip()):
            cur["gold"].append(line.strip())
    fixes = [f for f in fixes if f["gold"]]
    seen, rep = set(), []
    for f in fixes:
        rep.append(bool(set(f["gold"]) & seen)); seen |= set(f["gold"])
    n = len(fixes); r = sum(rep) / n if n else 0
    months = max(1e-9, (int(a.until[:4]) - int(a.since[:4])) * 12 + int(a.until[5:7]) - int(a.since[5:7]))
    nu = 1 - C * r
    out = OrderedDict(repo=a.repo, fixes=n, per_month=round(n / months, 1), files_per_fix=round(sum(len(f["gold"]) for f in fixes) / max(1, n), 2),
                      distinct_files=len(seen), r=round(r, 3), nu_pred=round(nu, 3), saving_pred=round(saving(nu), 2),
                      saving_range=[round(saving(1 - C_LO * r), 2), round(saving(1 - C_HI * r), 2)])
    print(json.dumps(out))
    if a.out:
        json.dump([{"k": i, **f} for i, f in enumerate(fixes)], open(a.out, "w"), indent=0)


if __name__ == "__main__":
    main()
