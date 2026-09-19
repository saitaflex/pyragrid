"""build_pdf.py — turns PyraGrid_Business_Plan.md into a designed PDF.

    python build_pdf.py

Runs build_plan.py (so the numbers are current), converts the Markdown to HTML, adds the
cover, charts and KPI dashboard, and prints it with headless Microsoft Edge. Headings use
TAN St. Canard and text uses Helvetica Now Display, the same fonts as the website. The
fonts are licensed and are read from frontend/public/fonts (kept out of Git); the PDF only
embeds the subsets it needs.
"""
from __future__ import annotations

import base64
import io
import math
import re
import subprocess
import tempfile
from pathlib import Path

import markdown
from PIL import Image
from pypdf import PdfReader

import build_plan as P
import model as M

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
FONTS = ROOT / "frontend" / "public" / "fonts"
LOGO = ROOT / "frontend" / "public" / "brand" / "PyraGrid - LOGO.png"
OUT = HERE / "PyraGrid_Business_Plan.pdf"
EDGE = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]

INK, FLAME, EMBER, MUTED, LINE, PAPER, NIGHT, SAND = "#0A0A0A", "#C53A19", "#F07A2A", "#5E5A54", "#E4DFD6", "#FAF9F6", "#0F1519", "#F4F1EB"
B, A, Y = P.B, P.A, M.YEARS


# ------------------------------------------------------------------ assets
def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def font_face(family: str, file: str, weight: str) -> str:
    return (f'@font-face {{ font-family: "{family}"; font-weight: {weight}; '
            f'src: url(data:font/woff2;base64,{b64((FONTS / file).read_bytes())}) format("woff2"); }}')


def transparent_logo() -> str:
    """The dragon on a transparent background (the source PNG is on white)."""
    im = Image.open(LOGO).convert("RGB")
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    out = Image.new("RGBA", im.size)
    px, po = im.load(), out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = px[x, y]
            a = min(255, int((255 - min(r, g, b)) * 1.25))
            if a == 0:
                po[x, y] = (0, 0, 0, 0)
                continue
            f = a / 255
            po[x, y] = tuple(max(0, min(255, int((c - 255 * (1 - f)) / f))) for c in (r, g, b)) + (a,)
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + b64(buf.getvalue())


# ------------------------------------------------------------------ charts (inline SVG)
def nice_step(span: float, n: int = 5) -> float:
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    return next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)


def axis(lo: float, hi: float, x0: float, x1: float, sy, fmt) -> str:
    step = nice_step(hi - lo)
    v, out = math.floor(lo / step) * step, []
    while v <= hi + 1e-9:
        y = sy(v)
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="{INK if abs(v) < 1e-9 else LINE}" stroke-width="{1 if abs(v) < 1e-9 else .6}"/>'
                   f'<text x="{x0 - 6}" y="{y + 3:.1f}" text-anchor="end" class="ax">{fmt(v)}</text>')
        v += step
    return "".join(out)


def legend(items, x: float, y: float) -> str:
    out = []
    for label, color, kind in items:
        mark = (f'<rect x="{x}" y="{y - 7}" width="10" height="10" rx="2" fill="{color}"/>' if kind == "bar"
                else f'<line x1="{x - 1}" x2="{x + 11}" y1="{y - 2}" y2="{y - 2}" stroke="{color}" stroke-width="2.4"/><circle cx="{x + 5}" cy="{y - 2}" r="3" fill="{color}"/>')
        out.append(mark + f'<text x="{x + 16}" y="{y + 2}" class="lg">{label}</text>')
        x += 22 + len(label) * 5.6
    return "".join(out)


def svg(w: int, h: int, body: str, caption: str) -> str:
    return (f'<figure class="chart"><svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">{body}</svg>'
            f'<figcaption>{caption}</figcaption></figure>')


