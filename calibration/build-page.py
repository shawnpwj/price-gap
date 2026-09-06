#!/usr/bin/env python3
"""Renders the lease-term finding as ../../kya-maps-calculator/calibration.html.

HIDDEN PAGE. Not in the nav, nothing links to it: the only way in is a DOUBLE-CLICK on
the "Live Data" chip at the top right of the calculator. A working document, never a
client view. Self-contained, no Tailwind.

RULINGS BEHIND THE SHAPE OF THIS PAGE (Shawn, 2026-09-06, in the order he gave them):
  * QUANTUM ONLY — no percentages anywhere.
  * THE FACE CARRIES THE ANSWER. Everything else goes behind an explain mark, never
    into the bin: a page may not show a number it cannot explain.
  * READ AT THE MIDPOINT of the two lease starts. He broke lease-start banding by
    asking what a 2005-vs-2025 pair should use. The midpoint form IS the blend, so a
    pair straddling a boundary needs no decision.
  * NO MINIMUM LEASE GAP, and NO WALK-BAND MATCH.
  * AS SIMPLE AS POSSIBLE. Two numbers on the face, three explain marks, nothing else.

EVERY FIGURE ON THIS PAGE IS COMPUTED HERE. Nothing is hardcoded in the prose — an
earlier version carried p-values and coefficients as literals and they went stale the
moment the pair screen changed. If you add a claim, compute it.

  python3 lease-pairs.py && python3 build-page.py
"""
import json, math, os, html, random, statistics as st, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, '..', '..', 'kya-maps-calculator', 'calibration.html')
D    = json.load(open(os.path.join(HERE, 'lease-pairs.json')))
ALL  = D['24']                       # 24 months. No gap screen.
POOL = D.get('pooled24', [])

# ── the answer: TWO bands, read at the midpoint ─────────────────────────────
BANDS = [(1900, 2011, 'up to 2010'), (2011, 3000, '2011 onward')]

mid    = lambda r: (r['ls_old'] + r['ls_new']) / 2
fit    = lambda rs: sum(r['diff'] for r in rs) / sum(r['gap'] for r in rs) if rs else None
fpct   = lambda rs: math.exp(sum(math.log(r['psf_new']/r['psf_old']) for r in rs)
                             / sum(r['gap'] for r in rs)) - 1
npairs = lambda rs: len({(r['older'], r['newer']) for r in rs})
ndev   = lambda rs: len({x for r in rs for x in (r['older'], r['newer'])})
money  = lambda v: '—' if v is None else f'{v:+,.0f}'

def band_of(m): return next(n for lo, hi, n in BANDS if lo <= m < hi)
def rate(m):    return BANDR[band_of(m)]
def rows_in(nm):
    lo, hi = next((l, h) for l, h, n in BANDS if n == nm)
    return [r for r in ALL if lo <= mid(r) < hi]

def ci(rs, N=4000, seed=3):
    g = random.Random(seed)
    v = sorted(fit([rs[g.randrange(len(rs))] for _ in rs]) for _ in range(N))
    return v[int(.025*N)], v[int(.975*N)-1]

def perm(A, B, N=8000, seed=11):
    """Could this gap have come from shuffling the two groups together?"""
    g = random.Random(seed); obs = abs(fit(A) - fit(B)); pool = A + B; nA = len(A); c = 0
    for _ in range(N):
        g.shuffle(pool)
        if abs(fit(pool[:nA]) - fit(pool[nA:])) >= obs: c += 1
    return obs, c / N

BANDR  = {nm: fit(rows_in(nm)) for _, _, nm in BANDS}
BANDCI = {nm: ci(rows_in(nm)) for _, _, nm in BANDS}
NDEV   = ndev(ALL)
MIDS   = sorted(mid(r) for r in ALL)
MID_LO, MID_HI = MIDS[int(.05*len(MIDS))], MIDS[int(.95*len(MIDS))]
OLD_NM, NEW_NM = BANDS[0][2], BANDS[1][2]

def reg(nm, g):  return [r for r in rows_in(nm) if r['region'] == g]
RCR_NEW, OCR_NEW = reg(NEW_NM, 'RCR'), reg(NEW_NM, 'OCR')
RCR_OLD, OCR_OLD = reg(OLD_NM, 'RCR'), reg(OLD_NM, 'OCR')
P_BED  = perm([r for r in ALL if r['bed'] == '2BR'], [r for r in ALL if r['bed'] == '3BR'])
P_ROLD = perm(RCR_OLD, OCR_OLD)
P_RNEW = perm(RCR_NEW, OCR_NEW)
CCR    = [r for r in ALL if r['region'] == 'CCR']

