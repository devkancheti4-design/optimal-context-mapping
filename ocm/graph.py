"""modeld graph: the context graph, the repository's DNA as Model D keeps it between sessions, written as JSON and as a
page that opens offline.

  modeld graph [workspace] [--out DIR] [--k 3] [--show 400]

What it holds:
- **file nodes:** every file of the workspace. A file's fingerprint is the majority, bit by bit, of the 1,024-bit
  fingerprints of its pieces of code.
- **question nodes:** every question taught (the Life), each with the exact line that answered it.
- **taught edges:** each question to the file and line that answered it.
- **meaning edges:** each file to its k nearest files by fingerprint agreement. An edge is kept only when the agreement
  is at least 74 bits above the median between files: the router law's GAP, twice the 37-bit spread of chance. Files
  linked this way mean similar things, whether or not either imports the other.

It is not a call or import graph. Model D never reads the code's structure; it leaves that to the agent reading the
code. No model calls: every fingerprint is already in the workspace.

Writes <out>/context-graph.json (everything) and <out>/context-graph.html. The page draws the `--show` files with the
most taught questions and meaning edges; click a file for its nearest files and its questions."""
import argparse, datetime, json, os, sys

import numpy as np

GAP = 74                                                                    # bits over the median: the router law's GAP


def _fingerprints(m, n):
    """Each unit's 1,024 bits as a (n, 128) uint8 array."""
    rows = np.concatenate([np.asarray(s) for s in m.fshards])[:n] if m.fshards else np.zeros((0, m.W), np.uint64)
    return np.ascontiguousarray(rows).view(np.uint8).reshape(len(rows), -1)


