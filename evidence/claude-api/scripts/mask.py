"""PROTOCOL_VALUE E4: remove every code identifier from a bug report, deterministically."""
import re

CODE_FENCE = re.compile(r"```.*?```", re.S)
BACKTICK = re.compile(r"`[^`\n]+`")
TRACE = re.compile(r"(?m)^\s*(File \".*|Traceback.*|\w*(Error|Exception)\b.*:.*|>>>.*|\.\.\..*)$")
INDENTED = re.compile(r"(?m)^(?: {4}|\t).*$")
PATH = re.compile(r"\b[\w./-]+\.(?:py|txt|html|js|cfg|toml|ini|rst|json)\b|\b(?:[\w-]+/){1,}[\w.-]+")
DOTTED = re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b")
CALL = re.compile(r"\b[A-Za-z_]\w*\(\)?")
SNAKE = re.compile(r"\b\w*_\w*\b")
CAMEL = re.compile(r"\b(?:[a-z]+[A-Z]\w*|[A-Z][a-z0-9]+[A-Z]\w*)\b")
UPPER = re.compile(r"\b[A-Z]{2,}[A-Z0-9_]*\b")


def mask(text):
    t = CODE_FENCE.sub(" [code] ", text)
    for rx in (TRACE, INDENTED):
        t = rx.sub("[code]", t)
    for rx in (BACKTICK, PATH, DOTTED, CALL, SNAKE, CAMEL, UPPER):
        t = rx.sub("[name]", t)
    t = re.sub(r"(\[(?:name|code)\][\s,.;:]*){2,}", lambda m: m.group(1).strip(" ,.;:") + " ", t)
    return re.sub(r"[ \t]+", " ", t).strip()


if __name__ == "__main__":
    import json, os
    iss = json.load(open(os.path.expanduser("~/cmlm-bench10/swe/issues.json")))["issues"]
    print(mask(iss[0]["issue"])[:600])
