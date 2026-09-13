#!/usr/bin/env python3
"""AGE CALIBRATION — freehold vs freehold, on matched neighbour pairs.

Shawn asked, 2026-09-13: "if its a freehold vs a freehold, what then would be the price
per year of TOP difference? can you do the analysis based on the same methodology as the
lease difference calibration exercise?"

WHY THIS IS A DIFFERENT QUESTION FROM lease-pairs.py. That study measures what a year of
LEASE START is worth between two LEASEHOLD neighbours, and its answer ($24.7 pre-2011 /
$42.3 from 2011) necessarily bundles two things that move together on a leasehold: the
building got newer, AND the lease got longer. Between two FREEHOLDS there is no lease to
lengthen. What is left is the pure price of a newer building, on the only clock both sides
share — COMPLETION. That is the number this script measures.

It is not new ground so much as a promotion. tenure-pairs.py already fits an FH x FH
vintage rate as a BY-PRODUCT of its placebo (`fh_age_rate`, $19.5/yr) — but as a single
grid-searched scalar, co-fitted with a premium term, with no interval, no band test and no
held-out error. Shawn asked for the lease exercise's methodology, so this runs it properly:
least squares through the origin, the band horse race, a bootstrap interval, a held-out
comparison and the gap-band table.

METHOD — identical to lease-pairs.py except where the clock forces a change:

  PAIR SCREEN
    BOTH FREEHOLD (999-year counts as freehold — Shawn's standing rule, one classifier)
    both >= 200 units, within 500 m, same nearest OPERATIONAL station,
    identical TOP-26 primary-school set within 1 km, TOP gap >= 1 yr
    EC excluded outright: an EC is leasehold, so it cannot appear on either side here.

  CELL SCREEN, per bedroom inside a pair
    >= 5 transactions each side in the window, median sizes within 20%

  THE CLOCK IS COMPLETION, NOT LEASE START. Ruled for the tenure study on 2026-09-08 and it
  binds here for the same reason: a freehold has no lease start to difference against, and
  the 999-year leases that Shawn classifies as freehold carry real lease starts as far back
  as 1827. Completion is the only clock both sides share.

  THE ESTIMATOR is lease-pairs.py's fitted(): sum(diff x gap) / sum(gap^2), least squares
  through the origin. Not the mean of per-cell $/yr, which the one-year cells dominate.

  THE BAND QUESTION IS AN OUTPUT, NOT AN ASSUMPTION. The lease study found two bands split
  at a 2011 lease-start midpoint. Whether the SAME shape holds on the TOP clock is exactly
  what a horse race decides, so flat, two-band (over a grid of boundaries) and a linear
  curve are all fitted and ranked on held-out error. Report what wins; if nothing separates,
  say the level is the finding and the shape is not identified — the lease study's own
  conclusion about its knee.

  THE PLACEBO IS THE INTERCEPT. Two freeholds completed the same year, next door, matched on
  bedroom and size, should cost the same. Fitting with an intercept and finding it
  indistinguishable from zero is what says the gap is doing the work and not the pairing.

Read-only consumer of ../../property-analyzer/data/. Run:
    python3 age-pairs.py
"""
import json, math, itertools, collections, statistics as st, os, random

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', '..', 'property-analyzer', 'data')
J = lambda f: json.load(open(os.path.join(DATA, f)))

RADIUS_M      = 500
MIN_UNITS     = 200
MIN_N         = 5
SIZE_TOL      = 0.20
MIN_GAP_YEARS = 1
SCHOOL_KM     = 1000
BEDS          = ['1BR', '2BR', '3BR', '4BR+']
WINDOWS       = [12, 24]

R = 6371000
def hav(a, b, c, d):
    ra, rc = math.radians(a), math.radians(c)
    dla, dln = math.radians(c - a), math.radians(d - b)
    q = math.sin(dla/2)**2 + math.cos(ra)*math.cos(rc)*math.sin(dln/2)**2
    return 2 * R * math.asin(math.sqrt(q))

dsi     = J('dsi-index.json')
projs   = dsi['projects']
schools = dsi['schools']
base    = J('pricegap-base.json')['projects']
det     = J('pg-project-details.json')['projects']
psf     = J('psf-history.json')['projects']
qh      = J('quantum-history.json')['projects']
mrt     = [s for s in J('mrt-stations.json')['stations'] if s.get('status') == 'operational']