def context_graph(folder, k=3, log=print):
    from .server import Workspace
    from .units import DOCS, is_test
    w = Workspace(folder); m = w.mem
    n = min(w.meta["units"], len(m.texts))
    src = np.array(m.src[:n]); fp = _fingerprints(m, n)
    keep = np.flatnonzero(src >= 0)
    order = keep[np.argsort(src[keep], kind="stable")]
    fids, starts, counts = np.unique(src[order], return_index=True, return_counts=True)
    ones = np.zeros((len(fids), fp.shape[1] * 8), np.int32)
    for s in range(0, len(order), 8192):                                   # bit counts per file, in blocks
        blk = order[s:s + 8192]; fi = np.searchsorted(fids, src[blk])
        cut = np.flatnonzero(np.r_[True, fi[1:] != fi[:-1]])               # where the next file starts (sorted by file)
        ones[fi[cut]] += np.add.reduceat(np.unpackbits(fp[blk], axis=1).astype(np.int32), cut, axis=0)
    F = np.packbits(ones * 2 > counts[:, None], axis=1)                    # the majority of its units, bit by bit
    bits = F.shape[1] * 8; nf = len(fids)
    near = np.zeros((nf, k), np.int64); agree = np.zeros((nf, k), np.int64); sample = []
    step = max(8, min(128, 32_000_000 // max(1, nf * F.shape[1])))        # about 32 MB per block
    for s in range(0, nf, step):
        a = bits - np.bitwise_count(F[s:s + step, None, :] ^ F[None, :, :]).sum(axis=2, dtype=np.int64)
        a[np.arange(len(a)), np.arange(s, s + len(a))] = -1                # never a file's own edge
        sample.append(a.ravel()[:: max(1, a.size // 4000)])
        top = np.argsort(-a, axis=1, kind="stable")[:, :k]
        near[s:s + len(a)], agree[s:s + len(a)] = top, np.take_along_axis(a, top, axis=1)
    sample = np.concatenate(sample); med = int(np.median(sample[sample >= 0])) if len(sample) else 0
    path = lambda f: m.sources[f]["path"]
    rel = lambda p: p.split("/", 1)[1] if "/" in p else p
    nodes = [{"id": f"f{int(f)}", "kind": "file", "path": rel(path(f)), "units": int(c), "taught": 0,
              "test": is_test(rel(path(f))), "doc": os.path.splitext(path(f))[1].lower() in DOCS} for f, c in zip(fids, counts)]
    index = {rel(path(f)): i for i, f in enumerate(fids)}
    edges, seen = [], set()
    for i in range(nf):
        for j, ag in zip(near[i], agree[i]):
            if ag - med >= GAP and (min(i, j), max(i, j)) not in seen:
                seen.add((min(i, j), max(i, j)))
                edges.append({"source": nodes[i]["id"], "target": nodes[j]["id"], "kind": "meaning", "over_median": int(ag - med)})
    nq = 0
    for key in sorted(w.life.store):
        v = json.loads(w.life.recall(key)); p, line = v["at"].rsplit(":", 1); i = index.get(rel(p))
        if i is None:
            continue
        nq += 1; qid = f"q{nq}"; nodes[i]["taught"] += 1
        nodes.append({"id": qid, "kind": "question", "text": key, "at": f"{rel(p)}:{line}", "line": (v.get("code") or "").strip()})
        edges.append({"source": qid, "target": nodes[i]["id"], "kind": "taught", "line": int(line)})
    stats = {"files": nf, "units": int(len(keep)), "questions": nq, "meaning_edges": len(seen),
             "taught_edges": nq, "median_agreement_bits": med, "gap_bits": GAP, "k": k}
    log(f"context graph of {os.path.abspath(folder)}: {nf:,} files ({len(keep):,} pieces of code), {nq:,} taught "
        f"questions, {len(seen):,} meaning edges (k = {k}, at least {GAP} bits over the median {med})")
    return {"workspace": os.path.basename(os.path.abspath(folder)), "built": datetime.date.today().isoformat(),
            "stats": stats, "nodes": nodes, "edges": edges}


def page(g, show=400, per_file=40):
    """A self-contained page: the `show` files with the most taught questions and meaning edges, drawn by a small force
    layout; each file's questions (up to per_file) come with it. No network, no libraries."""
    files = [x for x in g["nodes"] if x["kind"] == "file"]
    deg = {}
    for e in g["edges"]:
        if e["kind"] == "meaning":
            deg[e["source"]] = deg.get(e["source"], 0) + 1; deg[e["target"]] = deg.get(e["target"], 0) + 1
    pick = sorted(files, key=lambda x: (-(x["taught"] + 3 * deg.get(x["id"], 0)), x["path"]))[:show]
    ids = {x["id"] for x in pick}
    qs = {}
    for e in g["edges"]:
        if e["kind"] == "taught" and e["target"] in ids and len(qs.setdefault(e["target"], [])) < per_file:
            qs[e["target"]].append(e["source"])
    qtext = {x["id"]: [x["text"], x["at"]] for x in g["nodes"] if x["kind"] == "question"}
    data = {"stats": g["stats"], "workspace": g["workspace"],
            "files": [{"id": x["id"], "p": x["path"], "u": x["units"], "t": x["taught"], "x": x["test"], "d": x["doc"],
                       "q": [qtext[q] for q in qs.get(x["id"], [])]} for x in pick],
            "edges": [[e["source"], e["target"], e["over_median"]] for e in g["edges"] if e["kind"] == "meaning"
                      and e["source"] in ids and e["target"] in ids]}
    return PAGE.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))


PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Context graph</title><style>
:root{--bg:#fbfaf7;--fg:#1f1e1c;--mut:#6b6963;--line:#d9d6cc;--card:#fff;--q:#0f6e56;--accent:#534ab7}
@media (prefers-color-scheme:dark){:root{--bg:#1c1b19;--fg:#ecebe6;--mut:#a3a199;--line:#3a3935;--card:#262522;--q:#5dcaa5;--accent:#afa9ec}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif}
header{padding:14px 18px;border-bottom:1px solid var(--line)}h1{font-size:18px;font-weight:500;margin:0}
header p{margin:4px 0 0;color:var(--mut);font-size:13px}main{display:flex;flex-wrap:wrap;min-height:calc(100vh - 70px)}
#c{flex:1 1 560px;min-width:0;height:calc(100vh - 70px);display:block}aside{flex:0 1 360px;min-width:0;padding:14px 18px;
border-left:1px solid var(--line);overflow:auto;max-height:calc(100vh - 70px)}input{width:100%;padding:7px 9px;border:1px solid var(--line);
border-radius:8px;background:var(--card);color:var(--fg);font:inherit}h2{font-size:15px;font-weight:500;margin:14px 0 4px;word-break:break-all}
.m{color:var(--mut);font-size:12px}ul{padding-left:18px;margin:6px 0}li{margin:3px 0}.q{color:var(--q)}a{color:var(--accent);cursor:pointer}
</style></head><body><header><h1>Context graph</h1><p id="s"></p></header><main><canvas id="c"></canvas><aside>
<input id="f" placeholder="Find a file"><div id="info"><p class="m">Files sized by the questions taught onto them, linked by
meaning (not by imports). Click a file.</p></div></aside></main><script>
const D=__DATA__,S=D.stats;document.getElementById('s').textContent=`${D.workspace}: ${S.files.toLocaleString()} files, `+
`${S.units.toLocaleString()} pieces of code, ${S.questions.toLocaleString()} taught questions, ${S.meaning_edges.toLocaleString()} meaning edges `+
`(showing ${D.files.length}). Built ${S.k} nearest per file, kept at ${S.gap_bits}+ bits over the median.`;
const N=D.files,ix={};N.forEach((n,i)=>{ix[n.id]=i;n.vx=0;n.vy=0;const a=i*2.399;n.X=Math.cos(a)*Math.sqrt(i)*18;n.Y=Math.sin(a)*Math.sqrt(i)*18});
const E=D.edges.map(e=>[ix[e[0]],ix[e[1]]]),adj=N.map(()=>[]);E.forEach(([a,b])=>{adj[a].push(b);adj[b].push(a)});
const top=p=>p.split('/')[0],tops=[...new Set(N.map(n=>top(n.p)))],pal=['#534ab7','#d85a30','#1d9e75','#ba7517','#d4537e','#378add','#639922','#888780'];
const col=n=>pal[Math.min(tops.indexOf(top(n.p)),7)],rad=n=>3+Math.sqrt(n.t)*1.6;
for(let it=0;it<260;it++){const k=1-it/260;for(let i=0;i<N.length;i++)for(let j=i+1;j<N.length;j++){let dx=N[i].X-N[j].X,dy=N[i].Y-N[j].Y,d=dx*dx+dy*dy+.01;
if(d>90000)continue;const f=600/d;N[i].vx+=dx*f;N[i].vy+=dy*f;N[j].vx-=dx*f;N[j].vy-=dy*f}
E.forEach(([a,b])=>{const dx=N[b].X-N[a].X,dy=N[b].Y-N[a].Y,f=.02;N[a].vx+=dx*f;N[a].vy+=dy*f;N[b].vx-=dx*f;N[b].vy-=dy*f});
N.forEach(n=>{n.vx-=n.X*.004;n.vy-=n.Y*.004;n.X+=Math.max(-20,Math.min(20,n.vx*k));n.Y+=Math.max(-20,Math.min(20,n.vy*k));n.vx*=.5;n.vy*=.5})}
const c=document.getElementById('c'),x=c.getContext('2d');let sel=-1,sc=1,ox=0,oy=0;
function fit(){const r=c.getBoundingClientRect(),dpr=devicePixelRatio||1;c.width=r.width*dpr;c.height=r.height*dpr;x.setTransform(dpr,0,0,dpr,0,0);
const xs=N.map(n=>n.X),ys=N.map(n=>n.Y),w=Math.max(...xs)-Math.min(...xs)||1,h=Math.max(...ys)-Math.min(...ys)||1;
sc=Math.min(r.width/w,r.height/h)*.9;ox=r.width/2-(Math.max(...xs)+Math.min(...xs))/2*sc;oy=r.height/2-(Math.max(...ys)+Math.min(...ys))/2*sc;draw()}
const P=n=>[n.X*sc+ox,n.Y*sc+oy],css=v=>getComputedStyle(document.documentElement).getPropertyValue(v);
function draw(){const r=c.getBoundingClientRect();x.clearRect(0,0,r.width,r.height);x.lineWidth=.6;
E.forEach(([a,b])=>{const on=sel>=0&&(a==sel||b==sel);x.strokeStyle=on?css('--accent'):css('--line');x.globalAlpha=sel>=0&&!on?.35:1;
const [x1,y1]=P(N[a]),[x2,y2]=P(N[b]);x.beginPath();x.moveTo(x1,y1);x.lineTo(x2,y2);x.stroke()});
N.forEach((n,i)=>{const [px,py]=P(n),near=sel<0||i==sel||adj[sel].includes(i);x.globalAlpha=near?1:.25;x.fillStyle=col(n);
x.beginPath();x.arc(px,py,rad(n),0,7);x.fill();if(i==sel){x.strokeStyle=css('--fg');x.lineWidth=1.5;x.stroke();x.lineWidth=.6}});x.globalAlpha=1}
function pick(i){sel=i;draw();const n=N[i],h=s=>s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);
document.getElementById('info').innerHTML=`<h2>${h(n.p)}</h2><p class="m">${n.u} pieces of code, ${n.t} taught questions${n.x?', a test file':''}</p>`+
`<p class="m">Nearest by meaning</p><ul>${adj[i].map(j=>`<li><a data-i="${j}">${h(N[j].p)}</a></li>`).join('')||'<li class="m">none above the gap</li>'}</ul>`+
`<p class="m">Questions that point here${n.t>n.q.length?` (first ${n.q.length})`:''}</p><ul>${n.q.map(q=>`<li><span class="q">${h(q[0])}</span> <span class="m">${h(q[1])}</span></li>`).join('')||'<li class="m">none taught yet</li>'}</ul>`;
document.querySelectorAll('#info a').forEach(a=>a.onclick=()=>pick(+a.dataset.i))}
c.onclick=e=>{const r=c.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;let b=-1,bd=1e9;
N.forEach((n,i)=>{const [px,py]=P(n),d=(px-mx)**2+(py-my)**2;if(d<bd){bd=d;b=i}});if(bd<400)pick(b);else{sel=-1;draw()}};
document.getElementById('f').oninput=e=>{const v=e.target.value.toLowerCase();if(!v)return;const i=N.findIndex(n=>n.p.toLowerCase().includes(v));if(i>=0)pick(i)};
addEventListener('resize',fit);fit();
</script></body></html>"""


def main(argv=None):
    from .cli import find_workspace
    ap = argparse.ArgumentParser(prog="modeld graph", description=__doc__.split("\n\n")[0])
    ap.add_argument("workspace", nargs="?"); ap.add_argument("--out"); ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--show", type=int, default=400)
    a = ap.parse_args(argv)
    ws = a.workspace or find_workspace()
    if not ws or not os.path.exists(os.path.join(ws, "workspace.json")):
        sys.exit("no workspace here: run `modeld build .` first, or pass the workspace folder")
    g = context_graph(ws, a.k)
    out = a.out or ws; os.makedirs(out, exist_ok=True)
    json.dump(g, open(os.path.join(out, "context-graph.json"), "w"))
    open(os.path.join(out, "context-graph.html"), "w", encoding="utf-8").write(page(g, a.show))
    print(f"  {os.path.join(out, 'context-graph.json')}\n  {os.path.join(out, 'context-graph.html')}  (opens offline)")


if __name__ == "__main__":
    main()
