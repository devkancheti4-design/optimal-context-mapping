"""SWE-ContextBench (Lite, Django related tasks) prep, no model calls:
  1. check out each related task's base commit;
  2. keep the tasks whose official fix passes their official tests locally and whose tests fail without it
     (Python 3.11 for Django >= 4.0, Python 3.10 below);
  3. build the kit's index over each kept task's django/ package (cold), and a copy taught the experience pool:
     every Django experience task's issue, placed on the first line its merged fix changed (found by its text in
     this task's code).
Run with the package's venv: ~/ocm-eval/venvs/t021/bin/python cb_prep.py <validate | build>"""
import json, os, re, shutil, subprocess, sys

D = os.path.dirname(os.path.abspath(__file__)); H = os.path.dirname(D)
GIT = f"{H}/histories/django"
PY311 = f"{H}/value/venv_dj/bin/python"; PY310 = f"{D}/venv_dj310/bin/python"
REL = json.load(open(f"{D}/related_django.json")); EXP = json.load(open(f"{D}/experience_django.json"))


def sh(cmd, cwd=None, timeout=1800, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def py_for(version):
    return PY311 if float(version) >= 4.0 else PY310


def modules(test_patch):
    return sorted({f[len("tests/"):-3].replace("/", ".") for f in re.findall(r"^diff --git a/(\S+) b/", test_patch, re.M)
                   if f.startswith("tests/") and f.endswith(".py")})


def norm(name):
    return re.sub(r"^(\w+) \(([\w.]+)\.\1\)$", r"\1 (\2)", name.strip())      # 3.11: "t (m.C.t)" -> "t (m.C)"


def run_tests(repo, mods, py):
    r = sh([py, "tests/runtests.py", "--verbosity", "2", "--settings=test_sqlite", "--parallel", "1", *mods], cwd=repo,
           env=dict(os.environ, PYTHONPATH=repo))
    status, lines = {}, (r.stdout + "\n" + r.stderr).splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(.*?) \.\.\. (ok|FAIL|ERROR|skipped.*|expected failure|unexpected success)\s*$", line)
        if m:
            status[norm(m.group(1))] = m.group(2).split()[0]
            if i > 0 and " ... " not in lines[i - 1]:
                status[norm(lines[i - 1])] = m.group(2).split()[0]           # "test_x (mod.Class)" line before a docstring line
    return status


def apply(repo, patch):
    p = subprocess.run(["git", "apply", "-"], cwd=repo, input=patch, capture_output=True, text=True)
    return p.returncode == 0


def django_name(t):
    """SWE-ContextBench names Django tests the pytest way ("tests/a/b.py::Class::test"); Django's runner prints
    "test (a.b.Class)"."""
    m = re.match(r"^tests/(.+)\.py::(\w+)::(\w+)$", t)
    return f"{m.group(3)} ({m.group(1).replace('/', '.')}.{m.group(2)})" if m else t


def resolved(status, it):
    return (all(status.get(django_name(t)) == "ok" for t in it["FAIL_TO_PASS"])
            and all(status.get(django_name(t)) in ("ok", "skipped") for t in it["PASS_TO_PASS"]))


def checkout(it):
    base = f"{D}/wt/{it['id']}/base"
    if not os.path.exists(base):
        os.makedirs(os.path.dirname(base), exist_ok=True)
        r = sh(["git", "worktree", "add", "--detach", base, it["base"]], cwd=GIT)
        if r.returncode:
            print(it["id"], "checkout failed", r.stderr[-200:], flush=True); return None
    return base


def validate():
    out = f"{D}/cb_eval.json"; got = json.load(open(out)) if os.path.exists(out) else {}
    for it in REL:
        if it["id"] in got:
            continue
        base = checkout(it)
        if not base:
            got[it["id"]] = {"keep": False, "why": "checkout failed"}; continue
        res = {}
        for name, patches in (("without fix", [it["test_patch"]]), ("with fix", [it["test_patch"], it["patch"]])):
            tmp = f"{D}/wt/{it['id']}/check"
            shutil.rmtree(tmp, ignore_errors=True); sh(["cp", "-cR", base, tmp])
            ok = all(apply(tmp, p) for p in patches)
            try:
                st = run_tests(tmp, modules(it["test_patch"]), py_for(it["version"])) if ok else {}
            except subprocess.TimeoutExpired:
                st = {}
            res[name] = {"applied": ok, "resolved": resolved(st, it) if ok else False, "seen": len(st)}
            shutil.rmtree(tmp, ignore_errors=True)
        keep = res["with fix"]["resolved"] and not res["without fix"]["resolved"]
        got[it["id"]] = {"keep": keep, "version": it["version"], **res}
        json.dump(got, open(out, "w"), indent=1)
        print(it["id"], it["version"], res, "KEEP" if keep else "drop", flush=True)
    print("evaluable", sum(v["keep"] for v in got.values()), "of", len(REL), flush=True)


def first_change(patch):
    """The first file a fix changed (under django/), its first hunk's old start line, and the text of the line it
    changed: the first removed line, else the line just before the first added one."""
    f = re.search(r"^diff --git a/(\S+) b/", patch, re.M)
    if not f or not f.group(1).startswith("django/"):
        return None
    body = patch[f.end():]
    h = re.search(r"^@@ -(\d+)", body, re.M)
    if not h:
        return None
    start, prev, text, k = int(h.group(1)), None, None, int(h.group(1)) - 1
    for line in body[h.end():].split("\n")[1:]:
        if line.startswith("diff --git") or line.startswith("@@"):
            break
        if line.startswith("-"):
            text = line[1:]; k += 1; break
        if line.startswith("+"):
            text = prev; break
        prev = line[1:]; k += 1
    return f.group(1), max(1, k), (text or "").strip()


def place(base, change):
    """The line in this task's code that the experience fix changed: same text, nearest to the old line number."""
    path, line, text = change
    p = os.path.join(base, path)
    if not os.path.exists(p):
        return None
    lines = open(p, errors="ignore").read().split("\n")
    hits = [i + 1 for i, l in enumerate(lines) if text and l.strip() == text]
    if hits:
        return f"{path}:{min(hits, key=lambda i: abs(i - line))}"
    return None


def build():
    from ocm.build import build as kit_build
    from ocm.server import Workspace
    keep = [it for it in REL if json.load(open(f"{D}/cb_eval.json")).get(it["id"], {}).get("keep")]
    changes = {e["id"]: first_change(e["patch"]) for e in EXP}
    report = {}
    for it in keep:
        base = f"{D}/wt/{it['id']}/base"; cold = f"{D}/ws/{it['id']}_cold"; exp = f"{D}/ws/{it['id']}_exp"
        if not os.path.exists(f"{cold}/workspace.json"):
            kit_build([f"{base}/django"], cold, log=lambda *a: None)
        if os.path.exists(exp):
            shutil.rmtree(exp)
        shutil.copytree(cold, exp)
        pairs = []
        for e in EXP:
            at = place(base, changes[e["id"]]) if changes[e["id"]] else None
            if at:
                pairs.append({"question": e["issue"], "at": at})
        msg = Workspace(exp).handle("teach", {"pairs": pairs})
        linked = [x for x in it["experience"] if changes.get(x) and place(base, changes[x])]
        report[it["id"]] = {"placed": len(pairs), "of": len(EXP), "linked experience placed": len(linked), "of linked": len(it["experience"]),
                            "teach": msg[:160]}
        print(it["id"], report[it["id"]], flush=True)
    json.dump(report, open(f"{D}/cb_build.json", "w"), indent=1)
    print("CB BUILD DONE", flush=True)


if __name__ == "__main__":
    {"validate": validate, "build": build}[sys.argv[1]]()
