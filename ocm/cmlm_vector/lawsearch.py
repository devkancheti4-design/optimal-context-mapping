"""The learned law: fluidnet's searched integer law over the vector law's top candidates, learned from Claude's teaching.

The vector law ranks by closeness alone. The learned law decides which of its top N candidates comes first, from an
8-bit word measured per candidate, and it is SEARCHED, not trained: each lane is STRONG, WEAK or OFF (3^8 = 6,561
laws), the rank is the lexicographic (strong count, weak count, the vector law's order), one strong beats any number
of weak because the rank says so, and every law is monotone (a lane turning on never lowers a candidate), which
`monotone` checks on all 256 words as fluidnet checks its laws.

    b0 CUE1   best of all facts by cue bits          b1 FACT1  best by fact-text bits
    b2 CUE~   within 1% of the bits of the best cue  b3 FACT~  the same by fact text
    b4 CUE3   top 3 by cue                           b5 FACT3  top 3 by fact text
    b6 TYPE   the question asks for a date / amount / count / person / place / percent and the fact holds one;
              silent when it asks for none (fluidnet's revision 2: unmeasured is silent, not weak)
    b7 BOTH3  top 3 by cue and by fact text

The examples are the pairs Claude teaches for a fact the memory already holds: a new wording of a known fact, which
is what learning from a miss produces. Each is measured before its cue is stored, so it cannot match itself. The
gate is prequential and honest: every example is first scored by the law in use and by the plain vector order, and
the law takes over only when it has put the right fact first more often, on examples it had not yet learned from,
over the last 50 examples (and it is searched on those 50), so a law that stops winning loses its place.
sandbox/general_check/law_search.py is the same law judged on held-out facts and topics."""
import itertools
import re

import numpy as np

LANES = ("CUE1", "FACT1", "CUE~", "FACT~", "CUE3", "FACT3", "TYPE", "BOTH3")
NEAR = 0.01

ASK = {
    "date": r"\bwhen\b|\bdates?\b|\bdays?\b|\bdeadline\b|\bwhat time\b|\bmoment\b|\bwhich year\b|\bwhat year\b",
    "money": r"\bhow much\b|\bmoney\b|\bprice\b|\bcosts?\b|\bfees?\b|\bcharges?\b|\bspend|\bbudget|\bbill\b|\bpay\b|\bpaid\b|\bowe\b"
             r"|\bsalary\b|\bcompensation\b|\bdollar|\bfunding\b|\ballowance\b|\breimburse|\bbonus\b|\bstipend\b|\bearn\b|\bpayout\b",
    "count": r"\bhow many\b|\bnumber of\b|\bcapacity\b|\bheadcount\b|\bhold\b|\bfit\b|\bcount\b|\bsample size\b|\battendance\b",
    "person": r"\bwho\b|\bwhom\b|\bwhose\b|\bwhich (colleague|individual|person|people|employee|staff|hire|specialist)\b",
    "place": r"\bwhere\b|\baddress\b|\blocation\b|\bvenue\b|\bwhich city\b|\bregion\b|\bzone\b",
    "percent": r"\bpercent|\bproportion\b|\bshare of\b|\bfraction\b|\bportion\b",
}
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
HOLDS = {
    "date": rf"\b({MONTHS}|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b|\b(19|20)\d\d\b|\bQ[1-4]\b",
    "money": r"\$\s?\d",
    "count": r"(?<![$\d.,])\b\d[\d,]*\b(?!\s*(percent|%))",
    "person": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
    "place": r"\b(Street|Avenue|Road|Boulevard|floor|Room|Suite|region)\b",
    "percent": r"\bpercent\b|%",
}


def asks(q):
    return {t for t, rx in ASK.items() if re.search(rx, q.lower())}


def holds(f):
    return {t for t, rx in HOLDS.items() if re.search(rx, f)}


LAWS = np.array(list(itertools.product((0, 1, 2), repeat=8)), dtype=np.int16)          # 0 off, 1 weak, 2 strong
BASE = int(np.where(np.all(LAWS == 0, axis=1))[0][0])                                 # every lane off: the vector order
_BITS = ((np.arange(256)[:, None] >> np.arange(8)[None, :]) & 1).astype(np.int16)
VALUE = ((_BITS[None] * (LAWS[:, None, :] == 2)).sum(-1) * 16
         + (_BITS[None] * (LAWS[:, None, :] == 1)).sum(-1)).astype(np.int16)           # [law, word]


