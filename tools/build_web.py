#!/usr/bin/env python3
"""Convierte los dossiers (.txt de Homebrewery) en páginas web de solo lectura.

Uso:  python3 tools/build_web.py [carpeta_salida]      (por defecto: web/)
Fuente única: dossiers/<nombre>.txt + img/<nombre>-*.webp. Cada corrida regenera todo.
Salida:  <nombre>-dossier.html  +  img/*.webp   (listas para publicar junto a las hojas).
"""
import re, sys, shutil, datetime, html
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "web"

CHARS = {
    "narxira": dict(name="Narxira", acc="#ff8a2a", glow="255,138,42"),
    "eclipso": dict(name="Eclipso", acc="#b48cff", glow="169,124,255"),
    "nabi":    dict(name="Nabi",    acc="#f0c66e", glow="240,198,110"),
    "dieter":  dict(name="Dieter",  acc="#2fc6ff", glow="47,198,255"),
    "ront":    dict(name="Ront",    acc="#4fd13a", glow="79,209,58"),
}

def esc(s): return html.escape(s, quote=False)

def inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s

LI = re.compile(r"^(\s*)([-*])\s+(.*)$")
HD = re.compile(r"^(#{1,6})\s+(.*)$")

def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def md(lines, chapters=None):
    """Subconjunto de markdown: títulos, listas anidadas, párrafos (con <br> si la línea termina en 2 espacios)."""
    out, para, stack = [], [], []   # stack: sangrías de las listas abiertas
    def flush_p():
        nonlocal para
        if para:
            out.append("<p>" + "".join(para) + "</p>"); para = []
    def close_lists(to=0):
        while len(stack) > to:
            stack.pop(); out.append("</li></ul>")
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            flush_p(); close_lists(); continue
        m = LI.match(line)
        if m:
            flush_p()
            ind = len(m.group(1).replace("\t", "    "))
            while stack and ind < stack[-1]:
                stack.pop(); out.append("</li></ul>")
            if stack and ind == stack[-1]:
                out.append("</li><li>" + inline(m.group(3)))
            else:
                stack.append(ind); out.append("<ul><li>" + inline(m.group(3)))
            continue
        h = HD.match(line)
        if h:
            flush_p(); close_lists()
            n = len(h.group(1)); t = h.group(2).strip()
            idattr = ""
            if n == 2 and chapters is not None:
                i = slug(t); chapters.append((i, t)); idattr = f' id="{i}"'
            out.append(f"<h{n}{idattr}>{inline(t)}</h{n}>"); continue
        if stack:      # texto suelto dentro de una lista = continuación del ítem
            out.append(" " + inline(line.strip())); continue
        br = line.endswith("  ")
        para.append(inline(line.strip()) + ("<br>" if br else " "))
    flush_p(); close_lists()
    return "\n".join(out).replace("<br></p>", "</p>").replace(" </p>", "</p>")

def grid(lines):
    cards, cur = [], []
    for l in lines + [""]:
        if l.strip(): cur.append(l)
        elif cur:
            cards.append(cur); cur = []
    return '<div class="grid">' + "".join(f'<div class="sp">{md(c)}</div>' for c in cards) + "</div>"

IMG = re.compile(r"!\[(.*?)\]\((.*?)\)")

def parse_page(text, first, chapters, imgs):
    lines = text.split("\n")
    body, art, i = [], None, 0
    buf = []
    def flush():
        nonlocal buf
        if buf: body.append(md(buf, chapters)); buf = []
    while i < len(lines):
        l = lines[i]
        s = l.strip()
        if s.startswith("{{position"):
            j = i + 1; blk = []
            while j < len(lines) and lines[j].strip() != "}}": blk.append(lines[j]); j += 1
            m = IMG.search("\n".join(blk))
            if m: art = (m.group(1), Path(m.group(2)).name)
            i = j + 1; continue
        if s.startswith("{{spells-grid") or s.startswith("{{descriptive"):
            kind = "grid" if "spells-grid" in s else "desc"
            j = i + 1; blk = []
            while j < len(lines) and lines[j].strip() != "}}": blk.append(lines[j]); j += 1
            flush()
            body.append(grid(blk) if kind == "grid" else f'<div class="desc">{md(blk)}</div>')
            i = j + 1; continue
        if s.startswith("{{watercolor") or s.startswith("{{pageNumber") or s.startswith("<style") or s in (":::", "::", ":", "<div style=\"text-align: center\">", "</div>"):
            if s.startswith("<style"):
                while "</style>" not in lines[i]: i += 1
            i += 1; continue
        buf.append(l); i += 1
    flush()
    return "\n".join(body), art

