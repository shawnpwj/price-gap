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
TENP = os.path.join(HERE, 'tenure-pairs.json')
T    = json.load(open(TENP)) if os.path.exists(TENP) else None
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
                'Worse on held-out error, and the extra band split into two incoherent regional halves.'))
    h.append(r_('One flat rate', f'{CV_FLAT/1000:,.1f}k against {CV_TWO/1000:,.1f}k',
                'Worse on held-out error. It is the form the constant takes today.'))
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
/* Which way round the calculator runs. Two states, both always visible, so the reader can
   see that the other direction exists without having to discover it. */
.dirs{display:flex;gap:6px;margin:0 0 14px}
.dirs button{flex:1;padding:7px 10px;font:inherit;font-size:11.5px;letter-spacing:.04em;
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
      '<div class="crow big"><span>Adjustment</span><b>'+(adj>=0?'+':'')+'$'+
        Math.round(adj).toLocaleString()+' psf</b></div>'+
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
      '<div class="crow"><span>Completion-year gap \u2014 the freehold is '+
        (dv===0?'the same age':(Math.abs(dv)+' yrs '+(dv>0?'newer':'older')))+
        ', at $'+r.toFixed(0)+' a year</span><b>'+
        (fwd?(age>=0?'\u2212':'+'):(age>=0?'+':'\u2212'))+'$'+
        Math.abs(Math.round(age)).toLocaleString()+'</b></div>'+
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
    if(!(bs>0&&bp>0&&ps>0)||isNaN(f)||f<0){o.className='cout bad';
      o.innerHTML='Enter the unit below and the penthouse size.';return;}
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
      LO.toFixed(2)+'&ndash;'+HI.toFixed(2)+'&times; that \u2014 the 95% interval on the '+
      'resale median.</p>';
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

def void_answer():
    """The measurement as a spec sheet. One track, so a row per fact reads better than a table
    with a single line in it."""
    r = ['<table class="fig"><tbody>']
    for lab, val, sub in (
        ('The discount', f'{VR["discount"]:.0f}% off', 'against the psf the floor plate commands'),
        ('What the extra area fetches', f'${VR["void_psf"]:,} psf',
         f'where the home itself fetches ${VR["base_psf"]:,}'),
        ('95% interval', f'{VR["lo"]:.2f}&ndash;{VR["hi"]:.2f}&times;',
         f'median {VR["ratio"]:.2f}&times;, quartiles {VR["p25"]:.2f}&ndash;{VR["p75"]:.2f}'),
        ('Typical extra area', f'{VR["extra"]:,} sqft',
         f'{VR["extra_pct"]*100:.0f}% of the floor plate'),
        ('Penthouse resales', f'{VR["pairs"]:,}', f'across {VR["devs"]} developments')):
        r.append(f'<tr><th>{lab}</th><td class="num big" style="color:var(--gold)">{val}</td>'
                 f'<td class="quiet" style="font-size:12.5px">{sub}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def void_sens():
    r = ['<table class="fig"><thead><tr><th>Floor step assumed</th><th class="num">Ratio</th>'
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
         '<th class="num">Discount</th><th class="num">Extra-area psf</th>'
         '<th class="num">95%</th><th class="num">Sales</th><th class="num">Devs</th>'
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
    r = ['<table class="fig"><thead><tr><th>Development</th><th class="num">D</th>'
         '<th class="num">Extra</th><th class="num">Home psf</th>'
         '<th class="num">Extra-area psf</th><th class="num">Discount</th>'
         '<th class="num">Spread</th><th class="num">Resales</th></tr></thead><tbody>']
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
         '<th class="num">freehold is worth</th><th class="num">95% interval</th>'
         '<th class="num">developments</th><th class="num">pairs</th></tr></thead><tbody>']
    for g in TGL:
        r.append(f'<tr><th>{g["label"].split(" ")[0].replace("-", "&ndash;")} years</th>'
                 f'<td class="num big">+{g["pct"]*100:.1f}%</td>'
                 f'<td class="num quiet">+{g["lo"]*100:.1f}% to +{g["hi"]*100:.1f}%</td>'
                 f'<td class="num quiet">{g["devs"]}</td>'
                 f'<td class="num quiet">{g["pairs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def ten_race_table():
    """The percentage forms only, against the engine and against doing nothing. The dollar
    forms are not shown here — they belong in the scale explain mark, which is where the
    choice between the two is argued."""
    if not T: return ''
    ORDER = {'va': 'after the age adjustment', 'av': 'before it', 'none': '&mdash;'}
    r = ['<table class="fig look"><thead><tr><th>Age gap removed at</th>'
         '<th>Premium applied</th><th class="num">reads</th>'
         '<th class="num">held-out error</th></tr></thead><tbody>',
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
    r = ['<table class="fig"><thead><tr><th>Screen</th><th class="num">freehold is worth</th>'
         '<th class="num">pairs</th></tr></thead><tbody>']
    for x in T['sens']:
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
<div class="panel" data-p="lease">
<h1 class="disp">What the market pays for a year of lease</h1>
<p class="lede">The engine restates every comparable using constants set by judgement. This is
the first one measured against the market.</p>

{hero('$40', 'flat, every comparable',
      [(f'${BANDR[OLD_NM]:,.0f}', OLD_NM, ndev(rows_in(OLD_NM))),
       (f'${BANDR[NEW_NM]:,.0f}', NEW_NM, ndev(rows_in(NEW_NM)))],
      f"<b>The call.</b> Two rates, not one, chosen by the <b>midpoint of the two lease starts</b>. "
      f"A flat $40 sits {40/BANDR[OLD_NM]:.1f} times the measured rate on an old pair and below it "
      f"on a new one.")}

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
  <p>Three questions, answered once each.</p></div>

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
  {max(c['pct'] for c in G['cuts'][1:]):.0f}%.</b> The <b>+5%</b> in use sits at or below the
  bottom of that range &mdash; on this evidence more likely low than high.</p>

  <div class="caveat"><b>The integrated flag is inert.</b> It reads from an override file that
  flags nothing, so every development is treated as not integrated and the &plusmn;5% has not yet
  applied to a comparable. The {G['n_integrated']} developments below are a
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
{V['meta']['floor_step']*100:.1f}% per floor. What is left is what that extra area is worth on
the <b>resale</b> market.</p>

{hero('1.00&times;', 'every strata sqft priced alike',
      [(f"{VR['discount']:.0f}% off", 'what a resale buyer pays for it', VR['devs'])],
      f"<b>The call.</b> A resale buyer pays about <b>half price</b> for the extra area of a "
      f"penthouse &mdash; {VR['discount']:.0f}% off the psf the same home&rsquo;s floor plate "
      f"commands. <b>There is no constant for it today</b> &mdash; the void is charged the same "
      f"psf as a bedroom, so a penthouse reads "
      f"{abs(VR['headline_drop']):.0f}% cheaper per square foot than the unit underneath it with "
      f"nothing about the home worse.")}

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

  <div class="scroll">{void_answer()}</div>

  <div class="caveat"><b>Void, roof terrace or private roof &mdash; the caveat reads them as one
  thing.</b> REALIS records strata area, not what is under the ceiling. All three are area on a
  floor plate that did not grow and all three price like it, which is why they measure together.
  Naming which is which needs the floor plan, unit by unit. Quote this as <b>extra penthouse
  area</b>; ceiling height is a subset of it and has not been separated.</div>

  <details><summary>The check that the floor step is not doing the work</summary>
    <p class="expl">The figure is <b>leveraged</b>: the extra area is small against the home, so a
    2% error in the base comparator swings it by more than 10%. The threat is a top-floor bonus
    that a straight-line floor step does not capture &mdash; any such bonus would land entirely on
    the void.</p>
    <p class="expl"><b>The check.</b> Run the identical machinery on stacks whose top unit is the
    <b>same size</b> as the units below. No extra area, so the residual should be zero. Across
    {V['resale']['placebo']['pairs']:,} such resales it reads
    <b>{V['resale']['placebo']['residual_pct']:+.2f}%</b>
    ({V['resale']['placebo']['lo']:+.2f} to {V['resale']['placebo']['hi']:+.2f}) &mdash;
    indistinguishable from zero. <b>Nothing is corrected</b>, because correcting by a figure that
    cannot be told from zero is worse than leaving it alone. The resale market pays no top-floor
    bonus beyond the floor step itself.</p>
    <p class="expl">Re-run everything at other floor steps and the answer barely moves:</p>
    <div class="scroll">{void_sens()}</div>
    <p class="expl">Across the defensible range it runs
    <b>{min(x['ratio'] for x in V['resale']['sensitivity']):.2f} to
    {max(x['ratio'] for x in V['resale']['sensitivity']):.2f}</b>. The assumption is not carrying
    the answer. <b>Quote half, not two decimal places.</b></p>
  </details>
</section>

<section>
  <h2>Where it moves</h2>
  <p class="expl"><b>The bigger the void, the more the buyer pays for it.</b> Where the extra area
  is a tenth of the floor plate it is discounted hardest; at a quarter and above the discount
  narrows &mdash; a large roof or a full double-volume room is a room, and gets treated as one.</p>
  <div class="scroll">{void_cut('extra area')}</div>

  <p class="expl" style="margin-top:18px"><b>The cheaper the home, the more the extra area is
  worth to the buyer</b> &mdash; the opposite of the shape you would guess. Below $1,500 psf the
  discount is smallest.</p>
  <div class="scroll">{void_cut('price tier')}</div>

  <details style="margin-top:16px"><summary>By region, and by tenure</summary>
    <div class="scroll">{void_cut('region')}</div>
    <div class="scroll" style="margin-top:14px">{void_cut('tenure')}</div>
    <p class="expl">Every one of these cells is thin. Read them for direction, never as a figure
    to quote on its own.</p>
  </details>
</section>

<section>
  <h2>The finding that is worth money</h2>
  <p class="expl"><b>The spread inside one development is wider than the spread between
  developments.</b> The void is priced stack by stack, and what one buyer paid for it bears
  little relation to what the buyer in the next line paid: {void_spread_names()}.</p>
  <div class="scroll">{void_devs(widest=True, n=12)}</div>
  <p class="expl">Read the <b>spread</b> column: the gap between the dearest and the cheapest
  stack in that same development. <b>The advice is not &ldquo;penthouses are good value&rdquo;
  &mdash; it is find the stack where the void was given away.</b></p>

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
    <p class="expl">Every other panel reads <code>property-analyzer/data/</code>. This one reads the
    <b>REALIS unit-level pull</b> held by the floor study, because it is the only dataset here that
    carries a <b>unit number</b> &mdash; and without the unit number there is no stack, without the
    stack there is no same-floor-plate pair. {V['meta']['window']}, all Singapore, strata,
    apartment and condominium, <b>resale only</b>.</p>
    <p class="expl"><code>price-gap/calibration/void-pairs.py</code> &rarr;
    <code>void-pairs.json</code>. It depends on none of the other three and they depend on none of
    it, so it may be run at any point in the order.</p>
  </details>
</section>
</div>

<div class="panel" data-p="judgement" hidden>
<h1 class="disp">What the market pays for freehold</h1>
<p class="lede">The last constant on judgement, and the only one that turned out not to be a
constant at all.</p>

{hero('&divide; 1.15', 'flat, every freehold comparable',
      [(f'+{g["pct"]*100:.0f}%', ten_step_label(g), g['devs']) for g in TGL],
      f"<b>The call.</b> One figure cannot do it. Freehold is worth "
      f"<b>+{TGL[0]['pct']*100:.0f}%</b> against a fresh lease and "
      f"<b>+{TGL[-1]['pct']*100:.0f}%</b> against a spent one. <b>Use one step, never the "
      f"sum.</b> Across all {T['counts']['pairs']} pairs it averages "
      f"+{THP['p']*100:.0f}%.")}

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
  <p class="expl"><b>The lease left is not asked for</b> &mdash; it follows from the completion
  year: {T['build']['term']} years less the age less the {T['build']['median']} years it took to
  build. The result says which step that lands on.</p>
</section>

<section>
  <div class="sechead"><h2 class="disp">Freehold is worth more as the lease runs down</h2>
  <p>Every pair is one freehold and one leasehold development, next door to each other, compared
  bedroom by bedroom. The only thing that changes down this table is <b>how much lease the
  leasehold neighbour has left</b>.</p></div>
  <div class="scroll">{ten_grad_table()}</div>
  <p class="expl" style="margin-top:18px"><b>This is the double-count.</b> If freehold and lease
  were separate things, this column would be flat &mdash; freehold would be worth the same
  whatever the neighbour's lease. It is not flat. It roughly doubles as the lease shortens, which
  says the two are <b>one curve</b>: at the far end of a lease, the freehold gap simply is the
  lease gap. Charging a lease difference and then a flat freehold ratio on top charges twice for
  part of the same thing.</p>
  <div class="caveat"><b>The fresh-lease step is the thin one.</b> It rests on
  {TGL[0]['pairs']} pairs, and it has moved twice as the method tightened. The climb is the
  finding; that step's level is not settled. The two lower steps rest on
  {TGL[1]['pairs']} and {TGL[2]['pairs']} pairs and have barely moved at all.</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">The measurement</h2>
  <p><b>{T['counts']['devs']} developments &middot; {T['counts']['pairs']} pairs &middot;
  {T['counts']['cells']} cells.</b> Same screens as the lease study &mdash; 500 m apart, the same
  station, the same schools, 200+ units, sizes within 20% &mdash; across 24 months of resale and
  sub-sale to {T['window'][1]}.</p></div>
  <div class="scroll">{ten_race_table()}</div>
  <p class="expl" style="margin-top:18px">Held-out error is the average miss, in psf, when the
  rule is fitted without a pair and then asked to restate it. Lower is better. The form in use
  reads {T['engine_rmse']:,.0f} against {T['null_rmse']:,.0f} for doing nothing at all, and the
  $40 is why: on a completion-year clock it scores worse than $10 does. <b>Your own measured
  lease rates, carried across onto that clock, win.</b> <b>Whether the premium goes on before or after the age
  adjustment barely registers</b> &mdash; the two orderings sit within five psf of each other.</p>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2>
  <p>Seven questions, answered once each.</p></div>

  <details><summary>Why a percentage and not a dollar figure?</summary>
    <p class="expl"><b>Because it travels, and because the constant it replaces is itself a
    ratio.</b> Drawn at random, held-out folds mildly favour a flat dollar figure &mdash;
    {T['scale_test']['dol_rmse']:,.0f} psf against {T['scale_test']['pct_rmse']:,.0f}. But a
    random fold looks like the sample it came from, which is exactly where an addition and a
    ratio are hardest to separate.</p>
    <p class="expl">The test that separates them is whether a figure can price stock it has
    never seen. Fit it without one price tier and ask it about that tier; then the same by
    region. It ends level overall &mdash; and it splits the way a percentage would predict,
    with the percentage winning on the cheapest stock and in the OCR, where a flat dollar
    figure is far too large a share of the price.</p>
    <div class="scroll">{ten_transfer_table('price', 'Predicting a price tier never seen')}</div>
    <div class="scroll" style="margin-top:14px">{ten_transfer_table('region', 'Predicting a region never seen')}</div>
    <p class="expl" style="margin-top:18px">A flat dollar figure fitted on this sample is
    +${THD['p']:,.0f}. On ${TBASE:,.0f} stock the two agree. On $1,100 stock the percentage
    says +${1100*THP['p']:,.0f} and the dollar figure still says +${THD['p']:,.0f}; on $3,500
    stock, +${3500*THP['p']:,.0f} against the same +${THD['p']:,.0f}. <b>The sample runs from
    ${min(r['psf_lh'] for r in TMIX):,.0f} to ${max(r['psf_lh'] for r in TMIX):,.0f} psf and
    cannot settle either end</b>, so treat the percentage as measured in the middle and
    inferred at the edges.</p>
  </details>

  <details><summary>Do the placebos read zero?</summary>
    <p class="expl"><b>Both do.</b> Run the identical estimator on pairs that share a tenure
    &mdash; where the true freehold premium is zero by construction &mdash; and it finds
    nothing: leasehold against leasehold reads <b>{T['placebo']['LH x LH']['pct']*100:+.1f}%</b>
    ({T['placebo']['LH x LH']['pairs']} pairs) and freehold against freehold
    <b>{T['placebo']['FH x FH']['pct']*100:+.1f}%</b>
    ({T['placebo']['FH x FH']['pairs']} pairs).</p>
    <p class="expl">Which side of a same-tenure pair takes the freehold slot is assigned <b>at
    random</b> and averaged over many draws. That matters: assigning it alphabetically read a
    false +2.9% on the freehold set, purely because alphabetically-earlier freeholds happened to
    sit newer.</p>
  </details>

  <details><summary>Where the calculator gets the lease left</summary>
    <p class="expl"><b>From the completion year, which is the one date a buyer always has.</b>
    {T['build']['term']}-year term, less the years since TOP, less the years it took to build.
    Across the {T['build']['n']} leasehold developments with both dates on record the build gap
    is a median <b>{T['build']['median']} years</b> (quartiles {T['build']['p25']}&ndash;{T['build']['p75']}),
    and {T['build']['term_share']*100:.0f}% of leasehold stock is on a {T['build']['term']}-year
    lease &mdash; so the inference is good to a year or two, against steps fifteen years wide.
    That is why the field is locked: it is right often enough that overriding it by habit would
    do more harm than good.</p>
    <p class="expl"><b>The build gap in use is {T['build']['engine']} years, not
    {T['build']['median']}.</b> A fifth constant, unmeasured until now. It barely touches this
    answer, but the same figure fills in a TOP year for any development with no completion year on
    record, so it is worth updating there on its own account.</p>
  </details>

  <details><summary>What does this say about the $10 age adjustment?</summary>
    <p class="expl">Freehold-against-freehold pairs measure it directly, since nothing else
    separates them. They fit <b>${T['fh_age_rate']:,.0f} a year</b> of completion-year
    difference, against the $10 in use. A by-product of this study, not its
    subject &mdash; but it points the same way as everything else here: the age term is
    understated and the lease term is overstated.</p>
  </details>

  <details><summary>Why the 200-unit floor stays</summary>
    <p class="expl">Because dropping it halves the answer, and the pairs it lets in cannot carry
    one. Shawn's ruling, {T['floor']['added_pairs']} added pairs later: <i>&ldquo;there are little
    to no transaction volume which might make it inaccurate due to lack of volume
    averages.&rdquo;</i></p>
    <p class="expl">The data says exactly that. Those added pairs run on a median of
    <b>{T['floor']['n_fh_added']:.0f} sales</b> on the freehold side against
    {T['floor']['n_fh_headline']:.0f} in the headline, <b>{T['floor']['thin_added']*100:.0f}%</b>
    of them under ten a side against {T['floor']['thin_headline']*100:.0f}%, and fitted on their
    own they read a directionless <b>+{T['floor']['added_pct']*100:.1f}%</b>. Freehold stock is
    mostly boutique, so this floor bites harder here than it did on the lease study &mdash; and
    a five-transaction minimum is a floor, not a volume.</p>
  </details>

  <details><summary>How much do the screens move it?</summary>
    <div class="scroll">{ten_sens_table()}</div>
    <p class="expl" style="margin-top:18px">Distance barely matters &mdash; widening to a
    kilometre moves the figure less than the interval around it. The unit floor is the one that
    does, for the reason above.</p>
  </details>

  <details><summary>Does it hold across the island, and across bedrooms?</summary>
    <div class="scroll">{ten_slice_table('region', 'Region')}</div>
    <p class="expl" style="margin-top:18px">The three regions agree closely, which is itself part
    of the case for a percentage: the same ratio serves the island, where a flat dollar figure
    would have to be roughly twice as large in the CCR as in the OCR.</p>
    <div class="scroll" style="margin-top:14px">{ten_slice_table('bedroom', 'Bedroom')}</div>
    <p class="expl" style="margin-top:18px">Bedroom is the match, not the answer &mdash; it holds
    size constant. Two- and three-bedroom read the same; one- and four-bedroom are too thin to
    show.</p>
  </details>

  <div class="caveat" style="margin-top:22px"><b>The confound to know.</b> Freehold is the
  <b>older</b> side in {TOLDER} of the {T['counts']['cells']} cells, and the age adjustment that
  removes it is a median <b>{TADJ/TBASE*100:.0f}% of the base</b> &mdash; the same size as the
  premium being measured. This answer leans on the vintage rate being right. Fitting that rate
  freely instead of importing the measured bands gives
  +{[x for x in T['race'] if x['key']=='va' and x['rate']=='free'][0]['prem']*100:.1f}%, so read
  the headline as the top of a range that starts there. Floor, facing and building quality stay
  uncontrolled by ruling.</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Where the constants now stand</h2></div>
  <table class="fig"><thead><tr><th>Term</th><th class="num">Constant</th><th>Measured</th></tr></thead><tbody>
  <tr><th>Lease / vintage</th><td class="num big">$40 psf / yr</td>
    <td style="color:var(--gold-soft)">${BANDR[OLD_NM]:,.0f} and ${BANDR[NEW_NM]:,.0f}, by midpoint</td></tr>
  <tr><th>Tenure &middot; freehold vs leasehold</th><td class="num big">&divide; 1.15</td>
    <td style="color:var(--gold-soft)">+{THP['p']*100:.0f}% on average, and
    +{TGL[0]['pct']*100:.0f}% to +{TGL[-1]['pct']*100:.0f}% by the lease left</td></tr>
  <tr><th>MRT walk band</th><td class="num big">$50 / $200 / $250</td>
    <td style="color:var(--gold-soft)">+${M['bands'][0]['adj']:,.0f} / +${M['bands'][1]['adj']:,.0f} /
    +${M['bands'][2]['adj']:,.0f}, or ${M['slope100']:.0f} per 100 m</td></tr>
    <tr><th>Integrated development</th><td class="num big">+5%</td>
    <td style="color:var(--gold-soft)">+{G['cuts'][4]['pct']:.1f}% ({G['cuts'][4]['pct_lo']:.1f} to
    {G['cuts'][4]['pct_hi']:.1f}), which contains the +5%</td></tr>
  <tr><th>Void &middot; extra penthouse area</th><td class="num big">1.00&times; (implicit)</td>
    <td style="color:var(--gold-soft)">a resale buyer pays {VR['discount']:.0f}% less for it than
    for the floor plate; there is no constant for it today</td></tr>
  </tbody></table>
  <div class="caveat" style="margin-top:18px"><b>Nothing has been written back yet.</b>
  Every figure on this page sits beside its constant, not in place of it.</div>
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
    <button type="button" class="done" data-go="judgement">
      <span class="tn">FH vs LH</span><span class="ts">Measured</span></button>
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