import cut                      # THE PINNED CUT — a crawl must not move the figures
LAST = cut.last_month(psf)
def months_back(mo, n):
    y, m = map(int, mo.split('-')); t = y*12 + m - 1 - n
    return f'{t//12:04d}-{t%12+1:02d}'

# ── the eligible universe ────────────────────────────────────────────────────
P, rejected = {}, collections.Counter()
for p in projs:
    n = p['project']
    b = base.get(n)
    if not b:
        rejected['no tenure record'] += 1; continue
    t = b.get('tenure') or {}
    # FREEHOLD ONLY. pricegap-base's classifier already folds 999-year into 'FH' — the one
    # classifier Shawn insists on, never re-tested inline here.
    if t.get('type') != 'FH':
        rejected['not freehold'] += 1; continue
    d = det.get(n) or {}
    if (d.get('totalUnits') or 0) < MIN_UNITS:
        rejected[f'under {MIN_UNITS} units'] += 1; continue
    top = d.get('completionYear')
    if not top:
        rejected['no completion year'] += 1; continue
    if d.get('projectType') == 'Executive Condominium':
        rejected['EC (leasehold by definition)'] += 1; continue
    dist, station = min(((hav(p['lat'], p['lng'], s['lat'], s['lng']), s['name'])
                         for s in mrt if s.get('lat')), default=(None, None))
    if dist is None:
        rejected['no MRT fix'] += 1; continue
    P[n] = dict(name=n, lat=p['lat'], lng=p['lng'], region=p['region'], district=p['district'],
                top=int(top), units=d.get('totalUnits'), station=station,
                schools=frozenset(s['name'] for s in schools
                                  if hav(p['lat'], p['lng'], s['lat'], s['lng']) <= SCHOOL_KM))

def cell(name, bed, cut_mo):
    s, q = psf.get(name, {}).get(bed), qh.get(name, {}).get(bed)
    if not s or not q: return None
    ms = [m for m in s if cut_mo <= m <= LAST and m in q]
    if not ms: return None
    n = sum(q[m][2] for m in ms)
    if n < MIN_N: return None
    return dict(psf=st.median([s[m] for m in ms]), n=n,
                sqft=st.median([q[m][1] for m in ms]), months=len(ms))

def build(window, min_gap=MIN_GAP_YEARS):
    cut_mo = months_back(LAST, window - 1)
    rows = []
    for a, b in itertools.combinations(list(P), 2):
        A, B = P[a], P[b]
        if abs(A['top'] - B['top']) < min_gap: continue
        d = hav(A['lat'], A['lng'], B['lat'], B['lng'])
        if d > RADIUS_M: continue
        if A['station'] != B['station']: continue
        if A['schools'] != B['schools']: continue
        old, new = (A, B) if A['top'] < B['top'] else (B, A)
        gap = new['top'] - old['top']
        for bd in BEDS:
            co, cn = cell(old['name'], bd, cut_mo), cell(new['name'], bd, cut_mo)
            if not co or not cn: continue
            sd = abs(co['sqft'] - cn['sqft']) / max(co['sqft'], cn['sqft'])
            if sd > SIZE_TOL: continue
            rows.append(dict(older=old['name'], newer=new['name'], region=A['region'],
                             station=A['station'], metres=round(d), bed=bd,
                             top_old=old['top'], top_new=new['top'], gap=gap,
                             mid=(old['top'] + new['top']) / 2,
                             psf_old=co['psf'], psf_new=cn['psf'],
                             n_old=co['n'], n_new=cn['n'],
                             sqft_old=co['sqft'], sqft_new=cn['sqft'], size_delta=sd,
                             diff=cn['psf'] - co['psf'],
                             per_yr=(cn['psf'] - co['psf']) / gap))
    return cut_mo, rows

def fitted(rows):
    """Least squares through the origin — lease-pairs.py's estimator, unchanged."""
    if not rows: return None
    return sum(r['diff'] * r['gap'] for r in rows) / sum(r['gap'] ** 2 for r in rows)

def fitted_pct(rows):
    if not rows: return None
    tot = sum(math.log(r['psf_new'] / r['psf_old']) * r['gap'] for r in rows)
    return math.exp(tot / sum(r['gap'] ** 2 for r in rows)) - 1