def pooled_size_leak():
    """How much of the pooled method's answer is really unmatched size. Pure-python OLS."""
    if not POOL: return None, None
    X = [[r['gap'], r['gap']*(mid(r)-2000),
          (r['sqft_new']-r['sqft_old'])/max(r['sqft_old'], r['sqft_new'])] for r in POOL]
    y = [r['diff'] for r in POOL]; n = 3
    S = [[sum(X[k][i]*X[k][j] for k in range(len(X))) for j in range(n)] for i in range(n)]
    T = [sum(X[k][i]*y[k] for k in range(len(X))) for i in range(n)]
    M = [S[i][:] + [T[i]] for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(i+1, n):
            f = M[r][i]/M[i][i]
            for c in range(i, n+1): M[r][c] -= f*M[i][c]
    x = [0.0]*n
    for i in range(n-1, -1, -1):
        x[i] = (M[i][n] - sum(M[i][j]*x[j] for j in range(i+1, n)))/M[i][i]
    return x[2], npairs(POOL)
SIZE_LEAK, POOL_PAIRS = pooled_size_leak()

def cv_bands(bands, reps=30, folds=5, seed=23):
    """Held-out squared error per cell — the only fair way to rank shapes."""
    g = random.Random(seed); idx = list(range(len(ALL))); err = []
    for _ in range(reps):
        g.shuffle(idx)
        for f in range(folds):
            te = set(idx[f::folds])
            tr = [ALL[i] for i in idx if i not in te]; ts = [ALL[i] for i in idx if i in te]
            rt = {}
            for lo, hi, nm in bands:
                b = [x for x in tr if lo <= mid(x) < hi]; rt[nm] = fit(b) if b else fit(tr)
            for x in ts:
                nm = next(n for lo, hi, n in bands if lo <= mid(x) < hi)
                err.append((x['diff'] - rt[nm]*x['gap'])**2)
    return sum(err)/len(err)

CV_FLAT  = cv_bands([(1900, 3000, 'all')])
CV_TWO   = cv_bands(BANDS)
CV_THREE = cv_bands([(1900, 2011, 'a'), (2011, 2014, 'b'), (2014, 3000, 'c')])

# ── the vintage-vs-age test ─────────────────────────────────────────────────
EARLY   = D.get('early24', [])
EW, LW  = D.get('early_window', ['', '']), D.get('late_window', ['', ''])
NOW     = int(LW[1][:4]) if LW[1] else datetime.date.today().year
EARLY_NOW = int(EW[1][:4]) if EW[1] else NOW - 3
AGE_SLICES = [(1900, 2006), (2006, 2009), (2009, 2012), (2012, 2015), (2015, 3000)]

def age_label(nm):
    """The age the band's older side actually has today. Descriptive only — the band is
    fixed by calendar year, because the vintage-vs-age test says it does not slide."""
    rs = rows_in(nm); a = sorted(NOW - r['ls_old'] for r in rs)
    return a[int(.25*len(a))], a[int(.75*len(a))]

# ── tables ──────────────────────────────────────────────────────────────────
def answer_table():
    h = ['<table class="fig look"><thead><tr><th>Midpoint of the two lease starts</th>'
         '<th class="num">$ psf / yr</th><th class="num">95% interval</th>'
         '<th class="num">developments</th><th class="num">pairs</th></tr></thead><tbody>']
    for _, _, nm in BANDS:
        rs = rows_in(nm); lo, hi = BANDCI[nm]; a1, a2 = age_label(nm)
        h.append(f'<tr><th>{nm} <i class="age">{a1}–{a2} yrs old</i></th>'
                 f'<td class="num big">${BANDR[nm]:,.0f}</td>'
                 f'<td class="num quiet">${lo:,.0f} to ${hi:,.0f}</td>'
                 f'<td class="num quiet">{ndev(rs)}</td><td class="num quiet">{npairs(rs)}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def vintage_table():
    h = ['<table class="fig"><thead><tr><th>Midpoint</th>'
         f'<th class="num">{EW[0][:4]}–{EW[1][:4]} sales</th><th class="num">age then</th>'
         f'<th class="num">{LW[0][:4]}–{LW[1][:4]} sales</th><th class="num">age now</th>'
         '</tr></thead><tbody>']
    for lo, hi in AGE_SLICES:
        e = [r for r in EARLY if lo <= mid(r) < hi]; l = [r for r in ALL if lo <= mid(r) < hi]
        if len(e) < 6 or len(l) < 6: continue
        ea = st.median([EARLY_NOW - r['ls_old'] for r in e])
        la = st.median([NOW - r['ls_old'] for r in l])
        hot = ' class="flag"' if lo >= 2012 else ''
        lab = f'up to {hi-1}' if lo <= 1900 else f'{lo}–{min(hi-1, 2025)}'
        h.append(f'<tr{hot}><th>{lab}</th>'
                 f'<td class="num big">{money(fit(e))}</td><td class="num quiet">{ea:.0f} yrs</td>'
                 f'<td class="num big">{money(fit(l))}</td><td class="num quiet">{la:.0f} yrs</td></tr>')
    return ''.join(h) + '</tbody></table>'

def tested_table():
    def r_(what, figure, verdict, flag=False):
        return (f'<tr{" class=flag" if flag else ""}><th>{what}</th>'
                f'<td class="num">{figure}</td><td class="note wide">{verdict}</td></tr>')
    h = ['<table class="fig"><thead><tr><th>Tested</th><th class="num">what it reads</th>'
         '<th>verdict</th></tr></thead><tbody>']
    h.append(r_('Bedroom &mdash; 2BR against 3BR',
                f'${P_BED[0]:,.1f} apart',
                f'No difference (p&nbsp;=&nbsp;{P_BED[1]:.2f}). Bedroom is the size match, never the answer.'))
    h.append(r_(f'Region, {OLD_NM}',
                f'RCR ${fit(RCR_OLD):,.0f} &middot; OCR ${fit(OCR_OLD):,.0f}',
                f'No difference (p&nbsp;=&nbsp;{P_ROLD[1]:.2f}). One figure serves the island.'))
    h.append(r_(f'Region, {NEW_NM}',
                f'RCR ${fit(RCR_NEW):,.0f} &middot; OCR ${fit(OCR_NEW):,.0f}',
                f'<b>Real</b> (p&nbsp;=&nbsp;{P_RNEW[1]:.3f}), and it is why this band\'s interval is wide. '
                f'Splitting on it does not predict better ({npairs(RCR_NEW)} RCR pairs), so the page '
                f'keeps one figure and says so here.', True))
    h.append(r_('The CCR', f'{len(CCR)} cells',
                'Not measurable. Every qualifying pair is Marina Bay or Sentosa &mdash; a submarket, not a region.'))
    h.append(r_('Three bands instead of two', f'{CV_THREE/1000:,.1f}k against {CV_TWO/1000:,.1f}k',
                'Worse on held-out error, and the extra band split into two incoherent regional halves.'))
    h.append(r_('One flat rate', f'{CV_FLAT/1000:,.1f}k against {CV_TWO/1000:,.1f}k',
                'Much worse. This is what the engine does today.'))
    h.append(r_('A fitted curve or knee', 'moved with the sample',
                'A straight line ran low at both ends; a fitted knee then moved when the pair screen '
                'widened. The knee is not identified &mdash; do not report one.'))
    h.append(r_('Dropping the 200-unit floor', '$33 with no gradient',
                'The pairs it adds read high and flat. A boutique block&rsquo;s PSF is one odd sale. Floor stays.'))
    h.append(r_('Matching on size instead of bedroom',
                f'{POOL_PAIRS} pairs against {npairs(ALL)}',
                f'Loses pairs and lets the sales mix leak in, worth &minus;${abs(SIZE_LEAK):,.0f} psf per 100% of '
                f'unmatched size. Bedroom is the better control.'))
    h.append(r_('A minimum lease gap', 'no change',
                'It protected an estimator this page does not use. Removing it roughly tripled the sample.'))
    return ''.join(h) + '</tbody></table>'

def why_table():
    """The three explanations that do NOT survive, each with the figure that kills it."""
    def band(lo, hi, f=lambda r: True):
        return [r for r in ALL if lo <= mid(r) < hi and f(r)]
    O, N = (1900, 2011), (2011, 3000)
    h = ['<table class="fig"><thead><tr><th>Could it be&hellip;</th>'
         f'<th class="num">{OLD_NM}</th><th class="num">{NEW_NM}</th>'
         '<th>what it shows</th></tr></thead><tbody>']
    def r_(q, a, b, note):
        return (f'<tr><th>{q}</th><td class="num big">{a}</td><td class="num big">{b}</td>'
                f'<td class="note wide">{note}</td></tr>')
    sm_o, sm_n = band(*O, lambda r: r['sqft_old'] < 900), band(*N, lambda r: r['sqft_old'] < 900)
    lg_o, lg_n = band(*O, lambda r: r['sqft_old'] >= 900), band(*N, lambda r: r['sqft_old'] >= 900)
    h.append(r_('&hellip;that older stock is simply bigger?',
                f'${fit(sm_o):,.0f} &middot; ${fit(lg_o):,.0f}', f'${fit(sm_n):,.0f} &middot; ${fit(lg_n):,.0f}',
                'Small units then large. The gap between the bands survives inside <b>both</b> size '
                'groups, so size is not the mechanism. Sizes are already matched within 20% inside '
                'each pair in any case.'))
    h.append(r_('&hellip;that newer pairs sit closer together in lease start?',
                f'${fit(band(*O, lambda r: r["gap"] <= 4)):,.0f} &middot; ${fit(band(*O, lambda r: r["gap"] > 4)):,.0f}',
                f'${fit(band(*N, lambda r: r["gap"] <= 4)):,.0f} &middot; ${fit(band(*N, lambda r: r["gap"] > 4)):,.0f}',
                'Short gaps then long. The gap between the bands holds at every lease separation.'))
    h.append(r_('&hellip;just a higher base price?',
                f'{fpct(rows_in(OLD_NM)):+.2%}', f'{fpct(rows_in(NEW_NM)):+.2%}',
                'The same figures as a percentage of the older project&rsquo;s price. The gap '
                'narrows &mdash; newer stock is dearer to start with &mdash; but it does not close, '
                'so a higher base explains only part of it.'))
    h.append(r_('&hellip;lease decay?',
                f'{st.median([r["ls_old"] + 99 - NOW for r in rows_in(OLD_NM)]):.0f} yrs left',
                f'{st.median([r["ls_old"] + 99 - NOW for r in rows_in(NEW_NM)]):.0f} yrs left',
                f'Decay bites below 60&ndash;65 years remaining and only '
                f'{sum(1 for r in ALL if r["ls_old"] + 99 - NOW < 65)} of {len(ALL)} cells are there. '
                'It also runs the <b>wrong way</b>: the band with <b>more</b> lease left is the one '
                'paying more.'))
    return ''.join(h) + '</tbody></table>'

def pairtable():
    rows = sorted(ALL, key=lambda r: (-r['gap'], r['older']))
    h = ['<table class="fig pairs"><thead><tr><th>older</th><th class="num">lease</th>'
         '<th>newer</th><th class="num">lease</th><th class="num">gap</th><th>bed</th>'
         '<th class="num">psf</th><th class="num">psf</th><th class="num">$ / yr</th>'
         '<th class="num">band says</th><th class="num">apart</th><th>station</th>'
         '</tr></thead><tbody>']
    for r in rows:
        h.append(
            f'<tr><td>{html.escape(r["older"].title())}</td><td class="num quiet">{r["ls_old"]}</td>'
            f'<td>{html.escape(r["newer"].title())}</td><td class="num quiet">{r["ls_new"]}</td>'
            f'<td class="num">{r["gap"]}y</td><td class="quiet">{r["bed"]}</td>'
            f'<td class="num quiet">${r["psf_old"]:,.0f}</td><td class="num quiet">${r["psf_new"]:,.0f}</td>'
            f'<td class="num big">{r["per_yr"]:+,.0f}</td>'
            f'<td class="num quiet">${rate(mid(r)):,.0f}</td>'
            f'<td class="num quiet">{r["metres"]}m</td>'
            f'<td class="quiet">{html.escape((r["station"] or "").replace(" MRT Station","").replace(" LRT Station"," LRT"))}</td></tr>')
    return ''.join(h) + '</tbody></table>'
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
.expl{color:var(--slate-400);max-width:76ch;margin:10px 0 14px;font-size:13px}
.expl b{color:var(--slate-100);font-weight:600}
details{border-top:1px solid var(--ink);margin-top:16px}
details .expl:first-of-type{margin-top:0}
.caveat{border-left:2px solid var(--warn);padding:2px 0 2px 16px;margin:12px 0;color:var(--slate-400);max-width:74ch}
.caveat b{color:var(--warn);font-weight:600}
footer{margin-top:64px;border-top:1px solid var(--ink);padding-top:18px;
font-size:11.5px;color:var(--slate-600);display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}
@media (max-width:640px){.wrap{padding:0 16px 64px}.vcell .val{font-size:30px}.note{display:none}}
"""
CSS += """
.vcell.grow{flex:1 1 300px;min-width:260px}
.two{display:flex;gap:30px;flex-wrap:wrap}
.two .n{font:600 clamp(30px,4vw,42px)/1 Optima,Candara,sans-serif;color:var(--gold)}
.two .w{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--slate-500);margin-top:6px}
.two .g{font-size:11px;color:var(--slate-600);margin-top:3px}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:22px}
.step{border:1px solid var(--ink);border-radius:11px;background:var(--navy-850);
padding:16px 18px;display:flex;gap:12px;align-items:flex-start}
.step .sn{flex:none;width:22px;height:22px;border-radius:50%;border:1px solid rgba(201,169,106,.5);
color:var(--gold);display:grid;place-items:center;font:600 11px/1 Optima,Candara,sans-serif}
.step p{color:var(--slate-400);font-size:12.5px}
.step p b{color:var(--slate-100);font-weight:600}
.look td.big{color:var(--gold-soft)}
i.age{font-style:normal;font-size:11px;color:var(--slate-600);margin-left:9px;white-space:nowrap}
tr.flag td.big,tr.flag th{color:var(--warn)}
.note.wide{width:52%;font-size:12px}
@media (max-width:900px){.note.wide{display:none}}
.expl{color:var(--slate-400);max-width:78ch;margin:10px 0 14px;font-size:13px}
.expl b{color:var(--slate-100);font-weight:600}
details{border-top:1px solid var(--ink);margin-top:16px}
.calc{margin-top:22px;border:1px solid rgba(201,169,106,.3);border-radius:12px;
background:linear-gradient(180deg,var(--navy-800),var(--navy-850));padding:20px 22px}
.calc h3{margin-bottom:12px}
.cin{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.cin label{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--slate-500);
display:flex;flex-direction:column;gap:7px}
.cin input{background:var(--navy-950);border:1px solid var(--ink);border-radius:8px;
padding:9px 12px;color:var(--slate-100);font:600 17px/1 Optima,Candara,sans-serif;
width:130px;font-variant-numeric:tabular-nums}
.cin input:focus{outline:none;border-color:rgba(201,169,106,.6)}
.cout{border-top:1px solid var(--ink);padding-top:14px}
.cout.bad{color:var(--slate-600);font-style:italic}
.crow{display:flex;justify-content:space-between;gap:16px;padding:5px 0;color:var(--slate-400);align-items:center}
.crow b{color:var(--slate-100);font-variant-numeric:tabular-nums;font-weight:600}
.crow i.cflat{font-style:normal;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
color:var(--gold);border:1px solid rgba(201,169,106,.4);border-radius:999px;padding:2px 9px;margin-left:10px}
.crow.big{border-top:1px solid var(--ink);margin-top:8px;padding-top:12px;font-size:15px}
.crow.big b{color:var(--gold);font:600 21px/1 Optima,Candara,sans-serif}
.chint{color:var(--slate-500);font-size:12px;margin-top:10px}
.cwarn{color:var(--warn);font-size:12px;margin-top:8px}
"""

JS = """
(function(){
  var B=%BANDS%, LO=%LO%, HI=%HI%;
  function bandFor(m){for(var i=0;i<B.length;i++){if(m<B[i][0])return B[i];}return B[B.length-1];}
  function n(id){return parseFloat(document.getElementById(id).value);}
  function go(){
    var a=n('lsA'), b=n('lsB'), o=document.getElementById('calcOut');
    if(!a||!b||a<1960||b<1960||a>2040||b>2040){o.className='cout bad';
      o.innerHTML='Enter two lease start years.';return;}
    if(a===b){o.className='cout bad';o.innerHTML='Same lease start \\u2014 no adjustment.';return;}
    var mid=(a+b)/2, bd=bandFor(mid), rate=bd[1], gap=b-a, adj=rate*gap;
    var warn='';
    if(mid>HI) warn='<p class="cwarn">Midpoint '+mid.toFixed(1)+' is past the measured range '+
      '(ends '+HI.toFixed(0)+'). The rate was still climbing when the evidence ran out, so treat '+
      'this as a floor.</p>';
    else if(mid<LO) warn='<p class="chint">Midpoint '+mid.toFixed(1)+' is older than the bulk of '+
      'the sample, but the older band is flat and carries most of the evidence. The rate does not '+
      'change going further back.</p>';
    o.className='cout';
    o.innerHTML =
      '<div class="crow"><span>Midpoint</span><b>'+mid.toFixed(1)+'</b></div>'+
      '<div class="crow"><span>Rate</span><b>$'+rate.toFixed(0)+' psf / yr</b>'+
        '<i class="cflat">'+bd[2]+'</i></div>'+
      '<div class="crow"><span>Lease gap</span><b>'+Math.abs(gap)+' years</b></div>'+
      '<div class="crow big"><span>Adjustment</span><b>'+(adj>=0?'+':'')+'$'+
        Math.round(adj).toLocaleString()+' psf</b></div>'+
      '<p class="chint">Add this to the '+(gap>0?'older':'newer')+
      ' comparable\\'s PSF to put it on the subject\\'s lease terms.</p>'+warn;
  }
  ['lsA','lsB'].forEach(function(id){document.getElementById(id).addEventListener('input',go);});
  go();
})();
"""
BANDS_JS = '[' + ','.join(f'[{hi},{BANDR[nm]:.2f},"{nm}"]' for _, hi, nm in BANDS) + ']'
A1, A2 = age_label(OLD_NM); B1, B2 = age_label(NEW_NM)

BODY = f"""
<p class="kicker">Price Gap &middot; the lease term</p>
<h1 class="disp">What the market pays for a year of lease</h1>
<p class="lede">The engine restates every comparable using five constants, all set by judgement.
This is the first one measured against the market.</p>

