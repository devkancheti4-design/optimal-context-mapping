"""The CMLM memory with vector generalization: a context a frontier model asks and teaches instead of rereading.

Every stored text (a fact, and every cue taught for it) is embedded locally and kept only as B sign bits, one per
fixed random hyperplane (SimHash; 1,024 by default, 128 bytes a text). A question is measured the same way, and a
fact's evidence is counted in integers, ranked lexicographically as fluidnet ranks its lanes:

    strong = the most bits the question shares with any cue taught for the fact (for a unit ingested from a
             corpus, its own text is its cue)
    weak   = the bits it shares with the fact's own text
    then the newest first.

Bits shared estimate the angle between meanings, so a question in words never taught still lands near what it
means: that is the generalization. No weight moves and a stored bit never changes, so nothing is forgotten. On top,
the learned law (lawsearch.py) reorders the top candidates once it has earned it on the new wordings a frontier
teaches, and the certifier flags readouts that are ambiguous or near nothing.

On disk a memory is a folder: manifest.json (format, model, device, bits, seed, every file's sha256), planes.npy,
shards of facts and of cues (bits as .npy, text as .jsonl.gz), sources.jsonl, law.json. Shards are append-only, so a
memory grows without rewriting what it holds, and `verify` re-hashes every file."""
import gzip, hashlib, json, os, time

import numpy as np

from .chunk import units as split_units
from .lawsearch import LearnedLaw, asks, holds, NEAR, describe

