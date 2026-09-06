#!/usr/bin/env python3
"""INTEGRATED-DEVELOPMENT CALIBRATION — on the station vs next to it.

Measures what the market pays for a development built ON TOP OF a station and its mall,
against an ordinary condo a short walk away at the SAME station. Validates the
INTEGRATED_PREMIUM = 0.05 constant in ../scripts/price-gap.ts. Writes nothing back.

  THE FLAG DOES NOT EXIST IN THE DATA. price-gap.ts reads `integrated: ov.integrated ?? false`
  from pricegap-overrides.json, which carries two entries and flags NEITHER. So the engine's
  +/-5% has never fired on anything, ever. It is not merely unmeasured, it is INERT. The list
  below is a classification Shawn audited on 2026-09-06 — it is a judgement, not a datum, and
  it must be re-audited if it is extended.

  EXCLUDED BY HIS RULING: Marina One Residences and the two Midtown entries — all CCR, and
  every partner they have is Marina Bay or Bugis, which is the submarket his lease-study
  ruling already calls not measurable this way.
  EXCLUDED AS NOT ACTUALLY INTEGRATED, having been considered: The Tre Ver (687 m from
  Woodleigh), One-North Residences (431 m), The Clement Canopy (941 m), City Gate (a retail
  podium, but not joined to a station).

  THE METHOD. Pair an integrated development with a plain one at the SAME nearest station,
  bedroom by bedroom, then subtract the two things that separate them and are already measured:

      answer = raw PSF difference
             - the lease difference, at the measured two-band vintage rate
             - the walking difference, at the measured $/100 m from the MRT study

  THE CONFOUND, and it is the whole reason this file reports a RANGE and not a number
  (Shawn found it 2026-09-06 by asking what Pasir Ris 8 was being compared against):
  INTEGRATED DEVELOPMENTS ARE SYSTEMATICALLY NEWER THAN THEIR NEIGHBOURS — a mean lease gap
  of +9 years against -0.5 for the placebo pairs. So they carry a mean adjustment of ~$490,
  nearly double the placebo's, and the answer is what survives a very large subtraction.
  PASIR RIS 8 is the extreme: a 2021 lease against neighbours from 1996-2013, giving answers
  from -$424 (vs Coco Palms) to +$306 (vs Eastvale) — noise around a huge correction, not a
  measurement. Restricting to pairs the adjustments barely touch RAISES the answer and TIGHTENS
  it, which is the signature of a diluted estimate rather than an absent effect.

  THE PLACEBO is plain-vs-plain at the same station under the identical adjustments. It should
  read zero.
"""
import json, math, itertools, statistics as st, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', '..', 'property-analyzer', 'data')
J = lambda f: json.load(open(os.path.join(DATA, f)))

# Shawn's audited list, 2026-09-06. A judgement, not a datum.
INTEGRATED = {
    'THE WOODLEIGH RESIDENCES', 'WATERTOWN', 'SENGKANG GRAND RESIDENCES', 'COMPASS HEIGHTS',
    'HILLION RESIDENCES', 'PASIR RIS 8', 'THE POIZ RESIDENCES', 'BEDOK RESIDENCES',
    'SCENECA RESIDENCE', 'THE CENTRIS', 'PARK PLACE RESIDENCES AT PLQ', 'DUO RESIDENCES',
    'LENTOR MODERN', 'NORTH PARK RESIDENCES',
}

MIN_UNITS, MIN_N, SIZE_TOL, PAIR_CAP = 200, 3, 0.20, 1500
EC_PRIVATISE, BEDS = 5, ['1BR', '2BR', '3BR', '4BR+']
CUTS = [(99, 99999, 'every pair'), (10, 99999, 'lease gap 10 yrs or less'),
        (5, 99999, 'lease gap 5 yrs or less'), (10, 400, 'lease gap 10 or less, within 400 m'),
        (5, 400, 'lease gap 5 or less, within 400 m')]

R = 6371000
def hav(a, b, c, d):
    ra, rc = math.radians(a), math.radians(c)
    dla, dln = math.radians(c - a), math.radians(d - b)
    q = math.sin(dla/2)**2 + math.cos(ra)*math.cos(rc)*math.sin(dln/2)**2
    return 2 * R * math.asin(math.sqrt(q))