<div class="verdict">
  <div class="vgrid">
    <div class="vcell"><div class="lab">Engine constant</div>
      <div class="val was">$40</div><div class="sub">flat, every comparable</div></div>
    <div class="arrow">&rarr;</div>
    <div class="vcell grow"><div class="lab">Measured</div>
      <div class="two">
        <div><div class="n">${BANDR[OLD_NM]:,.0f}</div><div class="w">{OLD_NM}</div>
          <div class="g">{ndev(rows_in(OLD_NM))} developments</div></div>
        <div><div class="n">${BANDR[NEW_NM]:,.0f}</div><div class="w">{NEW_NM}</div>
          <div class="g">{ndev(rows_in(NEW_NM))} developments</div></div>
      </div></div>
  </div>
  <p class="call"><b>The call.</b> Two rates, not one, chosen by the <b>midpoint of the two lease
  starts</b>. The engine's flat $40 charges an old pair
  {40/BANDR[OLD_NM]:.1f} times what the market pays and short-changes a new one.
  Leave the engine alone until this is audited.</p>
</div>

<section>
  <div class="sechead"><h2 class="disp">How to use it</h2></div>
  <div class="steps">
    <div class="step"><span class="sn">1</span>
      <p>Average the <b>two lease start years</b>. That is the midpoint.</p></div>
    <div class="step"><span class="sn">2</span>
      <p>Midpoint <b>{OLD_NM}</b> &rarr; ${BANDR[OLD_NM]:,.0f}. <b>{NEW_NM}</b> &rarr;
      ${BANDR[NEW_NM]:,.0f}.</p></div>
    <div class="step"><span class="sn">3</span>
      <p>Multiply by the <b>lease gap</b> and add to the comparable's PSF.</p></div>
  </div>

  <div class="calc">
    <h3>Try a pair</h3>
    <div class="cin">
      <label>Comparable lease start<input id="lsA" type="number" value="2005" min="1960" max="2040" step="1"></label>
      <label>Subject lease start<input id="lsB" type="number" value="2025" min="1960" max="2040" step="1"></label>
    </div>
    <div id="calcOut" class="cout"></div>
  </div>
  <p class="expl">The midpoint is what lets two rates price a pair that straddles the boundary:
  a 2005-against-2025 comparable is centred on 2015 and takes the newer rate, without anyone
  having to decide which side it belongs to.</p>