def with_intercept(rows):
    """diff = c + a*gap. THE PLACEBO: c is what two same-vintage neighbours differ by, and
    it has to be indistinguishable from zero or the pairing itself is carrying a bias."""
    n = len(rows)
    sx = sum(r['gap'] for r in rows); sy = sum(r['diff'] for r in rows)
    sxx = sum(r['gap']**2 for r in rows); sxy = sum(r['gap']*r['diff'] for r in rows)
    det = n*sxx - sx*sx
    if not det: return None, None
    a = (n*sxy - sx*sy)/det
    c = (sy - a*sx)/n
    resid = [r['diff'] - c - a*r['gap'] for r in rows]
    s2 = sum(e*e for e in resid)/(n-2) if n > 2 else float('nan')
    se_c = math.sqrt(s2 * sxx / det) if det and s2 == s2 else float('nan')
    return (c, se_c), a

def boot(rows, fn, B=2000, seed=17):
    g = random.Random(seed); n = len(rows); out = []
    for _ in range(B):
        v = fn([rows[g.randrange(n)] for _ in range(n)])
        if v is not None: out.append(v)
    out.sort()
    return out[int(.025*len(out))], out[int(.975*len(out))-1]

def boot_pairs(rows, fn, B=2000, seed=17):
    """Resample BY PAIR, not by cell. The four bedrooms of one pair are not four independent
    readings of anything — a cell bootstrap treats them as though they were and reports an
    interval that is too tight. Every interval on the freehold panel comes through here."""
    g = random.Random(seed)
    ps = sorted({(r['older'], r['newer']) for r in rows})
    byp = collections.defaultdict(list)
    for r in rows: byp[(r['older'], r['newer'])].append(r)
    out = []
    for _ in range(B):
        s = [x for _ in ps for x in byp[ps[g.randrange(len(ps))]]]
        v = fn(s)
        if v is not None: out.append(v)
    if not out: return None, None
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out)) - 1]

def best_bound(rows, lo_y=1998, hi_y=2016, floor=8):
    """The boundary that minimises in-sample SSE. Used two ways: once on the data, and once
    inside every bootstrap resample to ask whether it lands in the same place twice."""
    best = None
    for b in range(lo_y, hi_y):
        lo = [r for r in rows if r['mid'] < b]; hi = [r for r in rows if r['mid'] >= b]
        if len(lo) < floor or len(hi) < floor: continue
        fl, fh = fitted(lo), fitted(hi)
        sse = sum((r['diff'] - (fl if r['mid'] < b else fh) * r['gap']) ** 2 for r in rows)
        if best is None or sse < best[0]: best = (sse, b)
    return best[1] if best else None

def banded(rows, bound):
    lo = [r for r in rows if r['mid'] < bound]
    hi = [r for r in rows if r['mid'] >= bound]
    return (fitted(lo) if len(lo) >= 8 else None,
            fitted(hi) if len(hi) >= 8 else None, len(lo), len(hi))

def curve(rows):
    """rate = a + b*(mid-2000), fitted as diff = gap*(a + b*(mid-2000))."""
    s11 = s12 = s22 = t1 = t2 = 0.0
    for r in rows:
        x1 = r['gap']; x2 = r['gap'] * (r['mid'] - 2000)
        s11 += x1*x1; s12 += x1*x2; s22 += x2*x2; t1 += x1*r['diff']; t2 += x2*r['diff']
    det = s11*s22 - s12*s12
    if not det: return None, None
    return (s22*t1 - s12*t2)/det, (s11*t2 - s12*t1)/det

# ── HELD-OUT ERROR — the horse race referee ──────────────────────────────────
# Same discipline as tenure-pairs.py: every shape is scored on data it did not see, by
# PAIR (never by cell), so the four bedrooms of one pair cannot be split across the fold
# boundary and flatter the fit.
def holdout(rows, shape, folds=200, seed=23):
    g = random.Random(seed)
    pairs = sorted({(r['older'], r['newer']) for r in rows})
    err, n = 0.0, 0
    for _ in range(folds):
        test = set(g.sample(pairs, max(1, len(pairs)//5)))
        tr = [r for r in rows if (r['older'], r['newer']) not in test]
        te = [r for r in rows if (r['older'], r['newer']) in test]
        if len(tr) < 10 or not te: continue
        pred = shape(tr)
        if pred is None: continue
        for r in te:
            err += (r['diff'] - pred(r))**2; n += 1
    return math.sqrt(err/n) if n else float('nan')

def shape_flat(tr):
    a = fitted(tr)
    return (lambda r: a * r['gap']) if a is not None else None

def shape_zero(tr):
    return lambda r: 0.0

def shape_band(bound):
    def mk(tr):
        lo, hi, nl, nh = banded(tr, bound)
        if lo is None or hi is None: return None
        return lambda r: (lo if r['mid'] < bound else hi) * r['gap']
    return mk

def shape_band_searched(tr):
    """THE HONEST TWO-BAND SHAPE. shape_band(b) is handed a boundary found on all the data,
    which leaks the answer into the training set. This makes every fold find its own. If the
    two shapes score the same, the boundary is so stable that searching for it costs nothing —
    which is itself the finding."""
    b = best_bound(tr)
    return shape_band(b)(tr) if b else None

def shape_curve(tr):
    a, b = curve(tr)
    if a is None: return None
    return lambda r: r['gap'] * (a + b * (r['mid'] - 2000))

def shape_lease_bands(tr):
    """The engine's current behaviour: the LEASE rate, applied to the TOP clock."""
    LP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'lease-pairs.json')))
    return None  # replaced below once the bands are loaded