dsi  = J('dsi-index.json')
base = J('pricegap-base.json')['projects']
det  = J('pg-project-details.json')['projects']
psf  = J('psf-history.json')['projects']
qh   = J('quantum-history.json')['projects']
mrt  = [s for s in J('mrt-stations.json')['stations']
        if s.get('lat') and s.get('status') == 'operational']

MRTJ  = json.load(open(os.path.join(HERE, 'mrt-pairs.json')))
SLOPE = MRTJ['slope100']                      # $ psf per 100 m, measured
LEASE = json.load(open(os.path.join(HERE, 'lease-pairs.json')))['24']
def _bands():
    mid = lambda r: (r['ls_old'] + r['ls_new']) / 2
    o = {}
    for lo, hi, nm in ((0, 2011, 'old'), (2011, 9999, 'new')):
        rs = [r for r in LEASE if lo <= mid(r) < hi]
        o[nm] = sum(r['diff'] for r in rs) / sum(r['gap'] for r in rs)
    return o
LB = _bands()
lease_rate = lambda m: LB['old'] if m <= 2010.5 else LB['new']

LAST = max(m for p in psf.values() for b in p.values() for m in b)
y, mo = map(int, LAST.split('-')); t = y*12 + mo - 1 - 23
CUT = f'{t//12:04d}-{t%12+1:02d}'

P = {}
for p in dsi['projects']:
    n = p['project']
    b = base.get(n)
    if not b: continue
    ten = b.get('tenure') or {}
    if ten.get('type') != 'LH' or not ten.get('leaseStart'): continue
    d = det.get(n) or {}
    if (d.get('totalUnits') or 0) < MIN_UNITS: continue
    if d.get('projectType') == 'Executive Condominium':
        top = d.get('completionYear')
        if not top or int(LAST[:4]) - top < EC_PRIVATISE: continue
    hit = min(((hav(p['lat'], p['lng'], s['lat'], s['lng']), s['name']) for s in mrt),
              default=(None, None))
    if hit[0] is None: continue
    P[n] = dict(name=n, lat=p['lat'], lng=p['lng'], region=p['region'], ls=ten['leaseStart'],
                station=hit[1], metres=hit[0], integrated=n in INTEGRATED)

MISSING = INTEGRATED - set(P)

def cell(name, bed):
    s, q = psf.get(name, {}).get(bed), qh.get(name, {}).get(bed)
    if not s or not q: return None
    ms = [m for m in s if CUT <= m <= LAST and m in q]
    if not ms: return None
    n = sum(q[m][2] for m in ms)
    if n < MIN_N: return None
    return dict(psf=st.median([s[m] for m in ms]), n=n, sqft=st.median([q[m][1] for m in ms]))

def build(kind):
    """kind='treat' -> integrated vs plain. 'placebo' -> plain vs plain, same adjustments."""
    rows = []
    for a, b in itertools.combinations(list(P), 2):
        A, B = P[a], P[b]
        if A['station'] != B['station']: continue
        if hav(A['lat'], A['lng'], B['lat'], B['lng']) > PAIR_CAP: continue
        if kind == 'treat':
            if A['integrated'] == B['integrated']: continue
            I, N = (A, B) if A['integrated'] else (B, A)
        else:
            if A['integrated'] or B['integrated']: continue
            I, N = (A, B) if A['metres'] < B['metres'] else (B, A)
        for bd in BEDS:
            ci, cn = cell(I['name'], bd), cell(N['name'], bd)
            if not ci or not cn: continue
            if abs(ci['sqft'] - cn['sqft']) / max(ci['sqft'], cn['sqft']) > SIZE_TOL: continue
            raw   = ci['psf'] - cn['psf']
            lg    = I['ls'] - N['ls']
            dg    = N['metres'] - I['metres']
            lease = lease_rate((I['ls'] + N['ls']) / 2) * lg
            dist  = SLOPE / 100 * dg
            rows.append(dict(a=I['name'], b=N['name'], bed=bd, region=I['region'],
                             station=I['station'].replace(' MRT Station', '').replace(' LRT Station', ''),
                             m_i=I['metres'], m_n=N['metres'], ls_i=I['ls'], ls_n=N['ls'],
                             lg=lg, dg=dg, base=cn['psf'],
                             raw=raw, lease=lease, dist=dist, adj=raw - lease - dist))
    return rows

