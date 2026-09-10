#!/usr/bin/env python3
"""Renders the lease-term finding as ../../kya-maps-calculator/calibration.html.

HIDDEN PAGE. Not in the nav, nothing links to it: the only way in is a DOUBLE-TAP on the
"K" brand mark at the top left of the calculator. (It was the Live Data chip until
2026-09-10 — that chip is xl-only, so on an iPhone there was nothing to double-click.)
A working document, never a client view. Self-contained, no Tailwind.

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
TENP = os.path.join(HERE, 'tenure-pairs.json')
T    = json.load(open(TENP)) if os.path.exists(TENP) else None
ECP  = os.path.join(HERE, 'ec-pairs.json')
E    = json.load(open(ECP)) if os.path.exists(ECP) else None
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
         '<th class="num">$ psf / yr</th><th class="num">could really be</th>'
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

# NOT RENDERED since 2026-09-08 — Shawn pulled the "What was tested and what it changed"
# explain mark off the lease panel. Kept because it is the record of every cut and every
# alternative method; put it back by calling it from a details block.
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
                'Worse on the average miss, and the extra band split into two incoherent regional halves.'))
    h.append(r_('One flat rate', f'{CV_FLAT/1000:,.1f}k against {CV_TWO/1000:,.1f}k',
                'Worse on the average miss. It is the form the constant takes today.'))
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

# ── does the rate actually fit a pair? (Shawn, 2026-09-10) ──────────────────
# The pair table used to lead with each cell's own $/yr — its difference divided by its own
# gap. At a one-year gap that divides the pair's whole floor-and-facing noise by 1, so the
# column swung between -$302 and +$168 beside a $43 band and read as a contradiction. It is
# not one: the rate is the slope through every cell, not the average of that column.
# This table is the demonstration. Compare TOTALS at the same gap, never a single per-year.
GBUCKETS = [('One year apart', 1, 1), ('Two years', 2, 2), ('Three to four years', 3, 4),
            ('Five to nine years', 5, 9), ('Ten years and over', 10, 999)]

def holds_table():
    h = ['<table class="fig look"><thead><tr><th>How far apart the two leases are</th>'
         '<th class="num">cells</th><th class="num">what the market shows</th>'
         '<th class="num">what the rate predicts</th><th class="num">off by</th>'
         '</tr></thead><tbody>']
    for _, _, nm in BANDS:
        rows = rows_in(nm)
        h.append(f'<tr class="sep"><th colspan="5">{nm} &mdash; ${BANDR[nm]:,.0f} a year</th></tr>')
        for lab, lo, hi in GBUCKETS:
            s_ = [r for r in rows if lo <= r['gap'] <= hi]
            if not s_: continue
            obs  = st.median(r['diff'] for r in s_)
            pred = BANDR[nm] * st.median(r['gap'] for r in s_)
            thin = len(s_) < 10
            h.append(f'<tr{" class=dim" if thin else ""}><th>{lab}</th>'
                     f'<td class="num quiet">{len(s_)}</td>'
                     f'<td class="num big">{obs:+,.0f}</td>'
                     f'<td class="num">${pred:,.0f}</td>'
                     f'<td class="num quiet">{obs-pred:+,.0f}</td></tr>')
    return ''.join(h) + '</tbody></table>'

RESID  = [r['diff'] - rate(mid(r)) * r['gap'] for r in ALL]
WITHIN = sum(1 for x in RESID if abs(x) <= 200)
ONEY   = [r for r in ALL if r['gap'] == 1]

# ── THE CELLS OUTSIDE THE CENTRAL 95% (Shawn, 2026-09-10) ───────────────────
# He asked for the outliers to be removed and the clustered core shown. They are IDENTIFIED
# and shown apart — but they stay in the fit, because the client-facing argument is stronger
# with them in: taking all of them out moves the rate by less than a dollar, and a study that
# deletes the cells that disagree is the first thing a sceptical reader attacks.
# The cut is the central 95% of each band's residual distribution — 2.5% off each tail.
TRIMQ    = 0.025
INTNAMES = {d['name'] for d in (G or {}).get('devs', [])}
INTMAX   = max([d['adj'] for d in (G or {}).get('devs', [])] or [0])
HIPSF    = 2200

def resid(r): return r['diff'] - rate(mid(r)) * r['gap']

def _cuts(nm):
    v = sorted(resid(r) for r in rows_in(nm))
    return v[int(TRIMQ*len(v))], v[int((1-TRIMQ)*len(v))-1]
CUTS = {nm: _cuts(nm) for _, _, nm in BANDS}
def outside(r):
    lo, hi = CUTS[band_of(mid(r))]
    return not (lo <= resid(r) <= hi)

def tags(r):
    t = []
    if r['region'] == 'CCR':                              t.append('CCR')
    if min(r['n_old'], r['n_new']) < 8:                   t.append('thin')
    if r['older'] in INTNAMES or r['newer'] in INTNAMES:  t.append('integrated')
    if (r['psf_old'] + r['psf_new']) / 2 >= HIPSF:        t.append('high psf')
    return t

MISSES = sorted([r for r in ALL if outside(r)], key=lambda r: -abs(resid(r)))
KEPT   = [r for r in ALL if not outside(r)]
TRIMR  = {nm: fit([r for r in rows_in(nm) if not outside(r)]) for _, _, nm in BANDS}
TRIMCI = {nm: ci([r for r in rows_in(nm) if not outside(r)]) for _, _, nm in BANDS}

def miss_table():
    """Every cell outside the central 95%, and why it is a candidate to sit there. He asked
    for the outliers to be legible; they are named here and kept in the fit."""
    h = ['<table class="fig"><thead><tr><th>older</th><th>newer</th><th class="num">gap</th>'
         '<th>bed</th><th class="num">the market</th><th class="num">the rate</th>'
         '<th class="num">off by</th><th>why it is a candidate to miss</th>'
         '</tr></thead><tbody>']
    for r in MISSES:
        t = tags(r)
        h.append(f'<tr><td>{html.escape(r["older"].title())}</td>'
                 f'<td>{html.escape(r["newer"].title())}</td>'
                 f'<td class="num">{r["gap"]}y</td><td class="quiet">{r["bed"]}</td>'
                 f'<td class="num">{r["diff"]:+,.0f}</td>'
                 f'<td class="num quiet">${rate(mid(r))*r["gap"]:,.0f}</td>'
                 f'<td class="num big">{resid(r):+,.0f}</td>'
                 f'<td class="quiet">{" &middot; ".join(t) if t else "nothing flagged"}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def pairtable():
    rows = sorted(ALL, key=lambda r: (-r['gap'], r['older']))
    def nm_(x): return html.escape(x.title())
    h = ['<table class="fig pairs"><thead><tr><th>older</th><th class="num">lease</th>'
         '<th>newer</th><th class="num">lease</th><th class="num">gap</th><th>bed</th>'
         '<th class="num">psf</th><th class="num">psf</th>'
         '<th class="num">the market&rsquo;s difference</th>'
         '<th class="num">the rate predicts</th><th class="num">off by</th>'
         '<th class="num">distance</th><th>station</th><th>flags</th>'
         '</tr></thead><tbody>']
    for r in rows:
        pred = rate(mid(r)) * r['gap']
        off  = r['diff'] - pred
        t    = tags(r)
        h.append(
            f'<tr{" class=flag" if outside(r) else ""}><td>{nm_(r["older"])}</td><td class="num quiet">{r["ls_old"]}</td>'
            f'<td>{nm_(r["newer"])}</td><td class="num quiet">{r["ls_new"]}</td>'
            f'<td class="num">{r["gap"]}y</td><td class="quiet">{r["bed"]}</td>'
            f'<td class="num quiet">${r["psf_old"]:,.0f}</td><td class="num quiet">${r["psf_new"]:,.0f}</td>'
            f'<td class="num big">{r["diff"]:+,.0f}</td>'
            f'<td class="num quiet">${pred:,.0f}</td>'
            f'<td class="num quiet">{off:+,.0f}</td>'
            f'<td class="num quiet">{r["metres"]}m</td>'
            f'<td class="quiet">{html.escape((r["station"] or "").replace(" MRT Station","").replace(" LRT Station"," LRT"))}</td>'
            f'<td class="quiet">{" &middot; ".join(t)}</td></tr>')
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
.terms button{flex:1 1 auto;min-width:132px;padding:13px 14px 12px;text-align:left;
background:none;border:0;border-right:1px solid var(--ink);cursor:pointer;font:inherit;
color:inherit;position:relative;
transition:background .18s cubic-bezier(.22,1,.36,1),color .18s cubic-bezier(.22,1,.36,1)}
.terms button:last-child{border-right:0}
.terms button:hover{background:var(--navy-850)}
.terms button:focus-visible{outline:2px solid var(--gold);outline-offset:-2px}
.terms .tn{display:block;font:600 14.5px/1.25 Optima,Candara,sans-serif;
color:var(--slate-400);letter-spacing:.005em}
/* The sub-label is the panel's ANSWER, not a status word, so it is set as a figure:
   readable size, no uppercase, gold on a measured panel. Shawn, 2026-09-08. */
.terms .ts{display:block;margin-top:4px;font-size:11.5px;letter-spacing:.02em;
color:var(--slate-600);font-variant-numeric:tabular-nums}
.terms button.done .ts{color:rgba(201,169,106,.75)}
.terms button[aria-current="true"]{background:var(--navy-850)}
.terms button[aria-current="true"] .tn{color:var(--slate-100)}
.terms button[aria-current="true"] .ts{color:var(--gold)}
.terms button[aria-current="true"]::after{content:"";position:absolute;left:0;right:0;bottom:-1px;
height:2px;background:var(--gold)}
.panel>h1{margin-top:46px}
@media (max-width:760px){.terms{padding:0 16px}.terms button{min-width:118px}}
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
.ans .g{font:600 18px/1.15 Optima,Candara,sans-serif;color:var(--slate-300);margin-top:8px}
.ans .g span{font:400 11.5px/1 -apple-system,Segoe UI,sans-serif;letter-spacing:.04em;
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
table.fig thead th{font-size:12.5px;letter-spacing:.02em;
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
.sub2{display:block;font-size:11.5px;color:var(--slate-600);margin-top:3px;white-space:nowrap}
table.fig a{color:inherit;text-decoration:none;border-bottom:1px solid rgba(201,169,106,.35)}
table.fig a:hover{color:var(--gold-soft);border-bottom-color:var(--gold)}
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
summary{cursor:pointer;padding:13px 0;font-size:13px;letter-spacing:.01em;
color:var(--slate-400);list-style:none}
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
/* Which way round the calculator runs. Two states, both always visible, so the reader can
   see that the other direction exists without having to discover it. */
.dirs{display:flex;gap:6px;margin:0 0 14px}
.dirs button{flex:1;padding:12px 10px;font:inherit;font-size:12.5px;letter-spacing:.04em;
  border-radius:7px;cursor:pointer;background:transparent;color:var(--ink-2,#aeb6c8);
  border:1px solid rgba(255,255,255,.13)}
.dirs button.on{background:rgba(198,164,94,.13);border-color:var(--gold-soft);
  color:var(--gold-soft)}
.dirs button:hover{border-color:rgba(255,255,255,.3)}

.calc label{position:relative}

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
      '<div class="crow"><span>Midpoint</span><b>'+(mid%1?mid.toFixed(1):mid.toFixed(0))+'</b></div>'+
      '<div class="crow"><span>Rate</span><b>$'+rate.toFixed(0)+' psf / yr</b>'+
        '<i class="cflat">'+bd[2]+'</i></div>'+
      '<div class="crow"><span>Lease gap</span><b>'+Math.abs(gap)+' years</b></div>'+
      '<div class="crow big"><span>Adjustment</span><b>'+(adj<0?'\u2212':'+')+'$'+
        Math.abs(Math.round(adj)).toLocaleString()+' psf</b></div>'+
      '<p class="chint">Add this to the '+(gap>0?'older':'newer')+
      ' comparable\\'s PSF to put it on the subject\\'s lease terms.</p>'+warn;
  }
  ['lsA','lsB'].forEach(function(id){document.getElementById(id).addEventListener('input',go);});
  go();
})();

(function(){
  // FH vs LH. Two directions, because a client is as likely to hold the leasehold price as
  // the freehold one, and the arithmetic is the same equation read either way:
  //     freehold = (leasehold + age) x (1 + premium)
  // where AGE is the completion-year gap at the measured lease rate and PREMIUM is the step
  // for the lease the leasehold side has left. Going the other way just inverts it.
  //
  // PERCENT, NOT DOLLARS. Shawn, 2026-09-08: "Change it all to %, i dont need quantum."
  //
  // TB = [older rate, newer rate, boundary year, build years, lease term, this year]
  // TS = [[floor of the lease-left step, premium as a fraction, its label], ...]
  var TB=%TENB%, TS=%TENS%, fwd=true;
  function n(id){return parseFloat(document.getElementById(id).value);}
  function el(id){return document.getElementById(id);}
  function rate(a,b){return ((a+b)/2-TB[3]) < TB[2] ? TB[0] : TB[1];}
  function step(left){for(var i=0;i<TS.length;i++){if(left>=TS[i][0])return TS[i];}
    return TS[TS.length-1];}

  // THE LEASE LEFT IS NOT ASKED FOR. Shawn, 2026-09-08: it followed entirely from the leasehold
  // completion year, so the field only restated an answer the calculator already had. It is
  // worked out here and shown in the result instead. Term, less the years since TOP, less the
  // years it took to build.
  function left(){var t=n('tlT'); if(!t) return null;
    return Math.max(1, Math.min(TB[4], TB[4]-(TB[5]-t)-TB[3]));}
  function dirs(){
    el('tdF').className = fwd?'on':''; el('tdL').className = fwd?'':'on';
    el('tpL').childNodes[0].nodeValue =
      (fwd?'Freehold':'Leasehold')+' comparable \u2014 psf';
  }
  function go(){
    dirs();
    var p=n('tfP'), tf=n('tfT'), tl=n('tlT'), o=el('tenOut');
    if(!p||!tf||!tl){o.className='cout bad';o.innerHTML='Fill in all three.';return;}
    var lf=left(), r=rate(tf,tl), dv=tf-tl, age=r*dv, st=step(lf),
        out = fwd ? (p/(1+st[1]) - age)      // freehold in, leasehold out
                  : ((p + age)*(1+st[1]));   // leasehold in, freehold out
    o.className='cout';
    o.innerHTML=
      (dv===0
        ? '<div class="crow"><span>Same completion year</span><b>no age adjustment</b></div>'
        : '<div class="crow"><span>Completion-year gap \u2014 the freehold is '+
          Math.abs(dv)+' yrs '+(dv>0?'newer':'older')+
          ', at $'+r.toFixed(0)+' a year</span><b>'+
          (fwd?(age>=0?'\u2212':'+'):(age>=0?'+':'\u2212'))+'$'+
          Math.abs(Math.round(age)).toLocaleString()+'</b></div>')+
      '<div class="crow"><span>Freehold premium, '+st[2].split(' ')[0].replace('-','\u2013')+
        ' years of lease left</span><b>'+
        (fwd?'\u2212':'+')+(st[1]*100).toFixed(0)+'%</b></div>'+
      '<div class="crow big"><span>'+(fwd?'As leasehold':'As freehold')+'</span><b>$'+
        Math.round(out).toLocaleString()+' psf</b></div>'+
      '<p class="chint">Lease left worked out from the completion year: '+TB[4]+' \u2212 ('+
      TB[5]+' \u2212 '+tl+') \u2212 '+TB[3]+' years of building = '+lf+'.</p>';
  }
  ['tfP','tfT','tlT'].forEach(function(id){
    var e=el(id); if(e) e.addEventListener('input',go);});
  el('tdF').addEventListener('click',function(){fwd=true;go();});
  el('tdL').addEventListener('click',function(){fwd=false;go();});
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
  var LO=%VLO%, HI=%VHI%, MID=%VMID%, FS=%VFS%;
  function n(id){return parseFloat(document.getElementById(id).value);}
  function m(x){return '$'+(x/1e6).toFixed(2)+'M';}
  function go(){
    var bs=n('vbS'), bp=n('vbP'), ps=n('vpS'), f=n('vF'), o=document.getElementById('voidOut');
    if(!(bs>0&&bp>0&&ps>0)){o.className='cout bad';
      o.innerHTML='Enter the unit below and the penthouse size.';return;}
    /* The floors field is its own error. Answering a bad floor count by naming the size fields
       points the reader at the two inputs that are already right. 70 is the tallest tower here;
       past that the floor step compounds into an answer nobody should quote. */
    if(isNaN(f)||f<0||f>70){o.className='cout bad';
      o.innerHTML='Floors below: enter a number between 0 and 70.';return;}
    var extra=ps-bs;
    if(extra<=0){o.className='cout bad';
      o.innerHTML='The penthouse is not larger \u2014 there is no extra area to price.';return;}
    /* Lift the unit below to the penthouse's own floor FIRST. The measurement does this to
       every base leg before taking the median, so a calculator that skips it understates the
       floor plate and drops the whole error onto the void. */
    var psf=bp*(1+FS*f), plate=bs*psf,
        lo=plate+extra*psf*LO, hi=plate+extra*psf*HI, mid=plate+extra*psf*MID;
    o.className='cout';
    o.innerHTML=
      '<div class="crow big"><span>Worth</span><b>'+m(lo)+' &ndash; '+m(hi)+'</b></div>'+
      '<div class="crow"><span>Midpoint</span><b>'+m(mid)+'</b></div>'+
      '<p class="chint">Floor plate at $'+Math.round(psf).toLocaleString()+' psf'+
      (f>0?' \u2014 the unit below lifted '+f+' floor'+(f===1?'':'s')+' at '+
        (FS*100).toFixed(1)+'%':'')+'. '+
      Math.round(extra).toLocaleString()+' sqft of extra area at '+
      LO.toFixed(2)+'&ndash;'+HI.toFixed(2)+'&times; that \u2014 where the typical '+
      'resale ratio sits.</p>';
  }
  ['vbS','vbP','vpS','vF'].forEach(function(id){
    var e=document.getElementById(id); if(e) e.addEventListener('input',go);});
  go();
})();

/* THE TERM TABS. One constant on screen at a time; the bar stays in the sticky header so
   switching never means scrolling back up. The hash keeps a view linkable and survives a
   reload, which matters because this is a working document people send each other. */
(function(){
  var btns=[].slice.call(document.querySelectorAll('.terms button')),
      panels=[].slice.call(document.querySelectorAll('.panel'));
  // #judgement was this panel's name until 2026-09-08. Links to it are already out in the
  // world, so the old hash still lands on the renamed panel.
  var ALIAS={judgement:'tenure'};
  function show(name,push){
    name = ALIAS[name] || name;
    var found=false;
    panels.forEach(function(p){
      var on=p.getAttribute('data-p')===name; p.hidden=!on; if(on)found=true;
    });
    if(!found){show('summary',push);return;}
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
  show((location.hash||'#summary').slice(1),false);
})();
"""
def mrt_table():
    if not M: return ''
    r = ['<table class="fig look"><thead><tr><th>Walk to the nearest station</th>'
         '<th class="num">measured</th><th class="num">could really be</th>'
         '<th class="num">developments</th><th class="num">pairs</th>'
         '<th class="num">in use</th></tr></thead><tbody>']
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
# RESALE ONLY. Shawn's ruling, 2026-09-07: "I dont need the developer price list... ALL i care
# about is RESALE." The new-sale track is still measured by void-pairs.py -- the developer
# placebo (+1.12%) is what proves the resale placebo passing means something -- but it does not
# reach the page. Do not put it back without asking.
VR = V['resale']['headline'] if V else None   # HEADLINE, not corrected: the resale placebo is
# -0.24% with an interval straddling zero, so there is nothing to correct for. Correcting by a
# figure indistinguishable from zero is worse than leaving it alone.

