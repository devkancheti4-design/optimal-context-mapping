"""modeld forecast: how much Model D would cut an agent's bill on this repository, from its own git history alone.

  modeld forecast [repo] [--months 12] [--json]

No model calls, no index, nothing leaves the machine: it reads `git log` only.

Fixes are non-merge commits whose subject starts with fix / fixes / fixed / bugfix / hotfix, or cites "fix #N". Each
fix's files are the ones it changed, minus tests, docs, lockfiles, translations and snapshots. From those, in commit
order, it measures:
- r: the share of fixes that touch a file an earlier fix in the window touched (work that repeats);
- lam: fixes per month.

It forecasts with the learning law, S = A / ((1 - nu) E + nu K), calibrated on Django 2022 (evidence/team-year):
- nu = 1 - c r, with c = 0.23 (range 0.13-0.38 across quarters);
- A / K = 1.80, the saving with no learning at all; E / A = 0.0044.
The time for novelty to fall to about 10% is t = 450 / lam months (the novelty curve fitted on ten years of Django)."""
import argparse, datetime, json, os, re, subprocess, sys

FIX = re.compile(r"^(fix(es|ed)?\b|bug ?fix|hotfix)|\bfix(es|ed)? #\d+", re.I)
SKIP = re.compile(r"(^|/)(tests?|__tests__|spec|specs|docs?|locales?|i18n|translations|__snapshots__|fixtures?)/"
                  r"|\.(md|mdx|rst|txt|adoc|snap|lock|min\.js)$|(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|go\.sum|"
                  r"Cargo\.lock|poetry\.lock|composer\.lock)$|(\.test\.|\.spec\.|_test\.go$|(^|/)test_[^/]*\.py$)", re.I)
A_OVER_K, E_OVER_A, C, C_LO, C_HI = 1.80, 0.0044, 0.23, 0.13, 0.38


def saving(nu):
    return 1 / ((1 - nu) * E_OVER_A + nu / A_OVER_K)


def fixes(repo, since, until=None):
    """The window's fix commits, oldest first: {hash, parent, date, subject, files}."""
    args = ["git", "-C", repo, "log", "--no-merges", "--no-renames", "--reverse", f"--since={since}", "--name-only",
            "--format=@@%H%x09%P%x09%cs%x09%s"] + ([f"--until={until}"] if until else [])
    out, cur = [], None
    for line in subprocess.run(args, capture_output=True, text=True, check=True).stdout.split("\n"):
        if line.startswith("@@"):
            h, p, d, s = line[2:].split("\t", 3)
            cur = {"hash": h, "parents": p.split(), "date": d, "subject": s, "files": []} if FIX.search(s) else None
            if cur:
                out.append(cur)
        elif line.strip() and cur is not None and not SKIP.search(line.strip()):
            cur["files"].append(line.strip())
    return [f for f in out if f["files"]]


def forecast(repo, months=12):
    since = (datetime.date.today() - datetime.timedelta(days=round(months * 30.44))).isoformat()
    fx = fixes(repo, since)
    seen, rep = set(), []
    for f in fx:
        rep.append(bool(set(f["files"]) & seen)); seen |= set(f["files"])
    n = len(fx); r = sum(rep) / n if n else 0.0; lam = n / months; nu = 1 - C * r
    return {"repo": os.path.abspath(repo), "since": since, "fixes": n, "fixes_per_month": round(lam, 1),
            "files_per_fix": round(sum(len(f["files"]) for f in fx) / max(1, n), 2), "distinct_files": len(seen),
            "repetition_r": round(r, 3), "novelty_now": round(nu, 3), "saving": round(saving(nu), 2),
            "saving_range": [round(saving(1 - C_LO * r), 2), round(saving(1 - C_HI * r), 2)],
            "months_to_10pct_novelty": round(450 / lam, 1) if lam else None}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="modeld forecast", description=__doc__.split("\n\n")[1])
    ap.add_argument("repo", nargs="?", default="."); ap.add_argument("--months", type=float, default=12)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if subprocess.run(["git", "-C", a.repo, "rev-parse"], capture_output=True).returncode:
        sys.exit(f"{a.repo} is not a git repository")
    f = forecast(a.repo, a.months)
    if a.json:
        print(json.dumps(f)); return
    print(f"Model D forecast for {f['repo']} (from git history since {f['since']}; no model calls)\n")
    if f["fixes"] < 10:
        print(f"only {f['fixes']} fix commits in the last {a.months:g} months: too few for a forecast. "
              f"Try a longer window, e.g. --months {max(24, int(a.months * 2))}.")
        return
    print(f"  fix commits                 {f['fixes']} ({f['fixes_per_month']} a month, {f['files_per_fix']} files each)")
    print(f"  fixes on a file fixed before {f['repetition_r']:.0%}   <- work that repeats; Model D learns it")
    print(f"  forecast saving             {f['saving']}x lower agent bill on this work "
          f"(range {f['saving_range'][0]}x-{f['saving_range'][1]}x)")
    if f["months_to_10pct_novelty"]:
        print(f"  time to learn the codebase  about {f['months_to_10pct_novelty']} months of this work")
    print("\nThe law behind it is calibrated on Django's real 2022 fixes, where the measured saving was 2.09x.\n"
          "Check it on your own code, at zero tokens: modeld prove .")


if __name__ == "__main__":
    main()
