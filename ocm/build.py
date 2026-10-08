"""Build a workspace over one or more repositories (and their docs).

    python -m ocm build <folder> [<folder> ...] --out <workspace folder>

Creates <workspace>/memory (the fingerprints: 1,024 bits per unit, from a small embedding model that runs on this
machine), <workspace>/keyword.db (a keyword index for the router's keyword lane), <workspace>/spans.json (the first and
last line of every unit, so a taught question's vector can be put on the unit holding a given line) and
<workspace>/workspace.json (which folders, how many units, the router's rare-word threshold). Rebuild after large code changes; teaching later only adds."""
import argparse, json, os, shutil, sqlite3, time

from .cmlm_vector import Memory
from .units import files, units

THETA_DEFAULT = 9.349                     # the router law's 44% rule on code questions (measured on transformers)


def build(roots, out, model=None, device=None, log=print, carry=None):
    if os.path.exists(os.path.join(out, "memory", "manifest.json")):
        raise SystemExit(f"{out} already holds a workspace; remove it or choose another --out")
    os.makedirs(out, exist_ok=True)
    roots = {os.path.basename(os.path.abspath(r).rstrip("/")) or "root": os.path.abspath(r) for r in roots}
    m = Memory.create(os.path.join(out, "memory"), bits=1024, seed=0, model=model, device=device)
    F = files(roots); U = []
    for name, rel, path in F:
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        us = units(rel, text)
        m.sources.append({"id": len(m.sources), "path": rel, "sha256": "", "units": len(us)})
        U.extend((t, len(m.sources) - 1, a, b) for t, a, b in us)
    if not U:
        raise SystemExit("no code or documentation found in those folders")
    step = max(1, len(U) // 20000)
    m.freeze_mean([u[0] for u in U[::step][:20000]])
    log(f"{len(m.sources):,} files, {len(U):,} units; fingerprinting (first run downloads the embedding model)")
    t0, seen, spans = time.time(), set(), []
    for s in range(0, len(U), 2048):
        chunk = [u for u in U[s:s + 2048] if u[0] not in seen]; seen.update(u[0] for u in chunk)
        for (t, sid, a, last), b in zip(chunk, m.measure([u[0] for u in chunk])):
            m._add_fact(t, sid, a, 0, True, b); spans.append([a, last])
        if len(m.pending_f) >= 200_000:
            m.save()
        log(f"  {min(s + 2048, len(U)):,} / {len(U):,} units, {time.time() - t0:.0f}s")
    m.save()
    db = os.path.join(out, "keyword.db")
    con = sqlite3.connect(db); con.execute("create virtual table s using fts5(t)")
    con.executemany("insert into s(rowid, t) values (?, ?)", ((j + 1, t) for j, t in enumerate(m.texts))); con.commit(); con.close()
    json.dump(spans, open(os.path.join(out, "spans.json"), "w"))
    json.dump({"roots": roots, "files": len(m.sources), "units": len(m.texts), "theta": THETA_DEFAULT,
               "built": time.strftime("%Y-%m-%dT%H:%M:%S")}, open(os.path.join(out, "workspace.json"), "w"), indent=1)
    shutil.copytree(os.path.join(out, "memory"), os.path.join(out, "memory_at_build"))
    log(f"workspace ready: {out} ({len(m.texts):,} units from {len(m.sources):,} files)")
    if carry:
        from .server import Workspace
        r = Workspace(out).carry(carry)
        log(f"carried from {carry}: {r['carried']} of {r['entries']} taught entries ({r['moved']} moved), "
            f"{r['abstained']} abstained (their line is gone); Life sha {r['life sha']}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ocm build"); ap.add_argument("folders", nargs="+"); ap.add_argument("--out", required=True)
    ap.add_argument("--model"); ap.add_argument("--device")
    ap.add_argument("--carry", help="an earlier workspace whose taught knowledge (its Life) is carried into this one")
    a = ap.parse_args(argv); build(a.folders, a.out, a.model, a.device, carry=a.carry)
