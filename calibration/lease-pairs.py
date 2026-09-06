#!/usr/bin/env python3
"""LEASE-YEAR CALIBRATION — matched neighbour pairs.

Measures what the market actually pays per year of lease start, to validate the
$40 psf/yr LEASE_PSF_PER_YEAR constant in ../scripts/price-gap.ts. Writes nothing
back to the engine: this is a validation table that sits BESIDE the constants.
(Shawn's ruling, 2026-09-06.)

METHOD (Shawn's spec, 2026-09-06). Two leasehold developments sitting next to each
other, with everything else held constant, differing only in lease start. Their PSF
difference over the same window, per bedroom type, divided by the lease-start gap,
is the market's price for a year of lease.

  PAIR SCREEN
    both leasehold, both >= 200 units      (volume: a boutique block is one odd sale)
    within 500 m of each other
    same nearest MRT station             (NOT the same walk band -- retired 2026-09-06, see
                                          below. Distance is already screened at 500 m.)
    identical set of TOP-26 primary schools within 1 km   (the 1 km cliff is absolute)
    lease-start gap >= 1 yr                (NO minimum -- the gap-band table is an output,
                                            not a screen. Shawn: "I don't need the lease
                                            gap to be a certain amount.")
    EC allowed only once privatised, taken as TOP + 5 yrs

  CELL SCREEN, applied per bedroom inside a pair
    >= 5 transactions each side within the window
    median sizes within 20%                (bedroom buckets are wide; 15% cost 44% of the
                                            sample for a smaller bias than it removed.
                                            Each pair carries its size delta so the residual
                                            can be checked against it.)

  THE ESTIMATOR -- TWO BANDS, READ AT THE MIDPOINT  (Shawn, 2026-09-06)

    rate = $25/yr for a pair centred up to 2010, $44/yr from 2011. Held-out error:
    flat 24.0k, THREE bands 20.9k, TWO BANDS 20.7k. Two beats three and is simpler.

    READ AT THE MIDPOINT of the two lease starts. That form IS the blend, so a pair
    straddling the boundary needs no special handling -- which is the whole reason for it.
    NEVER band on ls_old.

    FOUR SHAPES DIED AND MUST NOT BE RESURRECTED: a flat rate (the engine's $40, which
    charges an old pair 1.6x what the market pays); two bands on ls_old; a straight line on
    the midpoint (ran low at BOTH ends); and A FITTED KNEE -- which this docstring described
    as the answer until 2026-09-06 and which is DEAD. The knee moved when the screen widened
    from 168 to 231 pairs; the best knee is now anywhere in 1998-2008 and the fit changes
    under 2% across that span. THE KNEE IS NOT IDENTIFIED. Do not report a fitted year and
    slope. The LEVEL (~$25) is the robust finding; the tail is not.

    REJECTED: the lease-decay knee. A 1990s-centred pair has ~65 yrs left, the 2026-07-27
    study's knee, so decay was the obvious suspect. Refitting on the older project's REMAINING
    lease is worse, adding it alongside vintage is worse, and a below-65-years term earns
    nothing. The turn is in the VINTAGE of the stock, not the lease left on it.

    NO GAP SCREEN. Earlier passes dropped pairs under 5 years of lease separation. That screen
    existed for the per-pair MEAN, which divides each difference by its own gap and so
    multiplies a short pair's noise. This estimator fits the DIFFERENCE against the gap, so a
    3-year pair carries 3 years of leverage and cannot shout.

  BEDROOM IS THE MATCH, NOT THE ANSWER. It does not appear in the equation. It is the
    stratum that holds size constant, and it is the finest size resolution the data has.
    The pooled alternative -- one transaction-weighted PSF per project, matched on pooled
    median size -- is computed here as a diagnostic. It LOSES pairs (119 vs 168; matching
    a whole sales mix within 20% is harder than matching one bedroom) and lets mix leak:
    its residual tracks the unmatched size difference at about -$214 psf per 100% of size.

  THE WALK-BAND SCREEN IS RETIRED (Shawn, 2026-09-06). It required both sides of a pair to sit
    in the same 5/10-minute walk band of their shared station. With distance ALREADY screened at
    500 m that is redundant, and it cut arbitrarily: it was throwing out pairs 258-414 m apart on
    the same station purely because one sat at 640 m from the MRT and the other at 900 m, opposite
    sides of a 5-minute line. It cost 20 pairs at the newer end alone -- The Trilinq/Parc Clematis
    at 258 m, Oue Twin Peaks/Irwell Hill at 329 m, Queens Peak/Stirling at 387 m. 500 m, the same
    station, the school set and the 200-unit floor all stay: he ruled only the band out.

  WINDOWS  24 months is the headline. 12 is a FRESHNESS CHECK, not a second reading --
           54 of the 56 clean 12m cells sit inside the 24m set, so the two must never be
           averaged. That would count the last year twice.

Read-only consumer of ../../property-analyzer/data/. Run:
    python3 lease-pairs.py
"""
import json, math, itertools, collections, statistics as st, os, sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', '..', 'property-analyzer', 'data')
J = lambda f: json.load(open(os.path.join(DATA, f)))

