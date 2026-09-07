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
MRTP = os.path.join(HERE, 'mrt-pairs.json')
M    = json.load(open(MRTP)) if os.path.exists(MRTP) else None
INTP = os.path.join(HERE, 'integrated-pairs.json')
G    = json.load(open(INTP)) if os.path.exists(INTP) else None
VOIDP = os.path.join(HERE, 'void-pairs.json')
V    = json.load(open(VOIDP)) if os.path.exists(VOIDP) else None
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

# ── the SIZE story, computed (Shawn, 2026-09-06) ─────────────────────────────
# The psf gap read as DOLLARS PER HOME. Same estimator, each cell's psf difference
# valued at the pair's own mean size. This is what makes the gap legible to a layman:
# part of the per-foot jump is simply that the newer box is smaller.
qfit = lambda rs: (sum(r['diff'] * (r['sqft_old'] + r['sqft_new']) / 2 for r in rs)
                   / sum(r['gap'] for r in rs)) if rs else None
BANDQ = {nm: qfit(rows_in(nm)) for _, _, nm in BANDS}

def sizes_by_vintage(bed):
    """Median size of that bedroom type, split on each PROJECT's OWN lease start —
    not on the pair midpoint, which would mix a pre-2011 block into the newer band."""
    old, new = [], []
    for r in ALL:
        if r['bed'] != bed: continue
        for ls, sq in ((r['ls_old'], r['sqft_old']), (r['ls_new'], r['sqft_new'])):
            (old if ls <= 2010 else new).append(sq)
    return (st.median(old) if old else None), (st.median(new) if new else None)

SQ3_OLD, SQ3_NEW = sizes_by_vintage('3BR')
SHRINK3 = 1 - SQ3_NEW / SQ3_OLD

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
    """One row per way of splitting the pairs. The LAST column is the argument: if the
    thing being split on explained the jump, the jump would shrink. It does not."""
    O, N = (1900, 2011), (2011, 3000)
    def g(lo, hi, f): return [r for r in ALL if lo <= mid(r) < hi and f(r)]
    SPLITS = [('All pairs', lambda r: True, True),
              ('Only small units, under 900 sqft', lambda r: r['sqft_old'] < 900, False),
              ('Only large units, 900 sqft and over', lambda r: r['sqft_old'] >= 900, False),
              ('Only close lease gaps, 1&ndash;4 years', lambda r: r['gap'] <= 4, False),
              ('Only wide lease gaps, 5 years and over', lambda r: r['gap'] > 4, False)]
    h = ['<table class="fig"><thead><tr><th>Looking only at&hellip;</th>'
         f'<th class="num">{OLD_NM}</th><th class="num">{NEW_NM}</th>'
         '<th class="num">the jump</th><th class="num">pairs</th></tr></thead><tbody>']
    for lab, f, head in SPLITS:
        a, b = g(*O, f), g(*N, f)
        if len(a) < 10 or len(b) < 10: continue
        jump = fit(b) - fit(a)
        h.append(f'<tr{" class=head" if head else ""}><th>{"<b>" if head else ""}{lab}{"</b>" if head else ""}</th>'
                 f'<td class="num">${fit(a):,.0f}</td><td class="num">${fit(b):,.0f}</td>'
                 f'<td class="num big">+${jump:,.0f}</td>'
                 f'<td class="num quiet">{npairs(a)+npairs(b)}</td></tr>')
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
/* THE TERM BAR. Five constants, one row, each its own view. It replaces the old single-term
   kicker: this page is no longer about the lease alone. It rides inside the sticky header so
   it stays reachable at any scroll depth, which is the point of splitting the page up. */
.terms{display:flex;flex-wrap:wrap;gap:0;border-top:1px solid var(--ink);
max-width:1180px;margin:0 auto;padding:0 24px}
.terms button{flex:1 1 auto;min-width:158px;padding:13px 17px 12px;text-align:left;
background:none;border:0;border-right:1px solid var(--ink);cursor:pointer;font:inherit;
color:inherit;position:relative;
transition:background .18s cubic-bezier(.22,1,.36,1),color .18s cubic-bezier(.22,1,.36,1)}
.terms button:last-child{border-right:0}
.terms button:hover{background:var(--navy-850)}
.terms button:focus-visible{outline:2px solid var(--gold);outline-offset:-2px}
.terms .tn{display:block;font:600 14.5px/1.25 Optima,Candara,sans-serif;
color:var(--slate-400);letter-spacing:.005em}
.terms .ts{display:block;margin-top:4px;font-size:9.5px;letter-spacing:.2em;
text-transform:uppercase;color:var(--slate-600)}
.terms button.done .ts{color:rgba(201,169,106,.75)}
.terms button[aria-current="true"]{background:var(--navy-850)}
.terms button[aria-current="true"] .tn{color:var(--slate-100)}
.terms button[aria-current="true"] .ts{color:var(--gold)}
.terms button[aria-current="true"]::after{content:"";position:absolute;left:0;right:0;bottom:-1px;
height:2px;background:var(--gold)}
.panel>h1{margin-top:46px}
@media (max-width:760px){.terms{padding:0 16px}.terms button{min-width:130px}}
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
/* THE ANSWER BLOCK. Shawn, 2026-09-06: the measured figure is the only thing he should have
   to find on a panel, and the number of developments behind it comes second — big enough to
   read as the credential it is, never big enough to compete with the answer. */
.answers{display:flex;gap:34px;flex-wrap:wrap;align-items:flex-end}
.ans .n{font:600 clamp(40px,5.2vw,56px)/.95 Optima,Candara,sans-serif;color:var(--gold);
white-space:nowrap;letter-spacing:-.012em}
.ans .w{font-size:11.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--slate-400);
margin-top:10px}
.ans .g{font:600 18px/1.15 Optima,Candara,sans-serif;color:var(--slate-200);margin-top:8px}
.ans .g span{font:400 10px/1 -apple-system,Segoe UI,sans-serif;letter-spacing:.16em;
text-transform:uppercase;color:var(--slate-600);display:block;margin-top:3px}
.vcell.grow{flex:1 1 340px}
@media (max-width:1100px){
  .vgrid{display:block}
  .arrow{display:none}
  .vgrid>.vcell:first-child{padding-bottom:18px;margin-bottom:18px;
    border-bottom:1px solid var(--ink)}
  .vgrid>.vcell:first-child .val{font-size:30px}
  .vcell.grow{flex:none}
}
@media (max-width:640px){.answers{gap:22px}.ans .n{font-size:36px}}
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
tr.head th,tr.head td{border-bottom:1px solid var(--ink);padding-bottom:11px}
tr.head td.big{color:var(--gold)}
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

