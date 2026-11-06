"""A program checks every answer against the code at that commit. No judge.

    right    it states the fact as the code has it then
    stale    it states what used to be true, and not what is true now
    hedged   it states both
    miss     it states neither"""
import re


def forms(kind, value):
    """Each thing the answer must state, each as its acceptable spellings."""
    if kind == "where":
        return [[value]]
    if kind == "base":
        return [[v, v.rsplit(".", 1)[-1]] for v in value]
    if isinstance(value, bool) or value is None:
        return [[str(value)]]
    if isinstance(value, (int, float)):
        return [[repr(value)] + ([repr(float(value))] if isinstance(value, int) else [repr(int(value))] if value == int(value) else [])]
    return [[value]]


def clean(text):
    return re.sub(r"(?<=\d)[,_](?=\d{3}\b)", "", text)


def says(answer, spelling):
    return re.search(r"(?<![\w.])" + re.escape(spelling) + r"(?!\w|\.\d)", answer) is not None


def states(kind, value, answer):
    text = clean(answer or "")
    if isinstance(value, bool) or value is None:      # "defaults to true", "defaults to none"
        return re.search(r"(?<![\w.])" + str(value) + r"(?!\w)", text, re.I) is not None
    return all(any(says(text, s) for s in group) for group in forms(kind, value))


def grade(kind, truth, answer, old=None):
    """old is what used to be true, when the fact has changed."""
    now = states(kind, truth, answer)
    was = old is not None and old != truth and states(kind, old, answer)
    if now and was and kind == "base" and set(old) <= set(truth):     # a parent class was added: stating the whole list states the old part too
        return "right"
    return "hedged" if now and was else "right" if now else "stale" if was else "miss"