RADIUS_M      = 500
MIN_UNITS     = 200
MIN_N         = 5
SIZE_TOL      = 0.20
MIN_GAP_YEARS = 1
EC_PRIVATISE  = 5          # TOP + 5 yrs (Shawn, 2026-09-06)
SCHOOL_KM     = 1000
BEDS          = ['1BR', '2BR', '3BR', '4BR+']
WINDOWS       = [12, 24]

R = 6371000
def hav(a, b, c, d):
    ra, rc = math.radians(a), math.radians(c)
    dla, dln = math.radians(c - a), math.radians(d - b)
    q = math.sin(dla/2)**2 + math.cos(ra)*math.cos(rc)*math.sin(dln/2)**2
    return 2 * R * math.asin(math.sqrt(q))

def walk_band(m):
    w = m * 1.3 / 80
    return 'near' if w < 5 else ('mid' if w <= 10 else 'far')

dsi     = J('dsi-index.json')
projs   = dsi['projects']
schools = dsi['schools']              # the TOP-26 primary schools, with rank and coords
base    = J('pricegap-base.json')['projects']
det     = J('pg-project-details.json')['projects']
psf     = J('psf-history.json')['projects']
qh      = J('quantum-history.json')['projects']
# OPERATIONAL STATIONS ONLY. 37 of the 223 in mrt-stations.json are under construction, and an
# unbuilt station is not a walk to anything over a 2024-26 transaction window. Counting them
# changes the nearest station for 88 of 1,844 developments, and the nearest station is a PAIR
# SCREEN here -- so each one silently makes or breaks a pair. (Found via mrt-pairs.py, fixed
# 2026-09-06.)
mrt     = [s for s in J('mrt-stations.json')['stations'] if s.get('status') == 'operational']

LAST = max(m for p in psf.values() for b in p.values() for m in b)
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
    if t.get('type') != 'LH' or not t.get('leaseStart'):
        rejected['not leasehold / no lease start'] += 1; continue
    d = det.get(n) or {}
    if (d.get('totalUnits') or 0) < MIN_UNITS:
        rejected[f'under {MIN_UNITS} units'] += 1; continue
    # An EC prices like a subsidised flat until it privatises; after that it is
    # ordinary private stock and belongs in the pool.
    if d.get('projectType') == 'Executive Condominium':
        top = d.get('completionYear')
        if not top or int(LAST[:4]) - top < EC_PRIVATISE:
            rejected['EC not yet privatised'] += 1; continue
    dist, station = min(((hav(p['lat'], p['lng'], s['lat'], s['lng']), s['name'])
                         for s in mrt if s.get('lat')), default=(None, None))
    if dist is None:
        rejected['no MRT fix'] += 1; continue
    P[n] = dict(name=n, lat=p['lat'], lng=p['lng'], region=p['region'], district=p['district'],
                ls=t['leaseStart'], years=t.get('years'), units=d.get('totalUnits'),
                top=d.get('completionYear'), is_ec=d.get('projectType') == 'Executive Condominium',
                station=station, band=walk_band(dist),
                schools=frozenset(s['name'] for s in schools
                                  if hav(p['lat'], p['lng'], s['lat'], s['lng']) <= SCHOOL_KM))

def cell(name, bed, cut):
    """Median PSF, transaction count and median size for one project x bedroom in the window."""
    s, q = psf.get(name, {}).get(bed), qh.get(name, {}).get(bed)
    if not s or not q: return None
    ms = [m for m in s if cut <= m <= LAST and m in q]
    if not ms: return None
    n = sum(q[m][2] for m in ms)
    if n < MIN_N: return None
    return dict(psf=st.median([s[m] for m in ms]), n=n,
                sqft=st.median([q[m][1] for m in ms]), months=len(ms))