# ── run ───────────────────────────────────────────────────────────────────────
LP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lease-pairs.json')))
_lp24 = LP['24']
LEASE_BAND_BOUND = 2011
CONSTRUCTION_YEARS = 4          # measured in tenure-pairs.py: median TOP - lease start
LB = {}
for nm, lo, hi in (('old', 1900, LEASE_BAND_BOUND), ('new', LEASE_BAND_BOUND, 3000)):
    sel = [r for r in _lp24 if lo <= (r['ls_old'] + r['ls_new']) / 2 < hi]
    LB[nm] = fitted(sel)

def shape_engine(tr):
    """The lease bands read at the midpoint of the two lease-start EQUIVALENTS (TOP - 4).
    This is what the Price Gap engine does to a freehold comparable today."""
    def pred(r):
        mid_ls = r['mid'] - CONSTRUCTION_YEARS
        return (LB['old'] if mid_ls < LEASE_BAND_BOUND else LB['new']) * r['gap']
    return pred

print('AGE CALIBRATION — freehold vs freehold, price per year of TOP difference')
print('=' * 86)
print(f'cut: transactions to {LAST} (pinned)   lease bands carried in: '
      f'${LB["old"]:.1f} / ${LB["new"]:.1f}')
print(f'freehold universe: {len(P)} developments   rejected: '
      + ', '.join(f'{v} {k}' for k, v in rejected.most_common(5)))