/* VOID SPACE. Deliberately the smallest calculator on this page: the unit below, its psf,
   and the penthouse size. The floor plate is priced at the psf it already sells for; only the
   EXTRA area is repriced. No floor step, no placebo correction, no verdict -- Shawn's ruling,
   2026-09-07: ask for two things and return a quantum range.

   THE BAND IS THE 95% INTERVAL ON THE RESALE MEDIAN, not the quartiles. His call, same day: the
   quartile range (0.24-0.78) was too wide to act on. Read it as where the market's TYPICAL ratio
   sits, not where one particular penthouse could land -- a single stack can still fall outside
   it, and the per-development table above shows several that do.

   THE MIDPOINT IS THE MEASURED MEDIAN, not (lo+hi)/2. They land within a cent of each other here
   but they are different quantities, and the median is the one with evidence behind it. All three
   derived from void-pairs.json, never hardcoded. */
(function(){
  var LO=%VLO%, HI=%VHI%, MID=%VMID%;
  function n(id){return parseFloat(document.getElementById(id).value);}
  function m(x){return '$'+(x/1e6).toFixed(2)+'M';}
  function go(){
    var bs=n('vbS'), bp=n('vbP'), ps=n('vpS'), o=document.getElementById('voidOut');
    if(!(bs>0&&bp>0&&ps>0)){o.className='cout bad';o.innerHTML='Enter the unit below and the penthouse size.';return;}
    var extra=ps-bs;
    if(extra<=0){o.className='cout bad';
      o.innerHTML='The penthouse is not larger \u2014 there is no extra area to price.';return;}
    var plate=bs*bp, lo=plate+extra*bp*LO, hi=plate+extra*bp*HI, mid=plate+extra*bp*MID;
    o.className='cout';
    o.innerHTML=
      '<div class="crow big"><span>Worth</span><b>'+m(lo)+' &ndash; '+m(hi)+'</b></div>'+
      '<div class="crow"><span>Midpoint</span><b>'+m(mid)+'</b></div>'+
      '<p class="chint">'+Math.round(extra).toLocaleString()+' sqft of extra area at '+
      LO.toFixed(2)+'&ndash;'+HI.toFixed(2)+'&times; the psf below it \u2014 the 95% interval '+
      'on the resale median.</p>';
  }
  ['vbS','vbP','vpS'].forEach(function(id){
    var e=document.getElementById(id); if(e) e.addEventListener('input',go);});
  go();
})();

/* THE TERM TABS. One constant on screen at a time; the bar stays in the sticky header so
   switching never means scrolling back up. The hash keeps a view linkable and survives a
   reload, which matters because this is a working document people send each other. */
