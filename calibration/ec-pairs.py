#!/usr/bin/env python3
"""EC vs PRIVATE CONDO — the launch premium, and what is left of it at resale.

REFERENCE ONLY. This is NOT an engine constant and it must never become one: Shawn's
ruling, 2026-09-10, is that the figure stays in the back pocket for judging what a new EC
is worth paying, and does not translate downstream into the engine, into a Price Gap
constant, or into any client figure. It sits on the calibration page because that is where
the measured work lives, not because anything reads it.

WHAT IT ANSWERS. His three Private-vs-EC slides (Rivelle/Pinery, Parktown/Aurelle,
Copen Grand/Tengah Garden) each read a ~25-36% premium for the private condo launching
beside an EC. Two questions follow:
    1. is that premium general, or is it three well-chosen pairs?
    2. does it survive into the resale market once the EC clears its MOP?

THE DATA, and why it is pulled here rather than read off disk. The floor study's REALIS
files — launch-picker/floor-study/data/realis-{newsale,resale}-all-sg.json — were pulled as
"Apartment + Condominium" and contain ZERO EC transactions. There is no EC anywhere in the
local corpus. So this script pulls URA PMI itself (all four batches, five years, every sale
type), which serves the EC property-type code directly.

THE METHOD is matched PAIRS, per Shawn's no-averages rule — never a difference of two
medians. Each EC caveat is set against private caveats that are:
    * in the same district (or within 1.5 km where the project carries coordinates)
    * within +/- 6 months
    * within +/- 15% of its floor area
and the nearest three are taken. The answer is the median of the pair ratios.

    LAUNCH pairs new sale against new sale. Coordinates are missing from the URA feed for
    every uncompleted project — Rivelle, Aurelle, Copen Grand, Lumina Grand, Novo Place,
    Otto Place all read (null, null) — which is why the launch cut is matched on DISTRICT.
    A distance match would silently drop exactly the launches this exists to measure.

    RESALE pairs resale against resale, and adds two controls the launch cut cannot need:
    LEASEHOLD private comparables only, and lease start within 5 years. Without them a
    freehold comparable's tenure premium reads as an EC discount.

  python3 ec-pairs.py && python3 build-page.py
"""
import json, math, os, re, random, subprocess, statistics as st
from collections import defaultdict, Counter

HERE  = os.path.dirname(os.path.abspath(__file__))
OUT   = os.path.join(HERE, 'ec-pairs.json')
CACHE = os.path.join(HERE, '.ura-raw.json')          # gitignored; re-pull is cheap
ENVF  = os.path.join(HERE, '..', '..', 'property-analyzer', '.env.local')

MONTHS = 6          # +/- this many months between the two legs
SIZETOL = 0.15      # +/- this much floor area
NEAR = 3            # comparables taken per EC caveat, nearest first
KM = 1.5            # distance cut, where coordinates exist
LSTOL = 5           # lease-start tolerance, resale cut only
SQM_TO_SQFT = 10.7639

# ── the pull ────────────────────────────────────────────────────────────────
def pull():
    if os.path.exists(CACHE):
        return json.load(open(CACHE))
    key = re.search(r'^URA_ACCESS_KEY=(.+)$', open(ENVF).read(), re.M).group(1).strip()
    js = subprocess.run(['node', '-e', f'''
      const key = {json.dumps(key)};
      const t = await (await fetch("https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1",
        {{headers:{{AccessKey:key}}}})).json();
      if (t.Status !== "Success") throw new Error(JSON.stringify(t).slice(0,300));
      const out = [];
      for (const b of [1,2,3,4]) {{
        const r = await (await fetch(
          `https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch=${{b}}`,
          {{headers:{{AccessKey:key,Token:t.Result}},signal:AbortSignal.timeout(180000)}})).json();
        if (r.Status !== "Success") throw new Error(`batch ${{b}}: ${{r.Message}}`);
        out.push(...r.Result);
      }}
      process.stdout.write(JSON.stringify(out));
    ''', '--input-type=module'], capture_output=True, text=True, timeout=900)
    if js.returncode: raise SystemExit(js.stderr[-800:])
    raw = json.loads(js.stdout)
    json.dump(raw, open(CACHE, 'w'))
    return raw

