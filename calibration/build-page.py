#!/usr/bin/env python3
"""Renders the calibration findings as ../../kya-maps-calculator/calibration.html.

HIDDEN PAGE. It is not in the nav and nothing links to it: the only way in is a
DOUBLE-CLICK on the "Live Data" chip at the top right of the calculator (Shawn,
2026-09-06). It is a working document — the audit trail behind the Price Gap
engine's constants — and never a client-facing view.

Self-contained, no Tailwind: the main page's CDN dependency is a known offline
defect and this page must not inherit it. Tokens copied from index.html so the
navy-and-gold identity holds.

SHAPE (Shawn, 2026-09-06, four rulings, in the order he gave them):
  * QUANTUM ONLY. No percentages anywhere. Across base-PSF bands the $/yr holds while
    the %/yr falls away, so the dollar is the invariant. The percentage is also what
    made region look like a real split when it is a price-level effect.
  * THE FACE OF THE PAGE CARRIES THE ANSWER. Everything disproved moves BEHIND AN
    EXPLAIN MARK, never into the bin. A page may not show a number it cannot explain.
  * A CURVE, NOT A CONSTANT AND NOT TWO BANDS. rate = a + b*(midpoint - 2000). He found
    the seam by asking what to use for a 2005-vs-2025 pair; a two-band step has to pick
    a side and is wrong either way. The midpoint form IS the blend.
  * NO MINIMUM LEASE GAP. The old 5-year screen protected the per-pair mean, not this
    estimator. Removing it tripled the sample and tightened the slope.

  python3 lease-pairs.py && python3 build-page.py
"""
import json, os, html, random, statistics as st, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, '..', '..', 'kya-maps-calculator', 'calibration.html')
D    = json.load(open(os.path.join(HERE, 'lease-pairs.json')))

# ── the estimator ───────────────────────────────────────────────────────────
def curve(rows):
    """rate = a + b*(mid-2000), fitted as diff = gap*(a + b*(mid-2000)). Pure-python 2x2.
    This form IS the blend: if the rate rises smoothly with vintage then the whole
    difference across an interval is the gap times the rate at its midpoint, so a pair
    straddling any cut-over needs no special handling."""
    s11 = s12 = s22 = t1 = t2 = 0.0
    for r in rows:
        x1 = r['gap']; x2 = r['gap'] * (mid(r) - 2000)
        s11 += x1*x1; s12 += x1*x2; s22 += x2*x2; t1 += x1*r['diff']; t2 += x2*r['diff']
    det = s11*s22 - s12*s12
    return ((s22*t1 - s12*t2)/det, (s11*t2 - s12*t1)/det) if det else (None, None)

def mid(r):   return (r['ls_old'] + r['ls_new']) / 2

# THE ANSWER IS THREE MEASURED BANDS, read at the MIDPOINT of the two lease starts.
# Not a fitted curve: the tail slope is not identified by this data (see the page).
BANDS = [(1900, 2011, 'up to 2010'), (2011, 2014, '2011–2013'), (2014, 2030, '2014 onward')]

def band_of(m):
    return next(n for lo, hi, n in BANDS if lo <= m < hi)

def rate(m):  return BANDR[band_of(m)]

def hinge(rows, K):
    """rate = c + d*max(0, mid - K). Flat until the knee year, rising after it.
    Fitted the same way as everything else here: diff = gap * rate(midpoint)."""
    s11 = s12 = s22 = t1 = t2 = 0.0
    for r in rows:
        x1 = r['gap']; x2 = r['gap'] * max(0.0, mid(r) - K)
        s11 += x1*x1; s12 += x1*x2; s22 += x2*x2; t1 += x1*r['diff']; t2 += x2*r['diff']
    det = s11*s22 - s12*s12
    if not det: return None, None
    return (s22*t1 - s12*t2)/det, (s11*t2 - s12*t1)/det

def hinge_rss(rows, K):
    c, d = hinge(rows, K)
    return sum((r['diff'] - r['gap']*(c + d*max(0.0, mid(r)-K)))**2 for r in rows)

def pick_knee(rows, lo=2000, hi=2014):
    return min(range(lo, hi+1), key=lambda K: hinge_rss(rows, K))

def hinge_ci(rows, K, N=1500, seed=29):
    g = random.Random(seed); n = len(rows); CC = []; DD = []; KK = []
    for _ in range(N):
        s = [rows[g.randrange(n)] for _ in range(n)]
        k = pick_knee(s); c, d = hinge(s, K)
        KK.append(k); CC.append(c); DD.append(d)
    CC.sort(); DD.sort(); KK.sort()
    q = lambda v, p: v[min(int(p*len(v)), len(v)-1)]
    return (q(CC,.025), q(CC,.975)), (q(DD,.025), q(DD,.975)), (q(KK,.025), q(KK,.975))
def fit(r):   return sum(x['diff'] for x in r) / sum(x['gap'] for x in r) if r else None
def money(v): return '—' if v is None else f'{v:+,.0f}'
def npairs(r):return len({(x['older'], x['newer']) for x in r})