def chart_growth() -> str:
    W, H, l, r, t, b = 680, 205, 52, 14, 30, 26
    rev, eb, arr = [v / 1e6 for v in B["revenue"]], [v / 1e6 for v in B["ebitda"]], [v / 1e6 for v in B["arr"]]
    hi, lo = max(arr) * 1.08, min(eb) * 1.6
    sy = lambda v: t + (hi - v) / (hi - lo) * (H - t - b)
    gw = (W - l - r) / M.N
    body = axis(lo, hi, l, W - r, sy, lambda v: f"€{v:g}M")
    pts = []
    for i in range(M.N):
        x = l + gw * i
        for j, (vals, col) in enumerate([(rev, INK), (eb, FLAME)]):
            v, bx = vals[i], x + gw * (0.2 + 0.31 * j)
            y0, y1 = sorted([sy(0), sy(v)])
            body += f'<rect x="{bx:.1f}" y="{y0:.1f}" width="{gw * .28:.1f}" height="{max(y1 - y0, .6):.1f}" fill="{col}" rx="1.5"/>'
        body += f'<text x="{x + gw * .34:.1f}" y="{sy(rev[i]) - 5:.1f}" text-anchor="middle" class="vl">{rev[i]:.1f}</text>' if rev[i] else ""
        body += f'<text x="{x + gw / 2:.1f}" y="{H - 10}" text-anchor="middle" class="ax">FY{Y[i]}</text>'
        pts.append((x + gw / 2, sy(arr[i])))
    body += f'<polyline points="{" ".join(f"{a:.1f},{c:.1f}" for a, c in pts)}" fill="none" stroke="{EMBER}" stroke-width="2.2" stroke-dasharray="5 3"/>'
    body += "".join(f'<circle cx="{a:.1f}" cy="{c:.1f}" r="3.2" fill="{EMBER}"/>' for a, c in pts)
    body += f'<text x="{pts[-1][0] - 6:.1f}" y="{pts[-1][1] - 8:.1f}" text-anchor="end" class="vl" fill="{EMBER}">ARR €{arr[-1]:.1f}M</text>'
    body += legend([("Revenue", INK, "bar"), ("EBITDA", FLAME, "bar"), ("ARR (year end)", EMBER, "line")], l, 12)
    return svg(W, H, body, "Revenue, EBITDA and annual recurring revenue, €M, base case")


def chart_mix() -> str:
    W, H, l, r, t, b = 680, 240, 52, 14, 34, 30
    streams = [("Platform subscriptions", B["rev_platform"], INK), ("Sensor-as-a-Service", B["rev_sensor"], FLAME),
               ("Onboarding and training", B["rev_services"], EMBER)]
    hi = max(B["revenue"]) / 1e6 * 1.12
    sy = lambda v: t + (hi - v) / hi * (H - t - b)
    gw = (W - l - r) / M.N
    body = axis(0, hi, l, W - r, sy, lambda v: f"€{v:g}M")
    for i in range(M.N):
        x, base = l + gw * (i + .22), 0.0
        for _, vals, col in streams:
            v = vals[i] / 1e6
            body += f'<rect x="{x:.1f}" y="{sy(base + v):.1f}" width="{gw * .56:.1f}" height="{sy(base) - sy(base + v):.1f}" fill="{col}"/>'
            base += v
        if base:
            body += f'<text x="{x + gw * .28:.1f}" y="{sy(base) - 5:.1f}" text-anchor="middle" class="vl">{base:.1f}</text>'
        body += f'<text x="{l + gw * (i + .5):.1f}" y="{H - 10}" text-anchor="middle" class="ax">FY{Y[i]}</text>'
    body += legend([(s[0], s[2], "bar") for s in streams], l, 14)
    share = B["rev_platform"][5] / B["revenue"][5]
    return svg(W, H, body, f"Revenue by stream, €M. Recurring platform revenue is {P.pct(share)} of FY2031 revenue.")


