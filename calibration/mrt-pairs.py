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
    LEASEHOLD ONLY (Shawn, 2026-09-06). Freehold was built and dropped: 7-13 pairs a
      cell, reading -$17 / +$47 / +$100, incoherent and not worth quoting.
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
import json, math, itertools, collections, statistics as st, os, random

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', '..', 'property-analyzer', 'data')
J = lambda f: json.load(open(os.path.join(DATA, f)))

CIRCUITY, MPM = 1.3, 80          # from price-gap.ts — keep the study and engine aligned
NEAR_M = 5  * MPM / CIRCUITY     # 307.7 m
FAR_M  = 10 * MPM / CIRCUITY     # 615.4 m

MIN_UNITS, MIN_N, SIZE_TOL = 200, 3, 0.20
# MIN_N 3, not the lease study's 5, and PAIR_CAP 1500, not 1200 (Shawn asked for a laxer
# screen, 2026-09-06). Both were chosen ON THE PLACEBO, which is the only honest criterion
# here: it stays clean at -1.7 psf under both. The relaxations that were REJECTED all
# degraded it -- dropping the school screen -6.9, widening the size match to 30% -9.0,
# doing both -14.0. A screen that breaks the placebo is buying pairs with bias.
SCHOOL_KM, EC_PRIVATISE = 1000, 5
BEDS = ['1BR', '2BR', '3BR', '4BR+']
CATCHMENT = 2000          # max metres from the SHARED station -- his screen
PAIR_CAP  = 1500          # max metres BETWEEN the two projects. Not a guess: the placebo
                          # (same band, within 50 m of each other in station-distance, so it
                          # should read zero) stays clean out to 1500 m and degrades to +8.6 at
                          # 1800 m. The cap is set where the placebo breaks.
CATCHMENTS = [CATCHMENT]
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
    if ttype != 'LH': rej['not leasehold'] += 1; continue
    if not ten.get('leaseStart'): rej['LH with no lease start'] += 1; continue
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

def build(catchment):
    """Every qualifying cell. `adj` is the lease-adjusted PSF advantage of the CLOSER side.

    THE SCREEN IS THE STATION'S CATCHMENT, NOT THE DISTANCE BETWEEN THE PAIR (Shawn,
    2026-09-06). An earlier pass required the two projects to sit within 500 m of each
    other, carried over from the lease study where holding location constant was the
    whole point. Here it is self-defeating: two projects can differ in walking distance
    by at most the distance between them, so that screen mechanically caps the very
    thing being measured and made an under-5 vs over-10 pair almost impossible.
    They only need to share the station. His example: THE TRILINQ (577 m, 9.4 min)
    against CLAVON (710 m, 11.5 min), both nearest Clementi."""
    rows = []
    for a, b in itertools.combinations(list(P), 2):
        A, B = P[a], P[b]
        if A['station'] != B['station']: continue
        if A['metres'] > catchment or B['metres'] > catchment: continue
        if hav(A['lat'], A['lng'], B['lat'], B['lng']) > PAIR_CAP: continue
        if A['schools'] != B['schools']: continue
        near, far = (A, B) if A['metres'] < B['metres'] else (B, A)
        for bd in BEDS:
            cn, cf = cell(near['name'], bd), cell(far['name'], bd)
            if not cn or not cf: continue
            if abs(cn['sqft'] - cf['sqft']) / max(cn['sqft'], cf['sqft']) > SIZE_TOL: continue
            raw  = cn['psf'] - cf['psf']
            mid  = (near['ls'] + far['ls']) / 2
            lgap = near['ls'] - far['ls']
            adj  = raw - lease_rate(mid) * lgap
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

KEYS = [('near|mid', 'Under 5 min vs 5-10 min'),
        ('mid|far',  '5-10 min vs over 10 min'),
        ('near|far', 'Under 5 min vs over 10 min')]

def boot(g, B=4000, seed=17):
    """Cluster bootstrap by PAIR — cells inside one pair are not independent."""
    r = random.Random(seed); d = {}
    for x in g: d.setdefault((x['closer'], x['further']), []).append(x)
    k = list(d); o = []
    for _ in range(B):
        smp = [c for kk in (r.choice(k) for _ in k) for c in d[kk]]
        o.append(st.mean([x['adj'] for x in smp]))
    o.sort(); return o[int(.025*B)], o[int(.975*B)]