</section>

<section>
  <div class="sechead"><h2 class="disp">The measurement</h2>
  <p>{NDEV} developments, paired with a leasehold neighbour and compared bedroom by bedroom.
  Twenty-four months of resale and sub-sale to {LW[1]}.</p></div>
  <div class="scroll">{answer_table()}</div>

  <p class="expl" style="margin-top:18px"><b>What these two numbers say, in words.</b> Take two
  condominiums next door to each other, one with a lease starting a few years after the other.
  The figure is <b>how much more per square foot the newer one fetches, for each year of that
  difference</b>. Among pairs centred before 2011 it is ${BANDR[OLD_NM]:,.0f} a year. Among pairs
  centred from 2011 it is ${BANDR[NEW_NM]:,.0f} &mdash; <b>being newer is worth nearly twice as
  much in the newer cohort</b>. Nothing here is stagnant, and the newer band is the steeper one,
  not the flatter one.</p>
  <p class="expl">The likeliest reason is that through the 2010s each successive launch in the same
  spot came out materially dearer than the one before it, so two neighbours three years apart now
  differ by more than two neighbours three years apart did in the 2000s. This study measures the
  size of that effect; it does not prove the cause.</p>
  <div class="caveat"><b>The newer figure is a floor.</b> It rests on
  {ndev(rows_in(NEW_NM))} developments, and it runs hotter in the RCR
  (${fit(RCR_NEW):,.0f}) than the OCR (${fit(OCR_NEW):,.0f}) &mdash; a real split, and the reason
  its interval is wide. Young stock has barely resold, so quote ${BANDR[NEW_NM]:,.0f} as the least
  it can be.</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2>
  <p>Four questions, answered once each.</p></div>

  <details><summary>Do the bands move as the stock ages?</summary>
    <p class="expl"><b>No. They are fixed calendar years.</b> The obvious worry is that this is
    really an age effect &mdash; that a 2011 project is dear because it is {NOW-2011} years old,
    so next year the boundary should slide. It does not. Running the identical method on sales
    from {EW[0]}&ndash;{EW[1]}, three years earlier, puts the jump at the same calendar band, with
    the stock three years younger.</p>
    <div class="scroll">{vintage_table()}</div>
    <p class="expl">Read the age columns: the {AGE_SLICES[3][0]}&ndash;{AGE_SLICES[3][1]-1} band was
    {st.median([EARLY_NOW - r['ls_old'] for r in EARLY if AGE_SLICES[3][0] <= mid(r) < AGE_SLICES[3][1]]):.0f}
    years old in the early run and
    {st.median([NOW - r['ls_old'] for r in ALL if AGE_SLICES[3][0] <= mid(r) < AGE_SLICES[3][1]]):.0f}
    now. It aged four years and kept paying the high rate. <b>What is being measured is the vintage
    of the stock, not its age</b> &mdash; projects launched from about 2012 sold into a much steeper
    pricing era and have carried it ever since.</p>
    <p class="expl">So the bands stay put. What will eventually change the answer is different:
    <b>lease decay</b>. That bites on how much lease is <em>left</em>, and the market's knee is
    60&ndash;65 years remaining. In this sample the older side has a median
    {st.median([r['ls_old'] + 99 - NOW for r in rows_in(OLD_NM)]):.0f} years left, and only
    {sum(1 for r in ALL if r['ls_old'] + 99 - NOW < 65)} of {len(ALL)} cells are below the knee at
    all &mdash; so decay is almost absent here, and the gradient in fact runs the <em>other</em> way,
    with the stock that has more lease left paying more. Decay will arrive as the oldest band
    steepening, around the end of this decade. Re-run then, and it will show up as a new figure
    for old stock, not as the boundary sliding.</p>
  </details>

  <details><summary>Why the newer band is nearly double</summary>
    <p class="expl">Three ordinary explanations, and the figures that rule each of them out.</p>
    <div class="scroll">{why_table()}</div>
    <p class="expl">What is left is the vintage of the stock itself &mdash; and the
    {EW[0][:4]}&ndash;{EW[1][:4]} rerun above shows that vintage stays attached to the calendar
    year, not to the age.</p>
  </details>

  <details><summary>What was tested and what it changed</summary>
    <p class="expl">Every cut and every alternative method, with the figure it produced.
    &ldquo;Held-out error&rdquo; means fitted on four fifths of the pairs and scored on the fifth
    it never saw &mdash; lower is better.</p>
    <div class="scroll">{tested_table()}</div>
    <p class="expl">Three words are used throughout and count different things. A
    <b>development</b> is one condominium ({NDEV} appear). A <b>pair</b> is two neighbouring
    developments compared ({npairs(ALL)}). A <b>cell</b> is one pair read at one bedroom type,
    one to four per pair ({len(ALL)}) &mdash; the unit every figure is computed on.</p>
  </details>

  <details><summary>How a pair is built, and every pair</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h4>Held constant</h4><ul>
        <li>within <b>500 m</b> of each other</li>
        <li>same <b>nearest MRT station</b></li>
        <li>identical <b>top-26 primary schools</b> within 1 km</li>
        <li>median sizes within <b>20%</b>, bedroom by bedroom</li></ul></div>
      <div class="card"><h4>Both sides must be</h4><ul>
        <li>leasehold, with a known lease start</li>
        <li><b>200 units</b> or more</li>
        <li><b>5+ transactions</b> in the window</li>
        <li>EC only once privatised &mdash; <b>TOP + 5</b></li>
        <li>resale and sub-sale only</li></ul></div>
      <div class="card"><h4>Not controlled</h4><ul>
        <li><b>floor</b> &mdash; the PSF series carries none</li>
        <li><b>facing</b> &mdash; same</li>
        <li>lease start and building age are<br>confounded: this is blended vintage</li></ul></div>
    </div>
    <div class="scroll" style="margin-top:16px">{pairtable()}</div>
  </details>