def words(order, strong, weak, bits, qtypes, ftypes, n=8):
    """The 8-bit word of each of the top-n candidates in `order` (the vector law's order)."""
    sr = np.empty(len(strong), dtype=np.int64); sr[np.argsort(-strong, kind="stable")] = np.arange(len(strong))
    wr = np.empty(len(weak), dtype=np.int64); wr[np.argsort(-weak, kind="stable")] = np.arange(len(weak))
    bs, bw = int(strong.max()), int(weak.max())
    out = []
    for j in order[:n]:
        b = (sr[j] == 0, wr[j] == 0, strong[j] >= bs - NEAR * bits, weak[j] >= bw - NEAR * bits,
             sr[j] < 3, wr[j] < 3, bool(qtypes & ftypes[j]), sr[j] < 3 and wr[j] < 3)
        out.append(sum(int(v) << i for i, v in enumerate(b)))
    return out


def rank_of(law, ws, right):
    """Where `law` puts the candidate at position `right` (0 = first); ties keep the vector law's order."""
    if right < 0:
        return 99
    v = VALUE[law][ws].astype(np.int32) * 64 - np.arange(len(ws))
    return int((v > v[right]).sum())


def apply(law, ws):
    """The permutation of the candidates that `law` ranks."""
    v = VALUE[law][ws].astype(np.int32) * 64 - np.arange(len(ws))
    return list(np.argsort(-v, kind="stable"))


def search(examples, n=8):
    """fluidnet: the law that puts the right fact first most often; ties -> better top-3, then fewer lanes on."""
    ex = [(w + [0] * (n - len(w)), r) for w, r in examples if r >= 0]
    if not ex:
        return BASE
    Wd = np.array([w for w, _ in ex]); R = np.array([r for _, r in ex])
    v = VALUE[:, Wd].astype(np.int32) * 64 - np.arange(n, dtype=np.int32)[None, None, :]
    vr = np.take_along_axis(v, np.broadcast_to(R[None, :, None], v.shape[:2] + (1,)), 2)
    got = (v > vr).sum(-1)
    key = (got == 0).mean(1) * 1e6 + (got < 3).mean(1) * 1e3 - (LAWS > 0).sum(1)
    return int(np.argmax(key))


def monotone(law):
    return all(VALUE[law][w | (1 << b)] >= VALUE[law][w] for w in range(256) for b in range(8))


def describe(law):
    s = [x for x, t in zip(LANES, LAWS[law]) if t == 2]; w = [x for x, t in zip(LANES, LAWS[law]) if t == 1]
    return f"strong {{{', '.join(s)}}} weak {{{', '.join(w)}}}" if (s or w) else "the vector order"


class LearnedLaw:
    def __init__(self, n=8, min_examples=12, window=50):
        """window: the law is searched on, and must be winning over, the last `window` examples (None: all of
        them). The memory changes as Claude teaches (cues pile up and the vector order gets better), so a law
        that won early must keep winning to keep its place."""
        self.n, self.min_examples, self.window = n, min_examples, window
        self.examples = []                         # (words, position of the right fact among the candidates, or -1)
        self.scored = []                           # prequential, per example: (law in use first, vector order first)
        self.law = BASE

    @property
    def hits(self):
        recent = self.scored[-self.window:] if self.window else self.scored
        return {"law": sum(a for a, _ in recent), "vector": sum(b for _, b in recent)}

    @property
    def active(self):
        h = self.hits
        return len(self.examples) >= self.min_examples and self.law != BASE and h["law"] > h["vector"]

    def observe(self, ws, right):
        self.scored.append((int(rank_of(self.law, ws, right) == 0), int(right == 0)))
        self.examples.append((list(ws), int(right)))
        self.law = search(self.examples[-self.window:] if self.window else self.examples, self.n)
        assert monotone(self.law)

    def order(self, cand, ws):
        """The candidates reordered by the law when it has earned it, else as they came."""
        return [cand[i] for i in apply(self.law, ws)] if self.active else list(cand)

    def state(self):
        return {"law": describe(self.law), "active": self.active, "examples": len(self.examples),
                "prequential first-right": dict(self.hits)}