def summary():
    rows = build(CATCHMENT)
    out = dict(cells=len(rows), pairs=pair_count(rows), devs=dev_count(rows),
               near_m=NEAR_M, far_m=FAR_M, catchment=CATCHMENT, pair_cap=PAIR_CAP,
               window=[CUT, LAST], engine={'near|mid': 50, 'mid|far': 200, 'near|far': 250},
               bands=[])
    for k, label in KEYS:
        g = [r for r in rows if r['pairkey'] == k]
        lo, hi = boot(g)
        walk = st.mean([r['m_far'] - r['m_close'] for r in g])
        adj  = st.mean([r['adj'] for r in g])
        out['bands'].append(dict(key=k, label=label, adj=adj, lo=lo, hi=hi, walk=walk,
                                 per100=adj/walk*100, cells=len(g),
                                 pairs=pair_count(g), devs=dev_count(g)))
    tp = [r for r in rows if r['b_close'] == r['b_far'] and (r['m_far'] - r['m_close']) < 50]
    plo, phi = boot(tp)
    out['placebo'] = dict(adj=st.mean([r['adj'] for r in tp]), lo=plo, hi=phi,
                          cells=len(tp), pairs=pair_count(tp), devs=dev_count(tp))
    xs = [r['m_far'] - r['m_close'] for r in rows]; ys = [r['adj'] for r in rows]
    out['slope100'] = sum(x*y for x, y in zip(xs, ys)) / sum(x*x for x in xs) * 100
    # WHY THE HEADLINE under-5-vs-over-10 FIGURE UNDERSTATES THE CONTRAST PEOPLE PICTURE.
    # Most such pairs barely straddle the line -- the far side sits just past 615 m -- so the
    # band average is diluted. Split them by the walking they actually span. (Shawn asked
    # 2026-09-06 why $122 looked low. It is low because the pairs are not the extreme he
    # had in mind, and the pairs that ARE read far higher.)
    nf = [r for r in rows if r['pairkey'] == 'near|far']
    out['nf_split'] = []
    for lo, hi, lab in ((0, 500, 'under 500 m'), (500, 700, '500-700 m'), (700, 9999, 'over 700 m')):
        g = [r for r in nf if lo <= r['m_far'] - r['m_close'] < hi]
        if len(g) < 4: continue
        w = st.mean([r['m_far'] - r['m_close'] for r in g]); a = st.mean([r['adj'] for r in g])
        out['nf_split'].append(dict(label=lab, adj=a, walk=w, per100=a/w*100,
                                    pairs=pair_count(g), devs=dev_count(g)))
    out['nf_close'] = st.median([r['m_close'] for r in nf])
    out['nf_far']   = st.median([r['m_far'] for r in nf])
    out['rows'] = rows
    return out

if __name__ == '__main__':
    print('window %s..%s   near <%.0fm  mid %.0f-%.0fm  far >%.0fm' % (CUT, LAST, NEAR_M, NEAR_M, FAR_M, FAR_M))
    print('eligible universe: %d leasehold developments' % len(P))
    print()
    for cm in CATCHMENTS:
        rows = build(cm)
        print('=== catchment %d m from the shared station ===  %d cells / %d pairs / %d devs'
              % (cm, len(rows), pair_count(rows), dev_count(rows)))
        for key in ['near|mid', 'mid|far', 'near|far']:
            g = [r for r in rows if r['pairkey'] == key]
            if not g: continue
            print('    %-9s %4d cells %4d pairs %4d devs   adj %+7.0f' %
                  (key, len(g), pair_count(g), dev_count(g), st.mean([r['adj'] for r in g])))
        tp = [r for r in rows if r['b_close'] == r['b_far'] and (r['m_far'] - r['m_close']) < 50]
        if tp:
            print('    %-9s %4d cells %4d pairs %4d devs   adj %+7.1f   (should be 0)' %
                  ('PLACEBO', len(tp), pair_count(tp), dev_count(tp), st.mean([r['adj'] for r in tp])))
        print()
    # his example
    rows = build(1500)
    ex = [r for r in rows if 'TRILINQ' in r['closer'].upper() + r['further'].upper()
          and 'CLAVON' in r['closer'].upper() + r['further'].upper()]
    print('HIS EXAMPLE — THE TRILINQ vs CLAVON, both nearest Clementi:')
    for r in ex:
        print('   %-5s closer %-14s %4dm (%s)  further %-14s %4dm (%s)  ls %d vs %d  raw %+6.0f  lease-adj %+6.0f'
              % (r['bed'], r['closer'][:14], r['m_close'], r['b_close'], r['further'][:14],
                 r['m_far'], r['b_far'], r['ls_close'], r['ls_far'], r['raw'], r['adj']))
    if not ex: print('   (no qualifying cell)')

    S = summary()
    json.dump(S, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mrt-pairs.json'), 'w'), indent=1)
    print('\nwrote mrt-pairs.json  —  %d cells / %d pairs / %d developments' %
          (S['cells'], S['pairs'], S['devs']))
    for b in S['bands']:
        print('  %-28s %+5.0f  [%+4.0f,%+4.0f]  %3d pairs  %3d devs  %5.1f psf/100m'
              % (b['label'], b['adj'], b['lo'], b['hi'], b['pairs'], b['devs'], b['per100']))
    print('  placebo %+.1f  ·  slope %+.1f psf per 100 m' % (S['placebo']['adj'], S['slope100']))