OUT = {}
WINDOWS_CUT = {}
for W in WINDOWS:
    cut_mo, rows = build(W)
    WINDOWS_CUT[W] = cut_mo
    if not rows:
        print(f'\n{W}m: no pairs'); continue
    pairs = {(r['older'], r['newer']) for r in rows}
    devs  = {n for r in rows for n in (r['older'], r['newer'])}
    a = fitted(rows); apct = fitted_pct(rows)
    lo, hi = boot(rows, fitted)
    (c, se_c), a_int = with_intercept(rows)
    print(f'\n── {W}-month window ({cut_mo} .. {LAST}) ' + '─' * 42)
    print(f'  {len(rows)} cells   {len(pairs)} pairs   {len(devs)} developments')
    print(f'  RATE  ${a:+,.1f} per year of TOP difference   (bootstrap ${lo:+,.1f} .. ${hi:+,.1f})')
    print(f'        {apct:+.2%}/yr on the ratio scale')
    print(f'  median per-cell $/yr {st.median([r["per_yr"] for r in rows]):+,.1f}   '
          f'mean {st.mean([r["per_yr"] for r in rows]):+,.1f}   (NOT the estimator — the '
          f'1-yr cells dominate these)')
    print(f'  PLACEBO — intercept ${c:+,.0f} (se ${se_c:,.0f}, t={c/se_c:+.2f}) with slope '
          f'${a_int:+,.1f}/yr')

    print(f'\n  gap-band table (an OUTPUT, never a screen):')
    print(f'    {"gap":>10s} {"cells":>6s} {"pairs":>6s} {"fitted $/yr":>12s} {"median $/yr":>12s}')
    for label, g0, g1 in (('1-4 yrs', 1, 5), ('5-9 yrs', 5, 10), ('10-19 yrs', 10, 20),
                          ('20-29 yrs', 20, 30), ('30+ yrs', 30, 999)):
        sel = [r for r in rows if g0 <= r['gap'] < g1]
        if len(sel) < 5:
            print(f'    {label:>10s} {len(sel):>6d} {"":>6s} {"— thin —":>12s}'); continue
        sp = len({(r['older'], r['newer']) for r in sel})
        print(f'    {label:>10s} {len(sel):>6d} {sp:>6d} {fitted(sel):>+12.1f} '
              f'{st.median([r["per_yr"] for r in sel]):>+12.1f}')

    print(f'\n  vintage-band search (does the lease study\'s two-band shape hold on TOP?):')
    best = None
    for bound in range(1995, 2019):
        blo, bhi, nl, nh = banded(rows, bound)
        if blo is None or bhi is None: continue
        e = holdout(rows, shape_band(bound))
        if best is None or e < best[0]: best = (e, bound, blo, bhi, nl, nh)
        if bound % 3 == 0:
            print(f'    split {bound}   pre ${blo:>+7.1f} (n={nl:>3d})   post ${bhi:>+7.1f} '
                  f'(n={nh:>3d})   held-out {e:,.1f}')

    print(f'\n  HORSE RACE — held-out RMSE, split by PAIR, 200 folds (lower is better):')
    race = [('no age term at all (zero)', holdout(rows, shape_zero)),
            (f'FLAT — one rate ${a:,.1f}/yr', holdout(rows, shape_flat)),
            ('linear in vintage (a + b*mid)', holdout(rows, shape_curve)),
            (f'ENGINE — lease bands on the TOP clock', holdout(rows, shape_engine))]
    if best: race.append((f'two bands, split {best[1]} '
                          f'(${best[2]:,.1f} / ${best[3]:,.1f})', best[0]))
    for label, e in sorted(race, key=lambda x: x[1]):
        print(f'    {e:>9,.1f}   {label}')

    # ── ONE LINE OR TWO? (Shawn, 2026-09-13: "what does the data say? if the data says the
    # graph is a straight line I don't see why we need two bands. But if there is a clear
    # banding in terms of the gradient, then we should split it accordingly.")
    # Five tests, all written to the JSON so the page can show its working.
    ev = {}
    BB = best_bound(rows) or 2010

    #  (a) what the rate reads slice by slice — a step shows here, a climb shows here too
    ev['slices'] = []
    for lab, s0, s1 in (('before 1998', 0, 1998), ('1998–2003', 1998, 2004),
                        ('2004–2007', 2004, 2008), ('2008–2009', 2008, 2010),
                        ('2010–2012', 2010, 2013), ('2013 onward', 2013, 3000)):
        sel = [r for r in rows if s0 <= r['mid'] < s1]
        if not sel: continue
        sp = len({(r['older'], r['newer']) for r in sel})
        cl, ch = boot_pairs(sel, fitted) if sp >= 8 else (None, None)
        ev['slices'].append(dict(label=lab, lo_y=s0, hi_y=s1, cells=len(sel), pairs=sp,
                                 devs=len({x for r in sel for x in (r['older'], r['newer'])}),
                                 rate=fitted(sel), ci_lo=cl, ci_hi=ch))

    #  (b) IS THE BOUNDARY IDENTIFIED? Bootstrap the grid search itself. A real break lands in
    #      the same year every resample; a boundary chosen by noise scatters across the range.
    g2 = random.Random(5); ps2 = sorted(pairs)
    byp2 = collections.defaultdict(list)
    for r in rows: byp2[(r['older'], r['newer'])].append(r)
    found = collections.Counter()
    for _ in range(600):
        smp = [x for _ in ps2 for x in byp2[ps2[g2.randrange(len(ps2))]]]
        b = best_bound(smp)
        if b: found[b] += 1
    tot = sum(found.values()) or 1
    ev['bound_boot'] = dict(bound=BB, share=found[BB] / tot,
                            spread=sorted([[y, n / tot] for y, n in found.items()]))

    #  (c) is the STEP itself distinguishable from zero, in dollars and on the ratio scale?
    #      The ratio scale is the one that answers "is this just a price-level artefact" —
    #      post-2010 freeholds are dearer, and a flat dollar figure on a dearer pair is a
    #      smaller share of it. If the step survives in %/yr it is not the level talking.
    st_d = lambda rr: ((fitted([r for r in rr if r['mid'] >= BB]) or 0)
                       - (fitted([r for r in rr if r['mid'] < BB]) or 0))
    st_p = lambda rr: ((fitted_pct([r for r in rr if r['mid'] >= BB]) or 0)
                       - (fitted_pct([r for r in rr if r['mid'] < BB]) or 0))
    guard = lambda fn: (lambda rr: fn(rr) if len([r for r in rr if r['mid'] >= BB]) >= 5
                        and len([r for r in rr if r['mid'] < BB]) >= 5 else None)
    dlo, dhi = boot_pairs(rows, guard(st_d)); plo, phi = boot_pairs(rows, guard(st_p))
    pre_r = [r for r in rows if r['mid'] < BB]; post_r = [r for r in rows if r['mid'] >= BB]
    ev['step'] = dict(bound=BB, d=st_d(rows), d_lo=dlo, d_hi=dhi,
                      p=st_p(rows), p_lo=plo, p_hi=phi,
                      pre_pct=fitted_pct(pre_r), post_pct=fitted_pct(post_r),
                      pre_cells=len(pre_r), post_cells=len(post_r),
                      pre_pairs=len({(r['older'], r['newer']) for r in pre_r}),
                      post_pairs=len({(r['older'], r['newer']) for r in post_r}),
                      pre_devs=len({x for r in pre_r for x in (r['older'], r['newer'])}),
                      post_devs=len({x for r in post_r for x in (r['older'], r['newer'])}))

    #  (d) the OTHER confound: post-2010 freehold stock is disproportionately central. Is
    #      "post-2010" really "CCR"? Read the step inside each region separately.
    ev['region'] = []
    for reg in ('CCR', 'RCR', 'OCR'):
        cut_ = {}
        for lab, sel in (('pre', [r for r in rows if r['region'] == reg and r['mid'] < BB]),
                         ('post', [r for r in rows if r['region'] == reg and r['mid'] >= BB])):
            cut_[lab] = dict(cells=len(sel), rate=fitted(sel) if len(sel) >= 4 else None)
        ev['region'].append(dict(region=reg, **cut_))

    #  (e) the honest race — the boundary re-searched inside every training fold
    ev['race_honest'] = {
        'no age term at all (zero)': holdout(rows, shape_zero),
        f'FLAT — one rate ${a:,.1f}/yr': holdout(rows, shape_flat),
        'linear in vintage (a + b×vintage)': holdout(rows, shape_curve),
        'ENGINE — lease bands on the TOP clock': holdout(rows, shape_engine),
        f'TWO BANDS, boundary re-searched in fold': holdout(rows, shape_band_searched)}

    print(f'\n  ONE LINE OR TWO?')
    print(f'    boundary lands on {BB} in {found[BB]/tot:.0%} of resamples')
    print(f'    step ${st_d(rows):+,.1f}/yr  95% ${dlo:+,.1f}..${dhi:+,.1f}   '
          f'= {st_p(rows)*100:+.2f}pp  95% {plo*100:+.2f}..{phi*100:+.2f}pp')
    for l, e in sorted(ev['race_honest'].items(), key=lambda x: x[1]):
        print(f'    {e:>9,.1f}   {l}')

    OUT[str(W)] = dict(evidence=ev, cells=len(rows), pairs=len(pairs), devs=len(devs),
                       rate=a, lo=lo, hi=hi, pct=apct,
                       intercept=c, intercept_se=se_c, slope_with_intercept=a_int,
                       best_band=(dict(bound=best[1], pre=best[2], post=best[3],
                                       n_pre=best[4], n_post=best[5], holdout=best[0])
                                  if best else None),
                       race={l: e for l, e in race},
                       rows=rows)

# The window the freshness gate reads, so this JSON is pinned to cut.py like the other five.
OUT['meta'] = dict(window=[WINDOWS_CUT.get(24, LAST), LAST],
                   last=LAST, lease_bands=LB, construction_years=CONSTRUCTION_YEARS,
                   screens=dict(radius_m=RADIUS_M, min_units=MIN_UNITS, min_n=MIN_N,
                                size_tol=SIZE_TOL, min_gap_years=MIN_GAP_YEARS),
                   universe=len(P))
# NaN IS NOT JSON. A thin window can leave a held-out score undefined (the 12-month band
# search has too few pairs to fit both sides), and Python writes that as a bare NaN, which
# every strict parser rejects — the engine's loader among them. Scrub to null on the way out.
def clean(o):
    if isinstance(o, float):
        return o if o == o and o not in (float('inf'), float('-inf')) else None
    if isinstance(o, dict):  return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):  return [clean(v) for v in o]
    return o

json.dump(clean(OUT), open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        'age-pairs.json'), 'w'), allow_nan=False)
print('\n→ age-pairs.json')
