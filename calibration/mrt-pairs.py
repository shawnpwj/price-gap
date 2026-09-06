#!/usr/bin/env python3
"""MRT WALK-BAND CALIBRATION — matched neighbour pairs, lease adjusted out.

Measures what the market pays for walking distance to the station, to validate the
MRT_BAND_PSF constants in ../scripts/price-gap.ts ($50 near|mid, $200 mid|far,
$250 near|far). Writes nothing back to the engine. (Framing ruling 3, 2026-09-06.)

METHOD (Shawn's spec, 2026-09-06). This is the LEASE study inverted. There the station
was held constant and the lease start varied. Here the STATION is still held constant
but the WALK BAND varies, and the lease difference is adjusted OUT using the measured
vintage figure, so what is left is purely distance to the MRT.

  THE BANDS — his, converted from minutes using the engine's own convention
    (CIRCUITY 1.3, 80 m/min, both from price-gap.ts, so the study and the engine
    speak the same units):

        under 5 min   ->  under 308 m      straight line
        5-10 min      ->  308 - 615 m
        over 10 min   ->  over 615 m

  PAIR SCREEN
    SAME NEAREST STATION, and it must genuinely be the nearest for BOTH sides —
      if either project has some other station closer, the pair does not hold.
      Shawn was explicit about this. Enforced by construction: each project's band
      is measured against its own true nearest station, and the pair requires those
      to be the same station.
    OPERATIONAL STATIONS ONLY. 37 of 223 in mrt-stations.json are under construction.
      An unbuilt station is not a walk to anything over a 2024-26 transaction window.
      (NOTE: lease-pairs.py does NOT apply this filter. See §NOTE at the bottom.)
    SAME TENURE TYPE. A freehold-vs-leasehold pair would need the tenure constant,
      which is not measured yet, so it cannot be adjusted out. LH-LH and FH-FH are
      built and reported separately.
    DIFFERENT WALK BANDS -- that is the treatment. Same-band pairs are built too and
      kept as a PLACEBO: after the lease adjustment they should read about zero.
    both >= 200 units, identical top-26 primary schools within 1 km, within RADIUS_M
      of each other -- all carried over unchanged from the lease study's rulings.
    EC allowed only once privatised, taken as TOP + 5 yrs.

  CELL SCREEN, per bedroom inside a pair
    >= 5 transactions each side in the window, median sizes within 20%.

  THE LEASE ADJUSTMENT — the point of the whole exercise
    Each cell's raw difference is (PSF of the closer-to-MRT side) - (PSF of the further
    side). Positive means proximity pays. That raw number still contains whatever lease
    difference the pair carries, so subtract the measured vintage effect:

        adjusted = raw - rate(midpoint of the two lease starts) * (ls_closer - ls_further)

    rate is the MEASURED two-band figure, read at the midpoint, from the lease study:
    $25/yr for a pair centred up to 2010, $44/yr from 2011. NOT the engine's flat $40,
    which is 1.6x hot at the old end. If the closer project is also the newer one, the
    adjustment removes the vintage premium it would otherwise be credited with.

    FH-FH pairs carry NO lease term at all, so they need no adjustment -- which makes
    them the clean control on whether the adjustment is doing its job. They do still
    differ in BUILDING AGE, which is not measured yet, so they are additionally screened
    to similar completion years (AGE_TOL_YEARS) rather than adjusted.

  RADIUS IS THE OPEN SCREEN. Geometry binds here in a way it never did for the lease
    study: two projects on the same station can differ in station-distance by at most
    the distance between them, so a near|far pair (under 308 m vs over 615 m) is
    impossible inside a 308 m radius and rare inside 500 m. Every radius is reported
    so the screen can be ruled on the counts, not guessed.
"""
import json, math, itertools, collections, statistics as st, os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', '..', 'property-analyzer', 'data')
J = lambda f: json.load(open(os.path.join(DATA, f)))

CIRCUITY, MPM = 1.3, 80          # from price-gap.ts — keep the study and engine aligned
NEAR_M = 5  * MPM / CIRCUITY     # 307.7 m
FAR_M  = 10 * MPM / CIRCUITY     # 615.4 m

MIN_UNITS, MIN_N, SIZE_TOL = 200, 5, 0.20
SCHOOL_KM, EC_PRIVATISE = 1000, 5
AGE_TOL_YEARS = 8                # FH-FH only: age is not measured, so screen it
BEDS = ['1BR', '2BR', '3BR', '4BR+']
RADII = [500, 800, 1000, 1200, 1500]
WINDOW = 24

def lease_rate(mid):
    """The MEASURED vintage figure, two bands read at the midpoint (lease study, 2026-09-06)."""
    return 25.0 if mid <= 2010.5 else 44.0

R = 6371000
def hav(a, b, c, d):
    ra, rc = math.radians(a), math.radians(c)
    dla, dln = math.radians(c - a), math.radians(d - b)
    q = math.sin(dla/2)**2 + math.cos(ra)*math.cos(rc)*math.sin(dln/2)**2
    return 2 * R * math.asin(math.sqrt(q))

def band(m):
    return 'near' if m < NEAR_M else ('mid' if m <= FAR_M else 'far')

dsi     = J('dsi-index.json')
projs, schools = dsi['projects'], dsi['schools']
base    = J('pricegap-base.json')['projects']
det     = J('pg-project-details.json')['projects']
psf     = J('psf-history.json')['projects']
qh      = J('quantum-history.json')['projects']
mrt_all = J('mrt-stations.json')['stations']
mrt     = [s for s in mrt_all if s.get('lat') and s.get('status') == 'operational']

