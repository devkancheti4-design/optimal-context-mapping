"""The first router law's lanes and observations for a live memory: what router_eval.py measures offline, served live.

A slice memory (cut from the 9M memory, so its rows are the 9M rows in order) plus the 9M BM25 index (SQLite FTS5,
~/cmlm-bench4/fts9m.db) restricted to the slice. For a question: the five readouts (0 CERTIFIED, 1 MEANING, 2 KEYWORD,
3 MIX, 4 WIDE) as local rows, and the eight observation values the law reads."""
import math, os, re, sqlite3
import numpy as np

STOP = set("a an the of to in on for and or is are was were be been by with at from as that this which what who whom whose when where why how "
           "do does did has have had it its his her their they them he she i you we our your my me us not no than then there these those "
           "into about over under after before between during while can could would should may might will shall one some any all".split())
words = lambda s: [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1]
stem = lambda w: w[:-1] if len(w) > 3 and w.endswith("s") else w
N9 = 277681                                                     # sentences in the 9M memory (the IDF base, as offline)


import os as _os


def _bits(name):
    """An optional limit in bits from the environment (e.g. OCM_CERT_MIN_OVER_OWN=37); unset or empty: None."""
    v = _os.environ.get(name, "").strip()
    return int(v) if v else None


CERT_MIN_LIFT = _bits("OCM_CERT_MIN_LIFT")   # bits; when set, the taught lane also needs its cue this far above the question's median
                       # agreement (its chance level). None: the law as published (the lead alone decides).
RELATION_LIMIT = _bits("OCM_RELATION_LIMIT")      # bits; when set, taught question vectors count for a question only if the best of them
                           # beats the best code text's agreement by this much (candidate: 37 bits, one sd of chance
                           # agreement); otherwise the code alone ranks it, as if nothing were taught. None: off.
CERT_MIN_OVER_OWN = _bits("OCM_CERT_MIN_OVER_OWN")   # bits; when set, the taught lane also needs its cue this far above the best code text's
                           # agreement (a candidate relation limit: one sd of chance agreement, 37 bits). None: off.


class Lanes:
    def __init__(self, mem, global_rows, db, RL):
        self.m, self.RL = mem, RL
        self.g = np.asarray(global_rows); self.local = {int(gj): i for i, gj in enumerate(self.g)}
        self.con = sqlite3.connect(db, check_same_thread=False); self.dfc = {}

    def df(self, w):
        if w not in self.dfc:
            self.dfc[w] = self.con.execute("select count(*) from s where s match ?", (f'"{w}"',)).fetchone()[0]
        return self.dfc[w]

    def keyword(self, text, k=10, allow=None):
        ws = sorted(set(words(text)))
        if not ws:
            return []
        rows = self.con.execute("select rowid from s where s match ? order by bm25(s) limit 3000", (" OR ".join(f'"{w}"' for w in ws),)).fetchall()
        return [self.local[r[0] - 1] for r in rows if (r[0] - 1) in self.local
                and (allow is None or (r[0] - 1 < len(allow) and allow[r[0] - 1]))][:k]

    def scores(self, text):
        m = self.m
        qc = m.measure([text])[0]; qs = m.measure([text], query=True)[0] if m.query_prefix else qc
        weak = m._agree(qs, m.fshards, [p[-1] for p in m.pending_f]).astype(np.int64)
        own = np.where(m.self_a[:len(weak)], weak, 0)
        cue = np.full(len(weak), -1, dtype=np.int64)
        if m.cue_texts:
            np.maximum.at(cue, m.cue_fact_a, m._agree(qc, m.cshards, [p[-1] for p in m.pending_c]))
        return np.maximum(own, cue), weak, own, cue

    def measure(self, text, allow=None):
        """(lanes as local rows, observation values). allow: a boolean mask over the units; when given, the lanes and the
        router's observations are computed over the allowed units only (a scope, such as code files)."""
        RL, m = self.RL, self.m
        strong, weak, own, cue = self.scores(text)
        pool = np.arange(len(strong)) if allow is None else np.flatnonzero(np.asarray(allow[:len(strong)], bool))
        if not len(pool):                                                 # nothing in scope: the whole workspace
            pool, allow = np.arange(len(strong)), None
        if RELATION_LIMIT is not None and len(pool) and int(cue[pool].max()) >= 0 \
                and int(cue[pool].max()) - int(own[pool].max()) < RELATION_LIMIT:
            strong, cue = own.copy(), np.full_like(cue, -1)               # nothing taught is related enough: the code decides
        sp = strong[pool]
        key = sp * 1025 + weak[pool]
        n = len(key); kk = min(25, n)                                    # small workspaces: fewer than 26 units
        top = np.argpartition(-key, kk - 1)[:kk] if n > kk else np.arange(n)
        top = top[np.lexsort((top, -key[top]))]
        mean20 = [int(pool[j]) for j in top[:20]]
        second = int(strong[mean20[1]]) if len(mean20) > 1 else 0
        kw = self.keyword(text, allow=allow)
        allw = set(words(text))
        rare = {w for w in allw if self.df(w) > 0 and math.log(N9 / self.df(w)) >= RL.observe.THETA}
        def matched(j):
            toks = {stem(t) for t in re.findall(r"[a-z0-9]+", m.texts[j].lower())}
            return {w for w in allw if stem(w) in toks}
        keyhit = bool(kw) and bool(rare & matched(kw[0])) and (len(kw) < 2 or len(matched(kw[0])) > len(matched(kw[1])))
        best = int(strong[mean20[0]])
        j1 = mean20[0]
        cert = int(strong[j1]) - second if cue[j1] >= own[j1] and cue[j1] >= 0 else -1
        lift = int(cue[j1]) - int(np.median(sp)) if cue[j1] >= 0 else None      # the cue's agreement over chance
        if cert >= 0 and CERT_MIN_LIFT is not None and lift < CERT_MIN_LIFT:
            cert = -1                       # relation limit: the taught question is not related enough to this one
        over_own = int(cue[j1]) - int(own[pool].max()) if cue[j1] >= 0 else None   # the cue's margin over any code text
        if cert >= 0 and CERT_MIN_OVER_OWN is not None and over_own < CERT_MIN_OVER_OWN:
            cert = -1                       # the taught question must explain this one better than any code does
        obs = {"cert_lead": cert, "top_lead": best - second, "n_near": int((sp >= best - RL.NEAR).sum()),
               "best_minus_med": best - int(np.median(sp)),
               "idf": max([math.log(N9 / self.df(w)) for w in allw if self.df(w) > 0] or [0.0]),
               "key_lead": RL.TAU if keyhit else 0, "shared": bool(set(mean20[:10]) & set(kw)),
               "cue_lift": lift, "over_own": over_own, "from_cue": bool(cue[j1] >= own[j1] and cue[j1] >= 0), "top": j1}
        lanes = {0: mean20[:1], 1: mean20[:10], 2: kw, 3: list(dict.fromkeys(mean20[:5] + kw[:5])), 4: mean20}
        return lanes, obs

    def byte(self, obs, tried):
        return self.RL.observe(obs["cert_lead"], obs["top_lead"], obs["n_near"], obs["best_minus_med"], obs["idf"], obs["key_lead"], obs["shared"], tried)

    def readout(self, rows):
        m = self.m
        return "\n".join(f"{i}. {m.texts[j]}\n   source: corpus/{m.sources[m.src[j]]['path'] if m.src[j] >= 0 else '(taught)'}" for i, j in enumerate(rows, 1))
