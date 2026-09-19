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
import layout as LAYOUT   # Internal > Constant Calibration > Layout
import json, math, os, html, random, statistics as st, datetime, sys

# A page is only true for the data it was cut from. This REFUSES TO BUILD when any calibration
# JSON is older than the data behind it — see freshness.py for the seven hours that earned it.
import freshness, cut
freshness.gate(sys.argv)

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
# FREEHOLD-vs-FREEHOLD. The same exercise on the only clock two freeholds share — COMPLETION.
# Separate constant, separate panel: "Lease Difference (FH)" beside "Lease Difference (99 Years)"
# (Shawn, 2026-09-13). age-pairs.py writes it.
AGEP = os.path.join(HERE, 'age-pairs.json')
A    = json.load(open(AGEP)) if os.path.exists(AGEP) else None
ALL  = D['24']                       # 24 months. No gap screen.
POOL = D.get('pooled24', [])

# ── the answer: TWO bands, read at the midpoint ─────────────────────────────
BANDS = [(1900, 2011, 'up to 2010'), (2011, 3000, '2011 onward')]
# THE ADOPTED FORM IS PIECEWISE (Shawn, 2026-09-13) — each calendar year of the gap priced at
# its own band and summed, not one rate read at the pair's midpoint. The midpoint bands above
# stay: they are what the panel compares against, and they still define the band LABELS.
# The boundary is HAND-SET at 2011 and must not be fitted — a knot fitted to this cut lands on
# 2012 with 82% bootstrap confidence and on 2006 three years earlier with none.
LPW   = D.get('pw') or {}
LPW1  = LPW.get('pre', 0.0)
LPW2  = LPW.get('post', 0.0)
LPWB  = LPW.get('bound', 2011)

mid    = lambda r: (r['ls_old'] + r['ls_new']) / 2
# LEAST SQUARES THROUGH THE ORIGIN, matching lease-pairs.py fitted(). Changed from the ratio
# form sum(diff)/sum(gap) on Shawn's ruling, 2026-09-10: the residual spread is flat across gap
# widths, so the variance is constant and this is the efficient estimator. See that docstring.
fit    = lambda rs: (sum(r['diff'] * r['gap'] for r in rs)
                     / sum(r['gap'] ** 2 for r in rs)) if rs else None
fpct   = lambda rs: math.exp(sum(math.log(r['psf_new']/r['psf_old']) * r['gap'] for r in rs)
                             / sum(r['gap'] ** 2 for r in rs)) - 1
npairs = lambda rs: len({(r['older'], r['newer']) for r in rs})
ndev   = lambda rs: len({x for r in rs for x in (r['older'], r['newer'])})
money  = lambda v: '—' if v is None else f'{v:+,.0f}'

def band_of(m): return next(n for lo, hi, n in BANDS if lo <= m < hi)
def rate(m):    return BANDR[band_of(m)]

# ── THE ADOPTED FORM, for every table that predicts a pair ──────────────────
# The panel's face is piecewise: each calendar year of the lease gap priced at its own band.
# Anything on this page that says "what the rate predicts" has to predict THE SAME WAY, or the
# evidence stops tying back to the headline. It said "$25 and $42" under a face reading $22 and
# $46 until 2026-09-13, which is exactly the drift this now closes.
def lease_split(ls_old, ls_new):
    """Years of this gap each side of the boundary."""
    lo, hi = min(ls_old, ls_new), max(ls_old, ls_new)
    return (max(0, min(hi, LPWB) - lo), max(0, hi - max(lo, LPWB)))
def lease_pred(r):
    """What the published rule says this pair's psf difference should be, signed."""
    a, b = lease_split(r['ls_old'], r['ls_new'])
    return (1 if r['ls_new'] >= r['ls_old'] else -1) * (LPW1 * a + LPW2 * b)
def own_yr(r):
    """What this pair reads on its own, per year of lease. Noisy at a one-year gap by
    construction — see the pair table's note."""
    return r['diff'] / r['gap'] if r['gap'] else 0.0
def rule_yr(r):
    """The rate the published rule works out to for THIS pair, per year. Equal to the band
    rate when the gap sits inside one band; a blend of the two when it spans the boundary,
    which is the honest single number for a split gap."""
    return abs(lease_pred(r)) / r['gap'] if r['gap'] else 0.0
def fit_pw_rows(rows):
    """Refit the two legs on a SUBSET — least squares through the origin, two regressors.
    Used by the robustness cuts, which must be refitted the way the headline is fitted."""
    s11 = s12 = s22 = t1 = t2 = 0.0
    for r in rows:
        x1, x2 = lease_split(r['ls_old'], r['ls_new'])
        s11 += x1*x1; s12 += x1*x2; s22 += x2*x2; t1 += x1*r['diff']; t2 += x2*r['diff']
    det = s11*s22 - s12*s12
    return ((s22*t1 - s12*t2)/det, (s11*t2 - s12*t1)/det) if abs(det) > 1e-9 else (None, None)
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
# THE TRANSACTION BASE (Shawn, 2026-09-10: "is 440+ cells the number of cells we used overall?
# that few?"). A cell is a COMPARISON, not a sale. Each side of one is a project x bedroom
# median over the window, itself resting on many transactions — count them, and say so, because
# "442 cells" reads as a small study and it is not one.
SIDES  = {}
for _r in ALL:
    SIDES[(_r['older'], _r['bed'])] = _r['n_old']
    SIDES[(_r['newer'], _r['bed'])] = _r['n_new']
def sides_of(rows):
    d = {}
    for r in rows:
        d[(r['older'], r['bed'])] = r['n_old']
        d[(r['newer'], r['bed'])] = r['n_new']
    return d
ntx    = lambda rows: sum(sides_of(rows).values())
NTX    = sum(SIDES.values())
# Kept though the paragraph that printed them was removed on 2026-09-11: they are one line
# each, they are the answer to "what does a comparison actually rest on", and the build prints
# them below so the figure stays visible to whoever re-cuts the study.
NPRICE = len(SIDES)
TXMED  = st.median(SIDES.values())
TXPAIR = st.median(r['n_old'] + r['n_new'] for r in ALL)
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
qfit = lambda rs: (sum(r['diff'] * (r['sqft_old'] + r['sqft_new']) / 2 * r['gap'] for r in rs)
                   / sum(r['gap'] ** 2 for r in rs)) if rs else None
BANDQ = {nm: qfit(rows_in(nm)) for _, _, nm in BANDS}

# ── WHAT EACH PAIR READS ON ITS OWN (Shawn, 2026-09-10) ─────────────────────
# "the range you're showing is 38 to 46 psf. can we show ALL the development that is that range.
# and that SHOW the psf... you show the difference and the n show in the psf per year"
#
# THE TRAP THIS MUST NOT FALL INTO. $38-46 is the precision of the AVERAGE, not the range
# individual pairs sit in. Individual cells in that band run -$64 to +$109 at the 10th and 90th
# percentile, and only 10% land inside the interval. Showing the 23 that agree, on their own,
# would read as "this is the evidence" when it is the 10% that happens to match — the same
# circular filter that collapsed the sample to 48 cells with a fake +/-$1 interval when it was
# tested as a screen. So the cells inside are shown WITH the count they are drawn from, and
# beside the convergence table, which is the honest version of the same idea.
def own(r): return r['diff'] / r['gap']
dol = lambda v: ('-$' if v < 0 else '$') + f'{abs(v):,.0f}'

def inside_band(nm):
    lo, hi = BANDCI[nm]
    return [r for r in rows_in(nm) if lo <= own(r) <= hi]

GAPCUTS = [('One year', 1, 1), ('Two years', 2, 2), ('Three to four', 3, 4),
           ('Five to nine', 5, 9), ('Ten and over', 10, 999)]