LAST = max(m for p in psf.values() for b in p.values() for m in b)
y, mo = map(int, LAST.split('-')); t = y*12 + mo - 1 - (WINDOW - 1)
CUT = f'{t//12:04d}-{t%12+1:02d}'

P, rej = {}, collections.Counter()
for p in projs:
    n = p['project']
    b = base.get(n)
    if not b: rej['no tenure record'] += 1; continue
    ten = b.get('tenure') or {}
    ttype = ten.get('type')
    if ttype not in ('LH', 'FH'): rej['tenure not LH/FH'] += 1; continue
    if ttype == 'LH' and not ten.get('leaseStart'): rej['LH with no lease start'] += 1; continue
    d = det.get(n) or {}
    if (d.get('totalUnits') or 0) < MIN_UNITS: rej[f'under {MIN_UNITS} units'] += 1; continue
    if d.get('projectType') == 'Executive Condominium':
        top = d.get('completionYear')
        if not top or int(LAST[:4]) - top < EC_PRIVATISE:
            rej['EC not yet privatised'] += 1; continue
    hit = min(((hav(p['lat'], p['lng'], s['lat'], s['lng']), s['name']) for s in mrt),
              default=(None, None))
    if hit[0] is None: rej['no MRT fix'] += 1; continue
    dist, station = hit
    P[n] = dict(name=n, lat=p['lat'], lng=p['lng'], region=p['region'], tenure=ttype,
                ls=ten.get('leaseStart'), units=d.get('totalUnits'), top=d.get('completionYear'),
                station=station, metres=dist, band=band(dist),
                schools=frozenset(s['name'] for s in schools
                                  if hav(p['lat'], p['lng'], s['lat'], s['lng']) <= SCHOOL_KM))

def cell(name, bed):
    s, q = psf.get(name, {}).get(bed), qh.get(name, {}).get(bed)
    if not s or not q: return None
    ms = [m for m in s if CUT <= m <= LAST and m in q]
    if not ms: return None
    n = sum(q[m][2] for m in ms)
    if n < MIN_N: return None
    return dict(psf=st.median([s[m] for m in ms]), n=n, sqft=st.median([q[m][1] for m in ms]))

def build(radius):
    """Every qualifying cell. `adj` is the lease-adjusted PSF advantage of the CLOSER side."""
    rows = []
    for a, b in itertools.combinations(list(P), 2):
        A, B = P[a], P[b]
        if A['tenure'] != B['tenure']: continue
        if A['station'] != B['station']: continue
        if A['schools'] != B['schools']: continue
        if hav(A['lat'], A['lng'], B['lat'], B['lng']) > radius: continue
        if A['tenure'] == 'FH':
            if not A['top'] or not B['top']: continue
            if abs(A['top'] - B['top']) > AGE_TOL_YEARS: continue
        near, far = (A, B) if A['metres'] < B['metres'] else (B, A)
        for bd in BEDS:
            cn, cf = cell(near['name'], bd), cell(far['name'], bd)
            if not cn or not cf: continue
            if abs(cn['sqft'] - cf['sqft']) / max(cn['sqft'], cf['sqft']) > SIZE_TOL: continue
            raw = cn['psf'] - cf['psf']
            if A['tenure'] == 'LH':
                mid  = (near['ls'] + far['ls']) / 2
                adj  = raw - lease_rate(mid) * (near['ls'] - far['ls'])
                lgap = near['ls'] - far['ls']
            else:
                adj, lgap, mid = raw, 0, None
            rows.append(dict(closer=near['name'], further=far['name'], tenure=A['tenure'],
                             region=A['region'], station=A['station'], bed=bd,
                             apart=round(hav(A['lat'], A['lng'], B['lat'], B['lng'])),
                             m_close=round(near['metres']), m_far=round(far['metres']),
                             b_close=near['band'], b_far=far['band'],
                             pairkey=f"{near['band']}|{far['band']}",
                             ls_close=near['ls'], ls_far=far['ls'], lease_gap=lgap, mid=mid,
                             psf_close=cn['psf'], psf_far=cf['psf'],
                             n_close=cn['n'], n_far=cf['n'],
                             raw=raw, adj=adj))
    return rows

def dev_count(rows):
    return len({r['closer'] for r in rows} | {r['further'] for r in rows})

def pair_count(rows):
    return len({(r['closer'], r['further']) for r in rows})

if __name__ == '__main__':
    print(f'window {CUT}..{LAST}   bands: near <{NEAR_M:.0f}m  mid {NEAR_M:.0f}-{FAR_M:.0f}m  far >{FAR_M:.0f}m')
    print(f'eligible universe: {len(P)} developments '
          f'({sum(1 for v in P.values() if v["tenure"]=="LH")} LH, '
          f'{sum(1 for v in P.values() if v["tenure"]=="FH")} FH)')
    print('top rejections:', dict(rej.most_common(5)))
    print()
    for radius in RADII:
        rows = build(radius)
        print(f'=== radius {radius} m ===  {len(rows)} cells · {pair_count(rows)} pairs · {dev_count(rows)} devs')
        for ten in ('LH', 'FH'):
            sub = [r for r in rows if r['tenure'] == ten]
            if not sub: continue
            print(f'  {ten}:')
            for key in ['near|mid', 'mid|far', 'near|far',
                        'near|near', 'mid|mid', 'far|far']:
                g = [r for r in sub if r['pairkey'] == key]
                if not g: continue
                tag = 'PLACEBO' if key.split('|')[0] == key.split('|')[1] else ''
                print(f'    {key:10s} {len(g):4d} cells  {pair_count(g):3d} pairs  {dev_count(g):3d} devs '
                      f' raw {st.mean([r["raw"] for r in g]):+8.1f}  adj {st.mean([r["adj"] for r in g]):+8.1f}  {tag}')
        print()