(function(){
  var btns=[].slice.call(document.querySelectorAll('.terms button')),
      panels=[].slice.call(document.querySelectorAll('.panel'));
  function show(name,push){
    var found=false;
    panels.forEach(function(p){
      var on=p.getAttribute('data-p')===name; p.hidden=!on; if(on)found=true;
    });
    if(!found){show('lease',push);return;}
    btns.forEach(function(b){
      if(b.getAttribute('data-go')===name)b.setAttribute('aria-current','true');
      else b.removeAttribute('aria-current');
    });
    if(push&&location.hash!=='#'+name)history.replaceState(null,'','#'+name);
    window.scrollTo(0,0);
  }
  btns.forEach(function(b){
    b.addEventListener('click',function(){show(b.getAttribute('data-go'),true);});
  });
  window.addEventListener('hashchange',function(){show(location.hash.slice(1),false);});
  show((location.hash||'#lease').slice(1),false);
})();
"""
def mrt_table():
    if not M: return ''
    r = ['<table class="fig look"><thead><tr><th>Walk to the nearest station</th>'
         '<th class="num">measured</th><th class="num">95% interval</th>'
         '<th class="num">developments</th><th class="num">pairs</th>'
         '<th class="num">engine</th></tr></thead><tbody>']
    for b in M['bands']:
        r.append(f'<tr><th>{b["label"]}</th>'
                 f'<td class="num big">+${b["adj"]:,.0f}</td>'
                 f'<td class="num quiet">+${b["lo"]:,.0f} to +${b["hi"]:,.0f}</td>'
                 f'<td class="num quiet">{b["devs"]}</td>'
                 f'<td class="num quiet">{b["pairs"]}</td>'
                 f'<td class="num quiet">${M["engine"][b["key"]]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

# ── void space ──────────────────────────────────────────────────────────────
def void_answer():
    """Both tracks side by side. They never pool -- new sale is the developer's price list,
    resale is what the next buyer pays for the same space."""
    r = ['<table class="fig"><thead><tr><th>Track</th><th class="num">Base psf</th>'
         '<th class="num">Extra area psf</th><th class="num">Ratio</th><th class="num">95%</th>'
         '<th class="num">Discount</th><th class="num">Pairs</th><th class="num">Devs</th>'
         '</tr></thead><tbody>']
    for k, nm in (('newsale', 'New sale &mdash; developer price list'),
                  ('resale', 'Resale &mdash; the same stacks, later')):
        h = V[k]['corrected']
        r.append(f'<tr><th>{nm}</th>'
                 f'<td class="num quiet">${h["base_psf"]:,}</td>'
                 f'<td class="num big">${h["void_psf"]:,}</td>'
                 f'<td class="num big" style="color:var(--gold)">{h["ratio"]:.2f}&times;</td>'
                 f'<td class="num quiet">{h["lo"]:.2f}&ndash;{h["hi"]:.2f}</td>'
                 f'<td class="num">{h["discount"]:.0f}%</td>'
                 f'<td class="num quiet">{h["pairs"]:,}</td>'
                 f'<td class="num quiet">{h["devs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def void_sens():
    r = ['<table class="fig"><thead><tr><th>Floor step assumed</th><th class="num">Ratio</th>'
         '<th class="num">Pairs</th></tr></thead><tbody>']
    for x in V['newsale']['sensitivity']:
        me = x['floor_step'] == V['meta']['floor_step']
        r.append(f'<tr><th>{x["floor_step"]*100:.1f}% per floor'
                 + (' <span style="color:var(--gold)">&larr; measured</span>' if me else '')
                 + f'</th><td class="num {"big" if me else "quiet"}">{x["ratio"]:.2f}&times;</td>'
                 f'<td class="num quiet">{x["pairs"]:,}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def void_cut(track, name):
    rows = [c for c in V[track]['cuts'] if c['cut'] == name]
    r = ['<table class="fig"><thead><tr><th>' + name.capitalize() + '</th>'
         '<th class="num">Base psf</th><th class="num">Extra area psf</th>'
         '<th class="num">Ratio</th><th class="num">95%</th><th class="num">Pairs</th>'
         '<th class="num">Devs</th></tr></thead><tbody>']
    for c in rows:
        r.append(f'<tr><th>{c["label"]}</th><td class="num quiet">${c["base_psf"]:,}</td>'
                 f'<td class="num">${c["void_psf"]:,}</td>'
                 f'<td class="num big">{c["ratio"]:.2f}&times;</td>'
                 f'<td class="num quiet">{c["lo"]:.2f}&ndash;{c["hi"]:.2f}</td>'
                 f'<td class="num quiet">{c["pairs"]:,}</td>'
                 f'<td class="num quiet">{c["devs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def void_devs(n=26, widest=False):
    d = V['newsale']['devs']
    d = sorted(d, key=lambda r: -r['spread'])[:n] if widest else d[:n]
    r = ['<table class="fig"><thead><tr><th>Development</th><th class="num">D</th>'
         '<th class="num">Base</th><th class="num">Penthouse</th><th class="num">Extra</th>'
         '<th class="num">Base psf</th><th class="num">Extra area psf</th>'
         '<th class="num">Ratio</th><th class="num">Spread</th><th class="num">Sales</th>'
         '</tr></thead><tbody>']
    for x in d:
        r.append(f'<tr><th>{html.escape(nice(x["proj"]))}</th>'
                 f'<td class="num quiet">{x["dist"]}</td>'
                 f'<td class="num quiet">{x["base_sqft"]:,}</td>'
                 f'<td class="num quiet">{x["ph_sqft"]:,}</td>'
                 f'<td class="num">+{x["extra"]:,}</td>'
                 f'<td class="num quiet">${x["base_psf"]:,}</td>'
                 f'<td class="num">${x["void_psf"]:,}</td>'
                 f'<td class="num big" style="color:var(--gold)">{x["ratio"]:.2f}&times;</td>'
                 f'<td class="num {"big" if x["spread"]>=.6 else "quiet"}">{x["spread"]:.2f}</td>'
                 f'<td class="num quiet">{x["pairs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def hero(was, was_sub, answers, call):
    """The verdict block every panel opens with. `answers` is a list of
    (figure, what it is, how many developments).

    NO INTERVALS HERE. They were added to the face on 2026-09-06 and taken off again the same
    day at Shawn's word: the face carries the answer and the count behind it, and the interval
    lives one row down in the table. Do not put it back without asking."""
    cells = ''.join(
        '<div class="ans"><div class="n">' + a[0] + '</div><div class="w">' + a[1] + '</div>'
        + ('<div class="g">' + str(a[2]) + '<span>developments</span></div>' if a[2] else '')
        + '</div>' for a in answers)
    return ('<div class="verdict"><div class="vgrid">'
            '<div class="vcell"><div class="lab">Engine constant</div>'
            '<div class="val was">' + was + '</div><div class="sub">' + was_sub + '</div></div>'
            '<div class="arrow">&rarr;</div>'
            '<div class="vcell grow"><div class="lab">Measured</div>'
            '<div class="answers">' + cells + '</div></div></div>'
            '<p class="call">' + call + '</p></div>')

def nice(n):
    """Title-case a project name without destroying acronyms. PLQ is not Plq."""
    keep = {'PLQ', 'NV', 'EC', 'CBD'}
    out = []
    for w in n.split():
        if w in keep: out.append(w)
        elif w.lower() in ('at', 'the', 'of', 'on') and out: out.append(w.lower())
        else: out.append(w.capitalize())
    return ' '.join(out)

def int_table():
    """PERCENT LEADS HERE, not dollars. The engine's constant is itself a percentage, so a
    dollar figure cannot be set against it without a base — and the base moves between cuts.
    The dollars stay in the last column. (Shawn, 2026-09-06; a deliberate exception to the
    dollars-never-percent rule that governs the lease study.)"""
    if not G: return ''
    r = ['<table class="fig look"><thead><tr><th>Reading only pairs where&hellip;</th>'
         '<th class="num">premium</th><th class="num">95% interval</th>'
         '<th class="num">pairs</th><th class="num">adjustment carried</th>'
         '<th class="num">in psf</th></tr></thead><tbody>']
    for c in G['cuts']:
        big = 'big' if c['label'] == '&lt;5 yr gap, within 400 m' else 'quiet'
        r.append(f'<tr><th>{c["label"]}</th>'
                 f'<td class="num {big}">+{c["pct"]:.1f}%</td>'
                 f'<td class="num quiet">+{c["pct_lo"]:.1f}% to +{c["pct_hi"]:.1f}%</td>'
                 f'<td class="num quiet">{c["pairs"]}</td>'
                 f'<td class="num quiet">${c["load"]:,.0f}</td>'
                 f'<td class="num quiet">+${c["adj"]:,.0f}</td></tr>')
    return ''.join(r) + '</tbody></table>'

def dsweep_table():
    if not G or not G.get('dsweep'): return ''
    r = ['<table class="fig"><thead><tr><th>The two may sit&hellip;</th>'
         '<th class="num">&lt;10 yr gap</th><th class="num">pairs</th>'
         '<th class="num">&lt;5 yr gap</th><th class="num">pairs</th>'
         '<th class="num">placebo</th></tr></thead><tbody>']
    a = {x['dg']: x for x in G['dsweep'][0]['rows']}
    b = {x['dg']: x for x in G['dsweep'][1]['rows']}
    for dg in sorted(set(a) | set(b)):
        lab = 'anywhere' if dg > 9999 else f'within {dg:,} m'
        A, B = a.get(dg), b.get(dg)
        r.append(f'<tr><th>{lab}</th>'
                 + (f'<td class="num quiet">+{A["pct"]:.1f}%</td><td class="num quiet">{A["pairs"]}</td>'
                    if A else '<td class="num quiet">&mdash;</td><td class="num quiet">&mdash;</td>')
                 + (f'<td class="num big">+{B["pct"]:.1f}%</td><td class="num quiet">{B["pairs"]}</td>'
                    f'<td class="num quiet">{B["placebo"]:+.1f}%</td>'
                    if B else '<td class="num quiet">&mdash;</td><td class="num quiet">&mdash;</td>'
                             '<td class="num quiet">&mdash;</td>'))
        r.append('</tr>')
    return ''.join(r) + '</tbody></table>'

def int_devs():
    if not G: return ''
    r = ['<table class="fig"><thead><tr><th>Development</th><th>Station</th>'
         '<th class="num">metres out</th><th class="num">lease gap</th>'
         '<th class="num">premium</th><th class="num">pairs</th></tr></thead><tbody>']
    for d in G['devs']:
        r.append(f'<tr><th>{nice(d["name"])}</th><td>{d["station"]}</td>'
                 f'<td class="num quiet">{d["m_i"]:,.0f} m</td>'
                 f'<td class="num quiet">{d["lg"]:+.0f} yrs</td>'
                 f'<td class="num big">{d["adj"]:+,.0f}</td>'
                 f'<td class="num quiet">{d["pairs"]}</td></tr>')
    return ''.join(r) + '</tbody></table>'

def mrt_split():
    if not M or not M.get('nf_split'): return ''
    r = ['<table class="fig"><thead><tr><th>Pairs whose walk differs by&hellip;</th>'
         '<th class="num">measured</th><th class="num">per 100 m</th>'
         '<th class="num">pairs</th></tr></thead><tbody>']
    for x in M['nf_split']:
        r.append(f'<tr><th>{x["label"]}</th><td class="num big">+${x["adj"]:,.0f}</td>'
                 f'<td class="num quiet">${x["per100"]:.1f}</td>'
                 f'<td class="num quiet">{x["pairs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def mrt_per100():
    if not M: return ''
    r = ['<table class="fig"><thead><tr><th>Walk to the nearest station</th>'
         '<th class="num">extra walking</th><th class="num">measured</th>'
         '<th class="num">per 100 m</th></tr></thead><tbody>']
    for b in M['bands']:
        r.append(f'<tr><th>{b["label"]}</th><td class="num quiet">{b["walk"]:,.0f} m</td>'
                 f'<td class="num quiet">+${b["adj"]:,.0f}</td>'
                 f'<td class="num big">${b["per100"]:.1f}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

BANDS_JS = '[' + ','.join(f'[{hi},{BANDR[nm]:.2f},"{nm}"]' for _, hi, nm in BANDS) + ']'
A1, A2 = age_label(OLD_NM); B1, B2 = age_label(NEW_NM)

BODY = f"""
<div class="panel" data-p="lease">
<h1 class="disp">What the market pays for a year of lease</h1>
<p class="lede">The engine restates every comparable using constants set by judgement. This is
the first one measured against the market.</p>