def cell_between(name, bed, lo, hi):
    """Same as cell(), but for an arbitrary month window — used by the vintage-vs-age test."""
    s, q = psf.get(name, {}).get(bed), qh.get(name, {}).get(bed)
    if not s or not q: return None
    ms = [m for m in s if lo <= m <= hi and m in q]
    if not ms: return None
    n = sum(q[m][2] for m in ms)
    if n < MIN_N: return None
    return dict(psf=st.median([s[m] for m in ms]), n=n, sqft=st.median([q[m][1] for m in ms]))

def build_between(lo, hi):
    """The whole pair build against an arbitrary transaction window.

    THE VINTAGE-VS-AGE TEST (Shawn asked, 2026-09-06): should the bands slide forward as
    the stock ages? Run the identical method on a transaction window three years earlier.
    If the effect is AGE, the band that reads high slides ~3 years later in the late run.
    If it is CALENDAR VINTAGE, it sits still. IT SITS STILL — see the page."""
    rows = []
    for a, b in itertools.combinations(list(P), 2):
        A, B = P[a], P[b]
        if abs(A['ls'] - B['ls']) < MIN_GAP_YEARS: continue
        if hav(A['lat'], A['lng'], B['lat'], B['lng']) > RADIUS_M: continue
        if A['station'] != B['station']: continue
        if A['schools'] != B['schools']: continue
        old, new = (A, B) if A['ls'] < B['ls'] else (B, A)
        for bd in BEDS:
            co, cn = cell_between(old['name'], bd, lo, hi), cell_between(new['name'], bd, lo, hi)
            if not co or not cn: continue
            if abs(co['sqft'] - cn['sqft']) / max(co['sqft'], cn['sqft']) > SIZE_TOL: continue
            rows.append(dict(older=old['name'], newer=new['name'], region=A['region'],
                             ls_old=old['ls'], ls_new=new['ls'], gap=new['ls'] - old['ls'],
                             psf_old=co['psf'], psf_new=cn['psf'], diff=cn['psf'] - co['psf'],
                             bed=bd))
    return rows

def build(window):
    cut = months_back(LAST, window - 1)
    rows = []
    for a, b in itertools.combinations(list(P), 2):
        A, B = P[a], P[b]
        if abs(A['ls'] - B['ls']) < MIN_GAP_YEARS: continue
        d = hav(A['lat'], A['lng'], B['lat'], B['lng'])
        if d > RADIUS_M: continue
        if A['station'] != B['station']: continue
        if A['schools'] != B['schools']: continue
        old, new = (A, B) if A['ls'] < B['ls'] else (B, A)
        gap = new['ls'] - old['ls']
        for bd in BEDS:
            co, cn = cell(old['name'], bd, cut), cell(new['name'], bd, cut)
            if not co or not cn: continue
            sd = abs(co['sqft'] - cn['sqft']) / max(co['sqft'], cn['sqft'])
            if sd > SIZE_TOL: continue
            rows.append(dict(older=old['name'], newer=new['name'], region=A['region'],
                             station=A['station'], metres=round(d), bed=bd,
                             ls_old=old['ls'], ls_new=new['ls'], gap=gap,
                             psf_old=co['psf'], psf_new=cn['psf'],
                             n_old=co['n'], n_new=cn['n'],
                             sqft_old=co['sqft'], sqft_new=cn['sqft'], size_delta=sd,
                             ec=old['is_ec'] or new['is_ec'],
                             diff=cn['psf'] - co['psf'],
                             per_yr=(cn['psf'] - co['psf']) / gap,
                             pct_per_yr=(cn['psf'] / co['psf'] - 1) / gap))
    return cut, rows

def fitted(rows):
    """sum(difference) / sum(gap) — each pair weighted by its lease separation."""
    if not rows: return None
    return sum(r['diff'] for r in rows) / sum(r['gap'] for r in rows)

def fitted_pct(rows):
    """Same weighting, on the ratio scale: geometric, so it composes over years."""
    if not rows: return None
    tot = sum(math.log(r['psf_new'] / r['psf_old']) for r in rows)
    return math.exp(tot / sum(r['gap'] for r in rows)) - 1

def summarise(rows, label):
    if not rows: return f'{label:28s}     —      —       —       —      0'
    return (f'{label:28s} {fitted(rows):>+7.1f} {fitted_pct(rows):>+8.2%} '
            f'{st.median([r["per_yr"] for r in rows]):>+8.1f} '
            f'{st.mean([r["per_yr"] for r in rows]):>+8.1f} {len(rows):>5d}')