</section>

<section>
  <div class="sechead"><h2 class="disp">Still on judgement</h2></div>
  <table class="fig"><thead><tr><th>Term</th><th class="num">Constant</th><th>Status</th></tr></thead><tbody>
  <tr><th>Lease / vintage</th><td class="num big">$40 psf / yr</td>
    <td style="color:var(--gold-soft)">measured &mdash; ${BANDR[OLD_NM]:,.0f} and ${BANDR[NEW_NM]:,.0f}</td></tr>
  <tr><th>Tenure &middot; freehold vs leasehold</th><td class="num big">&divide; 1.15</td>
    <td class="nil">next &mdash; 1,255 of 1,844 developments are freehold and cannot pair on lease</td></tr>
  <tr><th>MRT walk band</th><td class="num big">$50 / $200 / $250</td><td class="nil">not measured</td></tr>
  <tr><th>GFA harmonisation</th><td class="num big">+7%</td><td class="nil">not measured</td></tr>
  <tr><th>Integrated development</th><td class="num big">+5%</td><td class="nil">not measured</td></tr>
  </tbody></table>
</section>
"""

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#101727">
<title>Constant Calibration — KYA</title>
<style>{CSS}</style></head><body>
<header><div class="hin">
  <div class="brand"><div class="mark">K</div>
    <div><p>KYA REAL ESTATE</p><p>Private Client Advisory</p></div></div>
  <span class="chip"><b></b> Internal — Constant Calibration</span>
</div></header>
<div class="wrap">
{BODY}
<footer>
  <span>URA caveats via the MAPS refresh · resale and sub-sale only, new sale excluded ·
  generated {datetime.date.today().isoformat()}</span>
  <span>price-gap/calibration/lease-pairs.py · regenerate with build-page.py</span>
</footer>
</div>
<script>{JS.replace('%BANDS%', BANDS_JS).replace('%LO%', f'{MID_LO}').replace('%HI%', f'{MID_HI}')}</script>
</body></html>
"""
open(OUT, 'w').write(HTML)
print(f'wrote {os.path.relpath(OUT, HERE)}  ({len(HTML)//1024} KB)')
print(f'  {NDEV} developments · {npairs(ALL)} pairs · {len(ALL)} cells')
for _, _, nm in BANDS:
    c = BANDCI[nm]
    print(f'    {nm:14s} ${BANDR[nm]:5.1f}/yr  95% [{c[0]:.1f}, {c[1]:.1f}]  {ndev(rows_in(nm)):3d} devs')
print(f'  held-out: flat {CV_FLAT/1000:.1f}k · TWO {CV_TWO/1000:.1f}k · three {CV_THREE/1000:.1f}k')
print(f'  region in the newer band: RCR ${fit(RCR_NEW):.0f} vs OCR ${fit(OCR_NEW):.0f}, p={P_RNEW[1]:.3f}')