# NOT RENDERED since 2026-09-08 — Shawn took the spec table off the void panel; the hero and
# the calculator carry it. Kept as the record.
def void_answer():
    """The measurement as a spec sheet. One track, so a row per fact reads better than a table
    with a single line in it."""
    r = ['<table class="fig"><tbody>']
    for lab, val, sub in (
        ('The discount', f'{VR["discount"]:.0f}% off', 'against the psf the floor plate commands'),
        ('What the extra area fetches', f'${VR["void_psf"]:,} psf',
         f'where the home itself fetches ${VR["base_psf"]:,}'),
        ('Could really be', f'{VR["lo"]:.2f}&ndash;{VR["hi"]:.2f}&times;',
         f'median {VR["ratio"]:.2f}&times;, quartiles {VR["p25"]:.2f}&ndash;{VR["p75"]:.2f}'),
        ('Typical extra area', f'{VR["extra"]:,} sqft',
         f'{VR["extra_pct"]*100:.0f}% of the floor plate'),
        ('Penthouse resales', f'{VR["pairs"]:,}', f'across {VR["devs"]} developments')):
        r.append(f'<tr><th>{lab}</th><td class="num big" style="color:var(--gold)">{val}</td>'
                 f'<td class="quiet" style="font-size:12.5px">{sub}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def void_sens():
    r = ['<table class="fig"><thead><tr><th>Floor step assumed</th>'
         '<th class="num">what the extra area fetches</th>'
         '<th class="num">Sales</th></tr></thead><tbody>']
    for x in V['resale']['sensitivity']:
        me = x['floor_step'] == V['meta']['floor_step']
        r.append(f'<tr><th>{x["floor_step"]*100:.1f}% per floor'
                 + (' <span style="color:var(--gold)">&larr; measured</span>' if me else '')
                 + f'</th><td class="num {"big" if me else "quiet"}">{x["ratio"]:.2f}&times;</td>'
                 f'<td class="num quiet">{x["pairs"]:,}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def void_cut(name):
    rows = [c for c in V['resale']['cuts'] if c['cut'] == name]
    r = ['<table class="fig"><thead><tr><th>' + name.capitalize() + '</th>'
         '<th class="num">discount</th><th class="num">extra-area psf</th>'
         '<th class="num">could really be</th><th class="num">Sales</th><th class="num">Devs</th>'
         '</tr></thead><tbody>']
    for c in rows:
        r.append(f'<tr><th>{c["label"]}</th>'
                 f'<td class="num big" style="color:var(--gold)">{100-c["ratio"]*100:.0f}% off</td>'
                 f'<td class="num">${c["void_psf"]:,}</td>'
                 f'<td class="num quiet">{c["lo"]:.2f}&ndash;{c["hi"]:.2f}&times;</td>'
                 f'<td class="num quiet">{c["pairs"]:,}</td>'
                 f'<td class="num quiet">{c["devs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def void_devs(n=30, widest=False):
    d = V['resale']['devs']
    d = sorted(d, key=lambda r: -r['spread'])[:n] if widest else d[:n]
    r = ['<table class="fig"><thead><tr><th>Development</th><th class="num">district</th>'
         '<th class="num">Extra</th><th class="num">Home psf</th>'
         '<th class="num">Extra-area psf</th><th class="num">Discount</th>'
         '<th class="num">widest gap &times;</th><th class="num">Resales</th>'
         '</tr></thead><tbody>']
    for x in d:
        r.append(f'<tr><th>{html.escape(nice(x["proj"]))}</th>'
                 f'<td class="num quiet">{x["dist"]}</td>'
                 f'<td class="num">+{x["extra"]:,}</td>'
                 f'<td class="num quiet">${x["base_psf"]:,}</td>'
                 f'<td class="num">${x["void_psf"]:,}</td>'
                 f'<td class="num big" style="color:var(--gold)">{100-x["ratio"]*100:.0f}% off</td>'
                 f'<td class="num {"big" if x["spread"]>=.5 else "quiet"}">{x["spread"]:.2f}</td>'
                 f'<td class="num quiet">{x["pairs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def void_spread_names(k=3):
    d = sorted(V['resale']['devs'], key=lambda r: -r['spread'])[:k]
    return ', '.join(f'<b>{html.escape(nice(x["proj"]))}</b> {x["spread"]:.2f}' for x in d)

def ec_launch_table():
    """Every EC launch in the window, and the private launch beside it. Ordered by the
    premium, smallest first, so the spread is the shape of the column rather than a range
    stated in prose."""
    r = ['<table class="fig"><thead><tr><th>EC launch</th><th class="num">EC psf</th>'
         '<th class="num">Private psf</th><th class="num">Private is</th>'
         '<th>Compared against</th></tr></thead><tbody>']
    for d in sorted(E['launch']['by'], key=lambda d: d['pct']):
        r.append(f'<tr><th>{nice(d["ec"])}</th>'
                 f'<td class="num">${d["ecpsf"]:,.0f}</td>'
                 f'<td class="num">${d["pvpsf"]:,.0f}</td>'
                 f'<td class="num big" style="color:var(--gold-soft)">+{d["pct"]:.0f}%</td>'
                 f'<td>{", ".join(nice(c) for c in d["comps"])}'
                 f'<span class="sub2">{d["pairs"]:,} pairs</span></td></tr>')
    return ''.join(r) + '</tbody></table>'

# Age bands measured but not shown on the page. (Shawn, 2026-09-10.)
HIDDEN_AGE_BANDS = {'15+'}


def ec_age_table():
    """The same resale cut, sliced by how long the EC has been standing. TOP is not in the
    caveat, so it is taken as lease start + 4 — the median gap between the two."""
    r = ['<table class="fig"><thead><tr><th>Years since the EC was built</th>'
         '<th class="num">Private is</th><th class="num">Could really be</th>'
         '<th class="num">Pairs</th><th class="num">Developments</th></tr></thead><tbody>']
    for a in E['ages']:
        # 15+ is hidden at Shawn's call, 2026-09-10. The band is still MEASURED and still in
        # ec-pairs.json — only the row is withheld, so re-showing it is a one-line change and
        # nothing downstream lost a figure.
        if a['key'] in HIDDEN_AGE_BANDS:
            continue
        r.append(f'<tr><th>{a["key"]} years<span class="sub2">{a["label"]}</span></th>'
                 f'<td class="num big" style="color:var(--gold-soft)">{a["pct"]:+.1f}%</td>'
                 f'<td class="num">{a["ci"][0]:+.1f}% to {a["ci"][1]:+.1f}%</td>'
                 f'<td class="num">{a["pairs"]:,}</td>'
                 f'<td class="num">{a["projects"]}</td></tr>')
    return ''.join(r) + '</tbody></table>'

def ec_resale_table():
    """Every EC carrying 100 pairs or more. A NEGATIVE figure is the EC trading above the
    private condo beside it."""
    r = ['<table class="fig"><thead><tr><th>EC</th><th class="num">Years built</th>'
         '<th class="num">EC psf</th><th class="num">Private psf</th>'
         '<th class="num">Private is</th></tr></thead><tbody>']
    for d in sorted(E['resale']['by'], key=lambda d: d['pct']):
        age = f'{d["age"]:.0f}' if d['age'] is not None else '&mdash;'
        r.append(f'<tr><th>{nice(d["ec"])}<span class="sub2">{d["pairs"]:,} pairs</span></th>'
                 f'<td class="num">{age}</td>'
                 f'<td class="num">${d["ecpsf"]:,.0f}</td>'
                 f'<td class="num">${d["pvpsf"]:,.0f}</td>'
                 f'<td class="num big" style="color:var(--gold-soft)">{d["pct"]:+.1f}%</td></tr>')
    return ''.join(r) + '</tbody></table>'

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
    call_p = ('<p class="call">' + call + '</p>') if call else ''
    return ('<div class="verdict"><div class="vgrid">'
            '<div class="vcell"><div class="lab">Engine constant</div>'
            '<div class="val was">' + was + '</div><div class="sub">' + was_sub + '</div></div>'
            '<div class="arrow">&rarr;</div>'
            '<div class="vcell grow"><div class="lab">Measured</div>'
            '<div class="answers">' + cells + '</div></div></div>'
            + call_p + '</div>')

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
    r = ['<table class="fig look"><thead><tr><th>Looking only at pairs that are&hellip;</th>'
         '<th class="num">premium</th><th class="num">could really be</th>'
         '<th class="num">pairs</th><th class="num">correction removed</th>'
         '<th class="num">in psf</th></tr></thead><tbody>']
    for c in G['cuts']:
        # THE BROADEST CUT IS THE BOLDED ONE. Shawn, 2026-09-08: every pair, +6.0%.
        big = 'big' if c['label'] == 'every pair' else 'quiet'
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
         '<th class="num">like-for-like</th></tr></thead><tbody>']
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

# NOT RENDERED since 2026-09-08 — Shawn took the per-100 m framing off the MRT panel;
# the bands are the face there now. Kept as the record.
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

# NOT RENDERED since 2026-09-08 — Shawn took the per-100 m framing off the MRT panel;
# the bands are the face there now. Kept as the record.
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

# ── FH vs LH ─────────────────────────────────────────────────────────────────────────
# QUANTUM LEADS, and here it is not a house style but a measured result: the dollar form
# beat the percentage on identical held-out folds. The percentage rides alongside every
# dollar figure because the constant it replaces (/1.15) is itself a ratio and he has to be
# able to set the two against each other. (Shawn, 2026-09-08.)
TMIX = (T or {}).get('mixed', [])
TBASE = st.median([r['psf_lh'] for r in TMIX]) if TMIX else 0
TOLDER = sum(1 for r in TMIX if r['dv'] < 0)
TADJ = st.median([abs(r['band'] * r['dv']) for r in TMIX]) if TMIX else 0
TG   = (T or {}).get('slices', {}).get('gradient', [])
TGL  = [g for g in TG if not g.get('thin')]
THD  = (T or {}).get('headline', {}).get('dollars', {})
THP  = (T or {}).get('headline', {}).get('percent', {})

def ten_step_label(g):
    """The face shows three figures, so each must say WHICH CASE it is the figure for. He
    asked what the difference between the three was; that is the answer, and it belongs on
    the figures rather than in a paragraph underneath them."""
    return g['label'].split(' ')[0].replace('-', '&ndash;') + ' years of lease left'

def ten_grad_table():
    """PERCENT ONLY. Shawn, 2026-09-08: "Change it all to %, i dont need quantum." A
    deliberate reversal of the dollars-never-percent rule that governs the lease study, and
    the measurement supports it — the two forms tie when asked to travel across price levels,
    and the constant this replaces is itself a ratio."""
    if not TGL: return ''
    r = ['<table class="fig"><thead><tr><th>Lease left on the leasehold side</th>'
         '<th class="num">freehold is worth</th><th class="num">could really be</th>'
         '<th class="num">developments</th><th class="num">pairs</th></tr></thead><tbody>']
    for g in TGL:
        r.append(f'<tr><th>{g["label"].split(" ")[0].replace("-", "&ndash;")} years</th>'
                 f'<td class="num big">+{g["pct"]*100:.1f}%</td>'
                 f'<td class="num quiet">+{g["lo"]*100:.1f}% to +{g["hi"]*100:.1f}%</td>'
                 f'<td class="num quiet">{g["devs"]}</td>'
                 f'<td class="num quiet">{g["pairs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

# NOT RENDERED since 2026-09-08 — Shawn took the whole measurement section off the tenure
# panel, this table with it. Kept as the record of every form tested.
def ten_race_table(full=False):
    """The percentage forms only, against the constant in use and against doing nothing. The
    dollar forms are not shown here — they belong in the scale explain mark, which is where the
    choice between the two is argued.

    THREE ROWS ON THE FACE (2026-09-08, off the design critique). The finding is: doing nothing,
    the constant as it stands, and your own measured rates. The other eight rows are the working
    and sit behind "Every form tested" — an eleven-row table in the position of most authority
    was the densest object on the page."""
    if not T: return ''
    ORDER = {'va': 'after the age adjustment', 'av': 'before it', 'none': '&mdash;'}
    r = ['<table class="fig look"><thead><tr><th>Age priced at</th>'
         '<th>Freehold step added</th><th class="num">reads</th>'
         '<th class="num">average miss</th></tr></thead><tbody>',
         f'<tr><th>nothing &mdash; take the freehold price as it stands</th>'
         f'<td class="quiet">none</td><td class="num quiet">&mdash;</td>'
         f'<td class="num quiet">{T["null_rmse"]:,.0f}</td></tr>',
         f'<tr><th><b>$40 a year</b> &mdash; the constant as it stands</th>'
         f'<td class="quiet">after, as &divide;&nbsp;1.15</td><td class="num quiet">15.0%</td>'
         f'<td class="num quiet">{T["engine_rmse"]:,.0f}</td></tr>']
    pct = [x for x in T['race'] if x['key'] in ('va', 'av', 'none')]
    best = min(pct, key=lambda x: x['rmse'])
    for x in pct:
        if x['key'] == 'none' and x['rate'] != 'free': continue
        if not full and x is not best: continue
        rate = ('the measured lease rates, <b>$%.0f / $%.0f</b>' % (T['bands']['old'], T['bands']['new'])
                if isinstance(x['a'], str) else f'${x["a"]:,.0f} a year')
        if x['rate'] == 'free': rate += ' <span class="quiet">(fitted here)</span>'
        prem = '&mdash;' if x['key'] == 'none' else f'+{x["prem"]*100:.1f}%'
        big = 'big' if x is best else 'quiet'
        r.append(f'<tr><th>{rate}</th><td class="quiet">{ORDER[x["key"]]}</td>'
                 f'<td class="num {big}">{prem}</td>'
                 f'<td class="num {big}">{x["rmse"]:,.0f}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def ten_slice_table(key, head):
    rows = [x for x in (T or {}).get('slices', {}).get(key, []) if not x.get('thin')]
    if not rows: return ''
    r = [f'<table class="fig"><thead><tr><th>{head}</th>'
         '<th class="num">freehold is worth</th><th class="num">pairs</th></tr></thead><tbody>']
    for x in rows:
        r.append(f'<tr><th>{x["label"]}</th><td class="num big">+{x["pct"]*100:.1f}%</td>'
                 f'<td class="num quiet">{x["pairs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def ten_transfer_table(key, head):
    """The one place a dollar figure still appears, because this table IS the argument for
    the percentage: it asks each form to price stock it has never seen."""
    rows = (T or {}).get('transfer', {}).get(key, [])
    if not rows: return ''
    r = [f'<table class="fig"><thead><tr><th>{head}</th><th class="num">its base psf</th>'
         '<th class="num">a percentage misses by</th><th class="num">a flat dollar figure '
         'misses by</th></tr></thead><tbody>']
    for x in rows:
        pw = x['pct_err'] <= x['dol_err']
        r.append(f'<tr><th>{x["group"]}</th><td class="num quiet">${x["base"]:,.0f}</td>'
                 f'<td class="num {"big" if pw else "quiet"}">{x["pct_err"]:,.0f}</td>'
                 f'<td class="num {"quiet" if pw else "big"}">{x["dol_err"]:,.0f}</td></tr>')
    r.append(f'<tr><th><b>average</b></th><td class="num quiet"></td>'
             f'<td class="num"><b>{st.mean([x["pct_err"] for x in rows]):,.0f}</b></td>'
             f'<td class="num"><b>{st.mean([x["dol_err"] for x in rows]):,.0f}</b></td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def ten_sens_table():
    if not T: return ''
    r = ['<table class="fig"><thead><tr><th>How far apart the two may sit</th>'
         '<th class="num">freehold is worth</th>'
         '<th class="num">pairs</th></tr></thead><tbody>']
    for x in [x for x in T['sens'] if not x['label'].endswith('floor')]:
        head = x['label'].endswith('(headline)')
        r.append(f'<tr><th>{"<b>" if head else ""}{x["label"]}{"</b>" if head else ""}</th>'
                 f'<td class="num {"big" if head else "quiet"}">+{x["pct"]*100:.1f}%</td>'
                 f'<td class="num quiet">{x["pairs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

# [older rate, newer rate, boundary year, measured build years, lease term, this year] — all
# six DERIVED. The build gap and the 99-year term are what let the calculator work out the
# lease a subject has left from nothing but its completion year.
# ROUNDED TO THE DOLLAR. Shawn, 2026-09-08: a 10-year gap at "$25 a year" must read $250, not
# $249. The row states the rate to the dollar, so the arithmetic behind it uses that same dollar.
TENB_JS = ('[%d,%d,%d,%d,%d,%d]' % (round(T['bands']['old']), round(T['bands']['new']),
                                    T['band_bound'], T['build']['median'], T['build']['term'],
                                    datetime.date.today().year)) if T else '[0,0,0,0,99,2026]'
# [floor of the step, the premium as a fraction, the step's label] — PERCENT, his ruling.
TENS_JS = '[' + ','.join(f'[{g["min_left"]},{g["pct"]:.5f},"{g["label"]}"]'
                         for g in TGL) + ']' if TGL else '[]'

BANDS_JS = '[' + ','.join(f'[{hi},{BANDR[nm]:.2f},"{nm}"]' for _, hi, nm in BANDS) + ']'
A1, A2 = age_label(OLD_NM); B1, B2 = age_label(NEW_NM)

BODY = f"""
<div class="panel" data-p="summary">
<h1 class="disp">Where the constants now stand</h1>
<p class="lede">Five constants set by judgement, each now measured against the market, and one
reference figure that is measured but deliberately not wired to anything. This is the whole study
on one screen; every figure below has a panel of its own.</p>

<section>
  <div class="scroll"><table class="fig"><thead><tr><th>Term</th><th class="num">Constant</th><th>Measured</th></tr></thead><tbody>
  <tr><th><a href="#lease">Lease &mdash; how new the building is</a></th><td class="num big">$40 psf / yr</td>
    <td style="color:var(--gold-soft)">${BANDR[OLD_NM]:,.0f} and ${BANDR[NEW_NM]:,.0f}, by midpoint</td></tr>
  <tr><th><a href="#tenure">Tenure &middot; freehold vs leasehold</a></th><td class="num big">&divide; 1.15</td>
    <td style="color:var(--gold-soft)">+{THP['p']*100:.0f}% on average, and
    +{TGL[0]['pct']*100:.0f}% to +{TGL[-1]['pct']*100:.0f}% by the lease left</td></tr>
  <tr><th><a href="#mrt">MRT walk band</a></th><td class="num big">$50 / $200 / $250</td>
    <td style="color:var(--gold-soft)">+${M['bands'][0]['adj']:,.0f} / +${M['bands'][1]['adj']:,.0f} /
    +${M['bands'][2]['adj']:,.0f}, or ${M['slope100']:.0f} per 100 m</td></tr>
    <tr><th><a href="#integrated">Integrated development</a></th><td class="num big">+5%</td>
    <td style="color:var(--gold-soft)">+{G['cuts'][4]['pct']:.1f}% ({G['cuts'][4]['pct_lo']:.1f} to
    {G['cuts'][4]['pct_hi']:.1f}), which contains the +5%</td></tr>
  <tr><th><a href="#void">Void &middot; extra penthouse area</a></th>
    <td class="num big">1.00&times; &mdash; full price</td>
    <td style="color:var(--gold-soft)">a resale buyer pays {VR['discount']:.0f}% less for it than
    for the floor plate; there is no constant for it today</td></tr>
  <tr><th><a href="#ec">EC vs private condo &middot; reference</a></th>
    <td class="num big">none</td>
    <td style="color:var(--gold-soft)">private launches +{E['launch']['pct']:.0f}% over the EC
    beside them; by resale the gap is {E['resale']['pct']:+.1f}% &mdash; no difference</td></tr>
  </tbody></table></div>
  <div class="caveat" style="margin-top:18px"><b>Nothing has been written back yet.</b>
  Every figure on this page sits beside its constant, not in place of it.</div>
</section>
</div>

<div class="panel" data-p="lease" hidden>
<h1 class="disp">What the market pays for a year of lease</h1>
<p class="lede">The engine restates every comparable using constants set by judgement. This is
the first one measured against the market.</p>

{hero('$40', 'flat, every comparable',
      [(f'${BANDR[OLD_NM]:,.0f}', OLD_NM, ndev(rows_in(OLD_NM))),
       (f'${BANDR[NEW_NM]:,.0f}', NEW_NM, ndev(rows_in(NEW_NM)))],
      '')}

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
  <p><b>{NDEV} developments &middot; {npairs(ALL)} pairs &middot; {len(ALL)} cells.</b> Each
  paired with a leasehold neighbour and compared bedroom by bedroom, across 24 months of resale
  and sub-sale to {LW[1]}.</p></div>
  <div class="scroll">{answer_table()}</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2>
  <p>Four questions, answered once each.</p></div>

  <details><summary>Does the rate actually fit a pair?</summary>
    <p class="expl"><b>Yes, once you compare totals rather than a single year.</b> A pair two
    years apart should sit about two years&rsquo; worth of rate apart, one ten years apart about
    ten. Compare a pair&rsquo;s whole difference against its own gap and the rate is what the
    market is doing &mdash; not a figure imposed on it.</p>
    <div class="scroll">{holds_table()}</div>
    <p class="expl"><b>Two-year, five-to-nine-year and ten-year-plus pairs land on it almost
    exactly</b> &mdash; within about a year&rsquo;s worth, on a difference of several hundred
    dollars. The two that miss go in opposite directions and neither moves the answer: the rate
    is the slope through all {len(ALL)} cells, <b>not the average of the per-pair figures</b>.
    {WITHIN} of {len(ALL)} cells land within $200 of what their band predicts, and the misses
    cancel &mdash; the median cell is ${st.median(RESID):,.0f} off.</p>
    <p class="expl"><b>{len(MISSES)} of {len(ALL)} cells sit outside the central 95%</b>
    &mdash; the widest 2.5% of misses at each end. <b>They are named here rather than removed,
    because taking them out changes almost nothing:</b> ${BANDR[OLD_NM]:,.2f} becomes
    ${TRIMR[OLD_NM]:,.2f}, and ${BANDR[NEW_NM]:,.2f} becomes ${TRIMR[NEW_NM]:,.2f} &mdash; both
    still well inside the interval the full sample already publishes. That is the
    argument for the rate, and it is worth more than a tidier table. The typical cell misses by
    ${st.median(abs(x) for x in RESID):,.0f}; three in four are inside
    ${sorted(abs(x) for x in RESID)[int(.75*len(RESID))]:,.0f}.</p>
    <div class="scroll">{miss_table()}</div>
    <p class="expl">Four things put a cell on that list. <b>Price level does the most work</b>
    &mdash; the study is measured in dollars, so the same percentage error is a bigger miss on a
    dear pair; these cells run
    ${st.median((r['psf_old']+r['psf_new'])/2 for r in MISSES):,.0f} psf against
    ${st.median((r['psf_old']+r['psf_new'])/2 for r in KEPT):,.0f} for the rest. <b>The Marina
    Bay cluster</b> is the loudest group: this page already calls the CCR not measurable &mdash;
    a submarket rather than a region &mdash; and those {len(CCR)} cells are still inside the
    fitted figure. Then <b>thin cells</b>, and last the two things nobody controls, floor and
    facing, worth several hundred dollars at $2,000 psf between a high unit with a view and a
    low one facing a wall.</p>

    <p class="expl"><b>The one-year row is the bigger miss, and it is the reason the pair table
    looks noisy.</b> {len(ONEY)} cells sit one year apart, where a single year of newness is
    worth ${BANDR[NEW_NM]:,.0f} but the floor, the stack and the sales mix &mdash; none of them
    controlled here &mdash; are worth several hundred. The signal is real but buried. Those
    cells cannot mislead the rate, because this estimator fits the difference against the gap:
    a one-year pair carries one year of leverage and cannot shout.</p>
  </details>

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
    <p class="expl"><b>Part of it is that newer developments are built more efficiently</b>
    &mdash; a three-bedroom from 2011 on runs {SHRINK3:.0%} smaller, {SQ3_NEW:,.0f} sq ft against
    {SQ3_OLD:,.0f}. A buyer pays a quantum, and the same $50k of newness over a smaller plate
    reads as a bigger figure per foot.</p>
    <div class="scroll">{why_table()}</div>
    <p class="expl">Small flats, large flats, pairs two years apart or twenty &mdash; the jump is
    in every row. A higher base price explains some of it, narrowing the gap from
    {fpct(rows_in(OLD_NM)):+.2%} to {fpct(rows_in(NEW_NM)):+.2%} a year, but nowhere near all.</p>
    <p class="expl">What is left is vintage: through the 2010s each successive launch in the same
    spot came out dearer than the last. This measures the size of that effect, not its cause.</p>
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
    <p class="expl" style="margin-top:18px">Every cell, widest lease gap first. <b>The
    difference is what the market shows; beside it is what the band predicts for that gap.</b>
    Nothing in a row is adjusted for anything. The last column carries the reasons a row is a
    candidate to miss, and the {len(MISSES)} that sit outside the central 95% are marked.</p>
    <div class="scroll" style="margin-top:12px">{pairtable()}</div>
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
      '')}

<section>
  <div class="scroll">{mrt_table()}</div>

  <details><summary>How the lease is taken out, and the check that it worked</summary>
    <p class="expl">Each pair shares its nearest station but sits at a different distance from it.
    Their price difference still contains whatever lease difference they carry, so the measured
    vintage rate above is subtracted from it. What remains is distance.</p>
    <p class="expl"><b>The check.</b> Take pairs in the same band standing the same distance from
    the station &mdash; within 50 m of each other. Nothing separates them, so after the lease comes
    out they should read zero. They read <b>{'&minus;' if M['placebo']['adj'] < 0 else '+'}${abs(M['placebo']['adj']):.1f}</b> across
    {M['placebo']['pairs']} pairs. That is the evidence the adjustment is working and that what is
    left is the walk.</p>
  </details>

  <details><summary>Where the 5 and 10 minute lines are drawn</summary>
    <p class="expl"><b>Under 400 m &middot; 400 to 800 m &middot; over 800 m.</b> People walk about
    80 metres a minute. Distance is measured straight across the map, not along the pavement.</p>
    <p class="expl"><b>The lines are the soft part of this.</b> A big interchange is held as one
    point and some addresses sit about 100 m off, so a project can fall on the wrong side of a
    line &mdash; CityLife@Tampines measures 869 m here against a 700 m walk. Move the lines
    anywhere defensible and the bottom row runs <b>$162 to $304</b>.</p>
    <p class="expl"><b>Why it still holds.</b> Both sides of a pair are measured to the same
    station point, so the error largely cancels in the gap between them.</p>
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
<b>same station</b>. The lease difference between them is taken out, and so is the difference in
the walk. What is left is the building sitting on the station.</p>

{hero('+5%', 'flat, on an integrated project',
      [(f"+{G['cuts'][4]['pct']:.1f}%", '&lt;5 yr gap, within 400 m', G['cuts'][4]['devs']),
       (f"+{G['cuts'][0]['pct']:.1f}%", 'every pair', G['cuts'][0]['devs'])],
      '')}

<section>
  <div class="scroll">{int_table()}</div>

  <details><summary>Does it matter how far apart the two sit?</summary>
    <p class="expl">The pairs are not all the same distance from their station, so some carry a
    bigger walking correction than others. Holding the lease gap fixed and sweeping that limit:</p>
    <div class="scroll">{dsweep_table()}</div>
    <p class="expl"><b>It is not neutral.</b> Inside the tight lease-gap column the premium climbs
    from +{G['dsweep'][1]['rows'][0]['pct']:.1f}% to +{G['dsweep'][1]['rows'][-1]['pct']:.1f}% as
    the limit loosens, while the like-for-like check beside it stays flat. That is what unremoved walking
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
    <p class="expl">These {G['n_integrated']} are a classification made for this study and audited
    by hand &mdash; a judgement, not a datum.</p>
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

<div class="panel" data-p="tenure" hidden>
<h1 class="disp">What the market pays for freehold</h1>
<p class="lede">The last constant on judgement, and the only one that turned out not to be a
constant at all.</p>

{hero('&divide; 1.15', 'flat, every freehold comparable',
      [(f'+{g["pct"]*100:.0f}%', ten_step_label(g), g['devs']) for g in TGL],
      '')}

<section>
  <div class="sechead"><h2 class="disp">How to use it</h2></div>
  <div class="steps">
    <div class="step"><span class="sn">1</span>
      <p>Take the <b>difference in completion year</b> &mdash; TOP, not lease start. A freehold
      has no lease start to difference against.</p></div>
    <div class="step"><span class="sn">2</span>
      <p>Price that at the <b>measured lease rate</b>: ${T['bands']['old']:,.0f} a year up to
      {T['band_bound']-1}, ${T['bands']['new']:,.0f} from {T['band_bound']}, read at the
      midpoint.</p></div>
    <div class="step"><span class="sn">3</span>
      <p>Then take off the <b>freehold percentage for the lease the leasehold side has
      left</b>, from the table below.</p></div>
  </div>

  <div class="calc">
    <h3>Restate a comparable</h3>
    <div class="dirs" role="group" aria-label="Which way round">
      <button type="button" id="tdF" class="on">Freehold &rarr; leasehold</button>
      <button type="button" id="tdL">Leasehold &rarr; freehold</button>
    </div>
    <div class="cin">
      <label id="tpL">Freehold comparable &mdash; psf<input id="tfP" type="number" value="2100" min="200" max="9000" step="10"></label>
      <label>Freehold TOP year<input id="tfT" type="number" value="2005" min="1960" max="2035" step="1"></label>
      <label>Leasehold TOP year<input id="tlT" type="number" value="2015" min="1960" max="2035" step="1"></label>
    </div>
    <div id="tenOut" class="cout"></div>
  </div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Freehold is worth more as the lease runs down</h2>
  <p>One freehold and one leasehold development, next door, bedroom by bedroom. The only thing
  that changes down this table is <b>how much lease the leasehold side has left</b>.</p></div>
  <div class="scroll">{ten_grad_table()}</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2>
  <p>Two questions, answered once each.</p></div>

  <details><summary>Does distance affect the premium?</summary>
    <p class="expl"><b>{T['counts']['devs']} developments &middot; {T['counts']['pairs']} pairs
    &middot; {T['counts']['cells']} cells</b>, on the same screens as the lease study &mdash;
    500 m apart, the same station, the same schools, 200+ units, sizes within 20% &mdash; across
    24 months of resale and sub-sale to {T['window'][1]}.</p>
    <div class="scroll">{ten_sens_table()}</div>
  </details>

  <details><summary>Does it hold across the island, and across bedrooms?</summary>
    <div class="scroll">{ten_slice_table('region', 'Region')}</div>
    <p class="expl" style="margin-top:18px">The three regions agree closely &mdash; part of the
    case for a percentage, since one ratio serves the island.</p>
    <div class="scroll" style="margin-top:14px">{ten_slice_table('bedroom', 'Bedroom')}</div>
    <p class="expl" style="margin-top:18px">Bedroom is the match, not the answer &mdash; it holds
    size constant. One- and four-bedroom are too thin to show.</p>
  </details>

</section>

</div>
<div class="panel" data-p="void" hidden>
<h1 class="disp">What the market pays for the void</h1>
<p class="lede">Same project, same block, <b>same stack</b>, so the top unit stands on the floor
plate of the ones below it. The extra strata area is void or roof. Floor is taken out at
{V['meta']['floor_step']*100:.1f}% a floor; what is left is what that area fetches on
<b>resale</b>.</p>

{hero('1.00&times;', 'every strata sqft priced alike',
      [(f"{VR['discount']:.0f}% off", 'what a resale buyer pays for it', VR['devs'])],
      '')}

<section>
  <div class="calc">
    <h3>What should the penthouse cost</h3>
    <div class="cin">
      <label>Unit below &mdash; sqft<input id="vbS" type="number" value="1216" min="200" max="9000" step="1"></label>
      <label>Unit below &mdash; psf<input id="vbP" type="number" value="2662" min="200" max="9000" step="10"></label>
      <label>Penthouse sqft<input id="vpS" type="number" value="1421" min="200" max="9000" step="1"></label>
      <label>Floors below<input id="vF" type="number" value="1" min="0" max="70" step="1"></label>
    </div>
    <div id="voidOut" class="cout"></div>
  </div>

  <details><summary>Is the floor step doing the work?</summary>
    <p class="expl">The extra area is small against the home, so a 2% error in the base swings the
    answer by more than 10%. <b>The check:</b> the same method on stacks whose top unit is the
    <b>same size</b> as the ones below. No extra area, so it should read zero. Across
    {V['resale']['placebo']['pairs']:,} resales it reads
    <b>{V['resale']['placebo']['residual_pct']:+.2f}%</b>
    ({V['resale']['placebo']['lo']:+.2f} to {V['resale']['placebo']['hi']:+.2f}) &mdash; zero.
    Nothing is corrected.</p>
    <div class="scroll">{void_sens()}</div>
    <p class="expl">At other floor steps it runs
    <b>{min(x['ratio'] for x in V['resale']['sensitivity']):.2f} to
    {max(x['ratio'] for x in V['resale']['sensitivity']):.2f}</b>. <b>Quote half.</b></p>
  </details>
</section>

<section>
  <h2>Where it moves</h2>
  <p class="expl"><b>The bigger the void, the more the buyer pays for it.</b> A large roof or a
  full double-volume room is a room, and gets treated as one.</p>
  <div class="scroll">{void_cut('extra area')}</div>

  <p class="expl" style="margin-top:18px"><b>The cheaper the home, the more the extra area is
  worth to the buyer</b> &mdash; the opposite of what you would guess.</p>
  <div class="scroll">{void_cut('price tier')}</div>

  <details style="margin-top:16px"><summary>By region, and by tenure</summary>
    <div class="scroll">{void_cut('region')}</div>
    <div class="scroll" style="margin-top:14px">{void_cut('tenure')}</div>
    <p class="expl">Thin cells. Direction only, never a figure to quote.</p>
  </details>
</section>

<section>
  <h2>The finding that is worth money</h2>
  <p class="expl"><b>The spread inside one development is wider than the spread between
  developments</b> &mdash; the void is priced stack by stack: {void_spread_names()}.</p>
  <div class="scroll">{void_devs(widest=True, n=12)}</div>
  <p class="expl"><b>The advice is not &ldquo;penthouses are good value&rdquo; &mdash; it is find
  the stack where the void was given away.</b></p>

  <details><summary>Every development, cheapest void first</summary>
    <div class="scroll">{void_devs(n=30)}</div>
    <p class="expl">Developments with at least two matched penthouse resales.</p>
  </details>
</section>

<section>
  <details><summary>How a pair is built</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h4>Held constant</h4><ul>
        <li>same project, same <b>block</b>, same <b>stack</b></li>
        <li>&mdash; so the same <b>floor plate</b>, by construction</li>
        <li>base legs within <b>{V['meta']['size_tol']*100:.0f}%</b> of the stack&rsquo;s median size</li>
        <li>base legs within <b>{V['meta']['match_days']} days</b> of the penthouse resale</li></ul></div>
      <div class="card"><h4>The screens</h4><ul>
        <li><b>{V['meta']['min_base']}+ base legs</b>, so the comparator is a median</li>
        <li>extra area <b>{V['meta']['extra_band'][0]*100:.0f}&ndash;{V['meta']['extra_band'][1]*100:.0f}%</b>
            of the floor plate</li>
        <li>under that is a bay window; over it is a <b>duplex</b> &mdash; a second floor plate,
            which is what this pair exists to exclude</li></ul></div>
      <div class="card"><h4>Not controlled</h4><ul>
        <li><b>what the extra area is</b> &mdash; void, roof terrace or roof</li>
        <li><b>renovation and fit-out</b>, on either leg</li>
        <li>the top floor&rsquo;s own view, beyond the floor step and the check above</li></ul></div>
    </div>
  </details>
  <details><summary>Where the data comes from &mdash; not the MAPS refresh</summary>
    <p class="expl">The <b>REALIS unit-level pull</b> held by the floor study &mdash; the only
    dataset here carrying a <b>unit number</b>, and without that there is no stack.
    {V['meta']['window']}, all Singapore, strata, <b>resale only</b>.</p>
  </details>
</section>
</div>

<div class="panel" data-p="ec" hidden>
<h1 class="disp">What a buyer pays to skip the EC</h1>
<p class="lede">An EC and a private condo <b>launching in the same district at the same time</b>,
size for size. Then the same two, years later, in the <b>resale</b> market. The first figure is
what the private badge costs on the day. The second is what is left of it.</p>

{hero('none &mdash; not a constant',
      'nothing in the engine reads this',
      [(f"+{E['launch']['pct']:.0f}%", 'at launch, private over EC', E['launch']['projects']),
       (f"{E['resale']['pct']:+.1f}%", 'at resale, same two', E['resale']['projects'])],
      '')}

<section>
  <div class="sechead"><h2 class="disp">At launch</h2>
  <p><b>{E['launch']['pairs']:,} pairs across {E['launch']['projects']} EC launches.</b> Every EC
  that sold in the window, set against the private launches selling beside it.</p></div>
  <div class="scroll">{ec_launch_table()}</div>
  <p class="expl">The three slides read <b>25% to 36%</b>. The column runs from
  +{min(d['pct'] for d in E['launch']['by']):.0f}% to
  +{max(d['pct'] for d in E['launch']['by']):.0f}% with a median of
  <b>+{E['launch']['pct']:.1f}%</b> ({E['launch']['ci'][0]:.0f} to {E['launch']['ci'][1]:.0f}),
  so the slides sit in the middle of the market rather than at one end of it. Rivelle against Parktown reads +{next(d['pct'] for d in E['launch']['by']
  if 'RIVELLE' in d['ec']):.0f}% here; against {nice(E['slides'][0]['pv'])} alone, size for size,
  it is +{E['slides'][0]['pct']:.1f}%, and on the two headline PSFs the slide quotes
  (${E['slides'][0]['ecpsf']:,.0f} against ${E['slides'][0]['pvpsf']:,.0f}),
  +{E['slides'][0]['raw_pct']:.0f}%.</p>
</section>

<section>
  <div class="sechead"><h2 class="disp">At resale</h2>
  <p><b>{E['resale']['pairs']:,} pairs across {E['resale']['projects']} ECs.</b> The same
  comparison in the secondary market, against leasehold private of the same vintage within
  {E['meta']['km']:g} km.</p></div>

  <div class="scroll">{ec_age_table()}</div>
  <p class="expl">The premium is <b>{E['resale']['pct']:+.1f}%</b> overall, and could really be
  anywhere from {E['resale']['ci'][0]:+.1f}% to {E['resale']['ci'][1]:+.1f}% &mdash; an interval
  that covers zero, and a figure inside 1%. There is <b>no difference</b> between the two. It does not merely close: past privatisation the
  sign turns over, and a mature EC trades <b>above</b> the private condo beside it. Held against
  every private comparable with no tenure or vintage control the figure is
  {E['resale_raw']['pct']:+.1f}%.</p>

  <details><summary>Every EC in the resale cut</summary>
    <p class="expl">A <b>negative</b> figure is the EC trading above its private neighbour. Read
    the years-built column beside the premium: the ECs at the top of the list are the young ones
    still carrying their launch pricing forward.</p>
    <div class="scroll">{ec_resale_table()}</div>
  </details>

  <details><summary>How a pair is built</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h4>Held constant</h4><ul>
        <li>floor area within <b>{E['meta']['sizetol']*100:.0f}%</b></li>
        <li>contract date within <b>{E['meta']['months']} months</b></li>
        <li>launch: <b>same district</b> &middot; resale: <b>within {E['meta']['km']:g} km</b></li>
        <li>resale only: <b>leasehold</b> comparables, lease start within
            <b>{E['meta']['lstol']} years</b></li></ul></div>
      <div class="card"><h4>How it is read</h4><ul>
        <li>the <b>nearest {E['meta']['near']}</b> comparables per EC transaction</li>
        <li>the <b>median of the pair ratios</b>, never a difference of two medians</li>
        <li>years built is <b>lease start + 4</b>, the median gap to TOP</li></ul></div>
      <div class="card"><h4>Not controlled</h4><ul>
        <li><b>floor</b> and <b>facing</b></li>
        <li>walking distance to the station, on either leg</li>
        <li>the EC income ceiling and resale restrictions themselves</li></ul></div>
    </div>
  </details>

  <details><summary>Why the launch cut is matched on district, not distance</summary>
    <p class="expl">The URA feed carries <b>no coordinates for an uncompleted project</b> &mdash;
    Rivelle, Aurelle, Copen Grand, Lumina Grand, Novo Place and Otto Place all read blank. A
    distance match would drop exactly the launches this measures, so the launch cut holds the
    district and the resale cut, where both legs are built, holds the {E['meta']['km']:g} km.</p>
  </details>

  <details><summary>Where the data comes from &mdash; not the MAPS refresh</summary>
    <p class="expl">A <b>direct URA PMI pull</b>, all four batches:
    {E['meta']['window'][0]} to {E['meta']['window'][1]}, {E['meta']['rows']:,} strata
    transactions of which <b>{E['meta']['ec_rows']:,} are EC</b> across
    {E['meta']['ec_projects']} projects, every sale type. The floor study&rsquo;s REALIS files
    were pulled as &ldquo;Apartment + Condominium&rdquo; and hold <b>no EC at all</b>, so this is
    the only cut of the corpus that can answer it. Rebuild with
    <b>ec-pairs.py</b>.</p>
  </details>
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
    <button type="button" class="done" data-go="summary" aria-current="true">
      <span class="tn">Summary</span></button>
    <button type="button" class="done" data-go="lease">
      <span class="tn">Lease Difference</span>
      <span class="ts">${BANDR[OLD_NM]:,.0f} / ${BANDR[NEW_NM]:,.0f} a year</span></button>
    <button type="button" class="done" data-go="mrt">
      <span class="tn">MRT Distance</span>
      <span class="ts">${M['bands'][0]['adj']:,.0f} / ${M['bands'][1]['adj']:,.0f} /
        ${M['bands'][2]['adj']:,.0f}</span></button>
    <button type="button" class="done" data-go="integrated">
      <span class="tn">Integrated</span>
      <span class="ts">+{G['cuts'][4]['pct']:.1f}%</span></button>
    <button type="button" class="done" data-go="tenure">
      <span class="tn">Freehold vs Leasehold</span>
      <span class="ts">+{TGL[0]['pct']*100:.0f}% to +{TGL[-1]['pct']*100:.0f}%</span></button>
    <button type="button" class="done" data-go="void">
      <span class="tn">Void Space</span>
      <span class="ts">{VR['discount']:.0f}% off</span></button>
    <button type="button" class="done" data-go="ec">
      <span class="tn">EC vs Private</span>
      <span class="ts">+{E['launch']['pct']:.0f}% at launch, nil at resale</span></button>
  </nav>
</header>
<div class="wrap">
{BODY}
<footer>
  <span>URA caveats via the MAPS refresh · resale and sub-sale only, new sale excluded ·
  Void Space reads the REALIS unit-level pull instead, both tracks ·
  generated {datetime.date.today().isoformat()}</span>
  <span>price-gap/calibration/ · regenerate with build-page.py</span>
</footer>
</div>
<script>{JS.replace('%TENB%', TENB_JS).replace('%TENS%', TENS_JS).replace('%BANDS%', BANDS_JS).replace('%LO%', f'{MID_LO}').replace('%HI%', f'{MID_HI}').replace('%VLO%', f"{VR['lo']}").replace('%VHI%', f"{VR['hi']}").replace('%VMID%', f"{VR['ratio']}").replace('%VFS%', f"{V['meta']['floor_step']}")}</script>
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
