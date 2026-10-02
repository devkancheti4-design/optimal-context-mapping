"""Text into units: the sentences a memory stores and returns.

Paragraphs are split on blank lines, then into sentences; a line break inside a paragraph is kept as a boundary
only when the next line starts a new thought (a capital, a digit or a bullet), so wrapped prose is rejoined. Units
under `min_words` words are dropped; a unit over `max_chars` is cut at word boundaries. Deterministic: the same
text gives the same units in the same order."""
import re

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")
# mail and news metadata: near-identical lines in every message, which crowd a readout and rarely answer anything
HEADER = re.compile(r"^(From|Subject|Organi[sz]ation|Lines|Reply-To|NNTP-Posting-Host|Distribution|Keywords|Summary|"
                    r"Article-I\.D\.|Expires|X-[\w-]+|Sender|Path|Newsgroups|Message-ID|References|Date|To|Cc):|^In article <|"
                    r"(writes|wrote):$", re.I)


def units(text, min_words=4, max_chars=400, drop_headers=False):
    if drop_headers:
        return [u for u in units(text, min_words, max_chars) if not HEADER.search(u)]
    out = []
    for para in re.split(r"\n\s*\n", text.replace("\r", "")):
        lines = [l.strip() for l in para.split("\n") if l.strip()]
        if not lines:
            continue
        joined = lines[0]
        for l in lines[1:]:
            joined += ("\n" if re.match(r"[A-Z0-9\-*>•]", l) and re.search(r"[.!?:]$", joined) else " ") + l
        for piece in joined.split("\n"):
            for s in _SENT.split(piece):
                s = " ".join(s.split())
                while len(s) > max_chars:
                    cut = s.rfind(" ", 0, max_chars)
                    cut = cut if cut > max_chars // 2 else max_chars
                    head, s = s[:cut], s[cut:].strip()
                    if len(head.split()) >= min_words:
                        out.append(head)
                if len(s.split()) >= min_words:
                    out.append(s)
    return out