prs = lambda g: len({(x['a'], x['b']) for x in g})
dvs = lambda g: len({y for x in g for y in (x['a'], x['b'])})

def boot(g, B=4000, seed=17):
    r = random.Random(seed); d = {}
    for x in g: d.setdefault((x['a'], x['b']), []).append(x)
    k = list(d); o = []
    for _ in range(B):
        s = [c for kk in (r.choice(k) for _ in k) for c in d[kk]]
        o.append(st.mean([x['adj'] for x in s]))
    o.sort(); return o[int(.025*B)], o[int(.975*B)]

def summary():
    T, PL = build('treat'), build('placebo')
    out = dict(window=[CUT, LAST], slope=SLOPE, pair_cap=PAIR_CAP,
               lease_old=LB['old'], lease_new=LB['new'],
               n_integrated=len({r['a'] for r in T}), missing=sorted(MISSING), cuts=[])
    for lgmax, dgmax, lab in CUTS:
        g = [r for r in T if abs(r['lg']) <= lgmax and abs(r['dg']) <= dgmax]
        if prs(g) < 3: continue
        lo, hi = boot(g)
        out['cuts'].append(dict(label=lab, adj=st.mean([r['adj'] for r in g]), lo=lo, hi=hi,
                                pct=100*st.mean([r['adj'] for r in g])/st.mean([r['base'] for r in g]),
                                load=st.mean([abs(r['lease'])+abs(r['dist']) for r in g]),
                                cells=len(g), pairs=prs(g), devs=dvs(g)))
    pl = [r for r in PL if abs(r['lg']) <= 5 and abs(r['dg']) <= 400]
    plo, phi = boot(pl)
    out['placebo'] = dict(adj=st.mean([r['adj'] for r in pl]), lo=plo, hi=phi,
                          cells=len(pl), pairs=prs(pl),
                          load=st.mean([abs(r['lease'])+abs(r['dist']) for r in pl]))
    out['confound'] = dict(treat_gap=st.mean([r['lg'] for r in T]),
                           placebo_gap=st.mean([r['lg'] for r in PL]),
                           treat_load=st.mean([abs(r['lease'])+abs(r['dist']) for r in T]),
                           placebo_load=st.mean([abs(r['lease'])+abs(r['dist']) for r in PL]))
    byd = {}
    for r in T: byd.setdefault(r['a'], []).append(r)
    out['devs'] = sorted(({'name': k, 'station': g[0]['station'], 'm_i': g[0]['m_i'],
                           'ls': g[0]['ls_i'], 'adj': st.mean([x['adj'] for x in g]),
                           'pairs': prs(g), 'lg': st.mean([x['lg'] for x in g])}
                          for k, g in byd.items()), key=lambda d: -d['adj'])
    out['rows'] = T
    return out

if __name__ == '__main__':
    S = summary()
    json.dump(S, open(os.path.join(HERE, 'integrated-pairs.json'), 'w'), indent=1)
    if MISSING: print('NOT IN THE ELIGIBLE POOL:', ', '.join(sorted(MISSING)))
    print('lease bands in use: $%.1f / $%.1f   ·   distance $%.1f per 100 m'
          % (LB['old'], LB['new'], SLOPE))
    print('%d integrated developments produced pairs\n' % S['n_integrated'])
    print('  %-36s %5s %5s %8s %s' % ('', 'cells', 'prs', 'adj load', 'answer'))
    for c in S['cuts']:
        print('  %-36s %5d %5d %8.0f  %+5.0f [%+.0f, %+.0f]  %+.1f%%'
              % (c['label'], c['cells'], c['pairs'], c['load'], c['adj'], c['lo'], c['hi'], c['pct']))
    p = S['placebo']
    print('  %-36s %5d %5d %8.0f  %+5.1f [%+.0f, %+.0f]  PLACEBO'
          % ('plain vs plain, tightest cut', p['cells'], p['pairs'], p['load'], p['adj'], p['lo'], p['hi']))
    print('\n  confound: integrated pairs sit %+.1f yrs apart on lease vs %+.1f for the placebo'
          % (S['confound']['treat_gap'], S['confound']['placebo_gap']))
