"""An embedding cache for rebuilds: each unit's embedding is stored once, keyed by the sha1 of its exact text and the
model's name, so a rebuild after code changes embeds only the units whose text changed.

The fingerprints are still computed by the build (centred on that build's own mean, then projected), so a cached build
gives the same workspace as a cold one: the cached vector is the one the model produced for that exact text. Tested
bit for bit in tests/test_kit.py. A cache holds 3 KB per distinct unit (768 float32 values)."""
import hashlib, os, sqlite3, threading

import numpy as np


class CachedEmbedder:
    def __init__(self, inner, path, model=""):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.inner, self.model, self.lock = inner, model, threading.Lock()
        self.con = sqlite3.connect(path, check_same_thread=False)
        self.con.execute("create table if not exists e(k blob primary key, v blob)")
        self.reused = self.embedded = 0

    def __getattr__(self, name):                       # dim, tokenizer, device: whatever else is asked of the model
        return getattr(self.inner, name)

    def __call__(self, texts, batch=256):
        keys = [hashlib.sha1((self.model + "\0" + t).encode("utf-8")).digest() for t in texts]
        with self.lock:
            found = {}
            uniq = list(dict.fromkeys(keys))
            for s in range(0, len(uniq), 900):
                part = uniq[s:s + 900]
                found.update((bytes(k), v) for k, v in
                             self.con.execute(f"select k, v from e where k in ({','.join('?' * len(part))})", part))
            first = list({k: i for i, k in reversed(list(enumerate(keys))) if k not in found}.values())
            if first:
                vec = self.inner([texts[i] for i in first], batch=batch)
                rows = [(keys[i], np.asarray(v, dtype=np.float32).tobytes()) for i, v in zip(first, vec)]
                self.con.executemany("insert or ignore into e(k, v) values (?, ?)", rows); self.con.commit()
                found.update(rows)
            self.embedded += len(first); self.reused += len(texts) - len(first)
        if not keys:
            return np.zeros((0, getattr(self.inner, "dim", 768)), np.float32)
        return np.stack([np.frombuffer(found[k], dtype=np.float32) for k in keys])