def chart_cash() -> str:
    W, H, l, r, t, b = 680, 250, 52, 14, 34, 30
    cash, fcf = [v / 1e6 for v in B["cash"]], [v / 1e6 for v in B["fcf"]]
    hi, lo = max(cash) * 1.12, min(min(fcf) * 1.4, -0.5)
    sy = lambda v: t + (hi - v) / (hi - lo) * (H - t - b)
    gw = (W - l - r) / M.N
    body = axis(lo, hi, l, W - r, sy, lambda v: f"€{v:g}M")
    pts = [(l + gw * (i + .5), sy(cash[i])) for i in range(M.N)]
    area = f"{pts[0][0]:.1f},{sy(0):.1f} " + " ".join(f"{a:.1f},{c:.1f}" for a, c in pts) + f" {pts[-1][0]:.1f},{sy(0):.1f}"
    body += f'<polygon points="{area}" fill="{EMBER}" opacity=".13"/>'
    for i in range(M.N):
        x = l + gw * (i + .36)
        y0, y1 = sorted([sy(0), sy(fcf[i])])
        body += f'<rect x="{x:.1f}" y="{y0:.1f}" width="{gw * .28:.1f}" height="{max(y1 - y0, .6):.1f}" fill="{FLAME if fcf[i] < 0 else INK}" rx="1.5"/>'
        body += f'<text x="{l + gw * (i + .5):.1f}" y="{H - 10}" text-anchor="middle" class="ax">FY{Y[i]}</text>'
    body += f'<polyline points="{" ".join(f"{a:.1f},{c:.1f}" for a, c in pts)}" fill="none" stroke="{EMBER}" stroke-width="2.4"/>'
    for i, (a, c) in enumerate(pts):
        body += f'<circle cx="{a:.1f}" cy="{c:.1f}" r="3.4" fill="{EMBER}"/><text x="{a:.1f}" y="{c - 8:.1f}" text-anchor="middle" class="vl">{cash[i]:.1f}</text>'
    ax, ay = pts[2]
    body += (f'<line x1="{ax:.1f}" x2="{ax - 34:.1f}" y1="{ay - 20:.1f}" y2="{ay - 52:.1f}" stroke="{MUTED}" stroke-width=".8"/>'
             f'<text x="{ax - 38:.1f}" y="{ay - 55:.1f}" text-anchor="end" class="an">Seed round {P.m(A["seed"])}, Q1 2028</text>')
    body += legend([("Cash at year end", EMBER, "line"), ("Free cash flow (burn)", FLAME, "bar"), ("Free cash flow (positive)", INK, "bar")], l, 14)
    return svg(W, H, body, f"Cash and free cash flow, €M. Lowest year-end cash {P.m(P.min_cash, 2)} in FY{P.min_cash_year}.")


def chart_market() -> str:
    W, H = 680, 250
    sam_sites, tam_sites, per_site = 27000, 120000, 2900
    lv = [("TAM", tam_sites * per_site, "Southern Europe, exposed critical sites", "#EDE8DF"),
          ("SAM", sam_sites * per_site, "Energy, telecom and forestry in high-risk Iberia", "#F6C8A8"),
          ("SOM", B["arr"][5], f"PyraGrid ARR FY2031 ({P.n(B['sites'][5])} sites)", FLAME)]
    R, cx, base = 112, 150, 236
    body = ""
    for name, v, desc, col in lv:
        rr = R * math.sqrt(v / lv[0][1])
        body += f'<circle cx="{cx}" cy="{base - rr:.1f}" r="{rr:.1f}" fill="{col}" stroke="{PAPER}" stroke-width="1.5"/>'
    for k, (name, v, desc, col) in enumerate(lv):
        rr = R * math.sqrt(v / lv[0][1])
        ty = base - 2 * rr + 16 if k < 2 else base - rr
        ly = 58 + k * 62
        body += (f'<line x1="{cx:.1f}" x2="330" y1="{ty:.1f}" y2="{ly - 4}" stroke="{MUTED}" stroke-width=".7"/>'
                 f'<circle cx="{cx:.1f}" cy="{ty:.1f}" r="2.2" fill="{INK}"/>'
                 f'<text x="338" y="{ly}" class="big">{name} · €{v / 1e6:,.0f}M</text>' if v >= 20e6 else
                 f'<line x1="{cx:.1f}" x2="330" y1="{ty:.1f}" y2="{ly - 4}" stroke="{MUTED}" stroke-width=".7"/>'
                 f'<circle cx="{cx:.1f}" cy="{ty:.1f}" r="2.2" fill="{INK}"/>'
                 f'<text x="338" y="{ly}" class="big">{name} · €{v / 1e6:,.1f}M</text>')
        body += f'<text x="338" y="{ly + 17}" class="lg">{desc}</text>'
    return svg(W, H, body, "Market size, annual revenue potential (area proportional to value). TAM and SAM are estimates.")


