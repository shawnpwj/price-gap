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
    same nearest MRT station AND same walk band
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

  TWO ESTIMATORS, reported side by side
    fitted    sum(psf difference) / sum(lease gap)  -- each pair weighted by the lease
              separation it actually contains. The HEADLINE.
    mean      average of each pair's own $/yr       -- every pair equal. Broken out by
              gap band, because that is the "does the rate narrow or widen with a wider
              gap" question.
    Both are also computed in PERCENT per year, because a flat $ figure cannot hold in
    both an OCR pair at $1,300 psf and a CCR pair at $2,800 psf.

  WINDOWS  12 and 24 months, side by side. 12 is the cleaner price basis; 24 is the only
           one with enough 1BR and 4BR+ cells to read a bedroom pattern at all.

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
mrt     = J('mrt-stations.json')['stations']

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

def build(window):
    cut = months_back(LAST, window - 1)
    rows = []
    for a, b in itertools.combinations(list(P), 2):
        A, B = P[a], P[b]
        if abs(A['ls'] - B['ls']) < MIN_GAP_YEARS: continue
        d = hav(A['lat'], A['lng'], B['lat'], B['lng'])
        if d > RADIUS_M: continue
        if A['station'] != B['station'] or A['band'] != B['band']: continue
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
    d = os.path.dirname(os.path.abspath(__file__))
    json.dump({str(w): out[w] for w in WINDOWS}, open(os.path.join(d, 'lease-pairs.json'), 'w'), indent=1)
    print(f'\nwrote lease-pairs.json')
