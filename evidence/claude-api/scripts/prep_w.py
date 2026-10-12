"""PROTOCOL_VALUE5 prep (no model calls): check out each issue's base commit, and keep the issues whose official fix
passes their official tests locally and whose tests fail without the fix."""
import json, os, re, shutil, subprocess, sys
V = os.path.dirname(os.path.abspath(__file__)); H = os.path.dirname(V)
GIT = f"{H}/histories/django"; PY = os.path.expanduser("~/cmlm-bench10/value/venv_dj/bin/python")
ISS = json.load(open(f"{V}/w_issues.json"))


def sh(cmd, cwd=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def modules(test_patch):
    out = []
    for f in re.findall(r"^diff --git a/(\S+) b/", test_patch, re.M):
        if f.startswith("tests/") and f.endswith(".py"):
            out.append(f[len("tests/"):-3].replace("/", "."))
    return sorted(set(out))


def run_tests(repo, mods):
    env = dict(os.environ, PYTHONPATH=repo)
    r = subprocess.run([PY, "tests/runtests.py", "--verbosity", "2", "--settings=test_sqlite", "--parallel", "1", *mods],
                       cwd=repo, capture_output=True, text=True, timeout=1800, env=env)
    status = {}
    lines = (r.stdout + "\n" + r.stderr).splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(.*?) \.\.\. (ok|FAIL|ERROR|skipped.*|expected failure|unexpected success)\s*$", line)
        if m:
            name = re.sub(r"^(\w+) \(([\w.]+)\.\1\)$", r"\1 (\2)", m.group(1).strip())   # 3.11: "t (m.C.t)" -> "t (m.C)"
            status[name] = m.group(2).split()[0]
            if i > 0 and not re.search(r" \.\.\. ", lines[i - 1]):
                prev = re.sub(r"^(\w+) \(([\w.]+)\.\1\)$", r"\1 (\2)", lines[i - 1].strip())
                status[prev] = m.group(2).split()[0]      # "test_x (mod.Class)" line before a docstring line
    return status, r.returncode


def apply(repo, patch):
    p = subprocess.run(["git", "apply", "-"], cwd=repo, input=patch, capture_output=True, text=True)
    return p.returncode == 0, p.stderr[-300:]


def judge(status, it):
    f2p = all(status.get(t) == "ok" for t in it["FAIL_TO_PASS"])
    p2p = all(status.get(t) in ("ok", "skipped") for t in it["PASS_TO_PASS"])
    return f2p and p2p


def main():
    keep = []
    for it in ISS:
        base = f"{V}/wt/{it['id']}/base"
        if not os.path.exists(base):
            os.makedirs(os.path.dirname(base), exist_ok=True)
            r = sh(["git", "worktree", "add", "--detach", base, it["base"]], cwd=GIT, timeout=1800)
            if r.returncode:
                print(it["id"], "checkout failed", r.stderr[-200:], flush=True); continue
        mods = modules(it["test_patch"])
        res = {}
        for name, patches in (("without fix", [it["test_patch"]]), ("with fix", [it["test_patch"], it["patch"]])):
            tmp = f"{V}/wt/{it['id']}/check"
            shutil.rmtree(tmp, ignore_errors=True); sh(["cp", "-cR", base, tmp])
            ok = all(apply(tmp, p)[0] for p in patches)
            st, _ = run_tests(tmp, mods) if ok else ({}, 1)
            res[name] = {"applied": ok, "resolved": judge(st, it) if ok else False, "f2p ok": sum(st.get(t) == "ok" for t in it["FAIL_TO_PASS"]), "seen": len(st)}
            shutil.rmtree(tmp, ignore_errors=True)
        good = res["with fix"]["resolved"] and not res["without fix"]["resolved"]
        print(it["id"], "modules", mods, res, "KEEP" if good else "drop", flush=True)
        if good:
            keep.append(it["id"])
    json.dump({"evaluable": keep, "n": len(keep)}, open(f"{V}/w_eval.json", "w"), indent=1)
    print("evaluable", len(keep), "of", len(ISS))


if __name__ == "__main__":
    main()