def chart_positioning() -> str:
    W, H, x0, y0, pw, ph = 680, 330, 70, 20, 560, 270
    sx = lambda v: x0 + v * pw
    sy = lambda v: y0 + (1 - v) * ph
    body = (f'<rect x="{x0}" y="{y0}" width="{pw}" height="{ph}" fill="{SAND}" rx="6"/>'
            f'<rect x="{x0 + pw / 2}" y="{y0}" width="{pw / 2}" height="{ph / 2}" fill="#FBE3D3" rx="6"/>'
            f'<line x1="{x0 + pw / 2}" x2="{x0 + pw / 2}" y1="{y0}" y2="{y0 + ph}" stroke="{LINE}" stroke-width="1.2"/>'
            f'<line x1="{x0}" x2="{x0 + pw}" y1="{y0 + ph / 2}" y2="{y0 + ph / 2}" stroke="{LINE}" stroke-width="1.2"/>'
            f'<text x="{x0 + pw / 2}" y="{H - 12}" text-anchor="middle" class="ax">Detects the fire  →  guides the company’s response</text>'
            f'<text transform="translate(22 {y0 + ph / 2}) rotate(-90)" text-anchor="middle" class="ax">One data source  →  many sources fused</text>'
            f'<text x="{x0 + pw - 12}" y="{y0 + 20}" text-anchor="end" class="qd">DECISION LAYER</text>'
            f'<text x="{x0 + 12}" y="{y0 + ph - 12}" class="qd">SINGLE-SOURCE DETECTION</text>')
    players = [("NASA FIRMS / EFFIS", .12, .30), ("OroraTech", .24, .42), ("Pano AI", .30, .24), ("Dryad Networks", .16, .14),
               ("IQ FireWatch", .38, .12), ("Technosylva", .56, .60), ("Overstory", .36, .66), ("Everbridge", .78, .20)]
    for name, x, y in players:
        body += f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="6" fill="{INK}"/><text x="{sx(x) + 10:.1f}" y="{sy(y) + 4:.1f}" class="lg">{name}</text>'
    px, py = sx(.84), sy(.82)
    body += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="15" fill="{FLAME}" opacity=".18"/><circle cx="{px:.1f}" cy="{py:.1f}" r="8" fill="{FLAME}"/>'
             f'<text x="{px - 14:.1f}" y="{py + 4:.1f}" text-anchor="end" class="big" fill="{FLAME}">PyraGrid</text>')
    return svg(W, H, body, "Positioning map, team assessment based on public information")


