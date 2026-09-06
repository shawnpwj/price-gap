#!/usr/bin/env python3
"""Renders the calibration findings as ../../kya-maps-calculator/calibration.html.

HIDDEN PAGE. It is not in the nav and nothing links to it: the only way in is a
DOUBLE-CLICK on the "Live Data" chip at the top right of the calculator (Shawn,
2026-09-06). It is a working document — the audit trail behind the Price Gap
engine's constants — and never a client-facing view.

Self-contained, no Tailwind: the main page's CDN dependency is a known offline
defect and this page must not inherit it. Tokens copied from index.html so the
navy-and-gold identity holds.

    python3 lease-pairs.py && python3 build-page.py
"""
import json, math, os, html, statistics as st, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, '..', '..', 'kya-maps-calculator', 'calibration.html')
D    = json.load(open(os.path.join(HERE, 'lease-pairs.json')))

SHORT_GAP = 5   # pairs under this many years of lease separation are diagnostic only

def fit(r):  return sum(x['diff'] for x in r) / sum(x['gap'] for x in r) if r else None
def fitp(r):
    if not r: return None
    return math.exp(sum(math.log(x['psf_new'] / x['psf_old']) for x in r) / sum(x['gap'] for x in r)) - 1
def clean(w):  return [r for r in D[w] if r['gap'] >= SHORT_GAP]
def money(v):  return '—' if v is None else f'{v:+,.0f}'
def pct(v):    return '—' if v is None else f'{v:+.2f}%'.replace('+', '+') if False else ('—' if v is None else f'{v*100:+.2f}%')
def npairs(r): return len({(x['older'], x['newer']) for x in r})

AGES  = [(1990, 1999, '1990s'), (2000, 2009, '2000s'), (2010, 2019, '2010s')]
GAPS  = [(1, 4, '1–4 yrs'), (5, 9, '5–9 yrs'), (10, 14, '10–14 yrs'), (15, 99, '15 yrs +')]
BEDS  = ['1BR', '2BR', '3BR', '4BR+']
REGS  = ['CCR', 'RCR', 'OCR']

def row(label, rows, note=''):
    if not rows:
        return f'<tr><th>{label}</th><td colspan="4" class="nil">not measurable</td></tr>'
    return (f'<tr><th>{label}</th><td class="num big">{money(fit(rows))}</td>'
            f'<td class="num">{pct(fitp(rows))}</td>'
            f'<td class="num quiet">{len(rows)}</td><td class="note">{note}</td></tr>')

def block(w):
    rows, all_rows = clean(w), D[w]
    months = sorted({r['ls_old'] for r in all_rows})
    h = [f'<div class="win" id="win{w}"><div class="winhead"><h3>{w}-month window</h3>'
         f'<p class="quiet">{npairs(rows)} pairs · {len(rows)} bedroom cells · '
         f'lease gaps of {SHORT_GAP} years and over</p></div><div class="scroll">']
    h.append('<table class="fig"><thead><tr><th></th><th class="num">$ psf / yr</th>'
             '<th class="num">% / yr</th><th class="num">cells</th><th></th></tr></thead><tbody>')
    h.append(row('<b>All pairs</b>', rows, 'the headline'))
    h.append('<tr class="sep"><th colspan="5">By lease start of the older project</th></tr>')
    for lo, hi, nm in AGES:
        h.append(row(nm, [r for r in rows if lo <= r['ls_old'] <= hi]))
    h.append('<tr class="sep"><th colspan="5">By bedroom</th></tr>')
    for bd in BEDS:
        s = [r for r in rows if r['bed'] == bd]
        h.append(row(bd, s, '' if len(s) >= 20 else 'thin' if s else ''))
    h.append('<tr class="sep"><th colspan="5">By region</th></tr>')
    for rg in REGS:
        s = [r for r in rows if r['region'] == rg]
        h.append(row(rg, s, 'Marina Bay and Sentosa only — not the CCR' if rg == 'CCR' else ''))
    h.append('</tbody></table></div></div>')
    return ''.join(h)