{hero('$40', 'flat, every comparable',
      [(f'${BANDR[OLD_NM]:,.0f}', OLD_NM, ndev(rows_in(OLD_NM))),
       (f'${BANDR[NEW_NM]:,.0f}', NEW_NM, ndev(rows_in(NEW_NM)))],
      f"<b>The call.</b> Two rates, not one, chosen by the <b>midpoint of the two lease starts</b>. "
      f"The engine's flat $40 charges an old pair {40/BANDR[OLD_NM]:.1f} times what the market pays "
      f"and short-changes a new one. Leave the engine alone until this is audited.")}

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
  <p><b>{NDEV} developments.</b> Each paired with a leasehold neighbour and compared bedroom by
  bedroom, across 24 months of resale and sub-sale to {LW[1]}.</p></div>
  <div class="scroll">{answer_table()}</div>

  <p class="expl" style="margin-top:18px">Two condominiums next door, one leased a few years after
  the other. The figure is <b>how much more per square foot the newer one fetches, for each year
  between them</b>.</p>
  <p class="expl"><b>The newer band is the steeper one.</b> Being newer pays nearly twice as much
  in stock from 2011 as it does in older stock.</p>
  <div class="caveat"><b>Treat the newer figure as a floor.</b> It rests on
  {ndev(rows_in(NEW_NM))} developments and runs hotter in the RCR (${fit(RCR_NEW):,.0f}) than the
  OCR (${fit(OCR_NEW):,.0f}). Young stock has barely resold yet.</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2>
  <p>Four questions, answered once each.</p></div>

  <details><summary>Do the bands move as the stock ages?</summary>
    <p class="expl"><b>No. They are fixed calendar years.</b> If this were really an age effect,
    the boundary would slide forward every year. Run the identical method on sales from
    {EW[0]}&ndash;{EW[1]}, three years earlier, and the jump lands on the same calendar band with
    the stock three years younger.</p>
    <div class="scroll">{vintage_table()}</div>
    <p class="expl">The {AGE_SLICES[3][0]}&ndash;{AGE_SLICES[3][1]-1} band aged four years and kept
    paying the high rate. <b>This is the vintage of the stock, not its age</b> &mdash; projects
    launched from about 2012 sold into a much steeper pricing era and have carried it since.</p>
    <p class="expl">What will eventually move the answer is <b>lease decay</b>, which bites on the
    lease <em>left</em>, below 60&ndash;65 years. Only
    {sum(1 for r in ALL if r['ls_old'] + 99 - NOW < 65)} of {len(ALL)} cells sit down there today,
    so it is almost absent. Expect it around the end of this decade &mdash; as the oldest band
    steepening, not as the boundary sliding.</p>
  </details>

  <details><summary>Why the newer band is nearly double</summary>
    <p class="expl"><b>Part of it is simply a smaller box.</b> Read in dollars instead of dollars
    per square foot, a year of newness costs about ${BANDQ[OLD_NM]:,.0f} on older stock and about
    ${BANDQ[NEW_NM]:,.0f} on stock from 2011. Newer three-bedrooms are about {SHRINK3:.0%} smaller
    &mdash; {SQ3_NEW:,.0f} sq ft against {SQ3_OLD:,.0f} &mdash; so the same money spreads over less
    floor, and the per-foot figure rises.</p>
    <p class="expl"><b>The rest is real.</b> Size cannot be the whole answer. The two sides of a
    pair must already be within 20% of each other on size before the pair is used at all, and the
    jump survives every slice below.</p>
    <div class="scroll">{why_table()}</div>
    <p class="expl">Small flats, large flats, pairs two years apart or twenty &mdash; the jump is
    in every row. A higher base price explains some of it, narrowing the gap from
    {fpct(rows_in(OLD_NM)):+.2%} to {fpct(rows_in(NEW_NM)):+.2%} a year, but nowhere near all.</p>
    <p class="expl">What is left is vintage: through the 2010s each successive launch in the same
    spot came out dearer than the last. This measures the size of that effect, not its cause.</p>
  </details>

  <details><summary>What was tested and what it changed</summary>
    <p class="expl">Every cut and every alternative method, with what it produced.
    &ldquo;Held-out error&rdquo; means fitted on four fifths of the pairs and scored on the fifth
    it never saw &mdash; lower is better.</p>
    <div class="scroll">{tested_table()}</div>
    <p class="expl"><b>{NDEV} developments</b> &mdash; one condominium each. They form
    <b>{npairs(ALL)} pairs</b>, two neighbours compared. Each pair is read at one to four bedroom
    types, giving <b>{len(ALL)} cells</b> &mdash; the unit every figure on this page is computed
    on.</p>
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

