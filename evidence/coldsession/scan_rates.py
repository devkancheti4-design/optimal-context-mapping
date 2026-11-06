"""How often do real facts stay, move or change? Only GitHub and git, no model calls. For each repository, the last commit before each date; the facts of the
first date against each later one.

    python3 scan_rates.py [--dates 2025-11-01,2026-05-01,2026-11-01] [--out rates.json] [--work ~/coldsession-work/scan]"""
import argparse, json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facts as F  # noqa: E402

REPOS = """astropy/astropy conan-io/conan django/django pallets/flask matplotlib/matplotlib pylint-dev/pylint pytest-dev/pytest reflex-dev/reflex psf/requests
scikit-learn/scikit-learn sphinx-doc/sphinx sqlfluff/sqlfluff streamlink/streamlink sympy/sympy pydata/xarray""".split()     # SWE-QA's 15, chosen by others
ap = argparse.ArgumentParser()
ap.add_argument("--dates", default="2025-11-01,2026-05-01,2026-11-01"); ap.add_argument("--out", default="rates.json"); ap.add_argument("--work", default=os.path.expanduser("~/coldsession-work/scan"))
a = ap.parse_args()
DATES = a.dates.split(",")


def gh(path):
    return json.loads(subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True).stdout)


def pin(slug, date):
    rows = gh(f"repos/{slug}/commits?until={date}T00:00:00Z&per_page=1")
    return rows[0]["sha"], rows[0]["commit"]["committer"]["date"]


def fetch(slug, sha, dest):
    shutil.rmtree(dest, ignore_errors=True); os.makedirs(dest)
    for cmd in (["init", "-q"], ["remote", "add", "origin", f"https://github.com/{slug}"], ["fetch", "-q", "--depth", "1", "origin", sha], ["checkout", "-q", "FETCH_HEAD"]):
        subprocess.run(["git", "-C", dest, *cmd], check=True, capture_output=True)
    shutil.rmtree(os.path.join(dest, ".git"))


def scan(slug):
    name = slug.split("/")[1]
    base = os.path.join(a.work, name)
    pins = [pin(slug, d) for d in DATES]
    seen = {}
    for i, (sha, _) in enumerate(pins):
        dest = os.path.join(base, str(i))
        fetch(slug, sha, dest)
        seen[i] = F.snapshot_facts(dest)
        shutil.rmtree(dest)
    shutil.rmtree(base, ignore_errors=True)
    out = {"repo": slug, "pins": [{"date": DATES[i], "sha": p[0], "committed": p[1]} for i, p in enumerate(pins)], "facts": len(seen[0]),
           "askable": sum(F.askable(r) for r in seen[0].values()), "rates": {DATES[i]: F.rates(F.compare(seen[0], seen[i])) for i in range(1, len(DATES))}}
    print(slug, out["facts"], out["askable"], flush=True)
    return out


with ThreadPoolExecutor(4) as ex:
    rows = list(ex.map(scan, REPOS))
json.dump(rows, open(a.out, "w"), indent=1)
print("SCAN DONE", flush=True)