MON = {m: i + 1 for i, m in enumerate('JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split())}
def contract(s):
    if re.fullmatch(r'\d{4}', s): m, y = int(s[:2]), 2000 + int(s[2:])
    else:                         m, y = MON[s[:3].upper()], 2000 + int(s[3:5])
    return y * 12 + m, f'{y}-{m:02d}'

def lease_start(t):
    m = re.search(r'[Ff]rom (\d{2})/(\d{2})/(\d{4})', t)
    if m: return int(m.group(3))
    m = re.search(r'from (\d{4})', t)
    return int(m.group(1)) if m else None

def rows():
    out = []
    for p in pull():
        try:    x, y = float(p['x']), float(p['y'])
        except (TypeError, ValueError, KeyError): x = y = None
        for t in p['transaction']:
            pt = t['propertyType']
            if pt not in ('Apartment', 'Condominium', 'Executive Condominium'): continue
            area = float(t['area'])
            if area <= 0: continue
            sqft = area * SQM_TO_SQFT
            mi, mk = contract(t['contractDate'])
            out.append(dict(proj=p['project'], dist=t['district'], x=x, y=y,
                            ec=(pt == 'Executive Condominium'), sqft=sqft,
                            psf=float(t['price']) / sqft, mi=mi, mk=mk,
                            sale=int(t['typeOfSale']), ls=lease_start(t['tenure'])))
    return out

import cut                       # THE PINNED CUT — see cut.py
# Shawn, 2026-09-10: the study is a dated cut, not a live feed. The URA pull returns whatever
# is current, so the upper bound is applied here rather than left to the API.
R = [r for r in rows() if r['mk'] <= cut.CUT_END]

# ── pairing ─────────────────────────────────────────────────────────────────
def gap(a, b):
    if None in (a['x'], a['y'], b['x'], b['y']): return None
    return math.hypot(a['x'] - b['x'], a['y'] - b['y'])

def pairs(sale, key, lhonly=False, agetol=None, maxkm=None):
    """key: 'dist' matches on district, 'geo' on distance. One EC caveat, NEAR comparables."""
    ec = [r for r in R if r['ec'] and r['sale'] == sale]
    pv = [r for r in R if not r['ec'] and r['sale'] == sale and (r['ls'] or not lhonly)]
    idx = defaultdict(list)
    for r in pv: idx[(r['dist'] if key == 'dist' else 0, r['mi'] // 3)].append(r)
    out = []
    for e in ec:
        cands = []
        for q in range((e['mi'] - MONTHS) // 3, (e['mi'] + MONTHS) // 3 + 1):
            for c in idx.get((e['dist'] if key == 'dist' else 0, q), ()):
                if abs(c['mi'] - e['mi']) > MONTHS: continue
                if abs(math.log(c['sqft'] / e['sqft'])) > math.log(1 + SIZETOL): continue
                if agetol and e['ls'] and c['ls'] and abs(c['ls'] - e['ls']) > agetol: continue
                d = gap(e, c)
                if maxkm is not None and (d is None or d > maxkm * 1000): continue
                cands.append((d if d is not None else 0, c))
        cands.sort(key=lambda t: t[0])
        for _, c in cands[:NEAR]:
            out.append(dict(ec=e['proj'], pv=c['proj'], mk=e['mk'], ratio=c['psf'] / e['psf'],
                            ecpsf=e['psf'], pvpsf=c['psf'], ecls=e['ls'], sqft=e['sqft']))
    return out

def pct(ps): return st.median(p['ratio'] for p in ps) * 100 - 100
def band(ps, lo=.25, hi=.75):
    v = sorted(p['ratio'] for p in ps)
    return (v[int(lo * len(v))] * 100 - 100, v[int(hi * len(v))] * 100 - 100)
def ci(ps, N=2000, seed=7):
    """Bootstrap resampled BY EC PROJECT, not by pair. One EC caveat contributes NEAR
    comparables and one project contributes hundreds of caveats, so pairs are nowhere near
    independent — a pair-level bootstrap on 16,000 rows returns an interval a fraction of a
    percent wide, which would be a statement about the resampling and not about the market.
    The project is the unit that varies."""
    g = random.Random(seed)
    cl = defaultdict(list)
    for x in ps: cl[x['ec']].append(x)
    keys, out = list(cl), []
    for _ in range(N):
        draw = [x for _ in keys for x in cl[keys[g.randrange(len(keys))]]]
        out.append(st.median(x['ratio'] for x in draw))
    v = sorted(out)
    return v[int(.025 * N)] * 100 - 100, v[int(.975 * N) - 1] * 100 - 100

def by_project(ps, floor=1):
    g = defaultdict(list)
    for p in ps: g[p['ec']].append(p)
    out = []
    for k, v in g.items():
        if len(v) < floor: continue
        out.append(dict(ec=k, n=len(v), pairs=len(v),
                        ecpsf=st.median(p['ecpsf'] for p in v),
                        pvpsf=st.median(p['pvpsf'] for p in v),
                        pct=pct(v),
                        comps=[n for n, _ in Counter(p['pv'] for p in v).most_common(2)],
                        age=(st.median([int(p['mk'][:4]) - (p['ecls'] + 4) for p in v if p['ecls']])
                             if any(p['ecls'] for p in v) else None)))
    out.sort(key=lambda d: -d['pct'])
    return out

LAUNCH = pairs(1, 'dist')
RESALE = pairs(3, 'geo', lhonly=True, agetol=LSTOL, maxkm=KM)
RES_RAW = pairs(3, 'geo', maxkm=KM)          # no tenure or vintage control

AGES = [('5-10', 5, 10, 'post-MOP, citizen-only'), ('10-15', 10, 15, 'privatised'),
        ('15+', 15, 99, 'privatised')]
def age_cut(lo, hi):
    return [p for p in RESALE if p['ecls'] and lo <= int(p['mk'][:4]) - (p['ecls'] + 4) < hi]

def head_to_head(ec_name, pv_name, sale=1):
    """One named EC against one named private launch, size for size — the shape his slides
    take. Both the matched figure and the raw pair of headline medians, because the slide
    quotes the second and the study quotes the first."""
    e = [r for r in R if ec_name in r['proj'] and r['sale'] == sale]
    v = [r for r in R if pv_name in r['proj'] and r['sale'] == sale]
    if not e or not v: return None
    rs = [c['psf'] / x['psf'] for x in e for c in v
          if abs(math.log(c['sqft'] / x['sqft'])) <= math.log(1 + SIZETOL)][:]
    return dict(ec=e[0]['proj'], pv=v[0]['proj'], pairs=len(rs),
                pct=(st.median(rs) * 100 - 100) if rs else None,
                ecpsf=st.median(x['psf'] for x in e), pvpsf=st.median(x['psf'] for x in v),
                raw_pct=st.median(x['psf'] for x in v) / st.median(x['psf'] for x in e) * 100 - 100)

mks = [r['mk'] for r in R]
DATA = dict(
    meta=dict(window=[min(mks), max(mks)], rows=len(R), ec_rows=sum(r['ec'] for r in R),
              months=MONTHS, sizetol=SIZETOL, near=NEAR, km=KM, lstol=LSTOL,
              ec_projects=len({r['proj'] for r in R if r['ec']})),
    launch=dict(pct=pct(LAUNCH), pairs=len(LAUNCH), projects=len({p['ec'] for p in LAUNCH}),
                lo=band(LAUNCH)[0], hi=band(LAUNCH)[1], ci=ci(LAUNCH), by=by_project(LAUNCH)),
    resale=dict(pct=pct(RESALE), pairs=len(RESALE), projects=len({p['ec'] for p in RESALE}),
                lo=band(RESALE)[0], hi=band(RESALE)[1], ci=ci(RESALE),
                by=by_project(RESALE, floor=100)),
    resale_raw=dict(pct=pct(RES_RAW), pairs=len(RES_RAW),
                    projects=len({p['ec'] for p in RES_RAW})),
    slides=[d for d in (head_to_head('RIVELLE', 'PINERY'),
                        head_to_head('AURELLE', 'PARKTOWN')) if d],
    ages=[dict(key=k, label=lab, pct=pct(c), pairs=len(c),
               projects=len({p['ec'] for p in c}), lo=band(c)[0], hi=band(c)[1],
               ci=ci(c))
          for k, lo, hi, lab in AGES for c in [age_cut(lo, hi)] if c],
)
json.dump(DATA, open(OUT, 'w'), indent=1)
print(f"wrote {os.path.basename(OUT)}  {DATA['meta']['window'][0]}..{DATA['meta']['window'][1]}  "
      f"{DATA['meta']['rows']:,} rows, {DATA['meta']['ec_rows']:,} EC")
print(f"  launch  {DATA['launch']['pct']:+.1f}%  {DATA['launch']['pairs']:,} pairs, "
      f"{DATA['launch']['projects']} EC launches")
print(f"  resale  {DATA['resale']['pct']:+.1f}%  {DATA['resale']['pairs']:,} pairs, "
      f"{DATA['resale']['projects']} EC projects   (no controls {DATA['resale_raw']['pct']:+.1f}%)")
for a in DATA['ages']:
    print(f"    {a['key']:>6s} yr  {a['pct']:+.1f}%  {a['pairs']:,} pairs, {a['projects']} projects")