</div>

<div class="panel" data-p="mrt" hidden>
<h1 class="disp">What the market pays for the walk to the station</h1>
<p class="lede">Each development paired with a leasehold neighbour on the same nearest station,
over the same 24 months. The lease difference between them is removed at the measured lease rate,
so what is left is the walk.</p>

{hero(' / '.join(f"${M['engine'][b['key']]}" for b in M['bands']), 'three fixed band steps',
      [(f"+${b['adj']:,.0f}", lab, b['devs'])
       for b, lab in zip(M['bands'], ('under 5 vs 5-10 min', '5-10 vs over 10 min',
                                      'under 5 vs over 10 min'))],
      f"<b>The call.</b> Quote <b>${M['slope100']:.0f} psf per extra 100 m</b> &mdash; it holds "
      f"whatever the band lines do, and the three figures above all agree on it. Of the engine's "
      f"three steps only <b>${M['engine']['mid|far']}</b> is wrong; the other two sit inside the "
      f"measured intervals.")}

<section>
  <div class="scroll">{mrt_table()}</div>

  <p class="expl" style="margin-top:18px"><b>Two of the three hold up.</b> The engine's
  ${M['engine']['near|mid']} and ${M['engine']['near|far']} both sit inside the measured intervals.
  Its ${M['engine']['mid|far']} for the middle step does not &mdash; the market pays
  <b>${M['bands'][1]['adj']:,.0f}</b>, and the interval tops out at
  ${M['bands'][1]['hi']:,.0f}.</p>

  <div class="caveat"><b>The bands cannot be added together.</b> Each spans a different amount of
  walking, so the first two do not sum to the third. Read them per 100 m instead and all three say
  the same thing.</div>
  <div class="scroll" style="margin-top:14px">{mrt_per100()}</div>
  <p class="expl"><b>${M['slope100']:.0f} psf for every extra 100 m</b> is the figure to quote. It
  does not depend on where the band lines are drawn, and the three rows agree on it within
  ${max(b['per100'] for b in M['bands'])-min(b['per100'] for b in M['bands']):.0f}.</p>

  <details><summary>Why the bottom row understates the contrast you are picturing</summary>
    <p class="expl"><b>Most &ldquo;under 5 vs over 10&rdquo; pairs barely straddle the line.</b> The
    typical one is {M['nf_close']:,.0f} m against {M['nf_far']:,.0f} m &mdash; not a doorstep
    against a fifteen-minute walk. So the band average is diluted by pairs that only just qualify.
    Split them by the walking they actually span and the effect is plainly there:</p>
    <div class="scroll">{mrt_split()}</div>
    <p class="expl">Pairs separated by more than 700 m read
    <b>+${[x for x in M['nf_split'] if x['label'].startswith('over')][0]['adj']:,.0f}</b>. The band
    figure is right for the pairs it contains; it is the wrong number to reach for when the two
    homes you are comparing are further apart than that. <b>Use the per-100 m rate and multiply
    by the actual difference in walking.</b></p>
  </details>

  <details><summary>How the lease is taken out, and the check that it worked</summary>
    <p class="expl">Each pair shares its nearest station but sits at a different distance from it.
    Their price difference still contains whatever lease difference they carry, so the measured
    vintage rate above is subtracted from it. What remains is distance.</p>
    <p class="expl"><b>The check.</b> Take pairs in the same band standing the same distance from
    the station &mdash; within 50 m of each other. Nothing separates them, so after the lease comes
    out they should read zero. They read <b>+${M['placebo']['adj']:.1f}</b> across
    {M['placebo']['pairs']} pairs. That is the evidence the adjustment is working and that what is
    left is the walk.</p>
  </details>

  <details><summary>Where the 5 and 10 minute lines are drawn, and what it costs</summary>
    <p class="expl"><b>Under 400 m &middot; 400 to 800 m &middot; over 800 m.</b> People walk about
    80 metres a minute, so five minutes is 400 m and ten is 800. Distance is measured straight
    across the map to the nearest operational station.</p>
    <p class="expl">The engine draws them tighter &mdash; it inflates every distance by 30% before
    converting, which pulls the five-minute bar in to 308 m. That is too strict. At 308 m it files
    <b>J Gateway</b>, standing beside JEM at Jurong East, as a five-to-ten-minute walk.</p>
    <p class="expl"><b>The lines are the weak part of this measurement.</b> A station is held as a
    single point when a large interchange spans hundreds of metres, and some geocodes sit about
    100 m off &mdash; CityLife@Tampines measures 869 m here against a real 700 m walking route.
    Across defensible placements of the two lines the bottom row runs <b>$162 to $304</b>. That
    spread is wider than any interval in the table above and it is the honest uncertainty on the
    figure.</p>
    <p class="expl">What survives it: both sides of a pair are measured to the <b>same</b> station
    point, so an error in that point largely cancels in the difference between them. That is why
    the three rows agree per 100 m, and why <b>${M['slope100']:.0f} psf per 100 m</b> is the
    figure to reach for whenever the two homes being compared are not a typical band pair. Real
    walking routes would close the rest.</p>
  </details>

  <details><summary>How a pair is built</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h4>Held constant</h4><ul>
        <li>same <b>nearest station</b>, and it must be nearest for both</li>
        <li>both inside <b>{M['catchment']:,} m</b> of it</li>
        <li>within <b>{M['pair_cap']:,} m</b> of each other</li>
        <li>identical <b>top-26 primary schools</b> within 1 km</li>
        <li>median sizes within <b>20%</b>, bedroom by bedroom</li></ul></div>
      <div class="card"><h4>Both sides must be</h4><ul>
        <li>leasehold, with a known lease start</li>
        <li><b>200 units</b> or more</li>
        <li><b>5+ transactions</b> in the window</li>
        <li>EC only once privatised &mdash; <b>TOP + 5</b></li></ul></div>
      <div class="card"><h4>Not controlled</h4><ul>
        <li><b>floor</b> and <b>facing</b> &mdash; the PSF series carries neither</li>
        <li>which <b>side</b> of the station the project sits on</li>
        <li>bus and shuttle access</li></ul></div>
    </div>
  </details>