def curve(rows):
    """rate = a + b*(mid-2000), fitted as diff = gap*(a + b*(mid-2000)). Pure-python 2x2."""
    s11 = s12 = s22 = t1 = t2 = 0.0
    for r in rows:
        x1 = r['gap']; x2 = r['gap'] * ((r['ls_old'] + r['ls_new']) / 2 - 2000)
        s11 += x1*x1; s12 += x1*x2; s22 += x2*x2; t1 += x1*r['diff']; t2 += x2*r['diff']
    det = s11*s22 - s12*s12
    if not det: return None, None
    return (s22*t1 - s12*t2)/det, (s11*t2 - s12*t1)/det

def hinge(rows, K):
    """rate = c + d*max(0, mid - K). Flat until the knee year, rising after it."""
    s11 = s12 = s22 = t1 = t2 = 0.0
    for r in rows:
        x1 = r['gap']; x2 = r['gap'] * max(0.0, (r['ls_old'] + r['ls_new'])/2 - K)
        s11 += x1*x1; s12 += x1*x2; s22 += x2*x2; t1 += x1*r['diff']; t2 += x2*r['diff']
    det = s11*s22 - s12*s12
    if not det: return 0.0, 0.0
    return (s22*t1 - s12*t2)/det, (s11*t2 - s12*t1)/det

def curve_ci(rows, B=2000, seed=17):
    import random as _r
    g = _r.Random(seed); n = len(rows); A = []; Bs = []
    for _ in range(B):
        a, b = curve([rows[g.randrange(n)] for _ in range(n)])
        if a is not None: A.append(a); Bs.append(b)
    A.sort(); Bs.sort(); lo, hi = int(.025*len(A)), int(.975*len(A)) - 1
    return (A[lo], A[hi]), (Bs[lo], Bs[hi])

def pooled_cell(name, cut):
    """One PSF for a whole project: every bedroom's monthly medians, weighted by the
    transactions behind them. The diagnostic for 'why not just match on size'."""
    sp, q = psf.get(name, {}), qh.get(name, {})
    obs = [(sp[bd][m], q[bd][m][1], q[bd][m][2])
           for bd in sp if bd in q for m in sp[bd] if cut <= m <= LAST and m in q[bd]]
    if not obs: return None
    n = sum(o[2] for o in obs)
    if n < MIN_N: return None
    return dict(psf=sum(o[0]*o[2] for o in obs)/n, sqft=sum(o[1]*o[2] for o in obs)/n, n=n)

def build_pooled(window):
    cut = months_back(LAST, window - 1); rows = []
    for a, b in itertools.combinations(list(P), 2):
        A, B = P[a], P[b]
        if abs(A['ls'] - B['ls']) < MIN_GAP_YEARS: continue
        if hav(A['lat'], A['lng'], B['lat'], B['lng']) > RADIUS_M: continue
        if A['station'] != B['station']: continue
        if A['schools'] != B['schools']: continue
        old, new = (A, B) if A['ls'] < B['ls'] else (B, A)
        co, cn = pooled_cell(old['name'], cut), pooled_cell(new['name'], cut)
        if not co or not cn: continue
        if abs(co['sqft'] - cn['sqft']) / max(co['sqft'], cn['sqft']) > SIZE_TOL: continue
        rows.append(dict(older=old['name'], newer=new['name'], region=A['region'],
                         ls_old=old['ls'], ls_new=new['ls'], gap=new['ls'] - old['ls'],
                         psf_old=co['psf'], psf_new=cn['psf'], diff=cn['psf'] - co['psf'],
                         sqft_old=co['sqft'], sqft_new=cn['sqft'],
                         n_old=co['n'], n_new=cn['n']))
    return rows

HEAD = f'{"":28s} {"fitted":>7s} {"fitted%":>8s} {"median":>8s} {"mean":>8s} {"cells":>5s}'

