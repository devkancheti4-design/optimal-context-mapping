"""What the scripts share: where things live, the pinned dates, GitHub and git, and the billed model."""
import json, os, shutil, subprocess, threading, time

DATES = ("2025-11-01", "2026-05-01", "2026-11-01")     # T0, T1, T2: 12 months of real commits
WORK = os.path.expanduser(os.environ.get("COLDSESSION_WORK", "~/coldsession-work"))
HERE = os.environ.get("COLDSESSION_HOME", os.path.dirname(os.path.abspath(__file__)))
MODEL = "gemini-3.5-flash-lite"
PRICE = (0.30, 0.03, 2.50)                             # dollars per million: input, cached input, output and thoughts
CAP = float(os.environ.get("COLDSESSION_CAP", "8.50")) # dollars across every script and arm
LEDGER = os.path.join(WORK, "spend.jsonl")
SESSIONS = {"guess": (1,), "alone": (2, 4), "map": (2, 4), "notes": (1, 2, 3, 4, 5), "modeld": (1, 2, 3, 4, 5)}


def data(repo, *p):
    return os.path.join(HERE, "data", repo, *p)


def work(repo, *p):
    return os.path.join(WORK, repo, *p)


def results(repo, *p):
    return os.path.join(HERE, "results", repo, *p)


def rows(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def gh(path):
    return json.loads(subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True).stdout)


def pin(slug, date):
    """The last commit on the default branch before this date."""
    r = gh(f"repos/{slug}/commits?until={date}T00:00:00Z&per_page=1")[0]
    return r["sha"], r["commit"]["committer"]["date"]


def fetch(slug, sha, dest):
    """The repository's files at this commit, without its history."""
    shutil.rmtree(dest, ignore_errors=True); os.makedirs(dest)
    for cmd in (["init", "-q"], ["remote", "add", "origin", f"https://github.com/{slug}"], ["fetch", "-q", "--depth", "1", "origin", sha], ["checkout", "-q", "FETCH_HEAD"]):
        subprocess.run(["git", "-C", dest, *cmd], check=True, capture_output=True)
    shutil.rmtree(os.path.join(dest, ".git"))


def spent():
    return sum(r["usd"] for r in rows(LEDGER))


class OverCap(RuntimeError):
    pass


class Bill:
    """Every model call goes through here: temperature 0, the API's own token counts, and a hard cap across every process."""
    def __init__(self, send):
        self.send, self.lock, self.local = send, threading.Lock(), threading.local()
        os.makedirs(WORK, exist_ok=True)

    def start(self):
        self.local.q = {"requests": 0, "tokens_in": 0, "cached": 0, "tokens_out": 0, "usd": 0.0}

    def tally(self):
        return dict(self.local.q)

    def post(self, model, body):
        with self.lock:
            if spent() >= CAP:
                raise OverCap(f"the ${CAP:.2f} cap is reached")
        r = self.send(model, {**body, "generationConfig": {"temperature": 0}})
        u = r.get("usageMetadata", {})
        tin, cached = u.get("promptTokenCount", 0), u.get("cachedContentTokenCount", 0)
        tout = u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
        usd = ((tin - cached) * PRICE[0] + cached * PRICE[1] + tout * PRICE[2]) / 1e6
        with self.lock:
            with open(LEDGER, "a") as f:
                f.write(json.dumps({"usd": round(usd, 7), "t": round(time.time())}) + "\n")
        q = getattr(self.local, "q", None)
        if q is not None:
            q["requests"] += 1; q["tokens_in"] += tin; q["cached"] += cached; q["tokens_out"] += tout; q["usd"] = round(q["usd"] + usd, 7)
        return r