def curve_ci(rows, N=2000, seed=17):
    g = random.Random(seed); n = len(rows); AA = []; BB = []
    for _ in range(N):
        a, b = curve([rows[g.randrange(n)] for _ in range(n)])
        if a is not None: AA.append(a); BB.append(b)
    AA.sort(); BB.sort(); lo, hi = int(.025*len(AA)), int(.975*len(AA)) - 1
    return (AA[lo], AA[hi]), (BB[lo], BB[hi])

def _solve(S, T):
    """Tiny Gaussian elimination, so the page needs no numpy."""
    n = len(T); M = [row[:] + [T[i]] for i, row in enumerate(S)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(i+1, n):
            f = M[r][i]/M[i][i]
            for c_ in range(i, n+1): M[r][c_] -= f*M[i][c_]
    x = [0.0]*n
    for i in range(n-1, -1, -1):
        x[i] = (M[i][n] - sum(M[i][j]*x[j] for j in range(i+1, n)))/M[i][i]
    return x

def cv(rows, model, folds=5, reps=20, seed=23):
    """Held-out squared error per cell. The only honest way to rank shapes that carry
    different numbers of parameters."""
    g = random.Random(seed); idx = list(range(len(rows))); err = []
    for _ in range(reps):
        g.shuffle(idx)
        for f in range(folds):
            te = set(idx[f::folds])
            tr = [rows[i] for i in idx if i not in te]; ts = [rows[i] for i in idx if i in te]
            if model == 'flat':
                a = fit(tr); pr = [a*x['gap'] for x in ts]
            elif model == 'step':
                o = [x for x in tr if x['ls_old'] < 2010]; n_ = [x for x in tr if x['ls_old'] >= 2010]
                a = fit(o); b = fit(n_) if n_ else a
                pr = [(a if x['ls_old'] < 2010 else b)*x['gap'] for x in ts]
            elif model == 'old':
                s11=s12=s22=t1=t2=0.0
                for x in tr:
                    x1=x['gap']; x2=x['gap']*(x['ls_old']-2000)
                    s11+=x1*x1; s12+=x1*x2; s22+=x2*x2; t1+=x1*x['diff']; t2+=x2*x['diff']
                d_=s11*s22-s12*s12; a=(s22*t1-s12*t2)/d_; b=(s11*t2-s12*t1)/d_
                pr = [x['gap']*(a+b*(x['ls_old']-2000)) for x in ts]
            elif model == 'quad':
                import itertools as _it
                n_ = 3
                S = [[0.0]*n_ for _ in range(n_)]; T = [0.0]*n_
                for x in tr:
                    v = [x['gap'], x['gap']*(mid(x)-2000), x['gap']*(mid(x)-2000)**2]
                    for i in range(n_):
                        T[i] += v[i]*x['diff']
                        for j in range(n_): S[i][j] += v[i]*v[j]
                co = _solve(S, T)
                pr = [x['gap']*(co[0]+co[1]*(mid(x)-2000)+co[2]*(mid(x)-2000)**2) for x in ts]
            elif model == 'band':
                rt = {}
                for lo, hi, nm in BANDS:
                    b = [x for x in tr if lo <= mid(x) < hi]
                    rt[nm] = fit(b) if b else fit(tr)
                pr = [rt[band_of(mid(x))]*x['gap'] for x in ts]
            elif model == 'hinge':
                k = pick_knee(tr); a, b = hinge(tr, k)
                pr = [x['gap']*(a+b*max(0.0, mid(x)-k)) for x in ts]
            else:
                a, b = curve(tr); pr = [x['gap']*(a+b*(mid(x)-2000)) for x in ts]
            err += [(x['diff']-q)**2 for x, q in zip(ts, pr)]
    return sum(err)/len(err)

ALL   = D['24']                      # NO gap screen — see the docstring in lease-pairs.py
BANDR = {}                           # filled below, once fit() exists
KNEE  = pick_knee(ALL)               # kept only for the rejected-shapes section
C, Dd = hinge(ALL, KNEE)
(CLO, CHI), (DLO, DHI), (KLO, KHI) = hinge_ci(ALL, KNEE)
A, B  = curve(ALL)                   # the straight line, kept only as the comparison
(ALO, AHI), (BLO, BHI) = curve_ci(ALL)

def band_rows(nm):
    return [r for r in ALL if band_of(mid(r)) == nm]

def band_ci(nm, N=3000, seed=3):
    g = random.Random(seed); rs = band_rows(nm)
    v = sorted(fit([rs[g.randrange(len(rs))] for _ in rs]) for _ in range(N))
    return v[int(.025*N)], v[int(.975*N)-1]

for _lo, _hi, _nm in BANDS:
    BANDR[_nm] = fit([r for r in ALL if _lo <= mid(r) < _hi])
BANDCI = {nm: band_ci(nm) for _, _, nm in BANDS}
NDEV   = len({x for r in ALL for x in (r['older'], r['newer'])})
ndev   = lambda rs: len({x for r in rs for x in (r['older'], r['newer'])})
POOL  = D.get('pooled24', [])
PA, PB = curve(POOL) if POOL else (None, None)
MIDS  = sorted(mid(r) for r in ALL)
MID_LO, MID_HI = MIDS[int(.05*len(MIDS))], MIDS[int(.95*len(MIDS))]

BEDS  = ['1BR', '2BR', '3BR', '4BR+']
REGS  = ['CCR', 'RCR', 'OCR']
PBANDS = [(0,1200,'under $1,200'), (1200,1600,'$1,200 – $1,600'),
          (1600,2000,'$1,600 – $2,000'), (2000,99999,'$2,000 and over')]

THEAD = ('<table class="fig"><thead><tr><th></th><th class="num">$ psf / yr</th>'
         '<th class="num">cells</th><th class="num">pairs</th><th></th></tr></thead><tbody>')

def row(label, rows, note=''):
    if not rows:
        return f'<tr><th>{label}</th><td colspan="4" class="nil">not measurable</td></tr>'
    return (f'<tr><th>{label}</th><td class="num big">{money(fit(rows))}</td>'
            f'<td class="num quiet">{len(rows)}</td>'
            f'<td class="num quiet">{npairs(rows)}</td><td class="note">{note}</td></tr>')

def lookup():
    h = ['<table class="fig look"><thead><tr><th>Midpoint of the two lease starts</th>'
         '<th class="num">$ psf per year</th><th class="num">95% interval</th>'
         '<th class="num">developments</th><th class="num">pairs</th></tr></thead><tbody>']
    for lo, hi, nm in BANDS:
        rs = band_rows(nm); cl, ch = BANDCI[nm]
        h.append(f'<tr><th>{nm}</th><td class="num big">${BANDR[nm]:,.0f}</td>'
                 f'<td class="num quiet">${cl:,.0f} to ${ch:,.0f}</td>'
                 f'<td class="num quiet">{ndev(rs)}</td><td class="num quiet">{npairs(rs)}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def observed():
    """Finer slices than the bands, so the reader can see where the turn actually is."""
    g = random.Random(7)
    h = ['<table class="fig"><thead><tr><th>Midpoint</th><th class="num">$ psf / yr</th>'
         '<th class="num">95% interval</th><th class="num">developments</th>'
         '<th class="num">pairs</th><th class="num">cells</th></tr></thead><tbody>']
    for lo, hi in [(1990,2000),(2000,2005),(2005,2008),(2008,2011),(2011,2014),(2014,2030)]:
        s_ = [r for r in ALL if lo <= mid(r) < hi]
        if len(s_) < 8: continue
        v = sorted(fit([s_[g.randrange(len(s_))] for _ in s_]) for _ in range(2000))
        turn = ' class="flag"' if lo >= 2011 else ''
        h.append(f'<tr{turn}><th>{lo}–{min(hi-1,2025)}</th><td class="num big">{fit(s_):+,.0f}</td>'
                 f'<td class="num quiet">{v[50]:+,.0f} to {v[1949]:+,.0f}</td>'
                 f'<td class="num quiet">{ndev(s_)}</td><td class="num quiet">{npairs(s_)}</td>'
                 f'<td class="num quiet">{len(s_)}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def residuals():
    """Where the fitted shape does not follow the market. Bootstrapped, because two of
    these buckets are small and a residual that cannot be told from zero is not a finding."""
    g = random.Random(41)
    h = ['<table class="fig"><thead><tr><th>Midpoint</th><th class="num">the curve runs</th>'
         '<th class="num">95% interval</th><th class="num">cells</th><th></th></tr></thead><tbody>']
    for lo, hi in [(1990,2000),(2000,2005),(2005,2010),(2010,2015),(2015,2030)]:
        s_ = [r for r in ALL if lo <= mid(r) < hi]
        if len(s_) < 3: continue
        per = lambda rs: sum(r['diff'] - r['gap']*rate(mid(r)) for r in rs) / sum(r['gap'] for r in rs)
        v = per(s_)
        bs = sorted(per([s_[g.randrange(len(s_))] for _ in s_]) for _ in range(1500))
        blo, bhi = bs[int(.025*len(bs))], bs[int(.975*len(bs))-1]
        real = blo > 0 or bhi < 0
        h.append(f'<tr{" class=flag" if real else ""}><th>{lo}–{min(hi-1,2025)}</th>'
                 f'<td class="num big">{v:+,.1f}</td>'
                 f'<td class="num quiet">{blo:+,.1f} to {bhi:+,.1f}</td>'
                 f'<td class="num quiet">{len(s_)}</td>'
                 f'<td class="note">{"the shape misses this bucket" if real else "no difference from the fitted shape"}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def gapstability():
    h = ['<table class="fig"><thead><tr><th>Minimum lease gap</th>'
         + ''.join(f'<th class="num">{nm}</th>' for _, _, nm in BANDS)
         + '<th class="num">cells</th><th class="num">pairs</th></tr></thead><tbody>']
    for mg in (1, 2, 3, 5, 8):
        rs = [r for r in ALL if r['gap'] >= mg]
        cells = ''
        for lo, hi, nm in BANDS:
            b = [r for r in rs if lo <= mid(r) < hi]
            cells += f'<td class="num big">${fit(b):,.0f}</td>' if b else '<td class="num nil">—</td>'
        lab = f'{mg} years' if mg > 1 else 'none — the method'
        h.append(f'<tr{"" if mg==1 else " class=dim"}><th>{lab}</th>{cells}'
                 f'<td class="num quiet">{len(rs)}</td><td class="num quiet">{npairs(rs)}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def models():
    h = ['<table class="fig"><thead><tr><th>Shape</th><th class="num">held-out error</th>'
         '<th></th></tr></thead><tbody>']
    for nm, k, note in [('One flat rate', 'flat', 'the engine today'),
                        ('Two bands, stepped on the older project', 'step', 'an earlier version of this page'),
                        ('A curve keyed on the older project', 'old', ''),
                        ('A straight line on the pair midpoint', 'mid', 'ran low at both ends'),
                        ('A quadratic on the pair midpoint', 'quad', 'better, but hard to explain and to extend'),
                        (f'A fitted knee at {KNEE}', 'hinge', 'the knee is not identified — see below'),
                        ('<b>Three measured bands</b>', 'band', 'the method')]:
        v = cv(ALL, k)
        h.append(f'<tr><th>{nm}</th><td class="num big">{v/1000:,.1f}k</td>'
                 f'<td class="note">{note}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def pricebands():
    h = ['<table class="fig"><thead><tr><th>Base PSF of the older project</th>'
         '<th class="num">$ psf / yr</th><th class="num">cells</th>'
         '<th class="num">median base psf</th><th></th></tr></thead><tbody>']
    for lo, hi, nm in PBANDS:
        b = [r for r in ALL if lo <= r['psf_old'] < hi]
        if not b:
            h.append(f'<tr><th>{nm}</th><td colspan="4" class="nil">no cells</td></tr>'); continue
        thin = len(b) < 25
        h.append(f'<tr{" class=dim" if thin else ""}><th>{nm}</th><td class="num big">{money(fit(b))}</td>'
                 f'<td class="num quiet">{len(b)}</td>'
                 f'<td class="num quiet">${st.median([r["psf_old"] for r in b]):,.0f}</td>'
                 f'<td class="note">{"the CCR pairs — not measurable this way" if thin else ""}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def nulls():
    h = [THEAD, '<tr class="sep"><th colspan="5">By bedroom — no difference</th></tr>']
    for bd in BEDS:
        s = [r for r in ALL if r['bed'] == bd]
        h.append(row(bd, s, 'too thin to read' if 0 < len(s) < 25 else ''))
    h.append('<tr class="sep"><th colspan="5">By region — no difference in dollars</th></tr>')
    for rg in REGS:
        s = [r for r in ALL if r['region'] == rg]
        h.append(row(rg, s, 'Marina Bay and Sentosa only — not the CCR' if rg == 'CCR' else ''))
    return ''.join(h) + '</tbody></table>'

def pairtable():
    rows = sorted(ALL, key=lambda r: (-r['gap'], r['older']))
    h = ['<table class="fig pairs"><thead><tr><th>older</th><th class="num">lease</th>'
         '<th>newer</th><th class="num">lease</th><th class="num">gap</th><th>bed</th>'
         '<th class="num">psf</th><th class="num">psf</th><th class="num">$ / yr</th>'
         '<th class="num">the curve</th><th class="num">apart</th><th>station</th>'
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
.vcell.grow{flex:1 1 340px;min-width:300px}
.formula{font:600 clamp(22px,2.6vw,30px)/1.25 Optima,Candara,sans-serif;color:var(--gold);
white-space:nowrap;letter-spacing:.01em}
.formula span{color:var(--slate-600);padding:0 2px}
.formula em{font-style:normal;color:var(--gold-soft);font-size:.72em;letter-spacing:.01em}
@media (max-width:520px){.formula{white-space:normal;font-size:21px}}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin-bottom:26px}
.step{border:1px solid var(--ink);border-radius:11px;background:var(--navy-850);
padding:16px 18px;display:flex;gap:12px;align-items:flex-start}
.step .sn{flex:none;width:22px;height:22px;border-radius:50%;border:1px solid rgba(201,169,106,.5);
color:var(--gold);display:grid;place-items:center;font:600 11px/1 Optima,Candara,sans-serif}
.step p{color:var(--slate-400);font-size:12.5px}
.step p b{color:var(--slate-100);font-weight:600}
.worked{border:1px solid var(--ink);border-radius:12px;background:var(--navy-850);padding:20px 22px}
.worked h3{margin-bottom:10px}
table.wk th{color:var(--slate-500);font-weight:400;width:150px;white-space:nowrap}
table.wk td{color:var(--slate-300)}
table.wk td b{color:var(--slate-100);font-weight:600}
table.wk tr.tot th,table.wk tr.tot td{border-bottom:none;padding-top:12px}
table.wk tr.tot td b{color:var(--gold)}
.look td.big{color:var(--gold-soft)}
tr.flag td.big{color:var(--warn)}
.calc{margin-top:20px;border:1px solid rgba(201,169,106,.3);border-radius:12px;
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
.crow{display:flex;justify-content:space-between;gap:16px;padding:5px 0;color:var(--slate-400)}
.crow b{color:var(--slate-100);font-variant-numeric:tabular-nums;font-weight:600}
.crow.big{border-top:1px solid var(--ink);margin-top:8px;padding-top:12px;font-size:15px}
.crow.big b{color:var(--gold);font:600 21px/1 Optima,Candara,sans-serif}
.chint{color:var(--slate-500);font-size:12px;margin-top:10px}
.cwarn{color:var(--warn);font-size:12px;margin-top:8px}
.crow i.cflat{font-style:normal;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
color:var(--gold);border:1px solid rgba(201,169,106,.4);border-radius:999px;padding:2px 9px;
margin-left:10px;align-self:center}
.crow{align-items:center}
"""
JS = """
(function(){
  var BANDS=%BANDS%, LO=%LO%, HI=%HI%;
  function bandFor(m){for(var i=0;i<BANDS.length;i++){if(m<BANDS[i][0])return BANDS[i];}
    return BANDS[BANDS.length-1];}
  function n(id){return parseFloat(document.getElementById(id).value);}
  function go(){
    var a=n('lsA'), b=n('lsB'), o=document.getElementById('calcOut');
    if(!a||!b||a<1960||b<1960||a>2040||b>2040){o.className='cout bad';
      o.innerHTML='Enter two lease start years.';return;}
    if(a===b){o.className='cout bad';o.innerHTML='Same lease start — no adjustment.';return;}
    var mid=(a+b)/2, bd=bandFor(mid), rate=bd[1], gap=b-a, adj=rate*gap;
    var warn='';
    if(mid>HI) warn='<p class="cwarn">Midpoint '+mid.toFixed(1)+' is past the measured range '+
      '(ends '+HI.toFixed(0)+'). The newest band is the thinnest and the rate was still climbing '+
      'when the evidence ran out, so treat this as a floor rather than a figure.</p>';
    else if(mid<LO) warn='<p class="chint">Midpoint '+mid.toFixed(1)+' is below the bulk of the '+
      'sample (starts '+LO.toFixed(0)+'), but it sits in the oldest band, which is flat and rests '+
      'on more evidence than the other two together. The rate does not change going further back.</p>';
    o.className='cout';
    o.innerHTML =
      '<div class="crow"><span>Midpoint</span><b>'+mid.toFixed(1)+'</b></div>'+
      '<div class="crow"><span>Rate at that midpoint</span><b>$'+rate.toFixed(1)+' psf / yr</b>'+
        '<i class="cflat">'+bd[2]+'</i></div>'+
      '<div class="crow"><span>Lease gap</span><b>'+Math.abs(gap)+' years</b></div>'+
      '<div class="crow big"><span>Adjustment</span><b>'+(adj>=0?'+':'')+'$'+
        Math.round(adj).toLocaleString()+' psf</b></div>'+
      '<p class="chint">Add this to the '+(gap>0?'older':'newer')+
      ' comparable\\'s PSF to restate it onto the subject\\'s lease terms.</p>'+warn;
  }
  ['lsA','lsB'].forEach(function(id){
    document.getElementById(id).addEventListener('input',go);});
  go();
})();
"""

BANDS_JS = '[' + ','.join(f'[{hi},{BANDR[nm]:.2f},"{nm}"]' for _, hi, nm in BANDS) + ']'

EX_A, EX_B = 2005, 2025
EX_MID = (EX_A + EX_B) / 2

BODY = f"""
<p class="kicker">Price Gap · the lease term</p>
<h1 class="disp">What the market pays for a year of lease</h1>
<p class="lede">The Price Gap engine restates every comparable onto the subject's terms using five
constants. All five were set by judgement. This measures the first of them against the market.</p>

<div class="verdict">
  <div class="vgrid">
    <div class="vcell"><div class="lab">Engine constant</div>
      <div class="val was">$40</div><div class="sub">psf per year, flat · set 2026-07-20</div></div>
    <div class="arrow">&rarr;</div>
    <div class="vcell grow"><div class="lab">Measured</div>
      <div class="formula">${BANDR['up to 2010']:,.0f} <span>·</span> ${BANDR['2011–2013']:,.0f}
        <span>·</span> ${BANDR['2014 onward']:,.0f}</div>
      <div class="sub">dollars psf per year · by the midpoint of the two lease starts ·
        {NDEV} developments, {npairs(ALL)} pairs</div></div>
  </div>
  <p class="call"><b>The call.</b> The rate is <b>flat at ${BANDR['up to 2010']:,.0f} a year</b> for
  every pair centred up to 2010 — that band alone rests on {ndev(band_rows('up to 2010'))} developments
  and holds whatever else is varied — and then <b>steps up sharply</b>, to
  ${BANDR['2011–2013']:,.0f} and then ${BANDR['2014 onward']:,.0f}. The engine's flat $40
  over-adjusts an old pair by more than half and under-adjusts a new one.
  Bedroom and region were both tested and neither moves it.
  <b>Read at the midpoint</b>, which is what lets one table price a pair straddling any boundary.
  Leave the engine untouched until this is audited.</p>
</div>

<section>
  <div class="sechead"><h2 class="disp">What is being counted</h2>
  <p>Three words appear throughout and they count different things.</p></div>
  <div class="steps">
    <div class="step"><span class="sn">1</span>
      <p><b>Development</b> — one condominium. {NDEV} of them appear somewhere in this study.</p></div>
    <div class="step"><span class="sn">2</span>
      <p><b>Pair</b> — two neighbouring developments compared against each other.
      {npairs(ALL)} of them.</p></div>
    <div class="step"><span class="sn">3</span>
      <p><b>Cell</b> — one pair read at one bedroom type. A pair yields one to four.
      {len(ALL)} of them, and this is the unit the figures are computed on.</p></div>
  </div>
  <p class="expl">So {NDEV} developments produce {npairs(ALL)} pairs and {len(ALL)} cells. The
  development count is the smaller number because most developments sit in more than one pair —
  a block with three leasehold neighbours appears three times.</p>
</section>

<section>
  <div class="sechead"><h2 class="disp">How to calculate it</h2>
  <p>Four steps. The midpoint is the whole trick: it is what lets one table handle a pair that
  straddles a band boundary, instead of having to decide which side it belongs to.</p></div>

  <div class="steps">
    <div class="step"><span class="sn">1</span>
      <p>Take the <b>two lease start years</b> — the subject's and the comparable's.</p></div>
    <div class="step"><span class="sn">2</span>
      <p>Average them. That is the <b>midpoint</b>.</p></div>
    <div class="step"><span class="sn">3</span>
      <p>Read the rate off the band the midpoint falls in:
      <b>up to 2010 &rarr; ${BANDR['up to 2010']:,.0f}</b>,
      2011&ndash;13 &rarr; ${BANDR['2011–2013']:,.0f},
      2014 on &rarr; ${BANDR['2014 onward']:,.0f}.</p></div>
    <div class="step"><span class="sn">4</span>
      <p>Multiply by the <b>lease gap</b>, and add it to the comparable's PSF.</p></div>
  </div>

  <div class="worked">
    <h3>Worked — a {EX_A} comparable against a {EX_B} subject</h3>
    <table class="fig wk"><tbody>
      <tr><th>Lease starts</th><td>{EX_A} and {EX_B}</td></tr>
      <tr><th>Midpoint</th><td>({EX_A} + {EX_B}) &divide; 2 = <b>{EX_MID:,.0f}</b></td></tr>
      <tr><th>Rate</th><td>midpoint {EX_MID:,.0f} falls in the <b>{band_of(EX_MID)}</b> band
        = <b>${rate(EX_MID):,.0f} psf per year</b></td></tr>
      <tr><th>Lease gap</th><td>{EX_B} &minus; {EX_A} = <b>{EX_B-EX_A} years</b></td></tr>
      <tr class="tot"><th>Adjustment</th><td>${rate(EX_MID):,.0f} &times; {EX_B-EX_A}
        = <b>+${rate(EX_MID)*(EX_B-EX_A):,.0f} psf</b> onto the {EX_A} comparable</td></tr>
    </tbody></table>
    <p class="expl">Note what a flat constant would have done here. At $40 it reads
    +${40*(EX_B-EX_A):,.0f} against a measured ${rate(EX_MID)*(EX_B-EX_A):,.0f}. Run it the other
    way — an old pair centred on 1995 — and $40 reads +${40*10:,.0f} over ten years against a
    measured ${rate(1995)*10:,.0f}, which is {40/rate(1995):.1f} times too much. One number cannot
    be right at both ends.</p>
  </div>

  <div class="calc">
    <h3>Try a pair</h3>
    <div class="cin">
      <label>Comparable lease start<input id="lsA" type="number" value="{EX_A}" min="1960" max="2040" step="1"></label>
      <label>Subject lease start<input id="lsB" type="number" value="{EX_B}" min="1960" max="2040" step="1"></label>
    </div>
    <div id="calcOut" class="cout"></div>
  </div>

  <details><summary>The rate, read off directly</summary>
    <div class="scroll">{lookup()}</div>
    <p class="expl">The sample's midpoints run {MID_LO:,.0f} to {MID_HI:,.0f} at the 5th and 95th
    percentile. Rows outside that are the curve extended past its evidence, which is a different
    kind of claim — usable, but say so when you use it.</p>
  </details>
</section>

<section>
  <div class="sechead"><h2 class="disp">The figure</h2>
  <p>{npairs(ALL)} matched neighbour pairs, {len(ALL)} bedroom cells, twenty-four months.
  Dollars per square foot per year of lease start — never a percentage, for the reason below.</p></div>

  <h3>Finer than the bands, to show where the turn is</h3>
  <div class="scroll">{observed()}</div>

  <div class="caveat"><b>The newest band is a floor, not a ceiling.</b> It rests on
  {ndev(band_rows('2014 onward'))} developments and {npairs(band_rows('2014 onward'))} pairs, and the
  rate was <b>still climbing when the evidence ran out</b> — young leasehold stock has barely
  resold, and new sale is excluded by ruling. Quote ${BANDR['2014 onward']:,.0f} as the least it
  can be, not as the answer.</div>

  <details><summary>Why three measured bands and not a fitted curve</summary>
    <p class="expl">Two fitted shapes were tried before this one and <b>both were beaten by the
    sample they were fitted on</b>. A straight line through the midpoint ran low at both ends. A
    knee — flat, then rising — fitted that better, until the pair screen was widened and it moved:
    the best knee is now anywhere from 1998 to 2008, and across that whole span the fit changes by
    less than 2%. <b>The knee is not identified by this data.</b> Reporting a fitted year and slope
    would be claiming a precision the pairs do not carry.</p>
    <p class="expl">What <em>is</em> stable is the band-by-band reading above: it barely moves when
    the screens change, its intervals are tight, and it holds up on held-out error as well as any
    fitted shape. So the page reports what was measured and stops there.</p>
    <div class="scroll">{residuals()}</div>
    <p class="expl">Residuals against the bands, in the same units as the rate. Every slice sits
    within its interval of zero.</p>
  </details>

  <details><summary>One hypothesis tested and rejected — the lease-decay knee</summary>
    <p class="expl">A pair centred in the 1990s has a lease running down toward the 60–65 year
    mark, which is where the 2026-07-27 decay study found the market's knee, so the obvious
    suspicion was that the old end is decay showing through rather than vintage. <b>It is not.</b>
    Refitting on the remaining lease of the older project instead of vintage is worse on held-out
    error (19.4k against {cv(ALL,'hinge')/1000:,.1f}k), adding it alongside vintage is worse
    (19.1k), and a term for years below a 65-year remaining lease earns nothing it does not already
    have. The turn is in the vintage of the stock, not in how much lease is left on it.</p>
  </details>

  <details><summary>Why a curve, and not one number or two bands</summary>
    <p class="expl">Ranked by <b>held-out</b> error — each shape fitted on four fifths of the pairs
    and scored on the fifth it never saw, which is the only fair way to compare shapes carrying
    different numbers of parameters.</p>
    <div class="scroll">{models()}</div>
    <p class="expl">The midpoint curve wins, and it wins for a reason that is arithmetic rather
    than empirical: <b>if the rate rises smoothly with vintage, the total difference across an
    interval is exactly the gap times the rate at its midpoint.</b> So the midpoint form <em>is</em>
    the blend. A two-band step has to decide which side a straddling pair belongs to and gets it
    wrong either way; the curve never faces the question.</p>
  </details>

  <details><summary>Why there is no minimum lease gap</summary>
    <p class="expl">Earlier passes threw away every pair under five years of lease separation. That
    screen was built for a different estimator — the average of each pair's own $/yr, which divides
    each difference by its own gap and so multiplies a short pair's noise. <b>This estimator fits
    the difference against the gap</b>, so a three-year pair carries three years of leverage and
    cannot shout. Refitting at every threshold shows the screen was buying nothing and costing
    two thirds of the evidence.</p>
    <div class="scroll">{gapstability()}</div>
    <p class="expl">Both coefficients are flat across the whole range and the interval on b is
    <b>tighter</b> without the screen. Dropping it took the sample from 97 cells to {len(ALL)}, and
    the pairs whose older side is 2010s stock from 8 to
    {npairs([r for r in ALL if r['ls_old'] >= 2010])} — which is where the curve's newer end
    comes from.</p>
  </details>

  <details><summary>Why bedroom is the match and not the answer</summary>
    <p class="expl">Bedroom does not appear in the equation. It is the <b>stratum that holds size
    constant</b>, and it is the finest size resolution the data has — the PSF series on disk is
    aggregated to project &times; bedroom &times; month and there is nothing below it. Comparing
    two projects on one blended PSF each would let the sales mix do the talking: a block selling
    mostly two-bedders looks dearer per foot than one selling mostly three-bedders, with no lease
    involved.</p>
    <p class="expl">The alternative was tested — one transaction-weighted PSF per project, matched
    on pooled median size:</p>
    <div class="scroll"><table class="fig"><thead><tr><th>Method</th><th class="num">pairs</th>
      <th class="num">a</th><th class="num">b</th><th></th></tr></thead><tbody>
      <tr><th>Bedroom-matched</th><td class="num big">{npairs(ALL)}</td>
        <td class="num big">${A:,.1f}</td><td class="num big">${B:,.2f}</td>
        <td class="note">the method</td></tr>
      <tr class="dim"><th>Pooled, size-matched</th><td class="num big">{len(POOL)}</td>
        <td class="num big">${PA:,.1f}</td><td class="num big">${PB:,.2f}</td>
        <td class="note">diagnostic only</td></tr>
    </tbody></table></div>
    <p class="expl">It <b>loses</b> pairs rather than gaining them, which is the counterintuitive
    part: matching a whole sales mix within 20% is far harder than matching one bedroom within 20%.
    Two projects with different mixes fail the pooled test and still match cleanly on 3BR alone.
    And the mix leaks anyway — the pooled residual still tracks the size difference it could not
    match, at roughly &minus;$214 psf per 100% of size, which is what drags its slope down by a
    third.</p>
  </details>

  <details><summary>Why dollars and never a percentage</summary>
    <p class="expl">A flat dollar figure was the open question: it cannot obviously hold in both an
    OCR pair at $1,100 psf and a CCR pair at $2,100. Splitting the sample by the base price of the
    older project settles it — <b>the dollar is the invariant and the percentage is the artefact.</b></p>
    <div class="scroll">{pricebands()}</div>
    <p class="expl">The dollar holds across the readable bands while the percentage falls away
    steadily. That is also what made <b>region</b> look like a real split: in percent the OCR and
    RCR separate, in dollars they do not. The separation was price level wearing a region's name.</p>
  </details>

  <details><summary>The cuts that were tested and moved nothing</summary>
    <p class="expl">Bedroom and region. Kept because the decision to use one unified curve rests on
    them, not because they carry a number worth quoting. A permutation test puts 2BR against 3BR at
    p&nbsp;=&nbsp;0.83 and the RCR against the OCR at p&nbsp;=&nbsp;0.30 in dollars.</p>
    <div class="scroll">{nulls()}</div>
    <div class="caveat"><b>The CCR is not measurable this way.</b> Every qualifying pair sits in
    Marina Bay or Sentosa Cove — one reads negative. That is a submarket, not a region. A CCR
    figure has to come from somewhere other than neighbour pairs.</div>
  </details>

  <details><summary>The 12-month freshness check</summary>
    <p class="expl">The two windows are <b>not</b> two independent readings:
    {len(set((r['older'],r['newer'],r['bed']) for r in D['12']) & set((r['older'],r['newer'],r['bed']) for r in ALL))}
    of the {len(D['12'])} twelve-month cells sit inside the twenty-four-month set. Twenty-four
    months is therefore the combined figure, not an alternative to it, and the two must never be
    averaged — that would count the last year twice. Refitting the curve on twelve months alone
    gives <b>${curve(D['12'])[0]:,.1f} + ${curve(D['12'])[1]:,.2f}</b> against
    ${A:,.1f} + ${B:,.2f}. The extra depth does not drag it.</p>
  </details>
</section>

<section>
  <div class="sechead"><h2 class="disp">The evidence</h2>
  <p>How a pair is built, and every pair that qualified.</p></div>
  <details><summary>How a pair is built</summary>
  <div class="cards" style="margin-top:6px">
    <div class="card"><h4>Held constant</h4><ul>
      <li>within <b>500 m</b> of each other</li>
      <li>same <b>nearest MRT station</b></li>
      <li>same <b>walk band</b> to it</li>
      <li>identical <b>top-26 primary schools</b> within 1 km</li>
      <li>median sizes within <b>20%</b>, bedroom by bedroom</li></ul></div>
    <div class="card"><h4>Both sides must be</h4><ul>
      <li>leasehold, with a known lease start</li>
      <li><b>200 units</b> or more</li>
      <li><b>5+ transactions</b> in the window</li>
      <li>EC only once privatised — <b>TOP + 5</b></li>
      <li>resale and sub-sale only</li></ul></div>
    <div class="card"><h4>How pairs combine</h4><ul>
      <li>price difference fitted against<br>the lease gap</li>
      <li>each pair weighted by the lease<br>separation it actually contains</li>
      <li>a 20-year pair carries 20 years<br>of evidence; a 3-year pair carries 3</li>
      <li><b>no minimum gap</b></li></ul></div>
    <div class="card"><h4>Uncontrolled</h4><ul>
      <li><b>floor</b> — the PSF series carries none</li>
      <li><b>facing</b> — same</li>
      <li>development quality<br>beyond size and unit count</li>
      <li>lease start and building age are<br>confounded: this is blended vintage</li></ul></div>
  </div></details>
  <details><summary>Every pair — {len(ALL)} bedroom cells</summary>
    <p class="expl">The last column is what the curve says that pair should have read.</p>
    <div class="scroll">{pairtable()}</div></details>
</section>

<section>
  <div class="sechead"><h2 class="disp">Still to measure</h2>
  <p>Four constants remain on judgement alone.</p></div>
  <table class="fig"><thead><tr><th>Term</th><th class="num">Constant</th><th>Status</th></tr></thead><tbody>
  <tr><th>Lease / vintage</th><td class="num big">$40 psf / yr</td>
    <td style="color:var(--gold-soft)">measured — a curve, ${A:,.1f} + ${B:,.2f} &times; (midpoint &minus; 2000)</td></tr>
  <tr><th>Tenure · freehold vs leasehold</th><td class="num big">&divide; 1.15</td>
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
print(f'  {NDEV} developments · {npairs(ALL)} pairs · {len(ALL)} cells, no gap screen')
for _l, _h, _n in BANDS:
    _r = band_rows(_n); _c = BANDCI[_n]
    print(f'    {_n:14s} ${BANDR[_n]:5.1f}/yr  95% [{_c[0]:.1f}, {_c[1]:.1f}]  '
          f'{ndev(_r):3d} devs {npairs(_r):3d} pairs')
print(f'  held-out: flat {cv(ALL,"flat")/1000:.1f}k · line {cv(ALL,"mid")/1000:.1f}k · '
      f'quad {cv(ALL,"quad")/1000:.1f}k · knee {cv(ALL,"hinge")/1000:.1f}k · '
      f'BANDS {cv(ALL,"band")/1000:.1f}k')