def crosstab(w):
    rows = D[w]
    h = ['<table class="fig cross"><thead><tr><th></th>'
         + ''.join(f'<th class="num">{g[2]}</th>' for g in GAPS)
         + '<th class="num tot">all gaps</th></tr></thead><tbody>']
    for lo, hi, nm in AGES:
        band = [r for r in rows if lo <= r['ls_old'] <= hi]
        cells = ''
        for glo, ghi, _ in GAPS:
            s = [r for r in band if glo <= r['gap'] <= ghi]
            cells += (f'<td class="num">{money(fit(s))}<i>{len(s)}</i></td>' if s
                      else '<td class="num nil">—</td>')
        h.append(f'<tr><th>{nm}</th>{cells}'
                 f'<td class="num tot">{money(fit(band))}<i>{len(band)}</i></td></tr>')
    cells = ''
    for glo, ghi, _ in GAPS:
        s = [r for r in rows if glo <= r['gap'] <= ghi]
        cells += f'<td class="num tot">{money(fit(s))}<i>{len(s)}</i></td>'
    h.append(f'<tr class="tot"><th>all ages</th>{cells}'
             f'<td class="num tot">{money(fit(rows))}<i>{len(rows)}</i></td></tr>')
    h.append('</tbody></table>')
    return ''.join(h)

def pairtable(w):
    rows = sorted(D[w], key=lambda r: (-r['gap'], r['older']))
    h = ['<table class="fig pairs"><thead><tr><th>older</th><th class="num">lease</th>'
         '<th>newer</th><th class="num">lease</th><th class="num">gap</th><th>bed</th>'
         '<th class="num">psf</th><th class="num">psf</th><th class="num">$ / yr</th>'
         '<th class="num">apart</th><th>station</th></tr></thead><tbody>']
    for r in rows:
        cls = ' class="dim"' if r['gap'] < SHORT_GAP else ''
        h.append(
            f'<tr{cls}><td>{html.escape(r["older"].title())}</td><td class="num quiet">{r["ls_old"]}</td>'
            f'<td>{html.escape(r["newer"].title())}</td><td class="num quiet">{r["ls_new"]}</td>'
            f'<td class="num">{r["gap"]}y</td><td class="quiet">{r["bed"]}</td>'
            f'<td class="num quiet">${r["psf_old"]:,.0f}</td><td class="num quiet">${r["psf_new"]:,.0f}</td>'
            f'<td class="num big">{r["per_yr"]:+,.0f}</td>'
            f'<td class="num quiet">{r["metres"]}m</td>'
            f'<td class="quiet">{html.escape((r["station"] or "").replace(" MRT Station","").replace(" LRT Station"," LRT"))}</td></tr>')
    h.append('</tbody></table>')
    return ''.join(h)