def kpi_cards() -> str:
    rev, arr = B["revenue"], B["arr"]
    cards = [
        ("ARR FY2031", P.m(arr[5]), f"from {P.m(arr[1], 2)} in FY2027"),
        ("Revenue FY2031", P.m(rev[5]), f"{P.pct(B['rev_platform'][5] / rev[5])} recurring platform revenue"),
        ("Gross margin", P.pct(P.gm[5]), "FY2031, after the +40% electricity rule"),
        ("EBITDA margin", P.pct(P.em[5]), f"FY2031, EBITDA {P.m(P.ebitda[5])}"),
        ("Break-even", P.be_label, f"first profitable year FY{Y[P.be_year]}"),
        ("LTV / CAC", f"{P.ltv / P.cac:.1f}x", f"CAC paid back in {P.cac_payback:.0f} months"),
        ("Sites protected", P.n(B["sites"][5]), f"{P.n(B['customers'][5])} customers in FY2031"),
        ("Net revenue retention", P.pct(P.nrr_at(3)), "FY2029, from site expansion"),
    ]
    return '<div class="cards">' + "".join(
        f'<div class="card"><div class="c-l">{a}</div><div class="c-v">{b}</div><div class="c-s">{c}</div></div>' for a, b, c in cards) + "</div>"


CHARTS = {"growth": chart_growth, "mix": chart_mix, "cash": chart_cash, "market": chart_market, "positioning": chart_positioning}


# ------------------------------------------------------------------ document
def cover(logo: str) -> str:
    stats = [(P.m(B["arr"][5]), "ARR in FY2031"), (P.be_label, "monthly break-even"),
             (P.n(B["sites"][5]), "sites protected by 2031"), (P.m(A["seed"]), "seed round, Q1 2028")]
    return f"""
<section class="cover">
  <div class="cv-top"><span>Business plan · FY2026–FY2031</span><span>Confidential</span></div>
  <div class="cv-mid">
    <img class="cv-logo" src="{logo}" alt="PyraGrid dragon">
    <h1 class="cv-name">Pyra<span style=\"color: var(--flame)\">Grid</span></h1>
    <p class="cv-tag">Wildfire intelligence for companies with sites in fire country</p>
    <div class="cv-rule"></div>
    <p class="cv-sub">Business plan, five-year financial model and valuation</p>
  </div>
  <div class="cv-night">
    <div class="cv-stats">{"".join(f'<div><b>{v}</b><span>{k}</span></div>' for v, k in stats)}</div>
    <div class="cv-meta"><span>PyraGrid, in formation, Spain</span><span>Version 1.0 · September 2026</span><span>rural-valley.vercel.app</span></div>
  </div>
</section>"""


def toc(pages: dict[int, int]) -> str:
    items = []
    for n, title in SECTIONS:
        pg = pages.get(n, "")
        items.append(f'<li><a href="#{SLUG[n]}"><span class="t-n">{n:02d}</span><span class="t-t">{title}</span>'
                     f'<span class="t-d"></span><span class="t-p">{pg}</span></a></li>')
    note = ("All financial figures are forecasts built from the assumptions in section 9.1. They are planning "
            "estimates, not guarantees. Market figures marked <em>estimate</em> are to be validated during the 2027 pilot programme.")
    return f'<section class="toc"><h2 class="toc-h">Contents</h2><ol>{"".join(items)}</ol><p class="toc-note">{note}</p></section>'


md = (HERE / "PyraGrid_Business_Plan.md").read_text(encoding="utf-8")
PB = '<div style="page-break-after: always;"></div>'
parts = md.split(PB)
body_md = PB.join(parts[2:])                       # drop the Markdown cover and contents; rebuilt below
html = markdown.markdown(body_md, extensions=["tables", "toc", "sane_lists"])

SECTIONS, SLUG = [], {}
def h2(mo):
    slug, n, title = mo.group(1), int(mo.group(2)), mo.group(3)
    SECTIONS.append((n, re.sub(r"<.*?>", "", title)))
    SLUG[n] = slug
    return (f'<h2 id="{slug}" class="sec"><span class="mk">@@S{n}@@</span>'
            f'<span class="num">{n:02d}</span><span class="t">{title}</span></h2>')