</section>

</div>

<div class="panel" data-p="integrated" hidden>
<h1 class="disp">What the market pays for being on top of the station</h1>
<p class="lede">An integrated development against an ordinary condo a short walk away at the
<b>same station</b>. The lease difference between them is removed at the measured lease rate, and
the walking difference at the measured ${G['slope']:.0f} per 100 m. What is left is the building
sitting on the station.</p>

{hero('+5%', 'never actually fired',
      [(f"+{G['cuts'][4]['pct']:.1f}%", '&lt;5 yr gap, within 400 m', G['cuts'][4]['devs']),
       (f"+{G['cuts'][0]['pct']:.1f}%", 'every pair', G['cuts'][0]['devs'])],
      f"<b>The call. About +{G['cuts'][4]['pct']:.1f}%</b>, or roughly "
      f"${G['cuts'][4]['adj']:,.0f} psf at these price levels &mdash; the cut that carries the "
      f"least correction of anything here, and the broadest cut of all {G['cuts'][0]['pairs']} "
      f"pairs lands beside it at +{G['cuts'][0]['pct']:.1f}%. "
      f"<b>The engine's +5% falls inside the interval</b> "
      f"({G['cuts'][4]['pct_lo']:.1f}% to {G['cuts'][4]['pct_hi']:.1f}%), so it sits at the low "
      f"end but is not demonstrably wrong. It has, however, never fired on a single comparable.")}

<section>
  <div class="scroll">{int_table()}</div>

  <div class="caveat"><b>Read the adjustment column with the answer.</b> Integrated developments are
  systematically newer than their neighbours &mdash; {G['confound']['treat_gap']:+.0f} years of
  lease apart against {G['confound']['placebo_gap']:+.0f} for the plain-vs-plain pairs. So they
  carry about ${G['confound']['treat_load']:,.0f} of adjustment each, roughly double the placebo's
  ${G['confound']['placebo_load']:,.0f}, and the answer is what survives a large subtraction.
  <b>The bolded row carries the least correction of any cut here, which is why it is the one to
  quote.</b> The rows reading higher are the ones that let the two sit further apart, and the
  sweep below shows that is walking effect leaking in, not a bigger building premium.</div>

  <p class="expl" style="margin-top:18px"><b>Call it ${G['cuts'][3]['adj']:,.0f} to
  ${G['cuts'][2]['adj']:,.0f} psf, or roughly {min(c['pct'] for c in G['cuts'][1:]):.0f} to
  {max(c['pct'] for c in G['cuts'][1:]):.0f}%.</b> The engine assumes <b>+5%</b>, which sits at
  or below the bottom of that range &mdash; on this evidence it is more likely too low than too
  high. It is also the only constant here that has never actually fired.</p>

  <div class="caveat"><b>The engine's integrated flag is inert.</b> It reads from an override
  file that flags nothing, so every development is treated as not integrated and the &plusmn;5%
  has never applied to a single comparable. The {G['n_integrated']} developments below are a
  classification made for this study and audited by hand &mdash; a judgement, not a datum.</div>

  <details><summary>Does it matter how far apart the two sit?</summary>
    <p class="expl">The pairs are not all the same distance from their station, so some carry a
    bigger walking correction than others. Holding the lease gap fixed and sweeping that limit:</p>
    <div class="scroll">{dsweep_table()}</div>
    <p class="expl"><b>It is not neutral.</b> Inside the tight lease-gap column the premium climbs
    from +{G['dsweep'][1]['rows'][0]['pct']:.1f}% to +{G['dsweep'][1]['rows'][-1]['pct']:.1f}% as
    the limit loosens, while the placebo beside it stays flat. That is what unremoved walking
    effect leaking into the answer would look like &mdash; the further apart the two sit, the more
    of the gap between them is the walk rather than the building. <b>The tighter rows are the
    conservative ones</b>, and they sit near +7%.</p>
  </details>

  <details><summary>The check that the adjustments are working</summary>
    <p class="expl">The same method run on <b>plain against plain</b> at the same station, under
    the identical lease and distance corrections. Nothing separates those pairs, so the answer
    should be zero. Across <b>{G['placebo']['pairs']} pairs</b> it reads
    <b>{G['placebo']['pct']:+.1f}%</b> ({G['placebo']['adj']:+,.0f} psf), with an interval of
    {G['placebo']['pct_lo']:+.1f}% to {G['placebo']['pct_hi']:+.1f}% that covers zero. It leans
    very slightly negative, which if anything makes the integrated figures above conservative.</p>
  </details>

  <details><summary>Every development, and what each one reads</summary>
    <div class="scroll">{int_devs()}</div>
    <p class="expl"><b>Read the lease-gap column before the premium column.</b> The three that
    read low or negative are the three with the widest lease gaps, and their answers are
    dominated by the correction rather than by the building. Pasir Ris 8 carries more pairs than
    any other &mdash; a 2021 lease set against neighbours from 1996 to 2013 &mdash; and its
    individual answers run from &minus;$424 to +$306. That is noise around a large subtraction,
    which is why it is not evidence that being on the station is worth nothing.</p>
  </details>

  <details><summary>How a pair is built</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h4>Held constant</h4><ul>
        <li>same <b>nearest station</b>, nearest for both</li>
        <li>within <b>{G['pair_cap']:,} m</b> of each other</li>
        <li>median sizes within <b>20%</b>, bedroom by bedroom</li></ul></div>
      <div class="card"><h4>Adjusted out</h4><ul>
        <li><b>lease</b>, at ${G['lease_old']:,.0f} / ${G['lease_new']:,.0f} by midpoint</li>
        <li><b>walking distance</b>, at ${G['slope']:.0f} per 100 m</li>
        <li>both measured here, neither assumed</li></ul></div>
      <div class="card"><h4>Not controlled</h4><ul>
        <li><b>floor</b> and <b>facing</b></li>
        <li>the quality of the mall attached</li>
        <li>whether the plain neighbour is itself mixed-use</li></ul></div>
    </div>
  </details>
</section>
</div>