c12, c24 = clean('12'), clean('24')
LO, HI = sorted([fit(c12), fit(c24)])
OLD  = fit([r for r in c24 if r['ls_old'] < 2010])
NEW  = fit([r for r in c24 if r['ls_old'] >= 2010])

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--navy-950:#0B111E;--navy-900:#101727;--navy-850:#141C2F;--navy-800:#182238;
--navy-700:#1F2C47;--ink:#243050;--gold:#C9A96A;--gold-soft:#E3CFA4;
--slate-100:#F1F5F9;--slate-300:#CBD5E1;--slate-400:#94A3B8;--slate-500:#8794AA;--slate-600:#7A8CA5;
--go:#10B981;--warn:#F59E0B}
html{color-scheme:dark;-webkit-text-size-adjust:100%}
body{background:var(--navy-950);color:var(--slate-300);
font:400 13px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif}
.disp{font-family:Optima,Candara,"Segoe UI",Helvetica,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px 96px}
header{border-bottom:1px solid rgba(36,48,80,.8);background:var(--navy-900);position:sticky;top:0;z-index:20}
.hin{max-width:1180px;margin:0 auto;padding:18px 24px;display:flex;align-items:center;
justify-content:space-between;gap:20px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:14px}
.mark{width:38px;height:38px;border-radius:9px;border:1px solid rgba(201,169,106,.5);
background:linear-gradient(180deg,var(--navy-700),#0f1524);display:grid;place-items:center;
color:var(--gold);font:600 19px/1 Optima,Candara,sans-serif}
.brand p:first-child{font:600 15px/1.3 Optima,Candara,sans-serif;letter-spacing:.14em;color:var(--slate-100)}
.brand p:last-child{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--slate-500)}
.chip{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--ink);
background:var(--navy-850);border-radius:999px;padding:6px 15px;font-size:11px;
letter-spacing:.18em;text-transform:uppercase;color:var(--slate-500);white-space:nowrap}
.chip b{width:6px;height:6px;border-radius:50%;background:var(--warn);display:block}
h1{font:600 clamp(28px,4vw,36px)/1.15 Optima,Candara,sans-serif;color:var(--slate-100);
letter-spacing:.01em;margin:52px 0 10px}
.kicker{font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:var(--gold);margin-top:52px}
.lede{font-size:15px;color:var(--slate-400);max-width:64ch;margin-bottom:14px}
h2{font:600 20px/1.3 Optima,Candara,sans-serif;color:var(--slate-100);margin:0 0 6px}
h3{font:600 15px/1.3 Optima,Candara,sans-serif;color:var(--gold-soft);letter-spacing:.02em}
section{margin-top:46px}
.sechead{border-top:1px solid var(--ink);padding-top:22px;margin-bottom:18px}
.sechead p{color:var(--slate-500);max-width:70ch;margin-top:5px}
/* verdict */
.verdict{margin-top:30px;border:1px solid rgba(201,169,106,.34);border-radius:14px;
background:linear-gradient(180deg,var(--navy-800),var(--navy-850));
box-shadow:0 10px 40px -12px rgba(0,0,0,.55);padding:26px 28px}
.vgrid{display:flex;gap:34px;flex-wrap:wrap;align-items:flex-end}
.vcell .lab{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--slate-500);margin-bottom:6px}
.vcell .val{font:600 38px/1 Optima,Candara,sans-serif;color:var(--slate-100);white-space:nowrap}
.vcell .val.was{color:var(--slate-600);text-decoration:line-through;text-decoration-thickness:1.5px}
.vcell .val.is{color:var(--gold)}
.vcell .sub{font-size:12px;color:var(--slate-500);margin-top:6px}
.arrow{font-size:26px;color:var(--slate-600);padding-bottom:8px}
.verdict .call{margin-top:22px;padding-top:18px;border-top:1px solid var(--ink);
font-size:15px;color:var(--slate-300);max-width:72ch}
.verdict .call b{color:var(--gold-soft);font-weight:600}
/* tables */
table.fig{width:100%;border-collapse:collapse;font-size:13px;margin-top:4px}
table.fig th,table.fig td{padding:8px 12px;text-align:left;border-bottom:1px solid rgba(36,48,80,.55);
vertical-align:baseline}
table.fig thead th{font-size:11px;letter-spacing:.16em;text-transform:uppercase;
color:var(--slate-600);font-weight:400;border-bottom:1px solid var(--ink);white-space:nowrap}
table.fig tbody th{font-weight:400;color:var(--slate-300);white-space:nowrap}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.big{color:var(--slate-100);font-weight:600}
.quiet{color:var(--slate-600)}
.nil{color:var(--slate-600);font-style:italic}
.note{color:var(--slate-600);font-size:12px;width:34%}
@media (max-width:1180px){.note{display:none}}
tr.sep th{padding-top:20px;font-size:11px;letter-spacing:.16em;text-transform:uppercase;
color:var(--gold);border-bottom:1px solid var(--ink)}
tr.dim td{color:var(--slate-600)}
tr.dim td.big{color:var(--slate-500);font-weight:400}
.cross td i{display:block;font-style:normal;font-size:10.5px;color:var(--slate-600);margin-top:1px}
.cross .tot{color:var(--gold-soft)}
.cross tr.tot th,.cross tr.tot td{border-top:1px solid var(--ink)}
.wins{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:34px}
/* Grid items default to min-width:auto, so a table wider than its track pushes the track out and
   the page scrolls sideways instead of the column stacking. min-width:0 lets auto-fit do its job;
   .scroll then carries any residual overflow inside the panel. */
.win{min-width:0}
/* The cross-tab is the argument of that section, and a cut-off "all gaps" column ruins it. Six
   numeric columns need ~520px, so this pair goes one-up wherever two of them will not fit whole —
   including iPad landscape at 1024. (The figure tables above are narrower and stay two-up there.) */