html = re.sub(r'<h2 id="([^"]+)">(\d+)\. (.*?)</h2>', h2, html)
html = re.sub(r"<!-- chart:(\w+) -->", lambda mo: CHARTS[mo.group(1)](), html)
html = html.replace("<!-- kpi-cards -->", kpi_cards())
html = re.sub(r"<tr>\s*<td><strong>", '<tr class="total"><td><strong>', html)
html = re.sub(r'<td style="text-align: right;">(\(|-\d)', r'<td style="text-align: right;" class="neg">\1', html)
html = html.replace(PB, '<div class="pb"></div>')
html = html.replace('<h2 id="1-executive-summary"', '<div class="exec"><h2 id="1-executive-summary"', 1)
html = html.replace('<div class="pb"></div>', '</div><div class="pb"></div>', 1)

LOGO_URI = transparent_logo()
fonts = "\n".join([font_face("TAN St Canard", "TANStCanard-Regular.woff2", "400"),
                   font_face("Helvetica Now Display", "HelveticaNowDisplay-Light.woff2", "300"),
                   font_face("Helvetica Now Display", "HelveticaNowDisplay-Regular.woff2", "400"),
                   font_face("Helvetica Now Display", "HelveticaNowDisplay-Medium.woff2", "500"),
                   font_face("Helvetica Now Display", "HelveticaNowDisplay-Bold.woff2", "700")])