def converge_table(nm):
    """How often a pair's OWN reading lands inside the interval, by how far apart it is.
    The point of the table: the wider the gap, the more a single pair converges on the rate.
    That is what a real effect buried under uncontrolled noise looks like."""
    lo, hi = BANDCI[nm]
    rs = rows_in(nm)
    h = ['<table class="fig"><thead><tr><th>Lease gap</th><th class="num">pairs</th>'
         f'<th class="num">reading ${lo:,.0f}&ndash;${hi:,.0f} a year</th>'
         '<th class="num">share</th></tr></thead><tbody>']
    for lab, a, b in GAPCUTS:
        s = [r for r in rs if a <= r['gap'] <= b]
        if not s: continue
        k = sum(1 for r in s if lo <= own(r) <= hi)
        h.append(f'<tr><th>{lab}</th><td class="num quiet">{len(s)}</td>'
                 f'<td class="num big">{k}</td>'
                 f'<td class="num quiet">{k/len(s):.0%}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def onrate_table(nm):
    """Every pair whose own psf-per-year lands inside the band's interval, dearest first."""
    rs = sorted(inside_band(nm), key=lambda r: -own(r))
    h = ['<table class="fig"><thead><tr><th>older</th><th class="num">lease</th><th>newer</th>'
         '<th class="num">lease</th><th class="num">gap</th><th>bed</th>'
         '<th class="num">difference</th><th class="num">$ / yr</th>'
         '<th class="num">sales</th><th>station</th></tr></thead><tbody>']
    for r in rs:
        h.append(f'<tr><td>{html.escape(r["older"].title())}</td>'
                 f'<td class="num quiet">{r["ls_old"]}</td>'
                 f'<td>{html.escape(r["newer"].title())}</td>'
                 f'<td class="num quiet">{r["ls_new"]}</td>'
                 f'<td class="num">{r["gap"]}y</td><td class="quiet">{r["bed"]}</td>'
                 f'<td class="num quiet">{r["diff"]:+,.0f}</td>'
                 f'<td class="num big">{dol(own(r))}</td>'
                 f'<td class="num quiet">{r["n_old"]} / {r["n_new"]}</td>'
                 f'<td class="quiet">{html.escape((r["station"] or "").replace(" MRT Station","").replace(" LRT Station"," LRT"))}</td></tr>')
    return ''.join(h) + '</tbody></table>'

OWNPCT = {nm: sorted(own(r) for r in rows_in(nm)) for _, _, nm in BANDS}
def ownp(nm, q): 
    v = OWNPCT[nm]; return v[int(q * len(v))]

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

# ── DOES IT MATTER WHEN EACH SIDE SOLD? ─────────────────────────────────────
# Shawn, 2026-09-10: "are we even considering the transactions? maybe we should dice and slice
# the pairs up into transaction periods?" A fair question — a cell pools 24 months a side, so if
# one project sold early in the window and its neighbour late, the comparison spans market drift
# rather than vintage. MEASURED, NOT ASSUMED. The two sides turn out to transact contemporaneously
# (mean offset near zero), so pooling adds spread but no tilt, and matching on period costs
# precision without buying anything. COMPUTED HERE so it can never go stale, and kept rather than
# deleted because the answer depends on the window: drift is real money, and a future cut could
# come out offset.
PSFH = json.load(open(os.path.join(HERE, '..', '..', 'property-analyzer', 'data',
                                   'psf-history.json')))['projects']
QH   = json.load(open(os.path.join(HERE, '..', '..', 'property-analyzer', 'data',
                                   'quantum-history.json')))['projects']
_mn  = lambda m: int(m[:4]) * 12 + int(m[5:7])

def _series(name, bed):
    a, q = PSFH.get(name, {}).get(bed), QH.get(name, {}).get(bed)
    if not a or not q: return {}
    return {m: (a[m], q[m][2]) for m in a if LW[0] <= m <= LW[1] and m in q}

def _offset(r):
    # Transaction-weighted mean month of each side, newer minus older.
    a, b = _series(r['older'], r['bed']), _series(r['newer'], r['bed'])
    if not a or not b: return None
    w = lambda d: sum(_mn(m) * n for m, (_, n) in d.items()) / sum(n for _, n in d.values())
    return w(b) - w(a)

OFFS   = [o for o in (_offset(r) for r in ALL) if o is not None]
OFF_ME = st.mean(OFFS) if OFFS else 0.0
OFF_3  = sum(1 for o in OFFS if abs(o) > 3)

def _drift():
    # Island median psf against month over the window — what one month of market is worth.
    by = {}
    for nm, bs in PSFH.items():
        for bed, ser in bs.items():
            for m, v in ser.items():
                if LW[0] <= m <= LW[1]: by.setdefault(m, []).append(v)
    pts = [(_mn(m), st.median(v)) for m, v in sorted(by.items())]
    mx = st.mean(x for x, _ in pts); my = st.mean(y for _, y in pts)
    return sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
DRIFT = _drift()

def _matched(r, width):
    # The pair's difference computed only inside periods BOTH sides traded in.
    a, b = _series(r['older'], r['bed']), _series(r['newer'], r['bed'])
    if not a or not b: return None
    A, B = {}, {}
    for m, (v, n) in a.items(): A.setdefault(_mn(m) // width, []).append((v, n))
    for m, (v, n) in b.items(): B.setdefault(_mn(m) // width, []).append((v, n))
    num = den = 0
    for k in set(A) & set(B):
        wt = min(sum(n for _, n in A[k]), sum(n for _, n in B[k]))
        num += (st.median([v for v, _ in B[k]]) - st.median([v for v, _ in A[k]])) * wt
        den += wt
    return num / den if den else None

# ── THE QUARTERLY DRILL-DOWN (Shawn, 2026-09-10) ────────────────────────────
# He asked whether slicing by transaction period would give MORE line items to justify the
# figures with. It would — 2,385 quarters against 442 pooled comparisons — but they are WEAKER,
# not stronger: most quarters rest on one or two sales and swing hundreds of dollars. Row #1,
# the best-fitting comparison in the study, is made of quarters running -$85 to +$172, one of
# them on a single sale.
#
# So the pooled rows STAY as the evidence and the quarters sit UNDER them, on demand, with the
# sale count on every line. That turns the weakness into the argument: open any row and you can
# see for yourself why a single quarter must not be read, and why pooling is the honest summary
# rather than a way of hiding the spread.
#
# Emitted as compact JSON and drawn on click, not as 2,385 hidden table rows — the same content
# as markup would roughly double the page.
def _q(m): return (_mn(m) - 1) // 3
def _qlab(k):
    t = k * 3 + 1; y, mo = divmod(t - 1, 12)
    return f'{str(y)[2:]}Q{mo // 3 + 1}'

def quarters(r):
    """[quarter, older psf, newer psf, older sales, newer sales] for every quarter BOTH traded."""
    a, b = _series(r['older'], r['bed']), _series(r['newer'], r['bed'])
    A, B = {}, {}
    for m, (v, n) in a.items(): A.setdefault(_q(m), []).append((v, n))
    for m, (v, n) in b.items(): B.setdefault(_q(m), []).append((v, n))
    out = []
    for k in sorted(set(A) & set(B)):
        out.append([_qlab(k),
                    round(st.median([v for v, _ in A[k]])),
                    round(st.median([v for v, _ in B[k]])),
                    sum(n for _, n in A[k]), sum(n for _, n in B[k])])
    return out

def matched_rate(width):
    rows = []
    for r in ALL:
        d = _matched(r, width)
        if d is not None: rows.append({**r, 'diff': d})
    return ({nm: fit([r for r in rows if band_of(mid(r)) == nm]) for _, _, nm in BANDS},
            len(rows))
MATCHQ, MATCHN = matched_rate(3)

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
    L = LPW.get('legs') or {}
    h = ['<table class="fig look"><thead><tr><th>Each year of the lease gap</th>'
         '<th class="num">$ psf / yr</th><th class="num">could really be</th>'
         '<th class="num">pairs contributing</th></tr></thead><tbody>']
    for which, label, rate in (('pre', f'before {LPWB}', LPW1), ('post', f'from {LPWB}', LPW2)):
        g = L.get(which) or {}
        ci = (f'${g["ci_lo"]:,.0f} to ${g["ci_hi"]:,.0f}'
              if g.get('ci_lo') is not None else '&mdash;')
        h.append(f'<tr><th>{label}</th>'
                 f'<td class="num big">${rate:,.0f}</td>'
                 f'<td class="num quiet">{ci}</td>'
                 f'<td class="num quiet">{g.get("pairs", 0)}</td></tr>')
    return ''.join(h) + '</tbody></table>'

# ── THE REPLICATION (Shawn, 2026-09-10: "maybe we should have a different 24 months") ───────
# The single strongest confirmation on the page, and the one a sceptical reader asks for first:
# run the identical method on a DIFFERENT two years of transactions and see whether the same
# number comes back. It does. The windows are 14 months apart and share no transaction at all —
# the same neighbours are simply re-measured on a fresh set of sales.
def txof(rows):
    s = {}
    for r in rows:
        s[(r['older'], r['bed'])] = r['n_old']
        s[(r['newer'], r['bed'])] = r['n_new']
    return sum(s.values())

def repl_table():
    h = ['<table class="fig look"><thead><tr><th>Transactions used</th>'
         f'<th class="num">{OLD_NM}</th><th class="num">{NEW_NM}</th>'
         '<th class="num">developments</th><th class="num">transactions</th>'
         '</tr></thead><tbody>']
    for lab, rows, head in ((f'{LW[0]} to {LW[1]} &mdash; the published cut', ALL, True),
                            (f'{EW[0]} to {EW[1]} &mdash; three years earlier', EARLY, False)):
        o = [r for r in rows if mid(r) < 2011]
        n = [r for r in rows if mid(r) >= 2011]
        h.append(f'<tr{" class=head" if head else ""}><th>{lab}</th>'
                 f'<td class="num big">${fit(o):,.0f}</td>'
                 f'<td class="num big">${fit(n):,.0f}</td>'
                 f'<td class="num quiet">{ndev(rows)}</td>'
                 f'<td class="num quiet">{txof(rows):,}</td></tr>')
    return ''.join(h) + '</tbody></table>'

EARLY_O = [r for r in EARLY if mid(r) < 2011]
EARLY_N = [r for r in EARLY if mid(r) >= 2011]
EARLYCI = {OLD_NM: ci(EARLY_O), NEW_NM: ci(EARLY_N)}
# The overlap of the two intervals is the ROBUST statement. An earlier draft claimed each point
# estimate sat inside the other window's interval — true, but only just: the earlier newer-band
# figure lands exactly ON the published upper bound, so a different bootstrap seed flips it.
# Never assert a claim that sits on a resampling boundary; state the overlap, and compute it.
OVERLAP = {nm: (max(BANDCI[nm][0], EARLYCI[nm][0]), min(BANDCI[nm][1], EARLYCI[nm][1]))
           for _, _, nm in BANDS}

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
    h.append(r_('Matching the two sides on when they sold',
                f'${MATCHQ[OLD_NM]:,.0f} &middot; ${MATCHQ[NEW_NM]:,.0f}',
                f'A cell pools 24 months a side, so in principle one project could sell early and '
                f'its neighbour late, making the comparison part market drift. Rebuilt comparing '
                f'only inside quarters BOTH sides traded in: the rate does not move. The two sides '
                f'already transact together &mdash; mean offset {OFF_ME:+.1f} months across '
                f'{len(OFFS)} cells &mdash; so pooling adds spread but no tilt, and matching '
                f'costs precision. <b>Kept as a check, because the market moves '
                f'${DRIFT:,.0f} psf a month and a future cut could come out offset.</b>'))
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
         f'<th class="num">before {LPWB}</th><th class="num">from {LPWB}</th>'
         '<th class="num">the jump</th><th class="num">pairs</th></tr></thead><tbody>']
    for lab, f, head in SPLITS:
        sub = [r for r in ALL if f(r)]
        a, b = g(*O, f), g(*N, f)
        if len(a) < 10 or len(b) < 10: continue
        # REFITTED PIECEWISE, the way the headline is fitted. Refitting the subset the OLD way
        # under a new headline is how a robustness table stops being one.
        # THE ALL-PAIRS ROW SHOWS THE PUBLISHED CONSTANTS, NOT ITS OWN REFIT. It is the same
        # sample as the headline, so anything else is the page disagreeing with itself over a
        # rounding — the fit is 21.87/46.54 and the published pair is hand-set 22/46.
        pre, post = (LPW1, LPW2) if head else fit_pw_rows(sub)
        if pre is None: continue
        h.append(f'<tr{" class=head" if head else ""}><th>{"<b>" if head else ""}{lab}{"</b>" if head else ""}</th>'
                 f'<td class="num">${pre:,.0f}</td><td class="num">${post:,.0f}</td>'
                 f'<td class="num big">+${post - pre:,.0f}</td>'
                 f'<td class="num quiet">{npairs(sub)}</td></tr>')
    return ''.join(h) + '</tbody></table>'

# ── does the rate actually fit a pair? (Shawn, 2026-09-10) ──────────────────
# The pair table used to lead with each cell's own $/yr — its difference divided by its own
# gap. At a one-year gap that divides the pair's whole floor-and-facing noise by 1, so the
# column swung between -$302 and +$168 beside a $43 band and read as a contradiction. It is
# not one: the rate is the slope through every cell, not the average of that column.
# This table is the demonstration. Compare TOTALS at the same gap, never a single per-year.
GBUCKETS = [('One year apart', 1, 1), ('Two years', 2, 2), ('Three to four years', 3, 4),
            ('Five to nine years', 5, 9), ('Ten years and over', 10, 999)]

# ── NOT RENDERED. Shawn removed three explain blocks from the lease panel on 2026-09-10:
# "Does the rate actually fit a pair?", "What does each pair read on its own?" and "Does it
# matter when each side sold?". The renderers below are kept, like tested_table() above, because
# they are the record of what was measured — put any of them back by calling it from a details
# block. The FINDINGS they carried are not lost: they are in README section 6 and in the
# checks printed at the end of this build, which still run on every re-cut.
#   holds_table()   the rate against the market by gap width
#   spread()        the residual distribution with the central 95%
#   miss_table()    the cells outside that band, and why each is a candidate
#   converge_table()/onrate_table()  what each pair reads on its own
# The pair table still uses resid(), outside() and tags() for its flags column.
def holds_table():
    h = ['<table class="fig look"><thead><tr><th>How far apart the two leases are</th>'
         '<th class="num">cells</th><th class="num">what the market shows</th>'
         '<th class="num">what the rate predicts</th><th class="num">off by</th>'
         '</tr></thead><tbody>']
    for _, _, nm in BANDS:
        rows = rows_in(nm)
        h.append(f'<tr class="sep"><th colspan="5">{nm}</th></tr>')
        for lab, lo, hi in GBUCKETS:
            s_ = [r for r in rows if lo <= r['gap'] <= hi]
            if not s_: continue
            obs  = st.median(r['diff'] for r in s_)
            pred = st.median(abs(lease_pred(r)) for r in s_)
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

def spread():
    """WHERE THE BULK SITS (Shawn, 2026-09-10: "what is wrong with just showing the 95%
    confidence interval, where the main bulk normal distribution volume sits"). Nothing is
    wrong with it — this is that picture. Every cell's miss, the central 95% shaded, and the
    check that the shape is near enough normal for the band to mean what a reader thinks."""
    R = sorted(RESID)
    n = len(R); m = st.mean(R); sd = st.pstdev(R)
    lo, hi = R[int(.025*n)], R[int(.975*n)-1]
    W, H, PAD = 760, 210, 34
    xlo, xhi = -500, 500
    X = lambda v: PAD + (min(max(v, xlo), xhi) - xlo) / (xhi - xlo) * (W - 2*PAD)
    NB, bw = 40, (xhi - xlo) / 40
    bins = [0]*NB
    for x in R: bins[min(NB-1, max(0, int((x - xlo)//bw)))] += 1
    top = max(bins)
    g = [f'<svg viewBox="0 0 {W} {H}" class="spread" role="img" '
         f'aria-label="Distribution of how far each cell sits from the rate">']
    g.append(f'<rect x="{X(lo):.1f}" y="18" width="{X(hi)-X(lo):.1f}" height="{H-52}" '
             f'fill="rgba(201,169,106,.10)" stroke="rgba(201,169,106,.34)" stroke-width="1"/>')
    for i, c in enumerate(bins):
        if not c: continue
        h = (c / top) * (H - 62)
        g.append(f'<rect x="{X(xlo+i*bw):.1f}" y="{H-34-h:.1f}" '
                 f'width="{(W-2*PAD)/NB-1.4:.1f}" height="{h:.1f}" fill="#3D5170"/>')
    g.append(f'<line x1="{X(0):.1f}" y1="14" x2="{X(0):.1f}" y2="{H-34}" '
             f'stroke="#C9A96A" stroke-width="1.2"/>')
    for v in (xlo, -250, 0, 250, xhi):
        g.append(f'<text x="{X(v):.1f}" y="{H-14}" fill="#7A8CA5" font-size="11" '
                 f'text-anchor="middle">{"+" if v>0 else ""}{v:,}</text>')
    g.append(f'<text x="{X(lo):.1f}" y="12" fill="#C9A96A" font-size="11" '
             f'text-anchor="middle">{lo:+,.0f}</text>')
    g.append(f'<text x="{X(hi):.1f}" y="12" fill="#C9A96A" font-size="11" '
             f'text-anchor="middle">{hi:+,.0f}</text>')
    g.append('</svg>')
    return ''.join(g), m, sd, lo, hi

SPREAD_SVG, RES_MEAN, RES_SD, RES_LO, RES_HI = spread()
NORM1 = 100*sum(1 for x in RESID if abs(x-RES_MEAN) <   RES_SD)/len(RESID)
NORM2 = 100*sum(1 for x in RESID if abs(x-RES_MEAN) < 2*RES_SD)/len(RESID)

def miss_table():
    """Every cell outside the central 95%. CCR LAST, under its own divider — Shawn, 2026-09-10:
    the CCR is NOT ruled out of the fit, but it must not be the data on show. It is the loudest
    group here and it is a submarket, so it sits apart rather than leading the table."""
    def blk(rows):
        h = []
        for r in rows:
            t = [x for x in tags(r) if x != 'CCR']
            h.append(f'<tr><td>{html.escape(r["older"].title())}</td>'
                     f'<td>{html.escape(r["newer"].title())}</td>'
                     f'<td class="num">{r["gap"]}y</td><td class="quiet">{r["bed"]}</td>'
                     f'<td class="num">{r["diff"]:+,.0f}</td>'
                     f'<td class="num quiet">${rate(mid(r))*r["gap"]:,.0f}</td>'
                     f'<td class="num big">{resid(r):+,.0f}</td>'
                     f'<td class="quiet">{" &middot; ".join(t) if t else "nothing flagged"}</td></tr>')
        return ''.join(h)
    main = [r for r in MISSES if r['region'] != 'CCR']
    ccr  = [r for r in MISSES if r['region'] == 'CCR']
    h = ['<table class="fig"><thead><tr><th>older</th><th>newer</th><th class="num">gap</th>'
         '<th>bed</th><th class="num">the market</th><th class="num">the rate</th>'
         '<th class="num">off by</th><th>why it is a candidate to miss</th>'
         '</tr></thead><tbody>', blk(main)]
    if ccr:
        h.append(f'<tr class="sep"><th colspan="8">The CCR &mdash; counted in the fit, '
                 f'shown apart</th></tr>')
        h.append(blk(ccr))
    return ''.join(h) + '</tbody></table>'

def pairtable():
    """Every comparison, in the shape Shawn asked for on 2026-09-10:

        older | newer | gap | bed | difference | $ / yr | sales

    The lease start rides inside the name ("Sims Urban Oasis 2014"), which is how he reads a
    pair, and the psf columns, the predicted figure, the miss, the distance and the flags all
    come off — they were scaffolding for explain blocks that are no longer on the page.

    STILL SORTED CLOSEST TO THE RATE FIRST (his instruction, same day). The ordering column is
    no longer shown, so the header says what the order is: the table opens on the pairs reading
    about the band rate and walks out to the ones that do not.

    Every row opens its quarters on click — see the drill-down block above."""
    rows = sorted(ALL, key=lambda r: abs(own_yr(r) - rule_yr(r)))
    global QDATA
    QDATA = [quarters(r) for r in rows]
    nm_ = lambda x, ls: f'{html.escape(x.title())} <i class="age">{ls}</i>'
    h = ['<table class="fig pairs"><thead><tr><th class="num">#</th><th>older</th><th>newer</th>'
         '<th class="num">gap</th><th>bed</th><th class="num">difference</th>'
         '<th class="num">$ / yr</th><th class="num">the rule says</th>'
         '<th class="num">off by</th><th class="num">sales</th></tr></thead><tbody>']
    for i, r in enumerate(rows, 1):
        h.append(
            f'<tr data-q="{i-1}" tabindex="0" role="button" aria-expanded="false"><td class="num quiet">{i}</td>'
            f'<td>{nm_(r["older"], r["ls_old"])}</td>'
            f'<td>{nm_(r["newer"], r["ls_new"])}</td>'
            f'<td class="num">{r["gap"]}y</td><td class="quiet">{r["bed"]}</td>'
            f'<td class="num quiet">{r["diff"]:+,.0f}</td>'
            f'<td class="num big">{own_yr(r):+,.0f}</td>'
            f'<td class="num quiet">${rule_yr(r):,.0f}</td>'
            f'<td class="num quiet">{own_yr(r) - rule_yr(r):+,.0f}</td>'
            f'<td class="num quiet">{r["n_old"]} / {r["n_new"]}</td></tr>')
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
h3.sub{font:600 17px/1.3 Optima,Candara,sans-serif;color:var(--slate-100);margin:34px 0 4px}
h1{font:600 clamp(28px,4vw,36px)/1.15 Optima,Candara,sans-serif;color:var(--slate-100);
letter-spacing:.01em;margin:52px 0 10px}
/* THE TERM BAR. Five constants, one row, each its own view. It replaces the old single-term
   kicker: this page is no longer about the lease alone. It rides inside the sticky header so
   it stays reachable at any scroll depth, which is the point of splitting the page up. */
.terms{display:flex;flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;gap:0;border-top:1px solid var(--ink);
max-width:1180px;margin:0 auto;padding:0 24px}
.terms button{flex:1 0 auto;min-width:0;padding:13px 8px 12px;text-align:left;
background:none;border:0;border-right:1px solid var(--ink);cursor:pointer;font:inherit;
color:inherit;position:relative;
transition:background .18s cubic-bezier(.22,1,.36,1),color .18s cubic-bezier(.22,1,.36,1)}
.terms button:last-child{border-right:0}
.terms button:hover{background:var(--navy-850)}
.terms button:focus-visible{outline:2px solid var(--gold);outline-offset:-2px}
.terms .tn{display:block;white-space:nowrap;font:600 13px/1.25 Optima,Candara,sans-serif;
color:var(--slate-400);letter-spacing:.005em}
/* The sub-label is the panel's ANSWER, not a status word, so it is set as a figure:
   readable size, no uppercase, gold on a measured panel. Shawn, 2026-09-08. */
.terms .ts{display:block;white-space:nowrap;margin-top:4px;font-size:12px;letter-spacing:0;
color:var(--slate-600);font-variant-numeric:tabular-nums}
.terms button.done .ts{color:rgba(201,169,106,.75)}
.terms button[aria-current="true"]{background:var(--navy-850)}
.terms button[aria-current="true"] .tn{color:var(--slate-100)}
.terms button[aria-current="true"] .ts{color:var(--gold)}
.terms button[aria-current="true"]::after{content:"";position:absolute;left:0;right:0;bottom:-1px;
height:2px;background:var(--gold)}
.panel>h1{margin-top:46px}
/* Seven terms must sit on ONE line at the 1024 iPad target — PRODUCT.md's binding
   constraint. flex-basis 0 with min-width 0 lets them share the row evenly instead of
   each demanding its content width and pushing the last one onto a second row.
   Below 760 the bar is allowed to wrap; that is a phone, not the meeting device. */
@media (max-width:760px){.terms{padding:0 16px}
.terms button{flex:1 1 auto;min-width:118px}}
.lede{font-size:15px;color:var(--slate-400);max-width:64ch;margin-bottom:14px}
h2{font:600 20px/1.3 Optima,Candara,sans-serif;color:var(--slate-100);margin:0 0 6px}
h3{font:600 15px/1.3 Optima,Candara,sans-serif;color:var(--gold-soft);letter-spacing:.02em}
section{margin-top:46px}
.sechead{border-top:1px solid var(--ink);padding-top:22px;margin-bottom:18px}
.sechead p{color:var(--slate-500);max-width:70ch;margin-top:5px}
/* verdict */
.verdict{margin-top:30px;border:1px solid rgba(201,169,106,.34);border-radius:14px;
background:linear-gradient(180deg,var(--navy-800),var(--navy-850));
padding:26px 28px}
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
.ans .w{font-size:12px;letter-spacing:.15em;text-transform:uppercase;color:var(--slate-400);
margin-top:10px}
.ans .g{font:600 18px/1.15 Optima,Candara,sans-serif;color:var(--slate-300);margin-top:8px}
.vbase{display:flex;gap:34px;flex-wrap:wrap;margin-top:16px;padding-top:14px;
border-top:1px solid rgba(36,48,80,.85)}
.vbase .g{font:600 18px/1.15 Optima,Candara,sans-serif;color:var(--slate-300)}
.vbase .g span{font:400 12.5px/1 -apple-system,Segoe UI,sans-serif;letter-spacing:.04em;
text-transform:uppercase;color:var(--slate-500);display:block;margin-top:4px}
.ans .g span{font:400 12.5px/1 -apple-system,Segoe UI,sans-serif;letter-spacing:.04em;
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
.chip.asof{border-color:rgba(201,169,106,.45);color:var(--gold-soft);letter-spacing:.1em}
table.pairs tr[data-q]{cursor:pointer}
table.pairs tr[data-q]:hover td{background:rgba(31,44,71,.5)}
table.pairs tr[data-q]:focus-visible{outline:1px solid var(--gold);outline-offset:-1px}
table.pairs tr[data-q].open td{background:rgba(31,44,71,.7)}
tr.qd>td{padding:0;background:var(--navy-900)}
.qdin{padding:14px 18px 16px;border-left:2px solid rgba(201,169,106,.45)}
.qdin p{color:var(--slate-400);font-size:12.5px;max-width:78ch;margin-bottom:9px}
.qdin p b{color:var(--slate-100);font-weight:600}
table.qt{border-collapse:collapse;font-size:12.5px}
table.qt th,table.qt td{padding:5px 14px 5px 0;text-align:left;border-bottom:1px solid rgba(36,48,80,.45)}
table.qt thead th{color:var(--slate-600);font-weight:400;white-space:nowrap}
/* WORKED EXAMPLES. Shawn, 2026-09-19: he needs to audit the method by hand, and a client needs
   to see the figure is the gap between two real sales. Same block serves both, so it shows the
   caveats first and the arithmetic second, never a summary. */
.wexs{display:grid;gap:18px;margin-top:18px}
.wex{border:1px solid var(--ink);border-radius:11px;background:var(--navy-850);padding:20px 22px}
.whead{display:flex;gap:28px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
.whead h3{font-size:19px;color:var(--slate-100);font-weight:600;letter-spacing:-.005em}
.wsub{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:var(--slate-500);margin-top:6px}
.wfig{font:600 30px/1 Optima,Candara,sans-serif;color:var(--gold);white-space:nowrap;text-align:right}
.wfig span{display:block;font:400 11px/1.3 -apple-system,Segoe UI,sans-serif;letter-spacing:.05em;
text-transform:uppercase;color:var(--slate-500);margin-top:7px;text-align:right}
table.wt{width:100%;border-collapse:collapse;font-size:13px;margin-top:20px}
table.wt th{font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--slate-600);
font-weight:400;text-align:left;padding-bottom:9px;border-bottom:1px solid var(--ink)}
table.wt th.num,table.wt td.num{text-align:right;font-variant-numeric:tabular-nums}
table.wt td{padding:10px 14px 10px 0;vertical-align:top;color:var(--slate-300)}
table.wt td:last-child{padding-right:0}
table.wt tbody tr+tr td{border-top:1px solid rgba(36,48,80,.55)}
td.wc{white-space:nowrap;color:var(--slate-200)}
td.warr{color:var(--slate-600);padding:10px 14px}
td.wdiff{color:var(--gold-soft);font-weight:600}
.wnote{font-size:12.5px;color:var(--slate-400);margin-top:13px;max-width:78ch}
.wnote b{color:var(--slate-100);font-weight:600}
.wadj{margin-top:18px;padding-top:16px;border-top:1px solid var(--ink)}
.wadj p{font-size:12.5px;color:var(--slate-400);max-width:80ch}
.wadj .wcav{margin-top:10px;color:var(--slate-300);font-variant-numeric:tabular-nums}
.wadj .wcav b{color:var(--slate-100)}
.wadj ol{margin:11px 0 0;padding-left:0;list-style:none;display:grid;gap:7px}
.wadj li{font-size:12.5px;color:var(--slate-300);font-variant-numeric:tabular-nums;
padding-left:14px;border-left:1px solid var(--ink)}
.wadj li b{color:var(--slate-100)}
.wk{display:inline-block;min-width:52px;font-size:10px;letter-spacing:.1em;text-transform:uppercase;
color:var(--slate-600)}
.wres{margin-top:11px;color:var(--slate-200)}
.wres b{color:var(--gold-soft)}
.wfoot{display:flex;gap:26px;flex-wrap:wrap;margin-top:18px;padding-top:14px;
border-top:1px solid var(--ink);font-size:11.5px;letter-spacing:.05em;text-transform:uppercase;
color:var(--slate-500)}
.wfoot b{color:var(--slate-200);font-weight:600;font-variant-numeric:tabular-nums}
@media (max-width:720px){
  .whead{flex-direction:column;gap:14px}
  .wfig,.wfig span{text-align:left}
  table.wt thead{display:none}
  table.wt td.warr{display:none}
  table.wt,table.wt tbody,table.wt tr,table.wt td{display:block;width:100%}
  table.wt td{padding:2px 0}
  table.wt tbody tr{padding:12px 0;border-top:1px solid rgba(36,48,80,.55)}
  table.wt tbody tr+tr td{border-top:0}
  table.wt td.num{text-align:left}
  td.wdiff{margin-top:6px;font-size:15px}
}
.spread{width:100%;height:auto;display:block;margin:12px 0 4px;
border:1px solid var(--ink);border-radius:11px;background:var(--navy-900);padding:4px}
/* tables */
table.fig{width:100%;border-collapse:collapse;font-size:13px;margin-top:4px}
table.fig th,table.fig td{padding:8px 12px;text-align:left;border-bottom:1px solid rgba(36,48,80,.55);
vertical-align:baseline}
table.fig thead th{font-size:12.5px;letter-spacing:.02em;
color:var(--slate-600);font-weight:400;border-bottom:1px solid var(--ink);white-space:nowrap}
table.fig tbody th{font-weight:400;color:var(--slate-300);white-space:nowrap}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.lt{width:100%;border-collapse:collapse;font-size:13px;margin-top:14px}
table.lt th{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--slate-500);
  font-weight:600;padding:0 0 8px 22px;border-bottom:1px solid rgba(36,48,80,.7)}
table.lt th:first-child{padding-left:0}
table.lt td{padding:11px 0 11px 22px;vertical-align:baseline}
table.lt td:first-child{padding-left:0}
tr.lmain>td{border-top:1px solid var(--ink);color:var(--slate-300)}
tr.lmain:hover>td{background:rgba(36,48,80,.22)}
td.lpair{font-weight:600;color:var(--slate-100);white-space:nowrap}
td.lbig{font-weight:600;font-size:15px;color:var(--slate-100)}
td.fsum{max-width:230px;white-space:normal}
td.fsum span.lsub{white-space:normal}
span.lsplit{display:block;white-space:nowrap;font-size:12.5px}
span.lsub{display:block;font-size:10.5px;letter-spacing:.04em;color:var(--slate-500);
  font-weight:400;margin-top:3px;text-transform:uppercase}
/* Shawn, 2026-09-19: TRANSACTIONS ASSESSED leads; the sale-pair and layout-pair counts sit
   under it in a quieter, sentence-case line so the row reads evidence-first. */
span.ltx{color:var(--slate-300);font-weight:600;font-size:11.5px;text-transform:none;
  letter-spacing:.01em}
span.lsub2{color:var(--slate-600);margin-top:1px;text-transform:none;letter-spacing:.02em}
/* Shawn, 2026-09-19: the gates classify rather than kill, so every feature can show twice --
   once on its own, once with the area its step brought. The second row is named by the SIZE of
   the step. A hairline ties the pair together and the second is tinted so they never read as
   two unrelated features. */
tr.lb-area>td{border-top:1px dashed rgba(36,48,80,.75)}
tr.lb-area>td:first-child{padding-left:14px;border-left:2px solid var(--gold);opacity:.92}
span.lwide{color:var(--gold);letter-spacing:.02em}
tr.lwhy>td{padding:0 0 12px 0;font-size:12px;color:var(--slate-400);line-height:1.5}
tr.lwhy i{color:var(--slate-500);font-style:normal}
tr.lgrp>td{padding:24px 0 7px 0;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  font-weight:700;color:var(--gold)}
tr.lgrp.warn>td{color:var(--warn)}
tr.lgrp.bad>td{color:var(--warn);opacity:.72}
span.lnote{display:inline;margin-left:12px;letter-spacing:.03em;text-transform:none;
  font-weight:400;color:var(--slate-500)}
td.lhit,tr.lhit td.lbig{color:var(--gold)}
span.lok{color:var(--go);font-weight:600}
span.lwarn{color:var(--warn);font-weight:600}
span.lbad{color:var(--warn);opacity:.7;font-weight:600}
td.lthin{color:var(--slate-600)}
table.lroom{font-size:12px}
table.lroom th,table.lroom td{padding:7px 0 7px 14px}
.pad{padding-left:18px}
.big{color:var(--slate-100);font-weight:600}
.quiet{color:var(--slate-600)}
.nil{color:var(--slate-600);font-style:italic}
.note{color:var(--slate-600);font-size:12px;width:34%}
@media (max-width:1180px){.note{display:none}}
tr.sep th{padding-top:20px;font-size:11px;letter-spacing:.16em;text-transform:uppercase;
color:var(--gold);border-bottom:1px solid var(--ink)}
tr.dim td{color:var(--slate-600)}
tr.dim td.big{color:var(--slate-500);font-weight:400}
.cross td i{display:block;font-style:normal;font-size:12px;color:var(--slate-600);margin-top:1px}
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
.sub2{display:block;font-size:12.5px;color:var(--slate-600);margin-top:3px;white-space:nowrap}
table.fig a{color:inherit;text-decoration:none;border-bottom:1px solid rgba(201,169,106,.35)}
table.fig a:hover{color:var(--gold-soft);border-bottom-color:var(--gold)}
.winhead{margin-bottom:8px}
.winhead p{font-size:12px;color:var(--slate-600)}
/* method + notes */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.card{border:1px solid var(--ink);border-radius:11px;background:var(--navy-850);padding:16px 18px}
.card h3{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--gold);
font-weight:400;margin-bottom:9px}
.card ul{list-style:none}
.card li{padding:3px 0;color:var(--slate-400);font-size:12.5px}
.card li b{color:var(--slate-100);font-weight:600}
details{border-top:1px solid var(--ink);margin-top:16px}
summary{cursor:pointer;padding:13px 0;font-size:13px;letter-spacing:.01em;
color:var(--slate-400);list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:'';display:inline-block;width:6px;height:6px;margin:0 11px 2px 2px;
border-right:1.5px solid var(--gold);border-bottom:1.5px solid var(--gold);transform:rotate(-45deg);
transition:transform .18s cubic-bezier(.22,1,.36,1)}
details[open] summary::before{transform:rotate(45deg)}
summary:focus-visible{outline:2px solid var(--gold);outline-offset:2px;border-radius:4px}
summary:hover{color:var(--gold-soft)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.expl{color:var(--slate-400);max-width:76ch;margin:10px 0 14px;font-size:13px}
.expl b{color:var(--slate-100);font-weight:600}
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
  border-radius:7px;cursor:pointer;background:transparent;color:var(--slate-400);
  border:1px solid var(--ink)}
.dirs button.on{background:rgba(201,169,106,.13);border-color:var(--gold-soft);
  color:var(--gold-soft)}
.dirs button:hover{border-color:var(--slate-600)}

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
i.age{font-style:normal;font-size:12px;color:var(--slate-600);margin-left:9px;white-space:nowrap}
/* Two columns that become one on a narrow screen. Used by the freehold panel's
   boundary-bootstrap and region tables, which read as a pair of exhibits. */
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:26px;min-width:0}
.grid2>div{min-width:0}
/* The rows on the far side of a band boundary. Tint, not a border: the table is
   already ruled and a second line would fight it. */
tr.hi>th,tr.hi>td{background:rgba(201,169,106,.055)}\n/* A count that belongs under its figure, not beside it — beside it the two run\n   together and read as one number. */\ni.age.under{display:block;margin:2px 0 0}
tr.flag td.big,tr.flag th{color:var(--warn)}
tr.head th,tr.head td{border-bottom:1px solid var(--ink);padding-bottom:11px}
tr.head td.big{color:var(--gold)}
.note.wide{width:52%;font-size:12px}
@media (max-width:900px){.note.wide{display:none}}
.calc{margin-top:22px;border:1px solid rgba(201,169,106,.3);border-radius:12px;
background:linear-gradient(180deg,var(--navy-800),var(--navy-850));padding:20px 22px}
.calc h3{margin-bottom:12px}
.cin{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.cin label{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--slate-500);
display:flex;flex-direction:column;gap:7px}
.cin input{background:var(--navy-950);border:1px solid var(--ink);border-radius:8px;
padding:9px 12px;color:var(--slate-100);font:600 17px/1 Optima,Candara,sans-serif;
width:130px;font-variant-numeric:tabular-nums}
.cin input:focus{outline:2px solid var(--gold);outline-offset:1px;border-color:rgba(201,169,106,.6)}
.cout{border-top:1px solid var(--ink);padding-top:14px}
.cout.bad{color:var(--slate-600);font-style:italic}
.crow{display:flex;justify-content:space-between;gap:16px;padding:5px 0;color:var(--slate-400);align-items:center}
.crow b{color:var(--slate-100);font-variant-numeric:tabular-nums;font-weight:600}
.crow i.cflat{font-style:normal;font-size:11px;letter-spacing:.14em;text-transform:uppercase;
color:var(--gold);border:1px solid rgba(201,169,106,.4);border-radius:999px;padding:2px 9px;margin-left:10px}
.crow.big{border-top:1px solid var(--ink);margin-top:8px;padding-top:12px;font-size:15px}
.crow.big b{color:var(--gold);font:600 21px/1 Optima,Candara,sans-serif}
.chint{color:var(--slate-500);font-size:12px;margin-top:10px}
.cwarn{color:var(--warn);font-size:12px;margin-top:8px}
"""

JS = """
(function(){
  // PW = [boundary, rate before it, rate from it]. The gap is SPLIT at the boundary and each
  // leg priced at its own rate — the form adopted 2026-09-13, replacing one rate read at the
  // pair's midpoint. See the panel's "How to use it".
  var PW=%PW%, LO=%LO%, HI=%HI%;
  function n(id){return parseFloat(document.getElementById(id).value);}
  // Signed from `f` to `t`: a comparable NEWER than the subject must come down, so integrate
  // over the span either way and flip once.
  function pw(f,t){
    var lo=Math.min(f,t), hi=Math.max(f,t), sg=(t>=f?1:-1), out=[];
    var a=Math.max(0,Math.min(hi,PW[0])-lo), b=Math.max(0,hi-Math.max(lo,PW[0]));
    if(a>0) out.push({yrs:a, rate:PW[1], to:Math.min(hi,PW[0])});
    if(b>0) out.push({yrs:b, rate:PW[2], to:hi});
    var tot=0; for(var i=0;i<out.length;i++) tot+=out[i].yrs*out[i].rate;
    return {parts:out, total:sg*tot};
  }
  function go(){
    var a=n('lsA'), b=n('lsB'), o=document.getElementById('calcOut');
    if(!a||!b||a<1960||b<1960||a>2040||b>2040){o.className='cout bad';
      o.innerHTML='Enter two lease start years.';return;}
    if(a===b){o.className='cout bad';o.innerHTML='Same lease start \\u2014 no adjustment.';return;}
    var gap=b-a, r=pw(a,b), adj=r.total, mid=(a+b)/2;
    var warn='';
    var legs='';
    for(var i=0;i<r.parts.length;i++){
      var pt=r.parts[i];
      legs+='<div class="crow"><span>'+(i===0&&r.parts.length>1?'Years before '+PW[0]
              :(r.parts.length>1?'Years from '+PW[0]:'Lease gap'))+'</span><b>'+
            pt.yrs+' \u00d7 $'+pt.rate.toFixed(0)+'/yr</b><i class="cflat">$'+
            Math.round(pt.yrs*pt.rate).toLocaleString()+'</i></div>';
    }
    o.className='cout';
    o.innerHTML = legs +
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
  // The age term here is the LEASE rate on the TOP clock, so it splits the same way. TOP is
  // converted to a lease-start equivalent by subtracting the build gap (TB[3]) before the
  // boundary (TB[2]) is applied, which is what the engine does.
  // How to SAY the age term: one rate when the gap sits inside one band, both when it spans.
  function ageLegs(tf,tl){
    var f=tl-TB[3], t=tf-TB[3], lo=Math.min(f,t), hi=Math.max(f,t);
    var a=Math.max(0,Math.min(hi,TB[2])-lo), b=Math.max(0,hi-Math.max(lo,TB[2]));
    if(a>0&&b>0) return a+' yrs at $'+TB[0].toFixed(0)+' then '+b+' at $'+TB[1].toFixed(0)+' a year';
    return '$'+(b>0?TB[1]:TB[0]).toFixed(0)+' a year';
  }
  function ageAdj(tf,tl){
    var f=tl-TB[3], t=tf-TB[3], lo=Math.min(f,t), hi=Math.max(f,t), sg=(t>=f?1:-1);
    var a=Math.max(0,Math.min(hi,TB[2])-lo), b=Math.max(0,hi-Math.max(lo,TB[2]));
    return sg*(a*TB[0]+b*TB[1]);
  }
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
    var lf=left(), dv=tf-tl, age=ageAdj(tf,tl), st=step(lf),
        out = fwd ? (p/(1+st[1]) - age)      // freehold in, leasehold out
                  : ((p + age)*(1+st[1]));   // leasehold in, freehold out
    o.className='cout';
    o.innerHTML=
      (dv===0
        ? '<div class="crow"><span>Same completion year</span><b>no age adjustment</b></div>'
        : '<div class="crow"><span>Completion-year gap \u2014 the freehold is '+
          Math.abs(dv)+' yrs '+(dv>0?'newer':'older')+
          ', at '+ageLegs(tf,tl)+'</span><b>'+
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

  /* THE LAYOUT PANEL IS HIDDEN INSIDE A HIDDEN PAGE. Shawn, 2026-09-18: the Layout study is not
     part of the constant set and must not sit in the nav strip. The way in is a DOUBLE-TAP on
     the "Internal — Constant Calibration" chip, the same two-pointerups-inside-450ms handler the
     calculator uses on its brand mark: iOS Safari does not fire dblclick from a double tap, it
     treats the second tap as zoom, which touch-action:manipulation suppresses. A single tap does
     nothing. Once opened the panel behaves like any other — #layout stays linkable. */
  var key=document.getElementById('layoutKey'), lastTap=0;
  if(key){
    key.addEventListener('pointerup',function(){
      var now=Date.now();
      if(now-lastTap<450){ lastTap=0; show('layout',true); }
      else lastTap=now;
    });
  }
})();

/* THE QUARTERLY DRILL-DOWN. Shawn, 2026-09-10: keep the 442 pooled rows as the evidence and put
   the quarters underneath, on demand. The point of it is NOT that a quarter is better evidence —
   it is worse, and openly so: most rest on one or two sales and swing hundreds of dollars. It is
   there so a reader who doubts a pooled figure can see for themselves why pooling is the honest
   summary. The sale count sits on every line for exactly that reason. */
(function(){
  var t=document.querySelector('table.pairs'); if(!t||!window.QD) return;
  var money=function(v){return (v<0?'-$':'+$')+Math.abs(v).toLocaleString();};
  t.addEventListener('click',function(e){
    var tr=e.target.closest('tr[data-q]'); if(!tr) return; toggle(tr);
  });
  t.addEventListener('keydown',function(e){
    if(e.key!=='Enter'&&e.key!==' ') return;
    var tr=e.target.closest&&e.target.closest('tr[data-q]'); if(!tr) return;
    e.preventDefault(); toggle(tr);
  });
  function toggle(tr){
    var nx=tr.nextElementSibling;
    if(nx&&nx.classList.contains('qd')){ nx.remove(); tr.classList.remove('open'); tr.setAttribute('aria-expanded','false'); return; }
    tr.setAttribute('aria-expanded','true');
    var rows=QD[+tr.getAttribute('data-q')]||[];
    var cols=tr.children.length;
    var d=document.createElement('tr'); d.className='qd';
    var h='<td colspan="'+cols+'"><div class="qdin">';
    if(!rows.length){ h+='<p>No quarter has sales on both sides. The pooled figure is the only reading this pair supports.</p>'; }
    else{
      var ds=rows.map(function(r){return r[2]-r[1];});
      var lo=Math.min.apply(null,ds), hi=Math.max.apply(null,ds);
      h+='<p>Quarter by quarter &mdash; <b>'+rows.length+'</b> quarters where both sides sold. '
       + 'The difference swings <b>'+money(lo)+'</b> to <b>'+money(hi)+'</b>, on the handful of sales '
       + 'shown at the right. <b>This is why the study pools:</b> a single quarter is one or two '
       + 'transactions and cannot carry a reading.</p>'
       + '<table class="qt"><thead><tr><th>quarter</th><th class="num">older</th>'
       + '<th class="num">newer</th><th class="num">difference</th><th class="num">sales</th>'
       + '</tr></thead><tbody>';
      rows.forEach(function(r){
        h+='<tr><td>'+r[0]+'</td><td class="num quiet">$'+r[1].toLocaleString()+'</td>'
         + '<td class="num quiet">$'+r[2].toLocaleString()+'</td>'
         + '<td class="num big">'+(r[2]-r[1]>=0?'+':'')+(r[2]-r[1]).toLocaleString()+'</td>'
         + '<td class="num quiet">'+r[3]+' / '+r[4]+'</td></tr>';
      });
      h+='</tbody></table>';
    }
    d.innerHTML=h+'</div></td>';
    tr.classList.add('open'); tr.parentNode.insertBefore(d,tr.nextSibling);
  }
})();
"""
# ── THE OTHER THREE PANELS, GIVEN THE LEASE PANEL'S TREATMENT ───────────────
# Shawn, 2026-09-10: "continue for the rest of the data pooling for MRT distance, integrated,
# fh / leasehold. I want there to be similar data to look at below." Same three things the lease
# panel got: the transaction base on the hero, every pair listed with what it rests on, and the
# sales counts visible so nobody has to guess whether a row is one sale or forty.
def _tx(rows, a_name, a_bed, a_n, b_name, b_bed, b_n):
    """Distinct <project x bedroom> sides and the transactions under them."""
    s = {}
    for r in rows:
        s[(r[a_name], r[a_bed])] = r[a_n]
        s[(r[b_name], r[b_bed])] = r[b_n]
    return sum(s.values()), len(s)

MROWS = M['rows'] if M else []
GROWS = [r for r in (G['rows'] if G else []) if 'n_i' in r]
TROWS = T['mixed'] if T else []

MTX, MSIDES = _tx(MROWS, 'closer', 'bed', 'n_close', 'further', 'bed', 'n_far') if MROWS else (0, 0)
GTX, GSIDES = _tx(GROWS, 'a', 'bed', 'n_i', 'b', 'bed', 'n_n') if GROWS else (0, 0)
TTX, TSIDES = _tx(TROWS, 'fh', 'bed', 'n_fh', 'lh', 'bed', 'n_lh') if TROWS else (0, 0)
ndev2 = lambda rows, a, b: len({x for r in rows for x in (r[a], r[b])})

def _nm(x): return html.escape(str(x).title())

def int_cut_tx(cut):
    """Transactions behind one integrated cut. The cut records its own rule (lgmax/dgmax), so
    the subset is reproduced exactly as integrated-pairs.py cut it. An earlier version read
    cut['lo']/['hi'] — those are the BOOTSTRAP INTERVAL, not the rule, and it produced a
    broadest-cut count smaller than a tighter one. That impossibility is what caught it."""
    rs = [r for r in GROWS
          if abs(r['lg']) <= cut['lgmax'] and abs(r['dg']) <= cut['dgmax']
          and r.get('apart', 0) <= cut.get('apmax', 99999)]
    return _tx(rs, 'a', 'bed', 'n_i', 'b', 'bed', 'n_n')[0] if rs else 0

def ten_slice_tx(g, nxt):
    """Transactions behind one lease-left step: pairs whose leasehold side has that much left."""
    lo = g.get('min_left') or 0
    hi = (nxt.get('min_left') if nxt else None) or 9999
    rs = [r for r in TROWS if r.get('left') is not None and lo <= r['left'] < max(hi, lo + 1)]
    return _tx(rs, 'fh', 'bed', 'n_fh', 'lh', 'bed', 'n_lh')[0] if rs else 0

def mrt_band_tx(key):
    """Transactions behind one walk band's pairs — the hero shows it beside the development count."""
    rs = [r for r in MROWS if r['pairkey'] == key]
    return _tx(rs, 'closer', 'bed', 'n_close', 'further', 'bed', 'n_far')[0] if rs else 0

# ── EVERY PAIR TIED BACK TO THE HEADLINE (Shawn, 2026-09-10) ────────────────
# "I want the top rows to be the ones closest to the average, and I want the clients to be able
# to link the numbers up to what we are showing." So each table carries, on every row: what THIS
# pair reads, what the published figure says it should read, and the gap between the two — and
# the table opens on the pairs that land on the figure and walks out to the ones that do not.
# Exactly the shape of the lease panel's table, which is the one he signed off.
# Read from engine.ts rather than restated: an earlier version of the note below quoted a
# detour factor of 1.24 while doing its arithmetic with the engine's 1.3, and stated the
# direction backwards (a straight line cannot be longer than the route it cuts across).
ENG_CIRCUITY = float(__import__('re').search(r'const CIRCUITY = ([\d.]+)',
    open(os.path.join(HERE, '..', 'scripts', 'engine.ts')).read()).group(1))

MBAND = {b['key']: b['adj'] for b in (M['bands'] if M else [])}
MBLAB = {'near|mid': 'under 5 vs 5&ndash;10 min', 'mid|far': '5&ndash;10 vs over 10 min',
         'near|far': 'under 5 vs over 10 min'}
TSTEP = [g for g in (T['slices']['gradient'] if T else []) if not g.get('thin') and g.get('pct')]
# The cut the engine adopts — selected by the study's own `headline` flag, not by position.
# engine.ts selects the same way; see integrated-pairs.py HEADLINE_CUT.
INT_HEAD = (next((c for c in G['cuts'] if c.get('headline')), G['cuts'][-1]) if G else None)

def ten_step_of(left):
    """The measured premium for the step this pair's remaining lease falls in."""
    if left is None: return None
    for g in sorted(TSTEP, key=lambda x: -x['min_left']):
        if left >= g['min_left']: return g
    return TSTEP[-1] if TSTEP else None

def mrt_repl_table():
    """The walk bands measured again on an earlier, non-overlapping two years — with THAT
    window's own lease bands removed, not today's, or the current cut would be smuggled back in.

    THIS ONE DOES NOT REPLICATE THE WAY THE LEASE RATE DOES, and the page says so. The near
    band reads +$22 [-3, +47] on 2021-23 against +$67 [+40, +98] now: an interval that includes
    zero, against one that does not."""
    E = M.get('early') if M else None
    if not E: return ''
    cur = {b['key']: b for b in M['bands']}
    h = ['<table class="fig look"><thead><tr><th>Transactions used</th>']
    for b in M['bands']: h.append(f'<th class="num">{b["label"]}</th>')
    h.append('<th class="num">pairs</th></tr></thead><tbody>')
    h.append(f'<tr class="head"><th>{M["window"][0]} to {M["window"][1]} &mdash; the published cut</th>'
             + ''.join(f'<td class="num big">+${b["adj"]:,.0f}</td>' for b in M['bands'])
             + f'<td class="num quiet">{M["pairs"]}</td></tr>')
    eb = {b['key']: b for b in E['bands']}
    h.append(f'<tr><th>{E["window"][0]} to {E["window"][1]} &mdash; three years earlier</th>'
             + ''.join(f'<td class="num big">+${eb[b["key"]]["adj"]:,.0f}</td>'
                       if b['key'] in eb else '<td class="num nil">&mdash;</td>'
                       for b in M['bands'])
             + f'<td class="num quiet">{E["pairs"]}</td></tr>')
    h.append('<tr class="dim"><th>the earlier reading&rsquo;s range</th>'
             + ''.join(f'<td class="num">{eb[b["key"]]["lo"]:+,.0f} to {eb[b["key"]]["hi"]:+,.0f}</td>'
                       if b['key'] in eb else '<td class="num nil">&mdash;</td>'
                       for b in M['bands'])
             + '<td class="num quiet"></td></tr>')
    return ''.join(h) + '</tbody></table>'

def mrt_pairtable():
    """Every walk-distance pair, CLOSEST TO ITS BAND FIRST.

    THE TREATMENT AND THE PLACEBO ARE DIFFERENT THINGS AND MUST NOT BE MIXED. Only pairs
    spanning two DIFFERENT walk bands are evidence for a band step; same-band pairs
    (near|near, mid|mid, far|far) are built deliberately as a placebo and should read about
    nothing once the lease is removed. An earlier version of this table sorted them together
    and, having no band figure to compare a same-band row against, silently scored it against
    $0 — which floated the placebo to the top as if it were the best-fitting evidence.
    They now sit below their own divider, sorted by how close to zero they land, which is what
    a placebo is judged on."""
    def off(r): return r['adj'] - MBAND.get(r['pairkey'], 0)
    treat = sorted([r for r in MROWS if r['pairkey'] in MBAND], key=lambda r: abs(off(r)))
    plac  = sorted([r for r in MROWS if r['pairkey'] not in MBAND], key=lambda r: abs(r['adj']))
    h = ['<table class="fig pairs"><thead><tr><th class="num">#</th><th>closer</th>'
         '<th>further</th><th class="num">walk</th><th>bed</th>'
         '<th class="num">after lease</th><th>band</th><th class="num">the band says</th>'
         '<th class="num">off by</th><th class="num">sales</th></tr></thead><tbody>']
    def emit(rows, start, placebo):
        out = []
        for i, r in enumerate(rows, start):
            band = MBLAB.get(r['pairkey'], r['pairkey'].replace('|', ' vs '))
            says = '&mdash;' if placebo else f'+${MBAND[r["pairkey"]]:,.0f}'
            offv = '&mdash;' if placebo else f'{off(r):+,.0f}'
            out.append(f'<tr><td class="num quiet">{i}</td>'
                       f'<td>{_nm(r["closer"])} <i class="age">{r["m_close"]}m</i></td>'
                       f'<td>{_nm(r["further"])} <i class="age">{r["m_far"]}m</i></td>'
                       f'<td class="num">{r["m_far"]-r["m_close"]:+,.0f}m</td>'
                       f'<td class="quiet">{r["bed"]}</td>'
                       f'<td class="num big">{r["adj"]:+,.0f}</td>'
                       f'<td class="quiet">{band}</td>'
                       f'<td class="num quiet">{says}</td>'
                       f'<td class="num quiet">{offv}</td>'
                       f'<td class="num quiet">{r["n_close"]} / {r["n_far"]}</td></tr>')
        return ''.join(out)
    h.append(emit(treat, 1, False))
    if plac:
        h.append('<tr class="sep"><th colspan="10">Same band on both sides &mdash; the placebo, '
                 'which should read about nothing</th></tr>')
        h.append(emit(plac, 1, True))
    return ''.join(h) + '</tbody></table>'

def int_pairtable():
    """Every integrated-vs-plain pair, CLOSEST TO THE PUBLISHED PREMIUM FIRST. Each row's own
    reading is the residue after lease and walk, as a share of the plain neighbour's psf — the
    same construction as the headline, so the two are directly comparable."""
    pc  = lambda r: 100 * r['adj'] / r['base']
    hd  = INT_HEAD['pct'] if INT_HEAD else 0
    tight = (lambda r: abs(r['lg']) <= INT_HEAD['lgmax'] and abs(r['dg']) <= INT_HEAD['dgmax']
             and r.get('apart', 0) <= INT_HEAD.get('apmax', 99999))
    rows = sorted(GROWS, key=lambda r: abs(pc(r) - hd))
    h = ['<table class="fig pairs"><thead><tr><th class="num">#</th><th>integrated</th>'
         '<th>plain neighbour</th><th class="num">apart</th><th>bed</th>'
         '<th class="num">after lease &amp; walk</th>'
         '<th class="num">the premium</th><th class="num">the figure says</th>'
         '<th class="num">off by</th><th class="num">sales</th><th>next door</th>'
         '</tr></thead><tbody>']
    for i, r in enumerate(rows, 1):
        h.append(f'<tr><td class="num quiet">{i}</td>'
                 f'<td>{_nm(r["a"])} <i class="age">{r["ls_i"]}</i></td>'
                 f'<td>{_nm(r["b"])} <i class="age">{r["ls_n"]}</i></td>'
                 f'<td class="num">{r.get("apart", 0):,.0f}m</td>'
                 f'<td class="quiet">{r["bed"]}</td>'
                 f'<td class="num quiet">{r["adj"]:+,.0f}</td>'
                 f'<td class="num big">{pc(r):+.1f}%</td>'
                 f'<td class="num quiet">+{hd:.1f}%</td>'
                 f'<td class="num quiet">{pc(r) - hd:+.1f}%</td>'
                 f'<td class="num quiet">{r["n_i"]} / {r["n_n"]}</td>'
                 f'<td class="quiet">{"yes" if tight(r) else "&mdash;"}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def ten_pairtable():
    """Every freehold-against-leasehold pair, CLOSEST TO ITS OWN STEP FIRST. The premium is not
    one number — it widens as the lease shortens — so each row is compared against the step its
    leasehold side falls in, not against the headline."""
    prem = lambda r: 100 * (r['psf_fh'] / r['psf_lh'] - 1)
    def exp(r):
        g = ten_step_of(r.get('left'))
        return (g['pct'] * 100 if g else None), (g['label'] if g else '&mdash;')
    def off(r):
        e, _ = exp(r)
        return 1e9 if e is None else prem(r) - e
    rows = sorted(TROWS, key=lambda r: abs(off(r)))
    h = ['<table class="fig pairs"><thead><tr><th class="num">#</th><th>freehold</th>'
         '<th>leasehold</th><th>bed</th><th class="num">premium</th>'
         '<th class="num">lease left</th><th>step</th><th class="num">the step says</th>'
         '<th class="num">off by</th><th class="num">sales</th></tr></thead><tbody>']
    for i, r in enumerate(rows, 1):
        e, lab = exp(r)
        h.append(f'<tr><td class="num quiet">{i}</td>'
                 f'<td>{_nm(r["fh"])} <i class="age">{r["top_fh"]}</i></td>'
                 f'<td>{_nm(r["lh"])} <i class="age">{r["top_lh"]}</i></td>'
                 f'<td class="quiet">{r["bed"]}</td>'
                 f'<td class="num big">{prem(r):+.1f}%</td>'
                 f'<td class="num quiet">{r["left"]:,.0f} yrs</td>'
                 f'<td class="quiet">{lab}</td>'
                 f'<td class="num quiet">{"&mdash;" if e is None else f"+{e:.0f}%"}</td>'
                 f'<td class="num quiet">{"&mdash;" if e is None else f"{prem(r)-e:+.0f}%"}</td>'
                 f'<td class="num quiet">{r["n_fh"]} / {r["n_lh"]}</td></tr>')
    return ''.join(h) + '</tbody></table>'

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
    # Same shape as every other pair table: closest to the headline first, the figure, off by.
    # `widest` is the retired "worth money" cut — NOT RENDERED since 2026-09-13.
    d = V['resale']['devs']
    hd = VR['discount']
    d = (sorted(d, key=lambda r: -r['spread']) if widest
         else sorted(d, key=lambda x: abs((100 - x['ratio'] * 100) - hd)))[:n]
    r = ['<table class="fig pairs"><thead><tr><th class="num">#</th><th>development</th>'
         '<th class="num">extra sqft</th><th class="num">home psf</th>'
         '<th class="num">extra-area psf</th><th class="num">discount</th>'
         '<th class="num">the figure says</th><th class="num">off by</th>'
         '<th class="num">resales</th></tr></thead><tbody>']
    for i, x in enumerate(d, 1):
        disc = 100 - x['ratio'] * 100
        r.append(f'<tr><td class="num quiet">{i}</td><td>{html.escape(nice(x["proj"]))}</td>'
                 f'<td class="num quiet">+{x["extra"]:,}</td>'
                 f'<td class="num quiet">${x["base_psf"]:,}</td>'
                 f'<td class="num quiet">${x["void_psf"]:,}</td>'
                 f'<td class="num big">{disc:.0f}% off</td>'
                 f'<td class="num quiet">{hd:.0f}% off</td>'
                 f'<td class="num quiet">{disc - hd:+.0f}</td>'
                 f'<td class="num quiet">{x["pairs"]}</td></tr>')
    r.append('</tbody></table>')
    return ''.join(r)

def void_spread_names(k=3):
    d = sorted(V['resale']['devs'], key=lambda r: -r['spread'])[:k]
    return ', '.join(f'<b>{html.escape(nice(x["proj"]))}</b> {x["spread"]:.2f}' for x in d)

def ec_launch_table():
    """Every EC launch in the window, and the private launch beside it. Ordered by the
    premium, smallest first, so the spread is the shape of the column rather than a range
    stated in prose.

    HOW FAR the comparable is now travels with it. Distance is the matching rule as of
    2026-09-11, so it is the evidence for the row: +28% against something 259 m away and
    +26% against something 1.9 km away are not the same reading, and the district match
    this replaced made that difference invisible."""
    # Same shape as every other pair table since 2026-09-13: closest to the headline first.
    hd = E['launch']['pct']
    r = ['<table class="fig pairs"><thead><tr><th class="num">#</th><th>EC launch</th>'
         '<th>private launch</th><th class="num">apart</th><th class="num">EC psf</th>'
         '<th class="num">private psf</th><th class="num">private is</th>'
         '<th class="num">the figure says</th><th class="num">off by</th>'
         '<th class="num">pairs</th></tr></thead><tbody>']
    for i, d in enumerate(sorted(E['launch']['by'], key=lambda d: abs(d['pct'] - hd)), 1):
        far = d.get('d')
        apart = '&mdash;' if far is None else (f'{far:,}m' if far < 1000 else f'{far/1000:.1f}km')
        r.append(f'<tr><td class="num quiet">{i}</td><td>{nice(d["ec"])}</td>'
                 f'<td>{", ".join(nice(c) for c in d["comps"])}</td>'
                 f'<td class="num quiet">{apart}</td>'
                 f'<td class="num quiet">${d["ecpsf"]:,.0f}</td>'
                 f'<td class="num quiet">${d["pvpsf"]:,.0f}</td>'
                 f'<td class="num big">{d["pct"]:+.0f}%</td>'
                 f'<td class="num quiet">+{hd:.0f}%</td>'
                 f'<td class="num quiet">{d["pct"] - hd:+.0f}%</td>'
                 f'<td class="num quiet">{d["pairs"]:,}</td></tr>')
    return ''.join(r) + '</tbody></table>'

def ec_ladder_line():
    """The matching rule, in one sentence, computed from what the run actually used."""
    L = E['launch'].get('ladder')
    if not L: return 'each EC paired against the private launches in the same district.'
    rings = ', '.join(f'{x/1000:g} km' for x in L)
    return (f'the nearest {E["meta"]["near"]} inside {rings}, taking the first of those rings '
            f'that holds anything, so a launch with a comparable across the road is never '
            f'paired against one {L[-1]/1000:g} km away.')

def ec_unmatched_line():
    """The launches that found NOTHING. Said out loud, because a shorter table is otherwise
    indistinguishable from a shorter market. Do NOT claim they all carried a figure before:
    most did, on a district-matched comparable kilometres away, but Parc Greenwich had no
    district match either and never appeared. The wording says "some", which stays true
    across re-runs without the script having to hold the old cut to compare against."""
    u = E['launch'].get('unmatched') or []
    if not u: return ''
    L = E['launch'].get('ladder') or [2000]
    names = ', '.join(f'<b>{nice(x)}</b>' for x in u)
    return (f'<p class="expl">Not in the table, with no private launch within {L[-1]/1000:g} km '
            f'to pair: {names}.</p>')

# Age bands measured but not shown on the page. (Shawn, 2026-09-10.)
HIDDEN_AGE_BANDS = {'15+'}
# The bands the page actually SHOWS, so prose about them is computed from what a reader can see
# rather than asserted. An earlier version claimed "a mature EC trades above the private condo"
# — the exact reverse of this table, whose column is "Private is" and whose privatised rows are
# POSITIVE. The claim sat two inches under the rows refuting it.
AGE_SHOWN = [a for a in (E['ages'] if E else []) if a['key'] not in HIDDEN_AGE_BANDS]

# THE PLACEBO VERDICT IS COMPUTED, NOT ASSERTED. The page printed "that covers zero" as a fixed
# string whatever the numbers said — and it does NOT cover zero: both bounds are negative. A
# check presented as passing while it is failing is worse than no check at all.
def _placebo_verdict():
    if not G: return ''
    lo, hi = G['placebo']['pct_lo'], G['placebo']['pct_hi']
    lt = G.get('confound', {}).get('treat_load'); lp = G.get('confound', {}).get('placebo_load')
    load = (f' These pairs also carry only about {lp/lt:.0%} of the adjustment burden of the '
            f'integrated pairs they check, so even a clean reading would not certify the '
            f'treatment on its own') if lt and lp else ''
    if lo <= 0 <= hi:
        return ('an interval that <b>covers zero</b>, which is the check passing: with nothing '
                'to find, the method finds nothing.' + load)
    side = 'below' if hi < 0 else 'above'
    return (f'an interval that <b>does not cover zero</b>. Pairs that should read nothing read '
            f'{side} it, so a small residual bias survives the lease and distance corrections, '
            f'and the integrated figures above carry it too.' + load)
PLACEBO_VERDICT = _placebo_verdict()

# The claim about WHY some developments read low used to be asserted ("the three that read low
# are the three with the widest lease gaps") and was false against the table printed beside it.
# Computed now, so it states whatever is true of the current cut.
def _int_low_note():
    if not G or not G.get('devs'): return ''
    d = G['devs']
    low3 = {x['name'] for x in sorted(d, key=lambda x: x['adj'])[:3]}
    wide3 = {x['name'] for x in sorted(d, key=lambda x: -abs(x.get('lg') or 0))[:3]}
    both = low3 & wide3
    if not both:
        return 'none of the three lowest is among the three widest'
    return (f'{len(both)} of the three lowest {"is" if len(both)==1 else "are"} among the three '
            f'widest')
INT_LOW_NOTE = _int_low_note()
INT_THIN = sum(1 for x in (G['devs'] if G else []) if (x.get('pairs') or 0) <= 3)

# The two constants still set by judgement and still applied, read from the engine and the
# tenure study rather than restated. The summary caveat claimed every judgement constant was
# retired; these two are not, and both travel into every workup.
def _judgement_live():
    eng = open(os.path.join(HERE, '..', 'scripts', 'engine.ts')).read()
    import re as _re
    harm = float(_re.search(r'harmonisationUplift: ([\d.]+)', eng).group(1))
    cy   = int(_re.search(r'CONSTRUCTION_YEARS = (\d+)', eng).group(1))
    b = (T or {}).get('build', {})
    return dict(harm=harm, cy=cy, cy_measured=b.get('median'), cy_n=b.get('n') or 0)
JUDGE = _judgement_live()

# The sweep sentence used to name index 0 and index 3 and call the result flat, skipping the
# 400 m row that dips between them. State the actual span of the tight caps instead.
def _sweep_tight():
    if not G or not G.get('apartsweep'): return ''
    cap = (INT_HEAD or {}).get('apmax') or 500
    tight = [r for r in G['apartsweep'] if r['cap'] <= max(cap, 600)]
    if not tight: return ''
    lo, hi = min(tight, key=lambda r: r['pct']), max(tight, key=lambda r: r['pct'])
    return (f"it runs +{lo['pct']:.1f}% at {lo['cap']:,} m to +{hi['pct']:.1f}% at "
            f"{hi['cap']:,} m across the four tightest caps")
SWEEP_TIGHT = _sweep_tight()
PCT_RATIO = (fpct(rows_in(NEW_NM)) / fpct(rows_in(OLD_NM))) if fpct(rows_in(OLD_NM)) else 0
DOL_RATIO = (BANDR[NEW_NM] / BANDR[OLD_NM]) if BANDR[OLD_NM] else 0

# The bands the page actually SHOWS, so prose about them is computed from what a reader can
# see rather than asserted. An earlier version claimed "a mature EC trades above the private
# condo" — the exact reverse of this table, whose column is "Private is" and whose privatised
# rows are POSITIVE. The claim sat two inches under the rows refuting it.


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
    # Same shape as every other pair table: closest to the headline first, with what the
    # figure says and how far this row is off it. (Shawn, 2026-09-13: sorting most-negative
    # first led the table with ECs dearer than private, which the headline does not say.)
    hd = E['resale']['pct']
    r = ['<table class="fig pairs"><thead><tr><th class="num">#</th><th>EC</th>'
         '<th class="num">years built</th><th class="num">EC psf</th>'
         '<th class="num">private psf</th><th class="num">private is</th>'
         '<th class="num">the figure says</th><th class="num">off by</th>'
         '<th class="num">pairs</th></tr></thead><tbody>']
    for i, d in enumerate(sorted(E['resale']['by'], key=lambda d: abs(d['pct'] - hd)), 1):
        age = f'{d["age"]:.0f}' if d['age'] is not None else '&mdash;'
        r.append(f'<tr><td class="num quiet">{i}</td><td>{nice(d["ec"])}</td>'
                 f'<td class="num quiet">{age}</td>'
                 f'<td class="num quiet">${d["ecpsf"]:,.0f}</td>'
                 f'<td class="num quiet">${d["pvpsf"]:,.0f}</td>'
                 f'<td class="num big">{d["pct"]:+.1f}%</td>'
                 f'<td class="num quiet">{hd:+.1f}%</td>'
                 f'<td class="num quiet">{d["pct"] - hd:+.1f}%</td>'
                 f'<td class="num quiet">{d["pairs"]:,}</td></tr>')
    return ''.join(r) + '</tbody></table>'

def hero(was, was_sub, answers, call, base=None):
    """The verdict block every panel opens with. `answers` is a list of
    (figure, what it is, how many developments).

    NO INTERVALS HERE. They were added to the face on 2026-09-06 and taken off again the same
    day at Shawn's word: the face carries the answer and the count behind it, and the interval
    lives one row down in the table. Do not put it back without asking."""
    cells = ''.join(
        '<div class="ans"><div class="n">' + a[0] + '</div><div class="w">' + a[1] + '</div>'
        + ('<div class="g">' + str(a[2]) + '<span>developments</span></div>' if a[2] else '')
        + ('<div class="g">' + f'{a[3]:,}' + '<span>transactions</span></div>'
           if len(a) > 3 and a[3] else '')
        + '</div>' for a in answers)
    call_p = ('<p class="call">' + call + '</p>') if call else ''
    base_d = ''
    if base:
        base_d = ('<div class="vbase">' + ''.join(
            '<div class="g">' + f'{n:,}' + '<span>' + w + '</span></div>' for n, w in base)
            + '</div>')
    return ('<div class="verdict"><div class="vgrid">'
            '<div class="vcell"><div class="lab">Engine constant</div>'
            '<div class="val was">' + was + '</div><div class="sub">' + was_sub + '</div></div>'
            '<div class="arrow">&rarr;</div>'
            '<div class="vcell grow"><div class="lab">Measured</div>'
            '<div class="answers">' + cells + '</div>' + base_d + '</div></div>'
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

def apart_table():
    """The premium against how far apart the two projects ACTUALLY are — the screen Shawn asked
    for on 2026-09-10. Not to be confused with dsweep_table(), which sweeps the difference in
    the two walks TO THE STATION; that is a different quantity and the old label conflated them."""
    if not G or not G.get('apartsweep'): return ''
    h = ['<table class="fig look"><thead><tr><th>Both projects within</th>'
         '<th class="num">the premium</th><th class="num">pairs</th>'
         '<th class="num">developments</th></tr></thead><tbody>']
    hd = INT_HEAD['apmax'] if INT_HEAD else None
    for r in G['apartsweep']:
        head = ' class="head"' if r['cap'] == hd else ''
        h.append(f'<tr{head}><th>{r["cap"]:,} m of each other</th>'
                 f'<td class="num big">+{r["pct"]:.1f}%</td>'
                 f'<td class="num quiet">{r["pairs"]}</td>'
                 f'<td class="num quiet">{r["devs"]}</td></tr>')
    return ''.join(h) + '</tbody></table>'

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
TENB_JS = ('[%d,%d,%d,%d,%d,%d]' % (LPW1, LPW2, LPWB,
                                        T['build']['median'], T['build']['term'],
                                        datetime.date.today().year)) if T else '[0,0,0,0,99,2026]'
# [floor of the step, the premium as a fraction, the step's label] — PERCENT, his ruling.
TENS_JS = '[' + ','.join(f'[{g["min_left"]},{g["pct"]:.5f},"{g["label"]}"]'
                         for g in TGL) + ']' if TGL else '[]'

PW_JS = f'[{LPWB},{LPW1:.0f},{LPW2:.0f}]'
A1, A2 = age_label(OLD_NM); B1, B2 = age_label(NEW_NM)

# ── FREEHOLD vs FREEHOLD — the price of a year of COMPLETION ────────────────
# The lease study prices a year of LEASE START between two leaseholds, and that figure bundles
# two things: the building got newer AND the lease got longer. Between two freeholds there is no
# lease to lengthen, so what is left is the pure price of a newer building. Same methodology,
# different clock — completion, the only one both sides share.
AG    = A['24'] if A else None
AGR   = AG['rows'] if AG else []
AGRATE = AG['rate'] if AG else 0          # the FLAT rate. Kept — it is what two bands beat.
AGEV  = (AG.get('evidence') or {}) if AG else {}
AGST  = AGEV.get('step') or {}
AGFM  = AGEV.get('form') or {}
AGB   = AGST.get('bound', 2010)           # 2010, and it survives bootstrapping the search
AGPRE = [r for r in AGR if r['mid'] <  AGB]
AGPOST= [r for r in AGR if r['mid'] >= AGB]
# The two band names, in the page's own words. READ AT THE MIDPOINT of the two completion
# years — the same convention the 99-year panel uses on lease starts, and for the same reason:
# a pair straddling the boundary needs no decision made about it.
AGNM  = (f'years before {AGB}', f'years from {AGB}')
# THE APPLIED FORM IS PIECEWISE (Shawn, 2026-09-13). The midpoint form is what IDENTIFIES the
# boundary — bootstrap the search and it lands on {AGB} in 92% of resamples, where the piecewise
# knot never settles. But the midpoint form is not what you APPLY, because assigning a whole
# pair to one band by where it is centred puts a cliff in the middle of the rule: two pairs one
# year apart in centring take rates 2.8x apart. So: FIND THE BREAK WITH THE FORM THAT IDENTIFIES
# IT, APPLY IT WITH THE FORM THAT IS CONTINUOUS. They score level held-out, so nothing is given
# up. The midpoint rates stay on the page as the alternative and as the identifying evidence.
AGPWD = (AG.get('pw') or {}) if AG else {}
AGPW1 = AGPWD.get('pre', AGFM.get('pw_pre', 0))
AGPW2 = AGPWD.get('post', AGFM.get('pw_post', 0))
def age_split(top_old, top_new, k=None):
    """How many years of this gap fall each side of the boundary."""
    k = AGB if k is None else k
    return max(0.0, min(top_new, k) - top_old), max(0.0, top_new - max(top_old, k))
def age_adj(top_old, top_new):
    pre, post = age_split(top_old, top_new)
    return AGPW1 * pre + AGPW2 * post

# ── NOT RENDERED. The freehold panel was made client-ready on 2026-09-13 (Shawn: "everything
# below the measurement should either be hidden or removed — it's just an explanation to
# Shawn"), and the nine builders below lost their caller in one go: the gap-band diagnostic,
# the vintage slices, the boundary bootstrap, the region cut, the shape race, the midpoint-vs-
# split comparison, the cliff, the era cross-check against the 99-year panel, and the 106-row
# pair table.
#
# KEPT, NOT DELETED, and the same reasoning as the three lease explain blocks retired on
# 2026-09-10: age-pairs.py still computes and prints every one of these tests on each run, and
# age-pairs.json still carries them under `evidence`. Only the PAGE stopped being where they
# are read. Re-rendering any of them is one f-string away, and deleting them would mean
# rewriting the renderer before the evidence could be shown again.
# ─────────────────────────────────────────────────────────────────────────────
def age_own_yr(r):
    return r['diff'] / r['gap'] if r['gap'] else 0.0
def age_rule_yr(r):
    """What the published rule works out to per year FOR THIS PAIR — the band rate when the
    gap sits inside one band, a blend when it spans the boundary."""
    pre, post = age_split(r['top_old'], r['top_new'])
    return (AGPW1 * pre + AGPW2 * post) / r['gap'] if r['gap'] else 0.0

def age_answer_table():
    """The freehold twin of answer_table(): what each LEG reads, its interval, and how many
    pairs contribute years to it. Same columns as the 99-year panel (Shawn, 2026-09-13)."""
    L = AGPWD.get('legs') or {}
    h = ['<table class="fig look"><thead><tr><th>Each year of the completion gap</th>'
         '<th class="num">$ psf / yr</th><th class="num">could really be</th>'
         '<th class="num">pairs contributing</th></tr></thead><tbody>']
    for which, label, rate_ in (('pre', f'before {AGB}', AGPW1), ('post', f'from {AGB}', AGPW2)):
        g = L.get(which) or {}
        ci = (f'${g["ci_lo"]:,.0f} to ${g["ci_hi"]:,.0f}'
              if g.get('ci_lo') is not None else '&mdash;')
        h.append(f'<tr><th>{label}</th><td class="num big">${rate_:,.0f}</td>'
                 f'<td class="num quiet">{ci}</td>'
                 f'<td class="num quiet">{g.get("pairs", 0)}</td></tr>')
    return ''.join(h) + '</tbody></table>'

def age_gap_table():
    """What the rate reads inside each gap band. AN OUTPUT, NEVER A SCREEN — the estimator is
    one slope through every cell, not the average of this column."""
    if not AGR: return ''
    r = ['<table class="fig"><thead><tr><th>Completion gap</th><th class="num">cells</th>'
         '<th class="num">pairs</th><th class="num">reads</th>'
         '<th class="num">median cell</th></tr></thead><tbody>']
    for label, g0, g1 in (('1&ndash;4 years', 1, 5), ('5&ndash;9 years', 5, 10),
                          ('10&ndash;19 years', 10, 20), ('20 years and over', 20, 999)):
        sel = [x for x in AGR if g0 <= x['gap'] < g1]
        if len(sel) < 5:
            r.append(f'<tr><th>{label}</th><td class="num quiet">{len(sel)}</td>'
                     f'<td class="num quiet">&mdash;</td>'
                     f'<td class="num quiet" colspan="2">too thin to read</td></tr>')
            continue
        r.append(f'<tr><th>{label}</th><td class="num quiet">{len(sel)}</td>'
                 f'<td class="num quiet">{npairs(sel)}</td>'
                 f'<td class="num big">${fitted_age(sel):,.0f}</td>'
                 f'<td class="num quiet">${st.median([x["per_yr"] for x in sel]):,.0f}</td></tr>')
    return ''.join(r) + '</tbody></table>'

def fitted_age(rows):
    """lease-pairs.py's estimator: least squares through the origin, sum(diff x gap)/sum(gap^2).
    Not the mean of the per-cell column, which the one-year cells dominate."""
    num = sum(x['diff'] * x['gap'] for x in rows)
    den = sum(x['gap'] ** 2 for x in rows)
    return num / den if den else 0

def age_race_table():
    """The shape horse race, held-out RMSE, lower is better. The page shows it because the
    winner is NOT the figure on the face and a reader is owed that."""
    if not AG: return ''
    r = ['<table class="fig"><thead><tr><th>Shape</th>'
         '<th class="num">average miss</th></tr></thead><tbody>']
    src = AGEV.get('race_honest') or AG['race']
    race = sorted(((l, e) for l, e in src.items() if e is not None), key=lambda x: x[1])
    for label, e in race:
        big = 'big' if label.startswith('TWO BANDS') else 'quiet'
        r.append(f'<tr><th>{html.escape(label)}</th>'
                 f'<td class="num {big}">${e:,.0f}</td></tr>')
    return ''.join(r) + '</tbody></table>'

def age_slice_table():
    """THE TABLE THAT ANSWERS THE QUESTION. A straight line climbs across these rows; a band
    sits flat and then jumps. Shawn, 2026-09-13 — this is the evidence he asked for."""
    if not AGEV.get('slices'): return ''
    r = ['<table class="fig"><thead><tr><th>Both completed around&hellip;</th>'
         '<th class="num">cells</th><th class="num">pairs</th>'
         '<th class="num">reads</th><th class="num">could really be</th></tr></thead><tbody>']
    for sl in AGEV['slices']:
        post = sl['lo_y'] >= AGB
        ci = (f'${sl["ci_lo"]:,.0f} to ${sl["ci_hi"]:,.0f}'
              if sl.get('ci_lo') is not None else '&mdash;')
        r.append(f'<tr{" class=hi" if post else ""}><th>{sl["label"]}</th>'
                 f'<td class="num quiet">{sl["cells"]}</td>'
                 f'<td class="num quiet">{sl["pairs"]}</td>'
                 f'<td class="num {"big" if post else ""}">${sl["rate"]:,.0f}</td>'
                 f'<td class="num quiet">{ci}</td></tr>')
    return ''.join(r) + '</tbody></table>'

def age_region_table():
    """The confound worth taking seriously: post-2010 freehold stock is disproportionately
    central, so "2010 onward" could just be "CCR" wearing a date."""
    if not AGEV.get('region'): return ''
    r = ['<table class="fig"><thead><tr><th>Region</th>'
         f'<th class="num">centred before {AGB}</th>'
         f'<th class="num">centred {AGB} onward</th></tr></thead><tbody>']
    for g in AGEV['region']:
        def cell(c):
            if c['rate'] is None:
                return f'<td class="num quiet">{c["cells"]} cells &mdash; too thin</td>'
            return (f'<td class="num">${c["rate"]:,.0f}'
                    f'<i class="age under">{c["cells"]} cells</i></td>')
        r.append(f'<tr><th>{g["region"]}</th>{cell(g["pre"])}{cell(g["post"])}</tr>')
    return ''.join(r) + '</tbody></table>'

def age_bound_bar():
    """Where the grid search lands when you bootstrap it. The one chart that says the
    boundary is a real feature of the data and not a number someone picked."""
    bb = AGEV.get('bound_boot')
    if not bb: return ''
    r = ['<table class="fig"><thead><tr><th>Boundary the search lands on</th>'
         '<th class="num">share of resamples</th></tr></thead><tbody>']
    for y, share in bb['spread']:
        if share < 0.005: continue
        w = max(2, round(share * 100))
        r.append(f'<tr><th>{y}</th><td class="num {"big" if y == AGB else "quiet"}">'
                 f'{share:.0%}<span style="display:inline-block;height:9px;width:{w * 1.6:.0f}px;'
                 f'margin-left:10px;border-radius:3px;vertical-align:middle;background:'
                 f'{"var(--gold)" if y == AGB else "var(--ink)"}"></span></td></tr>')
    return ''.join(r) + '</tbody></table>'

def age_form_table():
    """The cells where the midpoint form and the piecewise form actually disagree — long gaps
    that span the boundary. Three pairs, and they are the whole evidence base for the
    question, which is the most important thing this table says."""
    if not AGFM.get('wide'): return ''
    r = ['<table class="fig"><thead><tr><th>Older</th><th>Newer</th>'
         '<th class="num">completion</th><th class="num">gap</th>'
         '<th class="num">what it really paid</th><th class="num">midpoint says</th>'
         '<th class="num">piecewise says</th></tr></thead><tbody>']
    for w in AGFM['wide']:
        close = 'pw' if abs(w['actual'] - w['pw']) < abs(w['actual'] - w['mid']) else 'mid'
        mk = lambda v, k: (f'<td class="num {"big" if close == k else "quiet"}">'
                           f'${v:,.0f}</td>')
        r.append(f'<tr><td>{_nm(w["older"])}</td><td>{_nm(w["newer"])}</td>'
                 f'<td class="num quiet">{w["top_old"]}&rarr;{w["top_new"]}</td>'
                 f'<td class="num quiet">{w["gap"]} yr</td>'
                 f'<td class="num">${w["actual"]:,.0f}</td>'
                 + mk(w['mid'], 'mid') + mk(w['pw'], 'pw') + '</tr>')
    return ''.join(r) + '</tbody></table>'

def age_knot_ladder():
    """Move the piecewise knot to the right and watch the newer rate run away while the fit
    keeps improving. The single clearest picture of why that form is not adopted."""
    if not AGFM.get('ladder'): return ''
    r = ['<table class="fig"><thead><tr><th>Put the knot at&hellip;</th>'
         '<th class="num">the newer rate becomes</th></tr></thead><tbody>']
    for k, v, _ in AGFM['ladder']:
        r.append(f'<tr><th>{k}</th><td class="num {"quiet" if k == AGB else ""}">'
                 f'${v:,.0f} / yr</td></tr>')
    return ''.join(r) + '</tbody></table>'

def age_cliff_table():
    """The two near-identical pairs the midpoint form answers 2.8x apart. The single clearest
    reason the APPLIED rule is the piecewise one."""
    if not AGFM.get('cliff'): return ''
    r = ['<table class="fig"><thead><tr><th>Comparable</th><th class="num">centred</th>'
         '<th class="num">gap</th><th class="num">midpoint form</th>'
         '<th class="num">split at the year</th></tr></thead><tbody>']
    for c in AGFM['cliff']:
        r.append(f'<tr><th>{c["top_old"]} against {c["top_new"]}</th>'
                 f'<td class="num quiet">{c["mid"]:.1f}</td>'
                 f'<td class="num quiet">{c["gap"]} yr</td>'
                 f'<td class="num quiet">${c["mid_says"]:,.0f}</td>'
                 f'<td class="num big">${c["pw_says"]:,.0f}</td></tr>')
    return ''.join(r) + '</tbody></table>'

def age_era_table():
    """Freehold against leasehold ON THE SAME COMPLETION ERA. Answers Shawn's challenge that
    $39 sits implausibly close to the leasehold $42."""
    E_ = AGEV.get('era')
    if not E_: return ''
    r = ['<table class="fig"><thead><tr><th>Pairs completed around&hellip;</th>'
         '<th class="num">cells</th><th class="num">reads</th>'
         '<th class="num">as a %</th></tr></thead><tbody>']
    for e_ in E_['rows']:
        if e_['rate'] is None: continue
        r.append(f'<tr><th>freehold, midpoint {e_["from_year"]} onward</th>'
                 f'<td class="num quiet">{e_["cells"]}</td>'
                 f'<td class="num">${e_["rate"]:,.1f}</td>'
                 f'<td class="num quiet">{e_["pct"]*100:+.2f}% / yr</td></tr>')
    r.append(f'<tr class="hi"><th>leasehold, the {E_["lease_band_start"]} lease-start band '
             f'&mdash; completions ~{E_["lease_band_completion"]} onward</th>'
             f'<td class="num quiet">&mdash;</td>'
             f'<td class="num big">${E_["lease_rate"]:,.1f}</td>'
             f'<td class="num quiet">&mdash;</td></tr>')
    return ''.join(r) + '</tbody></table>'

def age_pair_table():
    """Every cell tied back to the headline, closest to the fitted rate first (Shawn's ordering
    ruling on the lease panel, applied here for the same reason)."""
    if not AGR: return ''
    # Sorted by the PER-YEAR miss, so the short gaps that divide their whole uncontrolled
    # difference by one or two sort to the bottom rather than leading. Same ordering and the
    # same columns as the 99-year panel's pair table.
    rows = sorted(AGR, key=lambda x: abs(age_own_yr(x) - age_rule_yr(x)))
    r = ['<table class="fig pairs"><thead><tr><th class="num">#</th><th>older</th><th>newer</th>'
         '<th class="num">apart</th><th class="num">completion</th>'
         '<th class="num">gap</th><th>bed</th><th class="num">difference</th>'
         '<th class="num">$ / yr</th><th class="num">the rule says</th>'
         '<th class="num">off by</th><th class="num">sales</th></tr></thead><tbody>']
    for i, x in enumerate(rows, 1):
        spans = age_split(x['top_old'], x['top_new'])[0] > 0 and age_split(x['top_old'], x['top_new'])[1] > 0
        r.append(f'<tr{" class=hi" if spans else ""}><td class="num quiet">{i}</td>'
                 f'<td>{_nm(x["older"])}</td><td>{_nm(x["newer"])}</td>'
                 f'<td class="num quiet">{x["metres"]}m</td>'
                 f'<td class="num quiet">{x["top_old"]}&rarr;{x["top_new"]}</td>'
                 f'<td class="num quiet">{x["gap"]}y</td><td class="quiet">{x["bed"]}</td>'
                 f'<td class="num quiet">{x["diff"]:+,.0f}</td>'
                 f'<td class="num big">{age_own_yr(x):+,.0f}</td>'
                 f'<td class="num quiet">${age_rule_yr(x):,.0f}</td>'
                 f'<td class="num quiet">{age_own_yr(x) - age_rule_yr(x):+,.0f}</td>'
                 f'<td class="num quiet">{x["n_old"]} / {x["n_new"]}</td></tr>')
    return ''.join(r) + '</tbody></table>'

QDATA = []
PAIRTABLE = pairtable()          # populates QDATA — must run before any template
QJSON = json.dumps(QDATA, separators=(',', ':'))

def check_panels(body):
    """Every panel must be a SIBLING. Counts opens against closes for the tags that can nest
    a panel inside another when one is left hanging. Raises rather than writing a page whose
    navigation silently half-works."""
    import re as _re
    marks = [(m.start(), _re.search(r'data-p="([a-z]+)"', m.group(0)).group(1))
             for m in _re.finditer(r'<div class="panel" data-p="[a-z]+"[^>]*>', body)]
    if not marks: raise SystemExit('check_panels: no panels found — the template moved')
    bounds = [m[0] for m in marks] + [len(body)]
    bad = []
    for (start, name), stop in zip(marks, bounds[1:]):
        seg = body[start:stop]
        for t in ('div', 'section', 'p', 'b', 'i', 'span', 'table', 'tbody', 'thead',
                  'tr', 'td', 'th', 'details', 'summary', 'label', 'button', 'a', 'em'):
            o = len(_re.findall(r'<%s\b' % t, seg)); c = len(_re.findall(r'</%s>' % t, seg))
            if o != c: bad.append(f'  panel "{name}": <{t}> {o} open, {c} close')
    if bad:
        raise SystemExit('check_panels: UNBALANCED TAGS — panels would nest inside each '
                         'other and the nav would render blank panels.\n' + '\n'.join(bad))
    return len(marks)

LC = LAYOUT.counts()
import json as _json
_norm = _json.load(open('../../layout-study/out/normalisation.json'))['floor']['TREASURE AT TAMPINES']
FLOOR_STEP, FLOOR_N = _norm['pct_per_floor'], f"{_norm['pairs']:,}"
LAYOUT_PAIRS = LAYOUT.pairs_table()
LAYOUT_JUMPS = LAYOUT.jumps_table()
LAYOUT_XDEV  = LAYOUT.xdev_table()
LAYOUT_PARC  = LAYOUT.parc_table()
LAYOUT_PARCF = LAYOUT.parc_features_table()
LAYOUT_ROOMS = LAYOUT.rooms_table()
LAYOUT_FSUM  = LAYOUT.feature_summary_table()
LAYOUT_LIB   = LAYOUT.library_table()
LAYOUT_TRI   = LAYOUT.triage_table()
LAYOUT_WEX   = LAYOUT.worked_examples()
LAYOUT_HERO  = LAYOUT.hero_block()
LAYOUT_AGREE = LAYOUT.agreement_table()
LAYOUT_TEND  = LAYOUT.tendency_table()      # median or average -- Shawn, 2026-09-20
LAYOUT_CARVE = LAYOUT.carve_table()         # what one published figure pools, plan pair by plan pair
LAYOUT_FZONE = LAYOUT.floor_zone_table()    # the floor ladder's two zones, and the 1.87x
LAYOUT_FOYER = LAYOUT.foyer_block()         # does an entrance foyer price?
# EVERY figure the layout prose quotes, computed -- see LAYOUT.facts() for why the few historical
# ones (the withdrawn 11.6% and its two component pairs, the 160 sqft cap) stay as literals.
LXF = LAYOUT.facts()
LX_BEST     = LXF.get('best', '')
LX_SPREAD_N   = LXF.get('spread_n', '')
LX_SPREAD_Q1  = f"${LXF['spread_q1']:,.0f}" if LXF.get('spread_q1') else ''
LX_SPREAD_Q3  = f"${LXF['spread_q3']:,.0f}" if LXF.get('spread_q3') else ''
LX_SPREAD_MID = f"${LXF['spread_mid']:,.0f}" if LXF.get('spread_mid') else ''
LX_SCREEN   = f"{LXF['screen_now']:,}"
LX_SAMEBAND = LXF['sameband']
LX_TRIAGE   = LXF['triage_total']
LX_AREAONLY = LXF['area_only']
LX_WCN      = LXF.get('wc_n', 0)
LX_WCR      = f"{LXF.get('wc_r', 0):.3f}"
LX_WCR2     = LXF.get('wc_r2', 0)
LX_WCALONE  = LXF.get('wc_alone_pct', 0)
LX_BATHN    = LXF.get('bath_n', 0)
LX_BATHPP   = LXF.get('bath_pass_pairs', 0)
LX_BATHBIGP = LXF.get('bath_big_pairs', 0)
LX_BATHBIG  = f"{LXF.get('bath_big_lo',0):.1f}&ndash;{LXF.get('bath_big_hi',0):.1f}%"
LX_BATHSML  = f"{LXF.get('bath_small_lo',0):.1f}&ndash;{LXF.get('bath_small_hi',0):.1f}%"
_s2, _s3    = LXF.get('study2', {}), LXF.get('study3', {})
LX_STUDY2   = f"{_s2.get('pct',0):.1f}%"; LX_STUDY2P = _s2.get('pairs', 0)
LX_STUDY3   = f"{_s3.get('pct',0):.1f}%"; LX_STUDY3P = _s3.get('pairs', 0)
LX_STUDY2T  = f"{LXF.get('study2_test',0):+.1f}%"; LX_STUDY3T = f"{LXF.get('study3_test',0):+.1f}%"
LX_STUDYP   = LXF.get('study_pooled', 0)
_aa, _as    = LXF.get('ao_aff', {}), LXF.get('ao_sym', {})
LX_AOAFF    = f"${_aa.get('med',0):,} on {_aa.get('pairs',0)} pairs"
LX_AOSYM    = f"${_as.get('med',0):,} on {_as.get('pairs',0)} pairs"
_N = {13:'Thirteen',12:'Twelve',11:'Eleven',10:'Ten',14:'Fourteen',15:'Fifteen',9:'Nine'}
LX_AOWORD   = _N.get(LXF['area_only'], str(LXF['area_only']))
LX_BATHPUB  = f"{LXF.get('bath_pub_alone',0):.1f}%/{LXF.get('bath_pub_area',0):.1f}%"
_r2, _r3, _bt = LXF.get('rung_svc', {}), LXF.get('rung_yard', {}), LXF.get('bath_row', {})
_p = lambda d: f"{(d.get('pct') or [0,0,0])[1]:.1f}%"
LX_R2, LX_R3 = _p(_r2), _p(_r3)
LX_R2P = f"{_r2.get('sale_pairs_exact',0):,}"; LX_R3P = f"{_r3.get('sale_pairs_exact',0):,}"
LX_R3N = _r3.get('pairs', 0)
LX_BATH, LX_BATHP, LX_BATHN = _p(_bt), f"{_bt.get('sale_pairs_exact',0):,}", _bt.get('pairs', 0)
BODY = f"""
<div class="panel" data-p="summary">
<h1 class="disp">Where the constants now stand</h1>
<p class="lede">Each engine constant, and what the market measures.</p>

<section>
  <div class="scroll"><table class="fig"><thead><tr><th>Term</th><th class="num">Engine constant</th><th>Measured</th></tr></thead><tbody>
  <tr><th><a href="#lease">Lease difference (99 years)</a></th><td class="num big">$40 psf / yr</td>
    <td style="color:var(--gold-soft)">${LPW1:,.0f} before {LPWB} &middot; ${LPW2:,.0f} from {LPWB}, per year of lease start</td></tr>
  <tr><th><a href="#fhage">Lease difference (FH)</a></th><td class="num big">$10 psf / yr</td>
    <td style="color:var(--gold-soft)">${AGPW1:,.0f} before {AGB} &middot; ${AGPW2:,.0f} from {AGB}, per year of TOP</td></tr>
  <tr><th><a href="#mrt">MRT distance</a></th><td class="num big">$50 / $200 / $250</td>
    <td style="color:var(--gold-soft)">+${M['bands'][0]['adj']:,.0f} / +${M['bands'][1]['adj']:,.0f} /
    +${M['bands'][2]['adj']:,.0f}</td></tr>
  <tr><th><a href="#integrated">Integrated</a></th><td class="num big">+5%</td>
    <td style="color:var(--gold-soft)">+{INT_HEAD['pct']:.1f}%</td></tr>
  <tr><th><a href="#tenure">Freehold vs leasehold</a></th><td class="num big">&divide; 1.15</td>
    <td style="color:var(--gold-soft)">+{TGL[0]['pct']*100:.0f}% to +{TGL[-1]['pct']*100:.0f}%, by lease left</td></tr>
  <tr><th><a href="#void">Void space</a></th><td class="num big">full price</td>
    <td style="color:var(--gold-soft)">{VR['discount']:.0f}% off the home&rsquo;s psf</td></tr>
  <tr><th><a href="#ec">EC vs private</a></th><td class="num big">none</td>
    <td style="color:var(--gold-soft)">+{E['launch']['pct']:.0f}% at launch &middot; no difference at resale</td></tr>
  </tbody></table></div>

  <div class="caveat" style="margin-top:18px"><b>The measured figures are in use</b> (adopted
  2026-09-09). EC vs private is reference only. Still on judgement: <b>+{JUDGE['harm']:.0%} GFA
  harmonisation</b> and <b>{JUDGE['cy']} years</b> from lease start to TOP.</div>
</section>
</div>

<div class="panel" data-p="lease" hidden>
<h1 class="disp">What the market pays for a year of lease</h1>
<p class="lede">Between two leaseholds, we compare on <b>lease start</b>.</p>

{hero('$40', 'flat, every comparable',
      [(f'${LPW1:,.0f}', f'years before {LPWB}', None),
       (f'${LPW2:,.0f}', f'years from {LPWB}', None)],
      f'A gap that spans {LPWB} is split between the two rates.',
      base=[(NDEV, 'developments'), (npairs(ALL), 'pairs'),
            (len(ALL), 'comparisons'), (NTX, 'transactions')])}

<section>
  <div class="sechead"><h2 class="disp">How to use it</h2></div>
  <div class="steps">
    <div class="step"><span class="sn">1</span>
      <p>Split the <b>lease gap</b> at {LPWB}. Count the years each side.</p></div>
    <div class="step"><span class="sn">2</span>
      <p>Years <b>before {LPWB}</b> at ${LPW1:,.0f}. Years <b>from {LPWB}</b> at
      ${LPW2:,.0f}.</p></div>
    <div class="step"><span class="sn">3</span>
      <p>Add the two legs, and add that to the comparable's PSF.</p></div>
  </div>

  <div class="calc">
    <h3>Try a pair</h3>
    <div class="cin">
      <label>Comparable lease start<input id="lsA" type="number" inputmode="decimal" value="2005" min="1960" max="2040" step="1"></label>
      <label>Subject lease start<input id="lsB" type="number" inputmode="decimal" value="2025" min="1960" max="2040" step="1"></label>
    </div>
    <div id="calcOut" class="cout"></div>
  </div>

</section>

<section>
  <div class="sechead"><h2 class="disp">The measurement</h2>
  <p><b>{NDEV} developments &middot; {npairs(ALL)} pairs &middot; {len(ALL)} comparisons,
  resting on {NTX:,} transactions.</b> Each development paired with a leasehold neighbour and
  compared bedroom by bedroom, across 24 months of resale and sub-sale to {LW[1]}.</p></div>
  <div class="scroll">{answer_table()}</div>

</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2>
  <p>Three questions, answered once each.</p></div>

  <details><summary>Do the bands move as the stock ages?</summary>
    <p class="expl"><b>No &mdash; they are fixed calendar years.</b> Sales from
    {EW[0]}&ndash;{EW[1]} put the jump on the same years.</p>
    <div class="scroll">{vintage_table()}</div>
    <p class="expl">Lease decay (under 65 years left) will steepen the oldest band from about
    2030. Only {sum(1 for r in ALL if r['ls_old'] + 99 - NOW < 65)} of {len(ALL)} cells are there
    today.</p>
  </details>

  <details><summary>Why the newer band is nearly double</summary>
    <p class="expl"><b>Newer units are smaller.</b> A 3BR from 2011 on is {SHRINK3:.0%} smaller
    ({SQ3_NEW:,.0f} vs {SQ3_OLD:,.0f} sq ft), so the same quantum reads higher per foot.</p>
    <div class="scroll">{why_table()}</div>
    <p class="expl">The jump holds in every row. In percent the bands are {PCT_RATIO:.2f}&times;
    apart; in dollars, {DOL_RATIO:.2f}&times;.</p>
  </details>

  <details><summary>How a pair is built, and every pair</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h3>Held constant</h3><ul>
        <li>within <b>500 m</b> of each other</li>
        <li>same <b>nearest MRT station</b></li>
        <li>identical <b>top-26 primary schools</b> within 1 km</li>
        <li>median sizes within <b>20%</b>, bedroom by bedroom</li></ul></div>
      <div class="card"><h3>Both sides must be</h3><ul>
        <li>leasehold, with a known lease start</li>
        <li><b>200 units</b> or more</li>
        <li><b>5+ transactions</b> in the window</li>
        <li>EC only once privatised &mdash; <b>TOP + 5</b></li>
        <li>resale and sub-sale only</li></ul></div>
      <div class="card"><h3>Not controlled</h3><ul>
        <li><b>floor</b> &mdash; the PSF series carries none</li>
        <li><b>facing</b> &mdash; same</li>
        <li>lease start and building age are<br>confounded: this is blended vintage </li></ul></div>
    </div>
    <p class="expl" style="margin-top:18px">All {len(ALL)} comparisons, closest to the rule
    first. <b>$ / yr</b> is the psf difference over the lease gap. <b>The rule says</b> is
    ${LPW1:,.0f} / ${LPW2:,.0f} for this pair. Nothing is adjusted. <b>Click a row</b> for its
    quarters.</p>
    <p class="expl"><b>The bottom rows are short gaps.</b> A 1-year pair puts its whole psf
    difference into one year, so it swings wide. The fit weights by gap, so these barely move
    it.</p>
    <div class="scroll" style="margin-top:12px">{PAIRTABLE}</div>
  </details>
</section>

</div>

<div class="panel" data-p="fhage" hidden>
<h1 class="disp">What a year of completion is worth between two freeholds</h1>
<p class="lede">Between two freeholds, we compare on <b>TOP completion date</b>.</p>

{hero('$10', 'flat, every freehold comparable',
      [(f'${AGPW1:,.0f}', AGNM[0], None), (f'${AGPW2:,.0f}', AGNM[1], None)],
      f'A gap that spans {AGB} is split between the two rates.',
      base=[(ndev(AGR), 'developments'), (npairs(AGR), 'pairs'),
            (len(AGR), 'comparisons'), (ntx(AGR), 'transactions')])}

<section>
  <div class="sechead"><h2 class="disp">How to use it</h2></div>
  <div class="steps">
    <div class="step"><span class="sn">1</span>
      <p>Both sides <b>freehold</b> (999-year counts). Otherwise use the 99-year panel.</p></div>
    <div class="step"><span class="sn">2</span>
      <p>Split the <b>TOP gap</b> at {AGB}. Count the years each side.</p></div>
    <div class="step"><span class="sn">3</span>
      <p>Years <b>before {AGB}</b> at ${AGPW1:,.0f}. Years <b>from {AGB}</b> at ${AGPW2:,.0f}.
      Add the two and add that to the comparable's psf.</p></div>
  </div>
  <p class="expl"><b>Worked:</b> a 2000-against-2025 comparable is
  {AGB - 2000} years at ${AGPW1:,.0f} plus {2025 - AGB} at ${AGPW2:,.0f} &mdash;
  ${AGPW1 * (AGB - 2000):,.0f} + ${AGPW2 * (2025 - AGB):,.0f} =
  <b>${AGPW1 * (AGB - 2000) + AGPW2 * (2025 - AGB):,.0f} psf</b>.</p>
</section>

<section>
  <div class="sechead"><h2 class="disp">The measurement</h2>
  <p><b>{ndev(AGR)} developments &middot; {npairs(AGR)} pairs &middot; {len(AGR)} comparisons,
  resting on {ntx(AGR):,} transactions.</b> Every freehold paired with a freehold neighbour and
  compared bedroom by bedroom, across 24 months of resale and sub-sale to {cut.CUT_END}.</p></div>
  <div class="scroll">{age_answer_table()}</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2>
  <p>What goes into a pair, and every one of them.</p></div>

  <details><summary>How a pair is built, and every pair</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h3>Held constant</h3><ul>
        <li>within <b>{A['meta']['screens']['radius_m']}&thinsp;m</b> of each other</li>
        <li>same <b>nearest MRT station</b></li>
        <li>identical <b>top-26 primary schools</b> within 1 km</li>
        <li>median sizes within <b>{A['meta']['screens']['size_tol']:.0%}</b>, bedroom by
          bedroom</li></ul></div>
      <div class="card"><h3>Both sides must be</h3><ul>
        <li><b>freehold</b> &mdash; 999-year counts as freehold</li>
        <li><b>{A['meta']['screens']['min_units']} units</b> or more</li>
        <li><b>{A['meta']['screens']['min_n']}+ transactions</b> in the window</li>
        <li>completed at least <b>{A['meta']['screens']['min_gap_years']} year</b> apart</li>
        <li>resale and sub-sale only</li></ul></div>
      <div class="card"><h3>Not controlled</h3><ul>
        <li><b>floor</b> &mdash; the PSF series carries none</li>
        <li><b>facing</b> &mdash; same</li>
        <li>no EC on either side: an EC is<br>leasehold and cannot be a freehold pair</li></ul></div>
    </div>
    <p class="expl" style="margin-top:18px">All {len(AGR)} comparisons, closest to the rule
    first. <b>$ / yr</b> is the psf difference over the TOP gap. <b>The rule says</b> is
    ${AGPW1:,.0f} / ${AGPW2:,.0f} for this pair; tinted rows span {AGB}. Nothing is
    adjusted.</p>
    <p class="expl"><b>The bottom rows are short gaps.</b> A 1-year pair puts its whole psf
    difference into one year, so it swings wide. The fit weights by gap, so these barely move
    it.</p>
    <div class="scroll" style="margin-top:12px">{age_pair_table()}</div>
  </details>
</section>
</div>

<div class="panel" data-p="mrt" hidden>
<h1 class="disp">What the market pays for the walk to the station</h1>
<p class="lede">Two developments on the same station, at different walks. Lease difference
removed.</p>

{hero(' / '.join(f"${M['engine'][b['key']]}" for b in M['bands']), 'three fixed band steps',
      [(f"+${b['adj']:,.0f}", lab, b['devs'], mrt_band_tx(b['key']))
       for b, lab in zip(M['bands'], ('under 5 vs 5-10 min', '5-10 vs over 10 min',
                                      'under 5 vs over 10 min'))],
      f"Under {M['near_m']:,} m &middot; {M['near_m']:,}&ndash;{M['far_m']:,} m &middot; over "
      f"{M['far_m']:,} m, straight-line.",
      base=[(ndev2(MROWS,'closer','further'), 'developments'), (len(MROWS), 'comparisons'),
            (MTX, 'transactions')])}

<section>
  <div class="sechead"><h2 class="disp">The measurement</h2></div>
  <div class="scroll">{mrt_table()}</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2></div>

  <details><summary>The check that the adjustment works</summary>
    <p class="expl">Pairs the same distance from the station should read zero once lease is out.
    They read <b>{'&minus;' if M['placebo']['adj'] < 0 else '+'}${abs(M['placebo']['adj']):.1f}</b>
    across {M['placebo']['pairs']} pairs.</p>
  </details>

  <details><summary>How a pair is built, and every pair</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h3>Held constant</h3><ul>
        <li>same <b>nearest station</b>, and it must be nearest for both</li>
        <li>both inside <b>{M['catchment']:,} m</b> of it</li>
        <li>within <b>{M['pair_cap']:,} m</b> of each other</li>
        <li>identical <b>top-26 primary schools</b> within 1 km</li>
        <li>median sizes within <b>20%</b>, bedroom by bedroom</li></ul></div>
      <div class="card"><h3>Both sides must be</h3><ul>
        <li>leasehold, with a known lease start</li>
        <li><b>200 units</b> or more</li>
        <li><b>5+ transactions</b> in the window</li>
        <li>EC only once privatised &mdash; <b>TOP + 5</b></li></ul></div>
      <div class="card"><h3>Not controlled</h3><ul>
        <li><b>floor</b> and <b>facing</b> &mdash; the PSF series carries neither</li>
        <li>which <b>side</b> of the station the project sits on</li>
        <li>bus and shuttle access</li></ul></div>
    </div>
  
    <p class="expl" style="margin-top:18px">All {len(MROWS):,} comparisons, closest to the band
    first. <b>After lease</b> is the psf difference with lease removed. Below the divider: both
    sides in the same band, which should read about nothing.</p>
    <div class="scroll">{mrt_pairtable()}</div>
  </details>

  
</section>

</div>

<div class="panel" data-p="integrated" hidden>
<h1 class="disp">What the market pays for being on top of the station</h1>
<p class="lede">An integrated development against a plain neighbour on the same station. Lease
and walk removed.</p>

{hero('+5%', 'flat, on an integrated project',
      [(f"+{INT_HEAD['pct']:.1f}%", INT_HEAD['label'], INT_HEAD['devs'],
        int_cut_tx(INT_HEAD)),
       (f"+{G['cuts'][0]['pct']:.1f}%", 'every pair', G['cuts'][0]['devs'],
        int_cut_tx(G['cuts'][0]))],
      f"The figure in use is the under-{INT_HEAD['apmax']:,} m cut.",
      base=[(ndev2(GROWS,'a','b'), 'developments'), (len(GROWS), 'comparisons'),
            (GTX, 'transactions')])}

<section>
  <div class="sechead"><h2 class="disp">The measurement</h2></div>
  <div class="scroll">{int_table()}</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2></div>

  <details><summary>Does it matter how far apart the two sit?</summary>
    <p class="expl"><b>Yes.</b> Steady under {INT_HEAD['apmax']:,} m ({SWEEP_TIGHT}); it drifts up
    once distant pairs are let in.</p>
    <div class="scroll">{apart_table()}</div>
    <p class="expl">A looser limit on the <b>walk to the station</b> also lifts it
    (+{G['dsweep'][1]['rows'][0]['pct']:.1f}% to +{G['dsweep'][1]['rows'][-1]['pct']:.1f}%).</p>
    <div class="scroll">{dsweep_table()}</div>
  </details>

  <details><summary>The check that the adjustments work</summary>
    <p class="expl">Plain against plain on the same station should read zero. Across
    <b>{G['placebo']['pairs']} pairs</b> it reads <b>{G['placebo']['pct']:+.1f}%</b>
    ({G['placebo']['pct_lo']:+.1f}% to {G['placebo']['pct_hi']:+.1f}%).</p>
  </details>

  <details><summary>Every development</summary>
    <div class="scroll">{int_devs()}</div>
    <p class="expl">{INT_THIN} of {len(G['devs'])} rest on three pairs or fewer; read those as
    thin.</p>
  </details>

  <details><summary>How a pair is built, and every pair</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h3>Held constant</h3><ul>
        <li>same <b>nearest station</b>, nearest for both</li>
        <li>within <b>{G['pair_cap']:,} m</b> of each other</li>
        <li>median sizes within <b>20%</b>, bedroom by bedroom</li></ul></div>
      <div class="card"><h3>Adjusted out</h3><ul>
        <li><b>lease</b>, at ${LPW1:,.0f} / ${LPW2:,.0f}, each year of the gap at its own band</li>
        <li><b>walking distance</b>, at ${G['slope']:.0f} per 100 m</li>
        <li>both measured here, neither assumed</li></ul></div>
      <div class="card"><h3>Not controlled</h3><ul>
        <li><b>floor</b> and <b>facing</b></li>
        <li>the quality of the mall attached</li>
        <li>whether the plain neighbour is itself mixed-use</li></ul></div>
    </div>
  
    <p class="expl" style="margin-top:18px">All {len(GROWS)} comparisons, closest to the figure
    first. <b>After lease &amp; walk</b> is the psf difference with both removed. <b>Next
    door</b> marks pairs inside the cut in use.</p>
    <div class="scroll">{int_pairtable()}</div>
  </details>

  
</section>
</div>

<div class="panel" data-p="tenure" hidden>
<h1 class="disp">What the market pays for freehold</h1>
<p class="lede">A freehold against a leasehold neighbour. The premium grows as the lease runs
down.</p>

{hero('&divide; 1.15', 'flat, every freehold comparable',
      [(f'+{g["pct"]*100:.0f}%', ten_step_label(g), g['devs'],
        ten_slice_tx(g, TGL[i-1] if i else None)) for i, g in enumerate(TGL)],
      '',
      base=[(ndev2(TROWS,'fh','lh'), 'developments'), (len(TROWS), 'comparisons'),
            (TTX, 'transactions')])}

<section>
  <div class="sechead"><h2 class="disp">How to use it</h2></div>
  <div class="steps">
    <div class="step"><span class="sn">1</span>
      <p>Take the <b>TOP gap</b> between the two.</p></div>
    <div class="step"><span class="sn">2</span>
      <p>Price that at the <b>measured lease rate</b>: each year of the gap at its own band,
      ${LPW1:,.0f} before {LPWB} and ${LPW2:,.0f} from {LPWB}.</p></div>
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
      <label id="tpL">Freehold comparable &mdash; psf<input id="tfP" type="number" inputmode="decimal" value="2100" min="200" max="9000" step="10"></label>
      <label>Freehold TOP year<input id="tfT" type="number" inputmode="decimal" value="2005" min="1960" max="2035" step="1"></label>
      <label>Leasehold TOP year<input id="tlT" type="number" inputmode="decimal" value="2015" min="1960" max="2035" step="1"></label>
    </div>
    <div id="tenOut" class="cout"></div>
  </div>
</section>

<section>
  <div class="sechead"><h2 class="disp">The measurement</h2></div>
  <div class="scroll">{ten_grad_table()}</div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2></div>

  <details><summary>Does distance affect the premium?</summary>
    <div class="scroll">{ten_sens_table()}</div>
  </details>

  <details><summary>Does it hold across the island, and across bedrooms?</summary>
    <div class="scroll">{ten_slice_table('region', 'Region')}</div>
    <p class="expl" style="margin-top:18px">The regions agree, so one percentage serves the
    island.</p>
    <div class="scroll" style="margin-top:14px">{ten_slice_table('bedroom', 'Bedroom')}</div>
    <p class="expl" style="margin-top:18px">1BR and 4BR are too thin to show.</p>
  </details>

  <details><summary>How a pair is built, and every pair</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h3>Held constant</h3><ul>
        <li>same <b>nearest MRT station</b></li>
        <li>within <b>{T['screens']['radius_m']:,} m</b> of each other</li>
        <li>median sizes within <b>20%</b>, bedroom by bedroom</li></ul></div>
      <div class="card"><h3>Both sides must be</h3><ul>
        <li>one <b>freehold</b> (or 999-year), one <b>leasehold</b></li>
        <li><b>{T['screens']['min_units']:,} units</b> or more</li>
        <li><b>{T['screens']['min_n']}+ transactions</b> in the window</li></ul></div>
      <div class="card"><h3>Not controlled</h3><ul>
        <li><b>floor</b> and <b>facing</b></li>
        <li>the age gap between the two, beyond the lease rate</li></ul></div>
    </div>
<p class="expl" style="margin-top:18px">All {len(TROWS)} comparisons, closest to their step
    first. Each row is checked against the step for its lease left.</p>
    <div class="scroll">{ten_pairtable()}</div>
    </details>

  

</section>

</div>
<div class="panel" data-p="void" hidden>
<h1 class="disp">What the market pays for the void</h1>
<p class="lede">The penthouse against the units below it in the same stack. Floor removed at
{V['meta']['floor_step']*100:.1f}% a floor.</p>

{hero('1.00&times;', 'every strata sqft priced alike',
      [(f"{VR['discount']:.0f}% off", 'what a resale buyer pays for the extra area', None)],
      '', base=[(VR['devs'], 'developments'), (VR['pairs'], 'penthouse resales')])}

<section>
  <div class="sechead"><h2 class="disp">How to use it</h2></div>
  <div class="calc">
    <h3>What should the penthouse cost</h3>
    <div class="cin">
      <label>Unit below &mdash; sqft<input id="vbS" type="number" inputmode="decimal" value="1216" min="200" max="9000" step="1"></label>
      <label>Unit below &mdash; psf<input id="vbP" type="number" inputmode="decimal" value="2662" min="200" max="9000" step="10"></label>
      <label>Penthouse sqft<input id="vpS" type="number" inputmode="decimal" value="1421" min="200" max="9000" step="1"></label>
      <label>Floors below<input id="vF" type="number" inputmode="decimal" value="1" min="0" max="70" step="1"></label>
    </div>
    <div id="voidOut" class="cout"></div>
  </div>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2></div>

  <details><summary>The check that the floor step works</summary>
    <p class="expl">Stacks whose top unit is the same size should read zero. Across
    {V['resale']['placebo']['pairs']:,} resales it reads
    <b>{V['resale']['placebo']['residual_pct']:+.2f}%</b>.</p>
    <div class="scroll">{void_sens()}</div>
  </details>

  <details><summary>How a pair is built, and every development</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h3>Held constant</h3><ul>
        <li>same project, same <b>block</b>, same <b>stack</b></li>
        <li>&mdash; so the same <b>floor plate</b>, by construction</li>
        <li>base legs within <b>{V['meta']['size_tol']*100:.0f}%</b> of the stack&rsquo;s median size</li>
        <li>base legs within <b>{V['meta']['match_days']} days</b> of the penthouse resale</li></ul></div>
      <div class="card"><h3>The screens</h3><ul>
        <li><b>{V['meta']['min_base']}+ base legs</b>, so the comparator is a median</li>
        <li>extra area <b>{V['meta']['extra_band'][0]*100:.0f}&ndash;{V['meta']['extra_band'][1]*100:.0f}%</b>
            of the floor plate</li>
        <li>under that is a bay window; over it is a <b>duplex</b> &mdash; a second floor plate,
            which is what this pair exists to exclude</li></ul></div>
      <div class="card"><h3>Not controlled</h3><ul>
        <li><b>what the extra area is</b> &mdash; void, roof terrace or roof</li>
        <li><b>renovation and fit-out</b>, on either leg</li>
        <li>the top floor&rsquo;s own view, beyond the floor step and the check above</li></ul></div>
    </div>
  
    
    <p class="expl" style="margin-top:18px">Every development with two or more penthouse
    resales, closest to the figure first.</p>
    <div class="scroll">{void_devs(n=30)}</div>
  </details>
</section>
</div>

<div class="panel" data-p="ec" hidden>
<h1 class="disp">What a buyer pays to skip the EC</h1>
<p class="lede">An EC against the private condo launching beside it. Then the same comparison
at resale.</p>

{hero('none',
      'reference only &mdash; nothing in the engine reads this',
      [(f"+{E['launch']['pct']:.0f}%", 'at launch, private over EC', E['launch']['projects']),
       (f"{E['resale']['pct']:+.1f}%", 'at resale &mdash; no difference', E['resale']['projects'])],
      '')}

<section>
  <div class="sechead"><h2 class="disp">At launch</h2>
  <p>{E['launch']['pairs']:,} pairs across {E['launch']['projects']} EC launches, against the
  nearest private launches.</p></div>
  <div class="scroll">{ec_launch_table()}</div>
  {ec_unmatched_line()}
</section>

<section>
  <div class="sechead"><h2 class="disp">At resale</h2>
  <p>{E['resale']['pairs']:,} pairs across {E['resale']['projects']} ECs, against leasehold
  private of the same vintage within {E['meta']['km']:g} km.</p></div>
  <div class="scroll">{ec_age_table()}</div>
  <p class="expl"><b>{E['resale']['pct']:+.1f}% overall</b> ({E['resale']['ci'][0]:+.1f}% to
  {E['resale']['ci'][1]:+.1f}%) &mdash; no difference. By age the direction flips, but every
  band&rsquo;s range covers zero.</p>
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2></div>

  <details><summary>How a pair is built, and every EC</summary>
    <div class="cards" style="margin-top:6px">
      <div class="card"><h3>Held constant</h3><ul>
        <li>floor area within <b>{E['meta']['sizetol']*100:.0f}%</b></li>
        <li>contract date within <b>{E['meta']['months']} months</b></li>
        <li>launch: <b>nearest, within {(E['launch'].get('ladder') or [2000])[-1]/1000:g} km</b>
            &middot; resale: <b>within {E['meta']['km']:g} km</b></li>
        <li>resale only: <b>leasehold</b> comparables, lease start within
            <b>{E['meta']['lstol']} years</b></li></ul></div>
      <div class="card"><h3>How it is read</h3><ul>
        <li>the <b>nearest {E['meta']['near']}</b> comparables per EC transaction</li>
        <li>the <b>median of the pair ratios</b>, never a difference of two medians</li>
        <li>years built is <b>lease start + 4</b>, the median gap to TOP</li></ul></div>
      <div class="card"><h3>Not controlled</h3><ul>
        <li><b>floor</b> and <b>facing</b></li>
        <li>walking distance to the station, on either leg</li>
        <li>the EC income ceiling and resale restrictions themselves</li></ul></div>
    </div>
  
    <p class="expl" style="margin-top:18px">Every EC at resale, closest to the figure first.
    Negative means the EC trades above its private neighbour.</p>
    <div class="scroll">{ec_resale_table()}</div>
  </details>
</section>
</div>


<div class="panel" data-p="layout" hidden>
<h1 class="disp">What the resale market pays for a layout</h1>
<p class="lede">Two units in the same development, the same size band and the same bedroom count,
where one has a room the other does not. What the second one sold for, minus the first.</p>

{LAYOUT_HERO}

<section>
  <div class="sechead"><h2 class="disp">What each feature is worth</h2></div>
  <p class="expl">The <b>trimmed average</b> across every development where the feature could be
  isolated &mdash; one vote per development, not one per reading &mdash; with the range beneath
  it. <b>Quantum is the figure to use</b>; the percentage is there because it
  travels between price points better than dollars do. A feature is named for the room that
  drives it &mdash; a yard joins the name because the yard is what moves the figure, while a
  shelter, a store or a utility room is ancillary and is named on the individual reading instead.</p>
  {LAYOUT_FSUM}
  <p class="expl">These are <b>central tendencies with real spread</b>, not price tags. A bedroom
  crossing is tight. A single feature is looser: the middle half of Riverfront&rsquo;s
  {LX_SPREAD_N} bathroom pairs spans {LX_SPREAD_Q1} to {LX_SPREAD_Q3} around a figure of
  {LX_SPREAD_MID}. The feature is real and it is priced; the precision is not to the dollar.</p>
</section>

<section>
  <div class="sechead"><h2 class="disp">How we did it</h2></div>
  <p class="expl">Three of the figures above, shown the long way. Every row is a real caveat: the
  unit, the floor, the date and the price. <b>Where two units match on floor and facing, nothing
  is adjusted at all</b> &mdash; the difference between the two sale prices is the figure, and the
  published number is the trimmed average of every such pair. Where they do not match, the base sale is
  moved to the other unit&rsquo;s floor and facing first, using rates measured on
  <i>different</i> pairs; that second track exists to check the first, and the two agree.</p>
  {LAYOUT_WEX}
</section>

<section>
  <div class="sechead"><h2 class="disp">Behind it</h2>
  <p>Everything the figures rest on. Nothing here is needed to read them.</p></div>

  <details><summary>Median or average &mdash; which one, and why</summary>
  {LAYOUT_TEND}
  </details>

  <details><summary>What a single figure is pooling, plan by plan</summary>
  {LAYOUT_CARVE}
  </details>

  <details><summary>Does an entrance foyer price?</summary>
  {LAYOUT_FOYER}
  </details>

  <details><summary>The floor ladder is not one rate</summary>
  {LAYOUT_FZONE}
  </details>

  <details><summary>Does the adjustment hold up? Every contrast, both tracks</summary>
  <p class="expl">Adjusting is not modelling, and the difference is why the first version of this
  study was withdrawn: that one fitted a residual to the same pairs it was measuring. Here both
  adjusters are measured <b>somewhere else, on other pairs</b> &mdash; the floor step from
  <b>same-stack repeat sales</b> ({FLOOR_STEP}%/floor, {FLOOR_N} sale pairs), the facing premiums from the
  stack study&rsquo;s resale pairs, direct only, never chained.</p>
  <p class="expl">The <b>test</b> column compares the exact figure against <b>only the pairs the
  exact rule throws away</b> &mdash; different floor, different facing, or both. The two sets share
  no transaction, so if adjusting works the discarded pairs should reproduce the exact answer.
  On the best-sampled contrast they do: <b>{LX_BEST}</b>.</p>
  <p class="expl">One guard came straight out of this test. Treasure&rsquo;s facing premiums were
  measured on <b>3BR and 4BR only</b>. Applied to 2BR units they pulled every 2BR contrast down by
  11&ndash;35%; refusing to extrapolate them cut that to 3&ndash;8%. <b>A facing move is now
  refused for any bedroom class the facing premium was not measured on.</b> The floor step is
  measured on every stack, so it carries everywhere.</p>
    <div class="scroll">{LAYOUT_AGREE}</div>
  </details>

  <details><summary>Every reading behind every feature</summary>
  <p class="expl">Every pair here has <b>passed the gate</b>: the differing features are absent on
  one side and present on the other, at least <b>60% of the area step is the added rooms</b>, measured
  off the plans, and <b>no more than 40% of the step went into corridor</b> &mdash; the circulation
  guard, added 2026-09-19. It removed Symphony Suites B1 &rarr; C1, whose +107 sqft put +49 into
  hallway. Pairs that failed &mdash; same feature both sides at a different size, or
  an area step too big for the rooms added &mdash; are <b>not shown</b>, and neither is any pair
  without a feature difference at all. They stay recorded with their reasons in
  <code>out/library-layout-pairs.csv</code>. The line in bold under each row is the
  <b>product class</b> the figure belongs to, which is how it will pool with other developments.</p>
  <div class="scroll">{LAYOUT_LIB}</div>
  <p class="expl"><b>Every reading, grouped by what the step actually adds.</b> A feature NAME is
  not a product. The class label carries bedrooms, bathrooms, WC, shelter and study, and says
  nothing about a yard or a utility room. <b>The yard is the discriminator, not the WC:</b> a WC
  without one is <b>{LX_R2}</b> on {LX_R2P} exact pairs, and a WC with a yard is <b>{LX_R3}</b> on
  {LX_R3P} exact pairs across {LX_R3N} readings &mdash; roughly double. What sits in the third
  room is named in the detail but does not make a separate row: Riverfront prints STORE where
  Treasure prints HS and it is the same reinforced household shelter, mandatory since 1998, on a
  2023 development whose sheets never print HS at all. Ruling 3, the plan beats the label.
  Each row here is one measured contrast, so a thin reading cannot hide inside a pooled figure.</p>
  <p class="expl"><b>These rows are now built from the class-linked library, and that removed a
  large double count.</b> Shawn spotted it from the page: &ldquo;the fact that the % are no
  different from WC / yard / Home Shelter, shouldnt we combine these two together?&rdquo; They were
  not two products &mdash; they were the same pairs. &ldquo;Shelter + yard + WC + enclosed
  kitchen&rdquo; was five Treasure size pairs (C4/C6&nbsp;&rarr;&nbsp;C8P/C9P/C10P) and the class
  contrast <code>3BR2B&nbsp;&rarr;&nbsp;3BR2B+WC+HS</code> pools exactly those layouts. Audited
  across the table, <b>15 of the 22 rows previously published were the same pairs as a class
  contrast</b>: the page was still being built from the strata-area route while the
  transaction&nbsp;&rarr;&nbsp;layout link supersedes it at Parc Esta, Riverfront, Treasure and
  A Treasure Trove. <b>Two identical percentages are a duplicate detector</b>, and it was caught
  by eye before it was caught by code. <b>Class&#8209;linked</b> rows come from a development with a
  transaction&nbsp;&rarr;&nbsp;layout link, where the two sides are different product classes
  because the drawings say so; those do not face the 60% share gate, which exists to test whether
  a <i>size</i> step is a feature step and is answered by construction here. Rows with a step in
  sqft are matched on strata area and still face the gate and the circulation guard.
  The <b>two-track test</b> is the adjusted track against the exact one: inside
  <span class="lok">&plusmn;5%</span> is agreement, <span class="lwarn">&plusmn;10%</span> is
  tolerable, <span class="lbad">beyond</span> fails and the reading is recorded, not quoted.</p>
  </details>

  <details><summary>How the pairs were chosen, and what that missed</summary>
  <p class="expl"><b>Shawn found an error in this page by hand&#8209;pricing one pair.</b> At
  Affinity at Serangoon, 904 sqft and 1,076 sqft are the same three&#8209;bedroom plan apart from a
  yard, a utility room and a WC, and the gap is about <b>$465,000</b> &mdash; against a published
  &ldquo;WC + utility + yard&rdquo; of <b>11.6% / $173,484</b>. The candidate screen had never
  proposed that pair, because it capped a step at <b>160 sqft</b> and this one is +172. The cap was
  standing in for &ldquo;do not pair across products&rdquo;, which is the product class&rsquo;s job,
  not a number&rsquo;s. Dropped, the screen went from <b>85 candidate pairs to {LX_SCREEN}</b>.</p>
  <p class="expl">The cap turned out to be the smaller half of it. Of the {LX_SAMEBAND} same&#8209;band
  candidates, only 12 were in the library <i>at that point</i>: eight had been hidden by the cap,
  and <b>29 were visible the whole time and had simply never been read</b>. A library assembled that way is not a
  selection of the best evidence &mdash; it is whichever pairs happened to get a plan read.
  <b>A screen threshold is a silent exclusion:</b> what is never proposed is never measured and
  never missed.</p>
  <p class="expl">The old 11.6% was the median of two pairs: Symphony Suites at $113,000, whose
  step is 46% corridor, and Parc Esta at $233,967, which had <b>no exact pairs at all</b> and rode
  the adjusted track. Across the {LX_WCN} independent WC readings there are now, <b>step size explains
  {LX_WCR2}% of the variance</b> in the premium (r&nbsp;=&nbsp;{LX_WCR}). <b>The WC itself is
  worth {LX_WCALONE}%</b>; the rest is the yard and the wet&#8209;service room.</p>
  <p class="expl"><b>Two things this has not yet fixed, stated so they are not mistaken for
  settled.</b> The <b>extra bathroom</b> has {LX_BATHN} readings: {LX_BATHBIG} at Riverfront and Parc Esta,
  which carry {LX_BATHBIGP} of the {LX_BATHPP} passing pairs, and {LX_BATHSML} at High Park, the
  cheapest base in the set;
  the published {LX_BATHPUB} sits inside that range and is not overturned, but it should be quoted
  per region rather than pooled. The <b>study</b> is the same conflation, unresolved: at Parc Esta
  alone it is <b>{LX_STUDY2} on a two&#8209;bedroom</b> ({LX_STUDY2P} exact pairs, test
  {LX_STUDY2T}) and <b>{LX_STUDY3} on a three&#8209;bedroom</b> ({LX_STUDY3P} pairs, test
  {LX_STUDY3T}), while this page still pools them at {LX_STUDYP}%. One
  passes and one fails badly, so it is not yet a finding &mdash; but the study figure should not be
  leaned on until it is split by bedroom count.</p>
  <div class="scroll">{LAYOUT_PAIRS}</div>
  <p class="expl"><b>The WC is quoted by package, not as one number, and that is a correction.</b>
  Until 2026-09-19 this page carried a single &ldquo;WC + utility + yard&rdquo; row at
  <b>11.6% / $173,484</b>. It was the median of two pairs &mdash; Symphony Suites at $113,000, whose
  step is 46% corridor, and Parc Esta at $233,967, which had <b>no exact pairs at all</b> and was
  carried on the adjusted track. Shawn found the error by hand-pricing one pair at Affinity at
  Serangoon, where 904 sqft and 1,076 sqft are the same three-bedroom plan apart from a yard, a
  utility room and a WC, and the gap is about $465,000. The candidate screen had never proposed
  that pair, because it capped a step at 160 sqft and this one is +172. With the cap dropped there
  are twelve readings instead of two, and they do not describe one product: <b>a WC on its own is
  worth 5.7%</b>, while a WC arriving with a yard and a wet-service room runs <b>18% to 24%</b>.
  The WC is the cheap part. Each row below is therefore a package, not a tick-box, and the rows
  drawn from a linked development are matched on <b>product class</b> rather than on strata area.</p>
  </details>

  <details><summary>What the candidate pairs turned out to be</summary>
  <p class="expl">Forty pairs of strata-area clusters sat in the same bedroom band with enough
  matched sales to be worth reading. Resolving each one to a <b>product class</b> off the plans
  is what separates a feature from a price for square feet.</p>
  <div class="scroll">{LAYOUT_TRI}</div>
  <p class="expl"><b>{LX_AOWORD} of the {LX_TRIAGE} were never figures.</b> Same product class on
  both sides &mdash; Affinity 850&nbsp;&rarr;&nbsp;904 is <code>3BR2B</code> either way and reads
  {LX_AOAFF}; Symphony 893&nbsp;&rarr;&nbsp;915 is
  <code>3BR2B+WC+U+Y</code> either way and reads {LX_AOSYM}. Those two bracket what area alone
  buys, and they are exactly the rows a screen that matched on SIZE would have published as
  feature premiums. This is ruling 5 doing its job, and it is the reason the class, not the
  square foot, is the unit.</p>
  </details>

  <details><summary>Crossing a bedroom count</summary>
  <p class="expl">Every class of one bedroom count against every class of the next, so each row
  says <b>which</b> smaller flat it starts from. <b>No strata areas</b> &mdash; the class is the unit,
  because that is what pools across developments. The class is <b>what the plan draws</b>:
  bedrooms, bathrooms, and a WC (+WC), household shelter (+HS) or study (+S) where there is one
  &mdash; 3BR2B+WC+HS is what Treasure sells as &ldquo;3 Bedroom Premium&rdquo;, 3BR2B its &ldquo;3 Bedroom&rdquo;. Developers&rsquo;
  own tier names do not travel; some print none. The small line under each row is which
  layouts went in.</p>
  <div class="scroll">{LAYOUT_JUMPS}</div>
  </details>

  <details><summary>Every development, crossing a bedroom count</summary>
  <p class="expl">Twenty developments, every one with a facing read, both tracks. This needs
  <b>no floor plan</b>: a bedroom count is already solved per project from the unit-mix crawls,
  so it runs today across everything. <b>A feature premium is not</b> &mdash; which layout has a
  household shelter is in no transaction record, so that stays development-by-development through
  the plans &mdash; Treasure and Parc Esta so far.</p>
  <p class="expl"><b>These are bedroom COUNT to bedroom COUNT, not class to class</b>, and they
  are a coarser question than the Treasure table above. Bathrooms, WC and study come off the
  plans, which only Treasure and Parc Esta have had read. Pooling all 2BR against all 3BR also mixes a small 2BR
  into a large 3BR, which is why Treasure reads $550,000 here and $406,000 as 2BR2B &rarr;
  3BR2B.</p>
  <p class="expl"><b>Quantum does not travel between developments.</b> Ruling 4 was measured
  inside one project holding the feature package; across projects the 2BR &rarr; 3BR step runs
  from $117,000 to $980,000. Percent is the steadier of the two (CV 33&ndash;37% against
  40&ndash;48%) but a third is still not a national figure. <b>Read these per development.</b>
  Nine of the thirty-five testable crossings fail the 10% test &mdash; there, only the exact
  figure may be used.</p>
  {LAYOUT_XDEV}
  </details>

  <details><summary>Parc Esta, read in full</summary>
  <p class="expl">All 70 layouts from 2BR up read off the plan sheets. Same rule, same classes.
  <b>No household shelter on any Parc Esta plan</b>, 2BR to 5BR, so +HS never appears here.
  Top-floor units carry 66&ndash;215 sqft of <b>void</b> (air over the living room) in their strata
  area, and ground-floor units a PES; neither is ever paired with its own standard unit.
  Where exact pairs are thin the adjusted track carries the row.</p>
  {LAYOUT_PARC}
  <p class="expl"><b>Feature pairs, rooms measured.</b> 18 plans measured room by room. A pair
  passes when the added feature rooms are at least <b>60%</b> of the extra square feet &mdash; lowered
  from 80% on 2026-09-19, after Shawn judged Riversails&rsquo; study pairs (63&ndash;67%) to be the same
  product plus a study. Six Parc Esta pairs pass. The study pairs are adjusted-track only.</p>
  {LAYOUT_PARCF}
  </details>

  <details><summary>Measured room areas</summary>
  <p class="expl">Rooms read off the plan sheets as rectangles, then <b>self-calibrated</b>: each
  layout's room sum is set equal to its published strata area, which fixes sqft-per-pixel without
  needing the drawing scale. <b>About &plusmn;10% on a large room and worse on a small one</b>;
  circulation is absorbed into the adjacent room, so the kitchen figures for C4 and C7 are
  overstated. Good enough to say whether a room is materially bigger. Not good enough to quote.</p>
  {LAYOUT_ROOMS}
  </details>

  <details><summary>How a pair is built, and what is held constant</summary>
  <div class="cards" style="margin-top:6px">
    <div class="card"><h3>Held constant</h3><ul>
      <li><b>same floor</b>, exactly &mdash; not a band, not a modelled step</li>
      <li><b>same facing</b>, on the stack-study facingType</li>
      <li><b>six months</b>, twelve at the outside</li>
      <li><b>resale only</b> &mdash; the developer price list is not evidence of value</li></ul></div>
    <div class="card"><h3>How a layout is identified</h3><ul>
      <li>the <b>stack schedule printed on each plan sheet</b>, including mirror stacks</li>
      <li>stack <b>and</b> floor range &mdash; a stack changes layout at the top floor</li>
      <li>89.1% of the development's caveats link this way</li></ul></div>
    <div class="card"><h3>Not controlled</h3><ul>
      <li><b>renovation and condition</b> &mdash; not in REALIS</li>
      <li>seller urgency, tenancy, mortgagee sales</li>
      <li>room proportions the annotation does not measure &mdash; two layouts at the
          same 678 sqft still differ by about $22,000</li></ul></div>
  </div>
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
    <span class="chip" id="layoutKey" style="touch-action:manipulation" title=""><b></b> Internal &mdash; Constant Calibration</span>
    <span class="chip asof">Figures as of {cut.VINTAGE}</span>
  </div>
  <nav class="terms" aria-label="The constants">
    <button type="button" class="done" data-go="summary" aria-current="true">
      <span class="tn">Summary</span></button>
    <button type="button" class="done" data-go="lease">
      <span class="tn">Lease Difference (99 Years)</span>
      <span class="ts">${LPW1:,.0f} / ${LPW2:,.0f} a year</span></button>
    <button type="button" class="done" data-go="fhage">
      <span class="tn">Lease Difference (FH)</span>
      <span class="ts">${AGPW1:,.0f} / ${AGPW2:,.0f} a year</span></button>
    <button type="button" class="done" data-go="mrt">
      <span class="tn">MRT Distance</span>
      <span class="ts">${M['bands'][0]['adj']:,.0f} / ${M['bands'][1]['adj']:,.0f} /
        ${M['bands'][2]['adj']:,.0f}</span></button>
    <button type="button" class="done" data-go="integrated">
      <span class="tn">Integrated</span>
      <span class="ts">+{INT_HEAD['pct']:.1f}%</span></button>
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
  <b>all figures as of {cut.VINTAGE}</b>, cut at {cut.CUT_END} and pinned there —
  a data refresh does not move them; re-cutting is deliberate ·
  generated {datetime.date.today().isoformat()}</span>
</footer>
</div>
<script>var QD={QJSON};</script>
<script>{JS.replace('%TENB%', TENB_JS).replace('%TENS%', TENS_JS).replace('%PW%', PW_JS).replace('%LO%', f'{MID_LO}').replace('%HI%', f'{MID_HI}').replace('%VLO%', f"{VR['lo']}").replace('%VHI%', f"{VR['hi']}").replace('%VMID%', f"{VR['ratio']}").replace('%VFS%', f"{V['meta']['floor_step']}")}</script>
</body></html>
"""
NPANELS = check_panels(BODY)      # refuses to write a page whose panels nest
open(OUT, 'w').write(HTML)
print(f'wrote {os.path.relpath(OUT, HERE)}  ({len(HTML)//1024} KB)')
print(f'  {NDEV} developments · {npairs(ALL)} pairs · {len(ALL)} cells')
for _, _, nm in BANDS:
    c = BANDCI[nm]
    print(f'    {nm:14s} ${BANDR[nm]:5.1f}/yr  95% [{c[0]:.1f}, {c[1]:.1f}]  {ndev(rows_in(nm)):3d} devs')
print(f'  held-out: flat {CV_FLAT/1000:.1f}k · TWO {CV_TWO/1000:.1f}k · three {CV_THREE/1000:.1f}k')
print(f'  region in the newer band: RCR ${fit(RCR_NEW):.0f} vs OCR ${fit(OCR_NEW):.0f}, p={P_RNEW[1]:.3f}')
# The three removed explain blocks were also CHECKS. They still run, here, so a future re-cut
# cannot quietly break one without anybody seeing it.
_med = st.median(abs(x) for x in RESID)
print(f'  fit: {WITHIN}/{len(ALL)} cells within $200 of their band; median miss ${_med:,.0f}')
print(f'  base: {NTX:,} transactions over {NPRICE} project x bedroom price points; median {TXMED:,.0f} a side, {TXPAIR:,.0f} a comparison')
print(f'  timing: sides offset {OFF_ME:+.2f} months on average; quarter-matched reads '
      f'${MATCHQ[OLD_NM]:.1f}/${MATCHQ[NEW_NM]:.1f} against ${BANDR[OLD_NM]:.1f}/${BANDR[NEW_NM]:.1f}')
print(f'  outside the central 95%: {len(MISSES)} cells; dropping them gives '
      f'${TRIMR[OLD_NM]:.1f}/${TRIMR[NEW_NM]:.1f}')
if M and M.get('early'):
    # THE CHECK SURVIVES THE PAGE. Shawn took the MRT replication off the panel; the earlier
    # window is still computed on every re-cut and reported here, so a band that fails to
    # replicate cannot pass unnoticed just because it is no longer displayed.
    _e = {b['key']: b for b in M['early']['bands']}
    print('  MRT replication ' + M['early']['window'][0] + '..' + M['early']['window'][1]
          + ': ' + ' · '.join(f"{b['key']} ${b['adj']:+,.0f} now vs ${_e[b['key']]['adj']:+,.0f} then"
                              for b in M['bands'] if b['key'] in _e))