def build_page(slugname, meta, ver):
    src = (ROOT / "dossiers" / f"{slugname}.txt").read_text(encoding="utf-8")
    pages = re.split(r"^\\page\s*$", src, flags=re.M)
    chapters, sheets, imgs = [], [], set()
    for n, p in enumerate(pages, 1):
        content, art = parse_page(p, n == 1, chapters, imgs)
        if n == 1:   # portada: nombre, subtítulo y lema centrados
            content = re.sub(r"<h1>", '<h1 class="cover">', content, count=1)
            content = re.sub(r"<h5>", '<h5 class="cover">', content, count=1)
            content = re.sub(r"(</h5>\s*)<p>(.*?)</p>", r'\1<p class="motto">\2</p>', content, count=1, flags=re.S)
        fig = ""
        if art:
            alt, fn = art
            f = ROOT / "img" / fn
            im = Image.open(f); w, h = im.size
            (OUT / "img").mkdir(parents=True, exist_ok=True); shutil.copy(f, OUT / "img" / fn)
            fig = f'<figure class="art"><img src="img/{fn}" width="{w}" height="{h}" alt="{html.escape(alt)}" loading="lazy"></figure>'
        sheets.append(f'<section class="sheet{" hasart" if art else ""}">{content}{fig}<div class="pn">{n}</div></section>')
    chips = "".join(f'<a href="#{i}">{esc(re.sub(r"^CHAPTER\\s*", "Cap. ", t.split(" — ")[0] if t.upper().startswith("CHAPTER") else t))}<small>{esc(t.split(" — ",1)[1].title() if " — " in t else "")}</small></a>' for i, t in chapters)
    nm = meta["name"]
    page = TEMPLATE
    for k, v in {"NAME": nm, "SLUG": slugname, "ACC": meta["acc"], "GLOW": meta["glow"], "CHIPS": chips,
                 "SHEETS": "\n".join(sheets), "VER": ver}.items():
        page = page.replace("{{" + k + "}}", v)
    (OUT / f"{slugname}-dossier.html").write_text(page, encoding="utf-8")
    return len(sheets), len(chapters)

TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{NAME}} · Dossier</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Spectral:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
<style>
:root{--acc:{{ACC}};--bg:#0b0907;--ink:#2b1e12;--paper:#e9dfc2;--red:#58180d;--gold:#c4a455;--muted:#ab9c80;--disp:"IM Fell English",Georgia,serif;--txt:"Spectral",Georgia,"Times New Roman",serif;color-scheme:dark}
*{box-sizing:border-box}html,body{margin:0}html{-webkit-text-size-adjust:100%}
body{background:radial-gradient(ellipse at 50% 0,rgba({{GLOW}},.16),transparent 60%),var(--bg);color:#ece2cc;font:17px/1.5 var(--txt);padding:0 12px 60px;transition:filter 1.2s}
body.shar{filter:brightness(.82) contrast(1.08)}
.top{max-width:816px;margin:0 auto;padding:12px 0 4px;display:flex;justify-content:space-between;gap:8px 16px;flex-wrap:wrap}
.top a{display:inline-flex;align-items:center;gap:8px;min-height:44px;color:var(--muted);text-decoration:none;font:italic 16px var(--txt)}
.top a:hover,.top a.on{color:var(--acc)}
.top svg{width:1em;height:1em;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
.chips{max-width:816px;margin:0 auto 6px;display:flex;flex-wrap:wrap;gap:6px 8px}
.chips a{display:flex;flex-direction:column;padding:6px 12px 7px;border:1px solid #4a3b29;color:#ece2cc;text-decoration:none;font:italic 15px/1.15 var(--txt);background:rgba(20,16,11,.6)}
.chips a small{font:11.5px var(--txt);letter-spacing:.06em;text-transform:uppercase;color:var(--acc);margin-top:2px}
.chips a:hover{border-color:var(--acc)}
.sheet{position:relative;max-width:816px;margin:18px auto;padding:34px 46px 44px;color:var(--ink);overflow:hidden;
 background:var(--paper) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='220' height='220'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='.7' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 .45 0 0 0 0 .33 0 0 0 0 .15 0 0 0 .13 0'/%3E%3C/filter%3E%3Crect width='220' height='220' filter='url(%23n)'/%3E%3C/svg%3E");
 box-shadow:0 0 0 1px rgba(0,0,0,.4),0 18px 44px rgba(0,0,0,.55),inset 0 0 70px rgba(120,86,40,.22)}
.sheet.hasart{padding-bottom:0}
.sheet h1,.sheet h2,.sheet h3,.sheet h4,.sheet h5{margin:0;font-weight:400;color:var(--red)}
.sheet h1.cover{font:400 clamp(38px,9vw,60px)/1 var(--disp);letter-spacing:.02em;text-align:center;padding-bottom:10px;border-bottom:3px solid var(--gold);margin-bottom:8px}
.sheet h5.cover{font:600 14px var(--txt);letter-spacing:.12em;text-transform:uppercase;text-align:center;color:#1d140b;margin:10px 0 2px}
.sheet p.motto{text-align:center;font-style:italic;margin:2px 0 6px}
.sheet h2{font:400 clamp(23px,5.4vw,31px)/1.1 var(--disp);text-transform:uppercase;letter-spacing:.015em;border-bottom:2px solid var(--gold);padding-bottom:3px;margin:22px 0 10px;scroll-margin-top:12px}
.sheet h2:first-child{margin-top:0}
.sheet h3{font:700 19px/1.2 var(--txt);font-variant:small-caps;letter-spacing:.03em;border-bottom:1px solid var(--gold);padding-bottom:2px;margin:18px 0 8px}
.sheet h4{font:700 18px var(--txt);font-variant:small-caps;letter-spacing:.03em;margin:0 0 4px}
.sheet p{margin:0 0 9px}
.sheet ul{margin:2px 0 9px;padding-left:22px}.sheet li{margin:0 0 3px}.sheet li>ul{margin:3px 0 4px}
.sheet strong{font-weight:700;color:#1d140b}
.grid{columns:2;column-gap:34px;margin:6px 0 4px}
.sp{break-inside:avoid;margin:0 0 12px}.sp p{margin:0;font-size:16px;line-height:1.45}
.sp p>strong:first-child{display:inline-block;font:700 16px var(--txt);letter-spacing:.04em;color:var(--red);margin-bottom:0}
.sp p>em:first-of-type{color:#4d3a24}
.desc{background:rgba(250,245,228,.82);border:1px solid #9a7c47;border-left:3px solid var(--red);border-right:3px solid var(--red);padding:10px 16px 6px;margin:12px 0;box-shadow:0 2px 6px rgba(70,45,15,.25)}
.desc ul{margin-bottom:6px}
.art{margin:10px -46px 0;padding:0;pointer-events:none}.art img{display:block;width:100%;height:auto}
.pn{position:absolute;right:22px;bottom:10px;font:italic 13px var(--txt);color:#8a7650;z-index:2}
.foot{max-width:816px;margin:22px auto 0;text-align:center;color:var(--muted);font:italic 14px var(--txt)}
@media (max-width:700px){.sheet{padding:24px 18px 34px;margin:12px auto}.grid{columns:1}.art{margin:8px -18px 0}.sheet h3{font-size:18px}body{font-size:16px}.sp p{font-size:15.5px}}
@media (prefers-reduced-motion:reduce){body{transition:none}}
@media print{body{background:#fff}.top,.chips,.foot{display:none}.sheet{box-shadow:none;break-after:page;margin:0;max-width:none}}
</style>
</head>
<body>
<nav class="top" aria-label="Navegación">
  <a href="{{SLUG}}.html"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>Hoja de combate</a>
  <a href="index.html">Todas las hojas</a>
</nav>
<div class="chips" aria-label="Capítulos">{{CHIPS}}</div>
{{SHEETS}}
<p class="foot">Dossier de {{NAME}} · versión web de solo lectura · actualizado el {{VER}}</p>
<script>
/* Cuando la lectura llega al Pacto con Shar, la luz de la página baja un poco. Al salir, vuelve. */
(function(){var h=[].find.call(document.querySelectorAll("h3"),function(e){return /Pact with Shar/i.test(e.textContent)});
if(!h||!window.IntersectionObserver)return;
new IntersectionObserver(function(e){document.body.classList.toggle("shar",e[0].isIntersecting)},{rootMargin:"-30% 0px -30% 0px"}).observe(h);})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    meses = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
    d = datetime.date.today(); ver = f"{d.day} {meses[d.month-1]} {d.year}"
    for k, m in CHARS.items():
        if (ROOT / "dossiers" / f"{k}.txt").exists():
            s, c = build_page(k, m, ver); print(f"{k}: {s} páginas, {c} capítulos")