head_logo = ("data:image/svg+xml;base64," + b64(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="19"><image href="{LOGO_URI}" width="20" height="19"/></svg>'.encode()))

CSS = f"""
{fonts}
:root {{ --ink: {INK}; --flame: {FLAME}; --ember: {EMBER}; --muted: {MUTED}; --line: {LINE}; --paper: {PAPER}; --night: {NIGHT}; --sand: {SAND};
  --display: "TAN St Canard", Georgia, serif; --body: "Helvetica Now Display", "Helvetica Neue", Arial, sans-serif; }}
@page {{ size: A4; margin: 21mm 17mm 19mm 17mm;
  @top-left {{ content: url("{head_logo}") "  PyraGrid"; font-family: var(--display); font-size: 10.5pt; color: {INK}; vertical-align: bottom; padding-bottom: 3mm; }}
  @top-right {{ content: "Business plan  ·  FY2026–FY2031"; font-family: "Helvetica Now Display", Arial; font-size: 7.5pt; color: {MUTED}; vertical-align: bottom; padding-bottom: 3.6mm; }}
  @bottom-left {{ content: "Confidential  ·  September 2026"; font-family: "Helvetica Now Display", Arial; font-size: 7.5pt; color: {MUTED}; vertical-align: top; padding-top: 4mm; }}
  @bottom-right {{ content: counter(page) " / " counter(pages); font-family: "Helvetica Now Display", Arial; font-weight: 700; font-size: 8pt; color: {INK}; vertical-align: top; padding-top: 4mm; }}
}}
@page :first {{ margin: 0; @top-left {{ content: none; }} @top-right {{ content: none; }} @bottom-left {{ content: none; }} @bottom-right {{ content: none; }} }}
* {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html {{ font-family: var(--body); font-size: 9.4pt; line-height: 1.5; color: #22201D; }}
body {{ margin: 0; }}
p {{ margin: 0 0 7pt; orphans: 3; widows: 3; }}
strong {{ font-weight: 700; color: var(--ink); }}
em {{ color: var(--muted); }}
a {{ color: inherit; text-decoration: none; }}
.pb {{ break-after: page; }}
.mk {{ position: absolute; font-size: 1px; color: transparent; }}

/* cover */
.cover {{ position: relative; width: 210mm; height: 297mm; background: var(--paper); break-after: page; overflow: hidden; display: flex; flex-direction: column; }}
.cv-top {{ display: flex; justify-content: space-between; padding: 16mm 18mm 0; font-size: 8pt; letter-spacing: .18em; text-transform: uppercase; color: var(--muted); font-weight: 500; }}
.cv-mid {{ flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 0 20mm; }}
.cv-logo {{ width: 96mm; height: auto; margin-bottom: 4mm; }}
.cv-name {{ font-family: var(--display); font-weight: 400; font-size: 64pt; line-height: 1; margin: 0 0 4mm; color: var(--ink); }}
.cv-tag {{ font-size: 15pt; font-weight: 300; color: var(--ink); margin: 0; max-width: 130mm; line-height: 1.3; }}
.cv-rule {{ width: 36mm; height: 3px; margin: 8mm auto 5mm; background: linear-gradient(90deg, var(--flame), var(--ember)); border-radius: 3px; }}
.cv-sub {{ font-size: 10pt; color: var(--muted); letter-spacing: .04em; margin: 0; }}
.cv-night {{ background: var(--night); color: #EDE9E2; padding: 12mm 18mm 13mm; position: relative; }}
.cv-night::before {{ content: ""; position: absolute; left: 0; right: 0; top: -1px; height: 3px; background: linear-gradient(90deg, var(--flame), var(--ember) 60%, transparent); }}
.cv-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6mm; }}
.cv-stats b {{ display: block; font-size: 19pt; font-weight: 700; color: #fff; letter-spacing: -.01em; }}
.cv-stats span {{ font-size: 8pt; color: #A8A39B; }}
.cv-meta {{ display: flex; justify-content: space-between; margin-top: 9mm; padding-top: 4mm; border-top: 1px solid #2A3237; font-size: 7.8pt; color: #8E8981; }}

/* contents */
.toc-h {{ font-family: var(--display); font-weight: 400; font-size: 34pt; margin: 4mm 0 8mm; }}
.toc ol {{ list-style: none; padding: 0; margin: 0; }}
.toc li a {{ display: flex; align-items: baseline; gap: 4mm; padding: 2.6mm 0; border-bottom: 1px solid var(--line); }}
.t-n {{ font-weight: 700; color: var(--flame); width: 8mm; font-size: 9pt; }}
.t-t {{ font-size: 11.5pt; color: var(--ink); }}
.t-d {{ flex: 1; }}
.t-p {{ font-weight: 700; color: var(--ink); }}
.toc-note {{ margin-top: 10mm; padding: 4mm 5mm; background: var(--sand); border-left: 3px solid var(--ember); font-size: 8.4pt; color: var(--muted); }}

/* headings */
h2.sec {{ position: relative; display: flex; align-items: baseline; gap: 4mm; font-family: var(--display); font-weight: 400; font-size: 27pt; line-height: 1.3; padding-top: 1mm;
  color: var(--ink); margin: 0 0 6mm; padding-bottom: 3mm; overflow: hidden; border-bottom: 1.5px solid var(--ink); break-after: avoid; }}
h2.sec .num {{ font-family: var(--body); font-size: 11pt; font-weight: 700; color: var(--flame); letter-spacing: .05em; }}
h3 {{ font-size: 12pt; font-weight: 700; color: var(--ink); margin: 7mm 0 3mm; break-after: avoid; display: flex; align-items: center; gap: 2.5mm; }}
h3::before {{ content: ""; width: 3px; height: 11pt; background: var(--flame); border-radius: 2px; }}
h2 + h3 {{ margin-top: 0; }}
p > strong:first-child {{ color: var(--ink); }}
ul, ol {{ padding-left: 5mm; margin: 0 0 7pt; }}
li {{ margin-bottom: 2.2pt; }}
li::marker {{ color: var(--flame); font-variant-numeric: normal; font-weight: 700; }}
blockquote {{ margin: 0 0 8pt; padding: 3mm 5mm; background: var(--sand); border-left: 3px solid var(--ember); color: var(--muted); }}
hr {{ border: 0; border-top: 1px solid var(--line); margin: 8mm 0 4mm; }}
code {{ font-size: 8.5pt; background: var(--sand); padding: 0 3px; border-radius: 3px; }}

/* tables */
table {{ width: 100%; border-collapse: collapse; margin: 0 0 8pt; font-size: 8.3pt; line-height: 1.35; }}
thead {{ display: table-header-group; }}
tr {{ break-inside: avoid; }}
th {{ background: var(--night); color: #F2EFE9; font-weight: 500; padding: 2.1mm 2.2mm; font-size: 7.9pt; }}
th strong {{ color: {EMBER}; }}
td {{ padding: 1.7mm 2.2mm; border-bottom: 1px solid var(--line); vertical-align: top; }}
tbody tr:nth-child(even) td {{ background: #FBFAF7; }}
tr.total td {{ background: var(--sand) !important; border-top: 1.2px solid var(--ink); border-bottom: 1.2px solid var(--ink); }}
td.neg {{ color: #A12E13; }}
td:first-child {{ color: var(--ink); }}
table:has(th:nth-child(6)) td, table:has(th:nth-child(6)) th {{ padding-left: 1.6mm; padding-right: 1.6mm; }}

.exec p {{ margin-bottom: 5pt; }} .exec td {{ padding-top: 1.1mm; padding-bottom: 1.1mm; }} .exec figure.chart {{ margin: 2mm 0 4mm; padding: 3mm 3mm 1.5mm; }}
.exec li {{ margin-bottom: 1.4pt; }}
/* charts and cards */
figure.chart {{ margin: 3mm 0 7mm; padding: 4mm 4mm 2mm; border: 1px solid var(--line); border-radius: 6px; break-inside: avoid; background: #fff; }}
figure.chart svg {{ width: 100%; height: auto; display: block; font-family: var(--body); }}
figcaption {{ font-size: 7.8pt; color: var(--muted); margin-top: 2mm; }}
.ax {{ font-size: 10px; fill: {MUTED}; }}
.vl {{ font-size: 10.5px; font-weight: 700; fill: {INK}; }}
.lg {{ font-size: 10.5px; fill: {INK}; }}
.an {{ font-size: 10px; fill: {MUTED}; font-style: italic; }}
.big {{ font-size: 15px; font-weight: 700; fill: {INK}; }}
.qd {{ font-size: 9.5px; font-weight: 700; letter-spacing: .12em; fill: {MUTED}; }}
.cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; margin: 2mm 0 7mm; break-inside: avoid; }}
.card {{ border: 1px solid var(--line); border-radius: 6px; padding: 3.2mm 3.4mm 3mm; background: #fff; border-top: 3px solid var(--flame); }}
.card:nth-child(n+5) {{ border-top-color: var(--ink); }}
.c-l {{ font-size: 7.4pt; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-weight: 500; }}
.c-v {{ font-size: 18pt; font-weight: 700; color: var(--ink); margin: 1.2mm 0 .6mm; letter-spacing: -.01em; }}
.c-s {{ font-size: 7.4pt; color: var(--muted); line-height: 1.3; }}
"""


def render(pages: dict[int, int]) -> Path:
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>PyraGrid Business Plan</title>'
           f"<style>{CSS}</style></head><body>{cover(LOGO_URI)}{toc(pages)}<div class=\"pb\"></div>{html}</body></html>")
    tmp = Path(tempfile.gettempdir()) / "pyragrid_plan.html"
    tmp.write_text(doc, encoding="utf-8")
    edge = next(p for p in EDGE if p.exists())
    subprocess.run([str(edge), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                    f"--print-to-pdf={OUT}", tmp.as_uri()], check=True, capture_output=True, timeout=180)
    tmp.unlink()                                   # the HTML embeds the licensed fonts; do not leave it around
    return OUT


# two passes: the first finds the page of each section, the second prints the contents with page numbers
render({})
found: dict[int, int] = {}
for i, page in enumerate(PdfReader(OUT).pages, start=1):
    for mo in re.finditer(r"@@S(\d+)@@", page.extract_text() or ""):
        found.setdefault(int(mo.group(1)), i)
render(found)
print("written", OUT, f"{OUT.stat().st_size / 1024:.0f} KB,", len(PdfReader(OUT).pages), "pages; sections found:", len(found), "of", len(SECTIONS))