.wins.pairwide{grid-template-columns:repeat(auto-fit,minmax(520px,1fr))}
.win .scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.winhead{margin-bottom:8px}
.winhead p{font-size:12px;color:var(--slate-600)}
/* method + notes */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.card{border:1px solid var(--ink);border-radius:11px;background:var(--navy-850);padding:16px 18px}
.card h4{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--gold);
font-weight:400;margin-bottom:9px}
.card ul{list-style:none}
.card li{padding:3px 0;color:var(--slate-400);font-size:12.5px}
.card li b{color:var(--slate-100);font-weight:600}
details{border-top:1px solid var(--ink);margin-top:16px}
summary{cursor:pointer;padding:14px 0;font-size:11px;letter-spacing:.18em;text-transform:uppercase;
color:var(--slate-500);list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:'▸ ';color:var(--gold)}
details[open] summary::before{content:'▾ '}
summary:hover{color:var(--gold-soft)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.caveat{border-left:2px solid var(--warn);padding:2px 0 2px 16px;margin:12px 0;color:var(--slate-400);max-width:74ch}
.caveat b{color:var(--warn);font-weight:600}
footer{margin-top:64px;border-top:1px solid var(--ink);padding-top:18px;
font-size:11.5px;color:var(--slate-600);display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}
@media (max-width:640px){.wrap{padding:0 16px 64px}.vcell .val{font-size:30px}.note{display:none}}
"""

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#101727">
<title>Constant Calibration — KYA</title>
<style>{CSS}</style></head><body>

<header><div class="hin">
  <div class="brand">
    <div class="mark">K</div>
    <div><p>KYA REAL ESTATE</p><p>Private Client Advisory</p></div>
  </div>
  <span class="chip"><b></b> Internal — Constant Calibration</span>
</div></header>

<div class="wrap">

<p class="kicker">Price Gap · the lease term</p>
<h1 class="disp">What the market pays for a year of lease</h1>
<p class="lede">The Price Gap engine restates every comparable onto the subject's terms using five
constants. All five were set by judgement. This measures the first of them against the market.</p>

<div class="verdict">
  <div class="vgrid">
    <div class="vcell"><div class="lab">Engine constant</div>
      <div class="val was">$40</div><div class="sub">psf per year · set 2026-07-20</div></div>
    <div class="arrow">→</div>
    <div class="vcell"><div class="lab">Measured</div>
      <div class="val is">${abs(LO):,.0f}–{abs(HI):,.0f}</div>
      <div class="sub">psf per year · {pct(fitp(c24))} · two independent windows</div></div>
    <div class="vcell"><div class="lab">Older stock · pre-2010 lease</div>
      <div class="val">${abs(OLD):,.0f}</div><div class="sub">psf per year</div></div>
    <div class="vcell"><div class="lab">Newer stock · 2010s lease</div>
      <div class="val">${abs(NEW):,.0f}</div><div class="sub">psf per year</div></div>
  </div>
  <p class="call"><b>The call.</b> The $40 constant runs roughly 25–30% hot and should come down.
  But a single number is the wrong shape: what the market pays for a year of lease depends on how
  old the stock is, not on how wide the lease gap is, and not on bedroom count.
  <b>Use ${abs(OLD):,.0f} psf per year against pre-2010 leasehold and ${abs(NEW):,.0f} against 2010s stock.</b>
  Leave the engine untouched until this is audited.</p>
</div>

<section>
  <div class="sechead"><h2 class="disp">The figure, two windows</h2>
  <p>Twelve months is the cleaner price basis; twenty-four is the only one deep enough to read
  1BR and 4BR+ at all. They are shown side by side because agreement between them is the
  validation — nothing here is fitted to one window.</p></div>
  <div class="wins">{block('12')}{block('24')}</div>
  <div class="caveat"><b>The CCR is not measurable this way.</b> Every qualifying pair sits in
  Marina Bay or Sentosa Cove — one reads negative. That is a submarket, not a region. A CCR figure
  has to come from somewhere other than neighbour pairs.</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Is it the gap, or is it the age?</h2>
  <p>A wide lease gap usually means the older project is genuinely old, so the two move together
  and one of them is doing the work. Holding each fixed in turn settles it.</p></div>
  <div class="wins pairwide">
    <div class="win"><div class="winhead"><h3>12-month window</h3>
      <p class="quiet">$ psf per year · cell counts below each figure</p></div>
      <div class="scroll">{crosstab('12')}</div></div>
    <div class="win"><div class="winhead"><h3>24-month window</h3>
      <p class="quiet">$ psf per year · cell counts below each figure</p></div>
      <div class="scroll">{crosstab('24')}</div></div>
  </div>
  <p style="margin-top:20px;max-width:74ch;color:var(--slate-400)">
  Read <b style="color:var(--slate-100)">down a column</b> — gap held fixed, age varying — and the rate
  climbs steadily as the older project gets newer. Read <b style="color:var(--slate-100)">across a row</b>
  — age held fixed, gap varying — and there is no trend beyond four years.
  <b style="color:var(--gold-soft)">So it is age, and the answer should be sliced by lease-start band,
  not by lease gap.</b></p>
  <div class="caveat"><b>The 1–4 year column is excluded from every headline.</b> Two projects three
  years apart divide every difference between them — a better developer, a better site, a better
  facing — by three, so noise arrives multiplied. That column is a diagnostic, not evidence.</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">How a pair is built</h2>
  <p>Two leasehold developments beside each other with everything else held constant, so the lease
  start is the only thing left to explain the price difference.</p></div>
  <div class="cards">
    <div class="card"><h4>Held constant</h4><ul>
      <li>within <b>500 m</b> of each other</li>
      <li>same <b>nearest MRT station</b></li>
      <li>same <b>walk band</b> to it</li>
      <li>identical <b>top-26 primary schools</b> within 1 km</li>
      <li>median sizes within <b>20%</b></li></ul></div>
    <div class="card"><h4>Both sides must be</h4><ul>
      <li>leasehold, with a known lease start</li>
      <li><b>200 units</b> or more</li>
      <li><b>5+ transactions</b> in the window</li>
      <li>EC only once privatised — <b>TOP + 5</b></li></ul></div>
    <div class="card"><h4>How pairs combine</h4><ul>
      <li>total price difference ÷ total lease gap</li>
      <li>each pair weighted by the lease<br>separation it actually contains</li>
      <li>a 20-year pair carries 20 years<br>of evidence; a 3-year pair carries 3</li></ul></div>
    <div class="card"><h4>Uncontrolled</h4><ul>
      <li><b>floor</b> — the PSF series carries none</li>
      <li><b>facing</b> — same</li>
      <li>development quality<br>beyond size and unit count</li>
      <li>these are the noise the<br>500-pair sample has to absorb</li></ul></div>
  </div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Every pair</h2>
  <p>The evidence in full. Rows in grey are the 1–4 year gaps, shown but excluded from the figures.</p></div>
  <details><summary>12-month window — {len(D['12'])} bedroom cells</summary>
    <div class="scroll">{pairtable('12')}</div></details>
  <details><summary>24-month window — {len(D['24'])} bedroom cells</summary>
    <div class="scroll">{pairtable('24')}</div></details>
</section>

<section>
  <div class="sechead"><h2 class="disp">Still to measure</h2>
  <p>Four constants remain on judgement alone.</p></div>
  <table class="fig"><thead><tr><th>Term</th><th class="num">Constant</th><th>Status</th></tr></thead><tbody>
  <tr><th>Lease / vintage</th><td class="num big">$40 psf / yr</td>
    <td style="color:var(--gold-soft)">measured — ${abs(OLD):,.0f} pre-2010, ${abs(NEW):,.0f} for 2010s stock</td></tr>
  <tr><th>Tenure · freehold vs leasehold</th><td class="num big">÷ 1.15</td>
    <td class="nil">not yet measured — same curve as the lease term</td></tr>
  <tr><th>MRT walk band</th><td class="num big">$50 / $200 / $250</td><td class="nil">not yet measured</td></tr>
  <tr><th>GFA harmonisation</th><td class="num big">+7%</td><td class="nil">not yet measured</td></tr>
  <tr><th>Integrated development</th><td class="num big">+5%</td><td class="nil">not yet measured</td></tr>
  <tr><th>Study vs no study</th><td class="num quiet">—</td>
    <td class="nil">not in the engine · 211 clean project cells available</td></tr>
  <tr><th>One bedroom fewer</th><td class="num quiet">—</td>
    <td class="nil">not in the engine · to be read as quantum, not psf</td></tr>
  </tbody></table>
</section>

<footer>
  <span>URA caveats via the MAPS refresh · resale and sub-sale only, new sale excluded ·
  generated {datetime.date.today().isoformat()}</span>
  <span>price-gap/calibration/lease-pairs.py · regenerate with build-page.py</span>
</footer>
</div></body></html>
"""

open(OUT, 'w').write(HTML)
print(f'wrote {os.path.relpath(OUT, HERE)}  ({len(HTML)//1024} KB)')
print(f'  12m: {npairs(c12)} pairs / {len(c12)} cells  fitted {fit(c12):+.1f}/yr')
print(f'  24m: {npairs(c24)} pairs / {len(c24)} cells  fitted {fit(c24):+.1f}/yr')
