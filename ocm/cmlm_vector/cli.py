"""cmlm-vector: a memory a frontier model asks and teaches, instead of a transcript it rereads.

    cmlm-vector init MEM [--bits 1024] [--seed 0] [--model BAAI/bge-base-en-v1.5] [--device cpu|mps|cuda]
    cmlm-vector ingest MEM PATH... [--glob '*.txt'] [--drop-headers]    files or folders; already-held files are skipped
    cmlm-vector ask MEM "question" [-k 5] [--context 1] [--json]        single shot: the top k facts with their sources
    cmlm-vector teach MEM --cue "how a person might ask" --fact "the one sentence that answers it"
    cmlm-vector info MEM
    cmlm-vector verify MEM                                              every file against its sha256, planes against seed

A memory is a folder; copy it and it answers the same way on another machine (use the same device for bit-exact
replication). Nothing is sent anywhere: embeddings are computed locally."""
import argparse, glob as globmod, json, os, sys

from .memory import Memory


def _files(paths, pattern):
    out = []
    for p in paths:
        if os.path.isdir(p):
            out += [f for f in globmod.glob(os.path.join(p, "**", pattern), recursive=True) if os.path.isfile(f)]
        elif os.path.isfile(p):
            out.append(p)
    return sorted(set(out))


def main(argv=None):
    p = argparse.ArgumentParser(prog="cmlm-vector", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init"); a.add_argument("mem"); a.add_argument("--bits", type=int, default=1024)
    a.add_argument("--seed", type=int, default=0); a.add_argument("--model"); a.add_argument("--device")
    a = sub.add_parser("ingest"); a.add_argument("mem"); a.add_argument("paths", nargs="+")
    a.add_argument("--glob", default="*.txt"); a.add_argument("--keep-float", action="store_true")
    a.add_argument("--drop-headers", action="store_true", help="skip mail/news metadata lines (From:, Subject:, ...)")
    a.add_argument("--no-center", action="store_true", help="do not centre the bits on the corpus mean")
    a = sub.add_parser("ask"); a.add_argument("mem"); a.add_argument("question"); a.add_argument("-k", type=int, default=5)
    a.add_argument("--context", type=int, default=1); a.add_argument("--json", action="store_true")
    a = sub.add_parser("teach"); a.add_argument("mem"); a.add_argument("--cue", required=True); a.add_argument("--fact", required=True)
    a = sub.add_parser("info"); a.add_argument("mem")
    a = sub.add_parser("verify"); a.add_argument("mem")
    x = p.parse_args(argv)

    if x.cmd == "init":
        m = Memory.create(x.mem, bits=x.bits, seed=x.seed, model=x.model, device=x.device)
        print(json.dumps(m.info(), indent=1)); return 0
    if x.cmd == "verify":                              # before opening: a damaged memory may not open at all
        bad = Memory.verify_path(x.mem)
        print("verified: every file matches its sha256 and the planes match the seed" if not bad else f"MISMATCH: {bad}")
        return 0 if not bad else 1
    m = Memory(x.mem)
    if x.cmd == "ingest":
        fs = _files(x.paths, x.glob)
        print(f"ingesting {len(fs):,} files into {x.mem}", flush=True)
        r = m.ingest(fs, keep_float=x.keep_float, log=lambda s: print(s, flush=True), drop_headers=x.drop_headers, center=not x.no_center)
        print(json.dumps({**r, **m.info()}, indent=1)); return 0
    if x.cmd == "ask":
        r = m.recall(x.question, k=x.k, context=x.context)
        if x.json:
            print(json.dumps(r, indent=1)); return 0
        if r["status"] == "abstain":
            print("NOTHING CLOSE: no stored fact stands out for this question; these are the nearest. Ask again in other words if none answers it.")
        for i, row in enumerate(r["rows"], 1):
            flag = " [ambiguous: check against the question]" if row["flag"] else ""
            print(f"{i}. {row['fact']}{flag}\n   source: {row['source']} (unit {row['unit']})")
            if row["context"]:
                print("   context: " + " | ".join(row["context"]))
        return 0
    if x.cmd == "teach":
        r = m.teach([(x.cue, x.fact)]); m.save(); print(json.dumps(r)); return 0
    if x.cmd == "info":
        print(json.dumps(m.info(), indent=1)); return 0


if __name__ == "__main__":
    sys.exit(main())