if __name__ == '__main__':
    print(f'LEASE-YEAR CALIBRATION   radius {RADIUS_M}m · units>={MIN_UNITS} · n>={MIN_N} · '
          f'size<={SIZE_TOL:.0%} · same station+band · same top-26 schools · EC after TOP+{EC_PRIVATISE}')
    print(f'eligible leasehold projects: {len(P)}   (rejected: '
          + ', '.join(f'{k} {v}' for k, v in rejected.most_common()) + ')')
    out = {}
    for w in WINDOWS:
        cut, rows = build(w); out[w] = rows
        print(f'\n{"="*86}\nWINDOW {w} MONTHS   {cut} .. {LAST}   —   {len(rows)} bedroom cells '
              f'across {len({(r["older"],r["newer"]) for r in rows})} pairs\n{"="*86}')
        print(HEAD)
        print(summarise(rows, 'ALL'))
        print('  — by bedroom')
        for bd in BEDS:
            print(summarise([r for r in rows if r['bed'] == bd], f'    {bd}'))
        print('  — by region')
        for rg in ('CCR', 'RCR', 'OCR'):
            print(summarise([r for r in rows if r['region'] == rg], f'    {rg}'))
        print('  — by lease-start band of the OLDER project')
        for lo, hi, nm in ((0, 1999, 'pre-2000'), (2000, 2019, '2000-2019'), (2020, 9999, '2020+')):
            print(summarise([r for r in rows if lo <= r['ls_old'] <= hi], f'    {nm}'))
        print('  — by size of the lease gap   (does the rate narrow as the gap widens?)')
        for lo, hi, nm in ((1, 4, '1-4 yrs'), (5, 9, '5-9 yrs'), (10, 14, '10-14 yrs'),
                           (15, 19, '15-19 yrs'), (20, 99, '20+ yrs')):
            print(summarise([r for r in rows if lo <= r['gap'] <= hi], f'    {nm}'))
    # ── the answer: the curve, on the full 24m sample with NO gap screen ────────
    full = out[24]
    a, b = curve(full); (alo, ahi), (blo, bhi) = curve_ci(full)
    K = min(range(2000, 2015),
            key=lambda k: sum((r['diff'] - r['gap']*sum(x*y for x, y in zip(
                hinge(full, k), (1, max(0.0, (r['ls_old']+r['ls_new'])/2 - k)))))**2 for r in full))
    c, d = hinge(full, K)
    print(f'\n{"="*86}\nTHE SHAPE   rate($/yr) = c + d x max(0, midpoint - K)\n{"="*86}')
    print(f'  flat at ${c:,.2f} up to a midpoint of {K}, then +${d:,.2f} per further year')
    print(f'  lookup:  ' + '   '.join(f'{m}:${c + d*max(0.0, m-K):.0f}' for m in range(1995, 2021, 5)))
    print(f'\n  the straight line it replaced (ran low at both ends):')
    print(f'  a = {a:+7.2f}   95% [{alo:+.2f}, {ahi:+.2f}]')
    print(f'  b = {b:+7.2f}   95% [{blo:+.2f}, {bhi:+.2f}]   per year of vintage')
    print(f'  on {len(full)} cells across {len({(r["older"],r["newer"]) for r in full})} pairs, no gap screen')
    print('  lookup:  ' + '   '.join(f'{m}:${a+b*(m-2000):.0f}' for m in range(1995, 2021, 5)))
    print('\n  stability against the retired gap screen:')
    for mg in (1, 2, 3, 5, 8):
        rs = [r for r in full if r['gap'] >= mg]
        hc, hd = hinge(rs, K)
        print(f'    gap >= {mg}   flat ${hc:6.2f}  slope ${hd:5.2f}   {len(rs):3d} cells')

    pooled = build_pooled(24)
    pa, pb = curve(pooled)
    print(f'\n  POOLED DIAGNOSTIC (one PSF per project, matched on pooled size — NOT the method):')
    print(f'    {len(pooled)} pairs vs {len({(r["older"],r["newer"]) for r in full})} bedroom-matched'
          f'   a {pa:+.2f}  b {pb:+.2f}')

    d = os.path.dirname(os.path.abspath(__file__))
    FIRST = min(m for p in psf.values() for b in p.values() for m in b)
    early = build_between(FIRST, months_back(FIRST, -23))
    print(f'\n  VINTAGE-VS-AGE TEST — same method on {FIRST}..{months_back(FIRST, -23)}: '
          f'{len(early)} cells, {len({(r["older"],r["newer"]) for r in early})} pairs')

    json.dump({**{str(w): out[w] for w in WINDOWS}, 'pooled24': pooled,
               'early24': early, 'early_window': [FIRST, months_back(FIRST, -23)],
               'late_window': [months_back(LAST, 23), LAST]},
              open(os.path.join(d, 'lease-pairs.json'), 'w'), indent=1)
    print(f'\nwrote lease-pairs.json')