FORMAT = 1
SHARD_UNITS = 200_000
BLOCK = 1_000_000


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _jsonl_gz_write(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _jsonl_gz_read(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f]


class Memory:
    # ---- create / open / save ------------------------------------------------------------------------------------
    def __init__(self, path):
        self.path = path
        self.man = json.load(open(os.path.join(path, "manifest.json")))
        if self.man.get("format") != FORMAT:
            raise ValueError(f"memory format {self.man.get('format')} is not {FORMAT}")
        self.bits = int(self.man["bits"]); self.W = (self.bits + 63) // 64
        self.planes = np.load(os.path.join(path, "planes.npy"))
        mp = os.path.join(path, "mean.npy")
        self.mean = np.load(mp) if os.path.exists(mp) else None          # frozen at the first ingest; never changes
        self.query_prefix = self.man.get("query_prefix", "")
        self.gap, self.near = self.man.get("gap", 0.04), self.man.get("near", 0.01)
        self._embedder = None
        self.fshards, self.cshards = [], []
        self.texts, self.src, self.pos, self.turn, self.selfcue = [], [], [], [], []
        self.cue_texts, self.cue_fact = [], []
        for sh in self.man["shards"]:
            d = os.path.join(path, sh["dir"])
            if sh["kind"] == "facts":
                fb = np.load(os.path.join(d, "bits.npy"), mmap_mode="r")
                self.fshards.append(fb)
                for r in _jsonl_gz_read(os.path.join(d, "rows.jsonl.gz")):
                    self.texts.append(r["t"]); self.src.append(r["s"]); self.pos.append(r["p"])
                    self.turn.append(r["u"]); self.selfcue.append(r["c"])
            else:
                self.cshards.append(np.load(os.path.join(d, "bits.npy"), mmap_mode="r"))
                for r in _jsonl_gz_read(os.path.join(d, "rows.jsonl.gz")):
                    self.cue_texts.append(r["t"]); self.cue_fact.append(r["f"])
        sp = os.path.join(path, "sources.jsonl")
        self.sources = [json.loads(l) for l in open(sp)] if os.path.exists(sp) else []
        self.by_text = {t: i for i, t in enumerate(self.texts)}
        self.cue_set = set(self.cue_texts)
        self.law = LearnedLaw(n=self.man.get("law_n", 8), min_examples=self.man.get("law_min", 12), window=self.man.get("law_window", 50))
        lp = os.path.join(path, "law.json")
        if os.path.exists(lp):
            st = json.load(open(lp))
            self.law.examples = [(list(w), int(r)) for w, r in st["examples"]]
            self.law.scored = [tuple(x) for x in st["scored"]]
            self.law.law = int(st["law"])
        self.pending_f, self.pending_c = [], []          # (text, src, pos, turn, selfcue, bits) / (text, fact, bits)
        self._arrays()

    @classmethod
    def create(cls, path, bits=1024, seed=0, model=None, device=None, gap=0.04, near=0.01):
        from .embed import DEFAULT_MODEL, pick_device
        if os.path.exists(os.path.join(path, "manifest.json")):
            raise FileExistsError(f"{path} already holds a memory")
        os.makedirs(path, exist_ok=True)
        model = model or DEFAULT_MODEL
        from .embed import shared
        dim = shared(model, device).dim
        planes = np.random.default_rng(seed).standard_normal((dim, bits)).astype(np.float32)
        np.save(os.path.join(path, "planes.npy"), planes)
        from . import __version__
        from .embed import QUERY_PREFIX
        man = {"format": FORMAT, "package": "cmlm-vector", "version": __version__, "model": model, "device": pick_device(device),
               "query_prefix": QUERY_PREFIX.get(model, ""),
               "dim": dim, "bits": bits, "seed": seed, "gap": gap, "near": near, "law_n": 8, "law_min": 12, "law_window": 50,
               "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "shards": [], "files": {}}
        json.dump(man, open(os.path.join(path, "manifest.json"), "w"), indent=1)
        m = cls(path); m.save(); return m

    def _arrays(self):
        self.turn_a = np.array(self.turn, dtype=np.int64)
        self.self_a = np.array(self.selfcue, dtype=bool)
        self.cue_fact_a = np.array(self.cue_fact, dtype=np.int64)

    def save(self):
        """Write what is pending as new shards (nothing already on disk is rewritten), the law and the manifest."""
        for kind, pend in (("facts", self.pending_f), ("cues", self.pending_c)):
            if not pend:
                continue
            n0 = sum(1 for s in self.man["shards"] if s["kind"] == kind)
            name = f"{kind}/{n0:05d}"; d = os.path.join(self.path, name); os.makedirs(d, exist_ok=True)
            np.save(os.path.join(d, "bits.npy"), np.stack([p[-1] for p in pend]))
            rows = ([{"t": p[0], "s": p[1], "p": p[2], "u": p[3], "c": p[4]} for p in pend] if kind == "facts"
                    else [{"t": p[0], "f": p[1]} for p in pend])
            _jsonl_gz_write(os.path.join(d, "rows.jsonl.gz"), rows)
            self.man["shards"].append({"dir": name, "kind": kind, "n": len(pend)})
            arr = np.load(os.path.join(d, "bits.npy"), mmap_mode="r")
            (self.fshards if kind == "facts" else self.cshards).append(arr)
        self.pending_f, self.pending_c = [], []
        json.dump({"law": self.law.law, "describe": describe(self.law.law), "active": self.law.active,
                   "examples": self.law.examples, "scored": self.law.scored}, open(os.path.join(self.path, "law.json"), "w"))
        with open(os.path.join(self.path, "sources.jsonl"), "w") as f:
            for s in self.sources:
                f.write(json.dumps(s) + "\n")
        self.man["units"], self.man["cues"], self.man["sources"] = len(self.texts), len(self.cue_texts), len(self.sources)
        self.man["files"] = {rel: _sha(os.path.join(self.path, rel)) for rel in self._files()}
        json.dump(self.man, open(os.path.join(self.path, "manifest.json"), "w"), indent=1)

    def _files(self):
        out = ["planes.npy", "mean.npy", "sources.jsonl", "law.json"]
        for s in self.man["shards"]:
            out += [f"{s['dir']}/bits.npy", f"{s['dir']}/rows.jsonl.gz"]
        return [f for f in out if os.path.exists(os.path.join(self.path, f))]

    @staticmethod
    def verify_path(path):
        """Every file against its recorded sha256, and the planes against the seed; [] when all hold. Reads the
        files as bytes and never parses them, so it works on a damaged memory that would not open."""
        man = json.load(open(os.path.join(path, "manifest.json")))
        bad = [rel for rel, h in man["files"].items()
               if not os.path.exists(os.path.join(path, rel)) or _sha(os.path.join(path, rel)) != h]
        try:
            planes = np.load(os.path.join(path, "planes.npy"))
            again = np.random.default_rng(man["seed"]).standard_normal(planes.shape).astype(np.float32)
            if not np.array_equal(again, planes):
                bad.append("planes.npy (does not match the seed)")
        except Exception as e:                                           # noqa: BLE001 -- unreadable is a finding
            bad.append(f"planes.npy ({type(e).__name__})")
        return bad

    def verify(self):
        return Memory.verify_path(self.path)

    # ---- measuring --------------------------------------------------------------------------------------------------
    @property
    def embedder(self):
        if self._embedder is None:
            from .embed import shared
            # the device the memory was built on, unless overridden: CPU and GPU can differ in a borderline bit
            self._embedder = shared(self.man["model"], os.environ.get("CMLM_DEVICE") or self.man.get("device"))
        return self._embedder

    def measure(self, texts, keep_float=False, query=False):
        """Sign bits of each text's embedding, centred on the memory's frozen mean when it has one. query=True puts
        the model's search instruction first: for a question matched against stored statements."""
        texts = [self.query_prefix + t for t in texts] if (query and self.query_prefix) else list(texts)
        v = self.embedder(texts)
        c = v - self.mean if self.mean is not None else v
        b = np.packbits(c @ self.planes > 0, axis=1)
        b = np.pad(b, ((0, 0), (0, self.W * 8 - b.shape[1])))
        packed = b.view(">u8").astype(np.uint64)
        return (packed, v) if keep_float else packed

    def _agree(self, q, shards, pending):
        out = []
        for arr in list(shards) + ([np.stack(pending)] if pending else []):
            for s in range(0, len(arr), BLOCK):
                x = np.asarray(arr[s:s + BLOCK])
                out.append(self.bits - np.bitwise_count(x ^ q).sum(axis=1, dtype=np.int64))
        return np.concatenate(out) if out else np.zeros(0, dtype=np.int64)

    # ---- teaching ---------------------------------------------------------------------------------------------------
    def _add_fact(self, text, src, pos, turn, selfcue, bits):
        j = len(self.texts)
        self.texts.append(text); self.src.append(src); self.pos.append(pos); self.turn.append(turn); self.selfcue.append(selfcue)
        self.by_text[text] = j; self.pending_f.append((text, src, pos, turn, selfcue, bits))
        return j

    def teach(self, pairs, turn=None):
        """Pairs of (cue, fact): a question a person might ask, and the one sentence that answers it. A new wording
        taught for a fact already held is also an example for the learned law, measured before it is stored."""
        pairs = [(" ".join(str(c).split()), " ".join(str(f).split())) for c, f in pairs if str(c).strip() and str(f).strip()]
        if not pairs:
            return {"pairs": 0, "examples": 0}
        turn = int(turn if turn is not None else (max(self.turn) + 1 if self.turn else 1))
        need = list(dict.fromkeys([c for c, _ in pairs] + [f for _, f in pairs if f not in self.by_text]))
        B = dict(zip(need, self.measure(need)))
        ex = 0
        for c, f in pairs:
            if f in self.by_text and c not in self.cue_set and self.texts:
                self._arrays()
                order, strong, weak = self._rank(c, bits=B[c])
                cand = order[:self.law.n]
                j = self.by_text[f]
                self.law.observe(self._lane_words(c, cand, strong, weak), cand.index(j) if j in cand else -1); ex += 1
            j = self.by_text.get(f)
            if j is None:
                j = self._add_fact(f, -1, -1, turn, False, B[f])
            if c not in self.cue_set:
                self.cue_texts.append(c); self.cue_fact.append(j); self.cue_set.add(c); self.pending_c.append((c, j, B[c]))
        self._arrays()
        return {"pairs": len(pairs), "examples": ex, "law": describe(self.law.law), "law_active": self.law.active}

    def teach_at(self, pairs):
        """Pairs of (cue, unit): a question a person asked, and the stored unit (by index) that holds its answer. The
        question's vector becomes a cue on that unit; nothing new is stored as a fact. Each is first an example for the
        learned law, measured before the cue is stored. Questions already taught as cues are skipped."""
        pairs = [(" ".join(str(c).split()), int(j)) for c, j in pairs if str(c).strip() and 0 <= int(j) < len(self.texts)]
        pairs = [(c, j) for c, j in dict.fromkeys(pairs) if c not in self.cue_set]
        if not pairs:
            return {"cues": 0, "examples": 0}
        B = dict(zip([c for c, _ in pairs], self.measure([c for c, _ in pairs])))
        for c, j in pairs:
            if c in self.cue_set:
                continue
            self._arrays()
            order, strong, weak = self._rank(c, bits=B[c])
            cand = order[:self.law.n]
            self.law.observe(self._lane_words(c, cand, strong, weak), cand.index(j) if j in cand else -1)
            self.cue_texts.append(c); self.cue_fact.append(j); self.cue_set.add(c); self.pending_c.append((c, j, B[c]))
        self._arrays()
        return {"cues": len(pairs), "examples": len(pairs), "law": describe(self.law.law), "law_active": self.law.active}

    def freeze_mean(self, texts):
        """Centre the bits: the mean embedding of these texts, frozen for good. Only on an empty memory, since the
        bits already stored were measured without it and a stored bit never changes."""
        if self.texts or self.cue_texts:
            raise ValueError("the mean is frozen before anything is stored")
        self.mean = self.embedder(texts).mean(axis=0).astype(np.float32)
        np.save(os.path.join(self.path, "mean.npy"), self.mean)
        self.man["center"] = {"texts": len(texts)}

    def ingest(self, files, root=None, keep_float=False, log=print, batch=4096, drop_headers=False, center=True, sample=20000):
        """Every file's text as units whose own text is their cue. Files already held (same sha256) are skipped;
        a shard is saved every SHARD_UNITS units, so a stopped ingest resumes where it stopped. On an empty memory
        the mean is first frozen from an even, deterministic sample of up to `sample` units (center=True)."""
        if center and self.mean is None and not self.texts and not self.cue_texts and files:
            allu = [u for fp in sorted(files) for u in split_units(open(fp, encoding="utf-8", errors="replace").read(),
                                                                    drop_headers=drop_headers)]
            step = max(1, len(allu) // sample)
            self.freeze_mean(allu[::step][:sample])
            log(f"  mean frozen from {min(sample, len(allu[::step])):,} of {len(allu):,} units")
        root = root or (os.path.commonpath([os.path.dirname(os.path.abspath(f)) for f in files]) if files else "")
        held = {s["sha256"] for s in self.sources}
        buf, floats, t0, n_files = [], [], time.time(), 0
        def flush():
            if not buf:
                return
            for s in range(0, len(buf), batch):
                chunk = buf[s:s + batch]
                got = self.measure([u[0] for u in chunk], keep_float)
                bits, fl = got if keep_float else (got, None)
                for (text, src, pos), b in zip(chunk, bits):
                    self._add_fact(text, src, pos, 0, True, b)
                if keep_float:
                    floats.append(fl.astype(np.float16))
            self.save()
            if keep_float:
                d = os.path.join(self.path, self.man["shards"][-1]["dir"])
                np.save(os.path.join(d, "emb16.npy"), np.concatenate(floats)); floats.clear()
            buf.clear()
            log(f"  {len(self.texts):,} units from {len(self.sources):,} files, {time.time() - t0:.0f}s")
        for fp in sorted(files):
            h = _sha(fp)
            if h in held:
                continue
            text = open(fp, encoding="utf-8", errors="replace").read()
            us = [u for u in split_units(text, drop_headers=drop_headers) if u not in self.by_text]
            sid = len(self.sources)
            self.sources.append({"id": sid, "path": os.path.relpath(os.path.abspath(fp), root) if root else fp, "sha256": h, "units": len(us)})
            held.add(h); n_files += 1
            seen = set()
            for p, u in enumerate(us):
                if u in seen:
                    continue
                seen.add(u); buf.append((u, sid, p))
            if len(buf) >= SHARD_UNITS:
                flush()
        flush()
        self._arrays()
        return {"files": n_files, "units": len(self.texts)}

    # ---- recall ------------------------------------------------------------------------------------------------------
    def _rank(self, query, bits=None, top=64):
        """A question against statements is measured with the search instruction (qs), against taught cues, which
        are questions themselves, without it (qc). An ingested unit is its own cue, so it is read with qs."""
        qc = bits if bits is not None else self.measure([query])[0]
        qs = self.measure([query], query=True)[0] if self.query_prefix else qc
        weak = self._agree(qs, self.fshards, [p[-1] for p in self.pending_f])
        strong = np.where(self.self_a[:len(weak)], weak, 0)
        if self.cue_texts:
            a = self._agree(qc, self.cshards, [p[-1] for p in self.pending_c])
            np.maximum.at(strong, self.cue_fact_a, a)
        key = strong * (self.bits + 1) + weak                                        # exactly (strong, weak)
        m = min(max(top, self.law.n), len(key))
        cand = np.argpartition(-key, m - 1)[:m] if m < len(key) else np.arange(len(key))
        cand = sorted(cand.tolist(), key=lambda j: (-key[j], -self.turn_a[j], j))
        return cand, strong, weak

    def _lane_words(self, query, cand, strong, weak):
        """lawsearch.words, for the candidates only: ranks are counted, not sorted, so it scales."""
        bs, bw, qt = int(strong.max()), int(weak.max()), asks(query)
        out = []
        for j in cand[:self.law.n]:
            sr = int((strong > strong[j]).sum() + (strong[:j] == strong[j]).sum())
            wr = int((weak > weak[j]).sum() + (weak[:j] == weak[j]).sum())
            b = (sr == 0, wr == 0, strong[j] >= bs - NEAR * self.bits, weak[j] >= bw - NEAR * self.bits,
                 sr < 3, wr < 3, bool(qt & holds(self.texts[j])), sr < 3 and wr < 3)
            out.append(sum(int(v) << i for i, v in enumerate(b)))
        return out

    def recall(self, query, k=5, context=1):
        """The top k facts for a question, best first, each with its neighbours from the same source, and the
        certifier's status: confident, ambiguous (facts too close to tell apart are flagged) or abstain (nothing
        stands out: a hint to ask in other words, not a verdict)."""
        if not self.texts:
            return {"status": "abstain", "rows": [], "law": describe(self.law.law), "law_active": False}
        cand, strong, weak = self._rank(query)
        if self.law.active:
            n = self.law.n
            cand = self.law.order(cand[:n], self._lane_words(query, cand, strong, weak)) + cand[n:]
        best = int(strong.max())
        taught = strong[strong > 0]
        med = float(np.median(taught)) if len(taught) else 0.0
        if best - med < self.gap * self.bits:
            status, flagged = "abstain", set()
        else:
            flagged = {j for j in cand[:k] if best - int(strong[j]) <= self.near * self.bits}
            status = "ambiguous" if len(flagged) > 1 else "confident"
        rows = []
        for j in cand[:k]:
            s = self.src[j]
            ctx = [self.texts[i] for i in range(max(0, j - context), min(len(self.texts), j + context + 1))
                   if i != j and s >= 0 and self.src[i] == s]
            rows.append({"fact": self.texts[j], "source": self.sources[s]["path"] if s >= 0 else "(taught)", "unit": self.pos[j],
                         "strong": int(strong[j]), "weak": int(weak[j]), "context": ctx,
                         "flag": "ambiguous" if (status == "ambiguous" and j in flagged) else None})
        return {"status": status, "rows": rows, "law": describe(self.law.law), "law_active": self.law.active}

    def info(self):
        return {"path": self.path, "model": self.man["model"], "device": self.man["device"], "bits": self.bits, "seed": self.man["seed"],
                "units": len(self.texts), "cues": len(self.cue_texts), "sources": len(self.sources), "shards": len(self.man["shards"]),
                "bytes of bits": int((len(self.texts) + len(self.cue_texts)) * self.W * 8),
                "learned law": {"law": describe(self.law.law), "active": self.law.active, "examples": len(self.law.examples)}}