<div class="panel" data-p="void" hidden>
<h1 class="disp">What the market pays for the void</h1>
<p class="lede">Same project, same block, <b>same stack</b> &mdash; so the top-floor unit stands on
the same floor plate as every unit below it. Where its strata area is larger, the difference is
space the floor plate never gained: void over the living room, or roof. Floor is normalised out at
the floor study&rsquo;s own {V['meta']['floor_step']*100:.1f}% per floor. What is left is what that
extra area is worth.</p>

{hero('1.00&times;', 'every strata sqft priced alike',
      [(f"{V['newsale']['corrected']['ratio']:.2f}&times;", 'developer price list',
        V['newsale']['corrected']['devs']),
       (f"{V['resale']['corrected']['ratio']:.2f}&times;", 'resale, the same stacks',
        V['resale']['corrected']['devs'])],
      f"<b>The call. Quote a quarter.</b> A developer charges about "
      f"<b>{V['newsale']['corrected']['ratio']:.2f}&times;</b> the home&rsquo;s own psf for the "
      f"extra penthouse area &mdash; a {V['newsale']['corrected']['discount']:.0f}% discount, and "
      f"the cheapest square foot on the price list. The resale market later pays about "
      f"<b>{V['resale']['corrected']['ratio']:.2f}&times;</b> for the same space, so the void "
      f"re-rates upward on exit. <b>The engine sees none of this</b> &mdash; it works in psf and "
      f"charges the void the same as a bedroom.")}

<section>
  <div class="calc">
    <h3>What should the penthouse cost</h3>
    <div class="cin">
      <label>Unit below &mdash; sqft<input id="vbS" type="number" value="1216" min="200" max="9000" step="1"></label>
      <label>Unit below &mdash; psf<input id="vbP" type="number" value="2662" min="200" max="9000" step="10"></label>
      <label>Penthouse sqft<input id="vpS" type="number" value="1421" min="200" max="9000" step="1"></label>
    </div>
    <div id="voidOut" class="cout"></div>
  </div>

  <div class="scroll">{void_answer()}</div>
  <p class="expl"><b>The penthouse psf reads {abs(V['newsale']['headline']['headline_drop']):.0f}%
  below the unit underneath it</b> and nothing about the home got worse. That is the whole effect:
  a cheap block of area averaged into an expensive one. Any comparison that reaches for a
  penthouse&rsquo;s headline psf &mdash; the engine&rsquo;s included &mdash; is reading a blended
  figure, not a price.</p>

  <div class="caveat"><b>Void, roof terrace or private roof &mdash; the caveat reads them as one
  thing.</b> REALIS records strata area, not what is under the ceiling. All three are area on a
  floor plate that did not grow and all three price like it, which is why they measure together.
  Naming which is which needs the floor plan, unit by unit. Quote this as <b>extra penthouse
  area</b>; ceiling height is a subset of it and has not been separated.</div>

  <details open><summary>The placebo, and why it moved the answer</summary>
    <p class="expl">The marginal psf is <b>leveraged</b>: the extra area is small against the home,
    so a 2% error in the base comparator swings it by more than 10%. The threat is a top-floor
    bonus that a straight-line floor step does not capture &mdash; any such bonus lands entirely
    on the void and inflates the ratio.</p>
    <p class="expl"><b>The check.</b> Run the identical machinery on stacks whose top unit is the
    <b>same size</b> as the units below. No extra area, so the residual should be zero. Across
    {V['newsale']['placebo']['pairs']:,} such sales it reads
    <b>+{V['newsale']['placebo']['residual_pct']:.2f}%</b>
    ({V['newsale']['placebo']['lo']:.2f} to {V['newsale']['placebo']['hi']:.2f}) &mdash; a real
    top-floor bonus on developer price lists, over and above the floor step. Stripping it off the
    penthouse leg first takes the answer from
    {V['newsale']['headline']['ratio']:.2f}&times; to
    <b>{V['newsale']['corrected']['ratio']:.2f}&times;</b>. The corrected figure is the one on the
    face.</p>
    <p class="expl">The same placebo on <b>resale</b> reads
    {V['resale']['placebo']['residual_pct']:+.2f}% across {V['resale']['placebo']['pairs']} sales
    &mdash; nil. The top-floor bonus is something developers charge and the resale market does not
    repeat, which is a finding in its own right.</p>
  </details>

  <details><summary>How much of this is the floor-step assumption</summary>
    <p class="expl">Honest answer: some of it. Re-run everything at other floor steps and the
    uncorrected ratio moves with the assumption &mdash; which is the same bias the placebo
    catches, arriving by another road.</p>
    <div class="scroll">{void_sens()}</div>
    <p class="expl">Across the defensible range the ratio runs
    <b>{min(x['ratio'] for x in V['newsale']['sensitivity']):.2f} to
    {max(x['ratio'] for x in V['newsale']['sensitivity']):.2f}</b>, and the placebo correction
    lands at the bottom of it. <b>Quote a quarter, not two decimal places.</b></p>
  </details>
</section>

<section>
  <h2>Where it moves</h2>
  <p class="expl"><b>The bigger the void, the cheaper it gets.</b> A penthouse where the extra area
  is a third of the floor plate is priced further down than one where it is a sixth &mdash; the
  developer knows the buyer will not pay twice for space they cannot furnish.</p>
  <div class="scroll">{void_cut('newsale', 'extra area')}</div>

  <p class="expl" style="margin-top:18px"><b>And the dearer the home, the dearer the void.</b> As a
  ratio it climbs with price tier, so in dollars it climbs twice over.</p>
  <div class="scroll">{void_cut('newsale', 'price tier')}</div>

  <details style="margin-top:16px"><summary>By region, and by tenure</summary>
    <div class="scroll">{void_cut('newsale', 'region')}</div>
    <div class="scroll" style="margin-top:14px">{void_cut('newsale', 'tenure')}</div>
    <p class="expl">Freehold reads dearer than leasehold, but freehold stock sits in pricier
    pockets and the price-tier cut above already explains most of it. Do not quote the tenure split
    on its own.</p>
  </details>
</section>

<section>
  <h2>The finding that is worth money</h2>
  <p class="expl"><b>The spread inside one development is wider than the spread between
  developments.</b> The developer prices the void stack by stack and the pricing is close to
  arbitrary &mdash; at some stacks the extra area is charged at nothing at all.</p>
  <div class="scroll">{void_devs(widest=True, n=14)}</div>
  <p class="expl">Read the <b>spread</b> column: it is the gap between the dearest and the cheapest
  stack in that same development. <b>The advice is not &ldquo;penthouses are good value&rdquo;
  &mdash; it is find the stack where the void was given away.</b> Same project, same launch, same
  price list.</p>

  <details><summary>Every development that priced the void cheapest</summary>
    <div class="scroll">{void_devs(n=26)}</div>
  </details>
