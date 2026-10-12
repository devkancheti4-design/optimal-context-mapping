"""PROTOCOL_SWE_SONNET.md report -> report_swe_sonnet.json. Per issue and arm: requests, tokens, dollars from each
subagent transcript; right from answer.json (eyes: the reply). Measured, and adjusted per DS1/DS2 (task read and
hand-back removed; for the eyes only the task read, since the reply is the answer)."""
import json, os, re, sys
from collections import Counter
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
sys.path.insert(0, f"{B}/reports"); sys.path.insert(0, H)
from common import ci
import transcripts as TR
PRICE = {"sonnet": (2.00, 2.50, 0.20, 10.00), "haiku": (0.10, 0.125, 0.01, 0.50)}     # input, cache write, cache read, output per 1M
ISSUES = json.load(open(f"{B}/swe/issues.json"))["issues"]; RO = json.load(open(f"{H}/readouts.json"))
TAUGHT = "(readout: the code a taught question"


def usd(reqs, m):
    p = PRICE[m]; return sum(r["input"] * p[0] + r["write"] * p[1] + r["read"] * p[2] + r["output"] * p[3] for r in reqs) / 1e6


def norm(a):
    a = str(a or "").strip().strip("`'\" ").lstrip("./"); return a[len("corpus/"):] if a.startswith("corpus/") else a


def right(a, gold):
    a = norm(a); return bool(a) and (a == gold or gold.endswith("/" + a) or a.endswith(gold))


ix = TR.index(); rows = {}; off = Counter(); models = Counter(); missing = []
for i in ISSUES:
    r = {}
    for arm in ("alone", "kit"):
        fs = ix.get((arm, i["id"]))
        ans = json.load(open(f"{H}/agents/{arm}/{i['id']}/answer.json"))["file"] if os.path.exists(f"{H}/agents/{arm}/{i['id']}/answer.json") else ""
        if not fs: missing.append((arm, i["id"])); continue
        m = TR.measure(fs[-1]); reqs = m["requests"]
        for x in m["models"]: models[(arm, x)] += 1
        off[arm] += len(m["off script"])
        adj = reqs[1:-1] if len(reqs) > 2 else reqs[-1:]
        r[arm] = {"right": right(ans, i["file"]), "answer": norm(ans), "requests": len(reqs), "usd": usd(reqs, "sonnet"),
                  "requests adj": len(adj), "usd adj": usd(adj, "sonnet"), "tokens": sum(sum(x.values()) for x in reqs), "off": m["off script"]}
    if "alone" not in r or "kit" not in r: continue
    md = dict(r["kit"]); md["path"] = "agent"
    if RO[i["id"]].startswith(TAUGHT):
        fs = ix.get(("eyes", i["id"]))
        m = TR.measure(fs[-1]); reqs = m["requests"]
        for x in m["models"]: models[("eyes", x)] += 1
        off["eyes"] += len(m["off script"])
        text = m["last text"] or ""
        for line in open(fs[-1]):                                      # the hand-back carries the reply
            d = json.loads(line); mm = (d.get("message") or {})
            for b in mm.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "SubagentHandback": text = str((b.get("input") or {}).get("message", text))
        e_req, e_usd, e_adj, e_usd_adj = len(reqs), usd(reqs, "haiku"), len(reqs[1:]), usd(reqs[1:], "haiku")
        hit = re.search(r"(?:corpus/)?(django/[\w/]+\.py)", text)
        if "NEED_SEARCH" not in text and hit:
            md = {"right": right(hit.group(1), i["file"]), "answer": hit.group(1), "requests": e_req, "usd": e_usd, "requests adj": e_adj, "usd adj": e_usd_adj, "path": "eyes"}
        else:
            md = {k: v for k, v in r["kit"].items()}; md["path"] = "eyes -> agent"
            md["requests"] += e_req; md["usd"] += e_usd; md["requests adj"] += e_adj; md["usd adj"] += e_usd_adj
        md["eyes reply"] = text[:80]
    r["modeld"] = md; rows[i["id"]] = r

ids = [i["id"] for i in ISSUES if i["id"] in rows]
seen, rep_file = set(), {}
for i in ISSUES: rep_file[i["id"]] = i["file"] in seen; seen.add(i["file"])


def block(sel):
    d = {"issues": len(sel)}
    for a in ("alone", "kit", "modeld"):
        d[a] = {"right": sum(rows[i][a]["right"] for i in sel),
                "requests per issue": round(sum(rows[i][a]["requests"] for i in sel) / len(sel), 2),
                "requests per issue, adjusted": round(sum(rows[i][a]["requests adj"] for i in sel) / len(sel), 2),
                "dollars per issue": round(sum(rows[i][a]["usd"] for i in sel) / len(sel), 5),
                "dollars per issue, adjusted": round(sum(rows[i][a]["usd adj"] for i in sel) / len(sel), 5)}
    for a in ("kit", "modeld"):
        for k, lab in (("requests", "request"), ("requests adj", "request (adjusted)"), ("usd", "dollar"), ("usd adj", "dollar (adjusted)")):
            num = [rows[i]["alone"][k] for i in sel]; den = [max(1e-9, rows[i][a][k]) for i in sel]
            d[f"{lab} factor alone/{a}"] = round(sum(num) / sum(den), 2); d[f"{lab} factor alone/{a} 95% CI"] = ci(num, den)
    return d


out = {"protocol sha256": json.load(open(f"{B}/prereg_hashes.json"))["PROTOCOL_SWE_SONNET.md"]["sha256"],
       "issues compared": len(ids), "missing sessions": missing, "models seen": {f"{a} {m}": n for (a, m), n in models.items()},
       "off-script tool calls": dict(off)}
out["all"] = block(ids); h = len(ids) // 2
out["first half"] = block(ids[:h]); out["second half"] = block(ids[h:])
out["repeat file"] = block([i for i in ids if rep_file[i]]); out["new file"] = block([i for i in ids if not rep_file[i]])
ey = [rows[i]["modeld"] for i in ids if rows[i]["modeld"]["path"] != "agent"]
out["model d eyes"] = {"taught-lane issues": len(ey), "answered by the eyes": sum(1 for r in ey if r["path"] == "eyes"),
                       "eyes right": sum(1 for r in ey if r["path"] == "eyes" and r["right"]),
                       "replies": {i: rows[i]["modeld"]["eyes reply"] for i in ids if "eyes reply" in rows[i]["modeld"]}}
a = out["all"]
out["S1"] = a["request factor alone/kit 95% CI"][0] > 1.0 and a["kit"]["right"] >= a["alone"]["right"] - 5
out["S2"] = a["modeld"]["requests per issue"] < a["kit"]["requests per issue"] and a["modeld"]["right"] >= a["alone"]["right"] - 5
out["S3"] = a["dollar factor alone/modeld 95% CI"][0] > 1.0
out["S4"] = out["second half"]["request factor alone/modeld"] > out["first half"]["request factor alone/modeld"]
out["S5"] = out["repeat file"]["request factor alone/modeld"] > out["new file"]["request factor alone/modeld"]
flash = json.load(open(f"{B}/swe/report_swe.json"))["all"]
out["gemini 2.5 flash, same task (PROTOCOL_SWE.md)"] = {k: flash[k] for k in flash if "factor" in k and "dollar" not in k} | {a: {"right": flash[a]["right"], "requests per issue": flash[a]["requests per issue"]} for a in ("alone", "kit", "modeld")}
json.dump(out, open(f"{H}/report_swe_sonnet.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("model d eyes",)}, indent=1)[:6000]); print(json.dumps(out["model d eyes"], indent=1))