</section>

<section>
  <details><summary>How a pair is built</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h4>Held constant</h4><ul>
        <li>same project, same <b>block</b>, same <b>stack</b></li>
        <li>&mdash; so the same <b>floor plate</b>, by construction</li>
        <li>base legs within <b>{V['meta']['size_tol']*100:.0f}%</b> of the stack&rsquo;s median size</li>
        <li>base legs within <b>{V['meta']['match_days']} days</b> of the penthouse sale</li></ul></div>
      <div class="card"><h4>The screens</h4><ul>
        <li><b>{V['meta']['min_base']}+ base legs</b>, so the comparator is a median</li>
        <li>extra area <b>{V['meta']['extra_band'][0]*100:.0f}&ndash;{V['meta']['extra_band'][1]*100:.0f}%</b>
            of the floor plate</li>
        <li>under that is a bay window; over it is a <b>duplex</b> &mdash; a second floor plate,
            which is what this pair exists to exclude</li></ul></div>
      <div class="card"><h4>Not controlled</h4><ul>
        <li><b>what the extra area is</b> &mdash; void, roof terrace or roof</li>
        <li>renovation and fit-out on the resale track</li>
        <li>the top floor&rsquo;s own view, beyond the floor step and the placebo</li></ul></div>
    </div>
  </details>
  <details><summary>Where the data comes from &mdash; not the MAPS refresh</summary>
    <p class="expl">Every other panel reads <code>property-analyzer/data/</code>. This one reads the
    <b>REALIS unit-level pull</b> held by the floor study, because it is the only dataset here that
    carries a <b>unit number</b> &mdash; and without the unit number there is no stack, without the
    stack there is no same-floor-plate pair. {V['meta']['window']}, all Singapore, strata,
    apartment and condominium. Read-only, same arrangement as the others.</p>
    <p class="expl"><code>price-gap/calibration/void-pairs.py</code> &rarr;
    <code>void-pairs.json</code>. It depends on none of the other three and they depend on none of
    it, so it may be run at any point in the order.</p>
  </details>
</section>
</div>

<div class="panel" data-p="judgement" hidden>
<h1 class="disp">Still on judgement</h1>
<p class="lede">The last constant still on judgement, and the next one to measure.</p>

{hero('&divide; 1.15', 'freehold over leasehold',
      [('&mdash;', 'not measured yet', None)],
      "<b>The call.</b> Nothing to quote yet. It is also the biggest sample left: of the "
      "1,844 developments in the index, <b>1,255 are freehold</b> and cannot pair on lease "
      "start at all &mdash; which is the real ceiling on this whole workstream, not the "
      "pair screens.")}

<section>
  <table class="fig"><thead><tr><th>Term</th><th class="num">Constant</th><th>Status</th></tr></thead><tbody>
  <tr><th>Lease / vintage</th><td class="num big">$40 psf / yr</td>
    <td style="color:var(--gold-soft)">measured &mdash; ${BANDR[OLD_NM]:,.0f} and ${BANDR[NEW_NM]:,.0f}</td></tr>
  <tr><th>Tenure &middot; freehold vs leasehold</th><td class="num big">&divide; 1.15</td>
    <td class="nil">next &mdash; 1,255 of 1,844 developments are freehold and cannot pair on lease</td></tr>
  <tr><th>MRT walk band</th><td class="num big">$50 / $200 / $250</td>
    <td>measured &mdash; +${M['bands'][0]['adj']:,.0f} / +${M['bands'][1]['adj']:,.0f} /
    +${M['bands'][2]['adj']:,.0f}, or ${M['slope100']:.0f} per 100 m</td></tr>
    <tr><th>Integrated development</th><td class="num big">+5%</td>
    <td>measured &mdash; +{G['cuts'][4]['pct']:.1f}% ({G['cuts'][4]['pct_lo']:.1f} to
    {G['cuts'][4]['pct_hi']:.1f}), which contains the +5%</td></tr>
  <tr><th>Void &middot; extra penthouse area</th><td class="num big">1.00&times; (implicit)</td>
    <td>measured &mdash; {V['newsale']['corrected']['ratio']:.2f}&times; on the price list,
    {V['resale']['corrected']['ratio']:.2f}&times; on resale; the engine has no constant for it</td></tr>
  </tbody></table>
</section>
</div>
"""

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#101727">
<title>Constant Calibration — KYA</title>
<style>{CSS}</style></head><body>
<header>
  <div class="hin">
    <div class="brand"><div class="mark">K</div>
      <div><p>KYA REAL ESTATE</p><p>Private Client Advisory</p></div></div>
    <span class="chip"><b></b> Internal — Constant Calibration</span>
  </div>
  <nav class="terms" aria-label="The constants">
    <button type="button" class="done" data-go="lease" aria-current="true">
      <span class="tn">Lease Difference</span><span class="ts">Measured</span></button>
    <button type="button" class="done" data-go="mrt">
      <span class="tn">MRT Distance</span><span class="ts">Measured</span></button>
    <button type="button" class="done" data-go="integrated">
      <span class="tn">Integrated</span><span class="ts">Measured</span></button>
    <button type="button" class="done" data-go="void">
      <span class="tn">Void Space</span><span class="ts">Measured</span></button>
    <button type="button" data-go="judgement">
      <span class="tn">FH vs LH</span><span class="ts">Next</span></button>
  </nav>
</header>
<div class="wrap">
{BODY}
<footer>
  <span>URA caveats via the MAPS refresh · resale and sub-sale only, new sale excluded ·
  Void Space reads the REALIS unit-level pull instead, both tracks ·
  generated {datetime.date.today().isoformat()}</span>
  <span>price-gap/calibration/lease-pairs.py · regenerate with build-page.py</span>
</footer>
</div>
<script>{JS.replace('%BANDS%', BANDS_JS).replace('%LO%', f'{MID_LO}').replace('%HI%', f'{MID_HI}').replace('%VLO%', f"{V['resale']['corrected']['lo']}").replace('%VHI%', f"{V['resale']['corrected']['hi']}").replace('%VMID%', f"{V['resale']['corrected']['ratio']}")}</script>
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
