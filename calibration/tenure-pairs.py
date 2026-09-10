#!/usr/bin/env python3
"""TENURE CALIBRATION — freehold vs leasehold, on matched neighbour pairs.

Measures what the market actually pays for freehold, to validate the FREEHOLD_PREMIUM = 0.15
(applied as a DIVISION by 1.15) in ../scripts/price-gap.ts. Writes nothing back to the engine.

METHOD, and every line of it is a ruling Shawn gave on 2026-09-08:

  THE CLOCK IS TOP, NOT LEASE START. A freehold has no lease start to difference against --
  and 999-year leases, which he ruled are FREEHOLD, carry real lease starts as far back as
  1827. Completion year is the only clock both sides share.

  NO TOP SCREEN. He rejected matching on TOP: "we dont need to match TOP, the question is
  also how do we adjust for TOP differences." So the vintage rate is not a nuisance to be
  screened away -- it is part of the answer, and the fit decides it.

  THE HORSE RACE IS THE POINT. His words: "It could be $10psf per year to match TOP followed
  by 15% premium. OR we could do 44psf per year adjustment then adjust by 15% premium.
  Whichever makes more sense. I want the data and number to tell." So this script fits the
  vintage rate, the premium, AND THE ORDER THEY ARE APPLIED IN, and ranks every combination
  on held-out error against the engine's own spec.

  REUSE $25/$43 AS MEASURED (his ruling). The lease bands are carried onto the TOP clock as
  a candidate rate, read at the midpoint of the two lease-start EQUIVALENTS (TOP - 6, the
  engine's own CONSTRUCTION_YEARS). They are DERIVED from lease-pairs.json, never literals.

  SCALE IS OPEN. Dollars won on lease; here the engine already uses a ratio, so percent may
  genuinely win. Both forms are fitted and the base-PSF invariance test decides, exactly as
  it did on lease.

  ONE FIGURE PLUS THE GRADIENT. The headline replaces the /1.15. The premium is then read
  against the LEASEHOLD side's REMAINING LEASE -- and that gradient IS the double-count test.
  Framing ruling 2: lease and tenure are ONE curve. If the premium is flat against remaining
  lease, they are separate terms. If it steepens as the lease runs down, the engine charges
  for the same thing twice.

  SCREENS: identical to lease-pairs.py -- 500 m, same operational station, same top-26 school
  set within 1 km, 200+ units both sides, 5+ transactions each side in 24 months, median sizes
  within 20% bedroom by bedroom, EC only once privatised. 800 m and a lowered unit floor run
  as SENSITIVITIES, never as the headline (his ruling: keep the lease-study screens).

  PLACEBO FIRST. LH-vs-LH and FH-vs-FH pairs run through the identical estimator must read a
  premium of ZERO once vintage is removed. On this study the placebo has decided every screen
  ruling. FH-vs-FH also fits the vintage rate on its own, which validates the engine's
  unmeasured AGE_PSF_PER_YEAR = 10 as a by-product.

Read-only consumer of ../../property-analyzer/data/ and of lease-pairs.json. Run:
    python3 tenure-pairs.py          (after lease-pairs.py)
"""
import json, math, itertools, collections, statistics as st, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', '..', 'property-analyzer', 'data')
J = lambda f: json.load(open(os.path.join(DATA, f)))

RADIUS_M      = 500
MIN_UNITS     = 200
MIN_N         = 5
SIZE_TOL      = 0.20
EC_PRIVATISE  = 5
SCHOOL_KM     = 1000
# CONSTRUCTION_YEARS is MEASURED below, not imported. The engine assumes 6.
BEDS          = ['1BR', '2BR', '3BR', '4BR+']
WINDOW        = 24

# ── the measured lease bands, DERIVED from lease-pairs.json, never hardcoded ────────────
LP = json.load(open(os.path.join(HERE, 'lease-pairs.json')))
def _lease_bands(lp):
    """Pull the two measured band rates and the boundary year out of lease-pairs.json."""
    for key in ('bands', 'answer', 'headline', 'two_bands'):
        v = lp.get(key)
        if isinstance(v, list) and v and isinstance(v[0], dict):
            out = []
            for b in v:
                r = b.get('rate', b.get('fitted', b.get('psf_per_yr')))
                out.append((b.get('from'), b.get('to'), r))
            if all(o[2] is not None for o in out): return out
    return None
BANDS = _lease_bands(LP)
BAND_BOUND = 2011               # the shape ruled on the lease study; the RATES are derived below

def fitted(rows, dk='diff', gk='gap'):
    """Least squares through the origin — the same estimator as lease-pairs.py fitted().
    Changed from the ratio form on Shawn's ruling, 2026-09-10; see that docstring."""
    if not rows: return None
    return sum(r[dk] * r[gk] for r in rows) / sum(r[gk] ** 2 for r in rows)

_lp = LP['24']
BANDR = {}
for nm, lo, hi in (('old', 1900, BAND_BOUND), ('new', BAND_BOUND, 3000)):
    sel = [r for r in _lp if lo <= (r['ls_old'] + r['ls_new']) / 2 < hi]
    BANDR[nm] = fitted(sel)

def band_rate(top_a, top_b):
    """The measured lease rate, read at the midpoint of the two LEASE-START EQUIVALENTS.
    A freehold has no lease start, so TOP - CONSTRUCTION_YEARS stands in for both sides —
    the same offset the engine itself uses when it has to invent one."""
    mid = (top_a + top_b) / 2 - CONSTRUCTION_YEARS
    return BANDR['old'] if mid < BAND_BOUND else BANDR['new']

# ── geo ───────────────────────────────────────────────────────────────────────────────
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

# ── HOW LONG A LEASEHOLD TAKES TO BUILD — measured, not assumed ───────────────────────
# Needed twice: to put a freehold's TOP year on the same footing as a lease start when the
# band is read, and to let the page's calculator DERIVE the lease a subject has left from
# its completion year (Shawn asked for that, 2026-09-08).
#
# THE ENGINE ASSUMES 6 YEARS. THE MARKET TAKES 4. Across every leasehold development with
# both dates on record the median gap is 4 years, quartiles 4-5, and 565 of 573 are 99-year
# leases -- so lease left = 99 - (this year - TOP) - 4 is a sound default and a poor rule to
# override with an assumption. The tenure answer barely notices which is used ($310 at 6,
# $328 at 4, held-out 267 against 269), so this is about being right rather than about the
# headline.
_gaps = sorted(d['completionYear'] - (base[n].get('tenure') or {}).get('leaseStart')
               for n, d in det.items()
               if (base.get(n, {}).get('tenure') or {}).get('type') == 'LH'
               and (base[n]['tenure'] or {}).get('leaseStart') and d.get('completionYear')
               and -5 < d['completionYear'] - base[n]['tenure']['leaseStart'] < 30)
_terms = collections.Counter((v.get('tenure') or {}).get('years') for v in base.values()
                             if (v.get('tenure') or {}).get('type') == 'LH')
BUILD_YEARS = int(st.median(_gaps))
LEASE_TERM  = _terms.most_common(1)[0][0]
CONSTRUCTION_YEARS = BUILD_YEARS
BUILD = dict(median=BUILD_YEARS, n=len(_gaps), p25=_gaps[len(_gaps)//4],
             p75=_gaps[3*len(_gaps)//4], engine=6, term=LEASE_TERM,
             term_share=_terms[LEASE_TERM]/sum(_terms.values()))

import cut                      # THE PINNED CUT — a crawl must not move the figures
LAST = cut.last_month(psf)      # Shawn, 2026-09-10: the study is a dated cut, not a live feed
NOW  = int(LAST[:4])
def months_back(mo, n):
    y, m = map(int, mo.split('-')); t = y*12 + m - 1 - n
    return f'{t//12:04d}-{t%12+1:02d}'
CUT = months_back(LAST, WINDOW - 1)

def universe(min_units):
    P, rej = {}, collections.Counter()
    for p in projs:
        n = p['project']; b = base.get(n)
        if not b: rej['no tenure record'] += 1; continue
        t = b.get('tenure') or {}
        if t.get('type') not in ('FH', 'LH'): rej['tenure unknown'] += 1; continue
        d = det.get(n) or {}
        if (d.get('totalUnits') or 0) < min_units: rej[f'under {min_units} units'] += 1; continue
        if d.get('projectType') == 'Executive Condominium':
            top = d.get('completionYear')
            if not top or NOW - top < EC_PRIVATISE: rej['EC not yet privatised'] += 1; continue
        if not d.get('completionYear'): rej['no TOP year'] += 1; continue
        dist, station = min(((hav(p['lat'], p['lng'], s['lat'], s['lng']), s['name'])
                             for s in mrt if s.get('lat')), default=(None, None))
        if dist is None: rej['no MRT fix'] += 1; continue
        ls, yrs = t.get('leaseStart'), t.get('years')
        # remaining lease, LEASEHOLD ONLY. 999-yr stock is freehold by his ruling and its
        # 1827 lease start is not a remaining-lease reading of anything.
        left = (ls + yrs - NOW) if (t['type'] == 'LH' and ls and yrs) else None
        P[n] = dict(name=n, lat=p['lat'], lng=p['lng'], region=p['region'], district=p['district'],
                    ty=t['type'], ls=ls, years=yrs, left=left, units=d['totalUnits'],
                    top=d['completionYear'], station=station,
                    schools=frozenset(s['name'] for s in schools
                                      if hav(p['lat'], p['lng'], s['lat'], s['lng']) <= SCHOOL_KM))
    return P, rej

def cell(name, bed):
    s, q = psf.get(name, {}).get(bed), qh.get(name, {}).get(bed)
    if not s or not q: return None
    ms = [m for m in s if CUT <= m <= LAST and m in q]
    if not ms: return None
    n = sum(q[m][2] for m in ms)
    if n < MIN_N: return None
    return dict(psf=st.median([s[m] for m in ms]), n=n, sqft=st.median([q[m][1] for m in ms]))

def build(P, radius, kind):
    """kind: 'mixed' (FH vs LH), 'FH' (FH vs FH placebo), 'LH' (LH vs LH placebo).

    In a placebo there is no freehold side, so the 'fh' slot is assigned AT RANDOM by
    placebo(), which runs it many times and averages. A NAME SORT is NOT neutral: it read
    +2.9% on the FH x FH set purely because alphabetically-earlier freeholds happened to sit
    newer. That is not an estimator bias -- randomising the slot brings the same set back to
    about -0.7%. A correct estimator must read zero on both placebos."""
    rows = []
    for a, b in itertools.combinations(sorted(P), 2):
        A, B = P[a], P[b]
        if kind == 'mixed' and A['ty'] == B['ty']: continue
        if kind in ('FH', 'LH') and not (A['ty'] == B['ty'] == kind): continue
        d = hav(A['lat'], A['lng'], B['lat'], B['lng'])
        if d > radius: continue
        if A['station'] != B['station']: continue
        if A['schools'] != B['schools']: continue
        fh, lh = (A, B) if (A['ty'] == 'FH' if kind == 'mixed' else True) else (B, A)
        for bd in BEDS:
            cf, cl = cell(fh['name'], bd), cell(lh['name'], bd)
            if not cf or not cl: continue
            sd = abs(cf['sqft'] - cl['sqft']) / max(cf['sqft'], cl['sqft'])
            if sd > SIZE_TOL: continue
            rows.append(dict(fh=fh['name'], lh=lh['name'], pair=f'{fh["name"]}|{lh["name"]}',
                             bed=bd, region=A['region'], station=A['station'], metres=round(d),
                             top_fh=fh['top'], top_lh=lh['top'], dv=fh['top'] - lh['top'],
                             left=lh['left'], ls_lh=lh['ls'], yrs_lh=lh['years'],
                             units_fh=fh['units'], units_lh=lh['units'],
                             psf_fh=cf['psf'], psf_lh=cl['psf'],
                             n_fh=cf['n'], n_lh=cl['n'],
                             sqft_fh=cf['sqft'], sqft_lh=cl['sqft'], size_delta=sd,
                             band=band_rate(fh['top'], lh['top'])))
    return rows

# ── the estimator ─────────────────────────────────────────────────────────────────────
# Three forms, and the ORDER is one of the things being measured. His question, verbatim:
# "$10psf per year to match TOP followed by 15% premium. OR ... 44psf per year adjustment
# then adjust by 15% premium. Whichever makes more sense."
#
#   va  : vintage first, then a PERCENTAGE premium   pred = (psf_lh + a*dv) * (1+f)
#   av  : the percentage first, then vintage         pred = psf_lh*(1+f) + a*dv
#   dol : vintage, then a DOLLAR premium             pred = psf_lh + a*dv + d   (order-free)
#
# For a DOLLAR premium the order does not exist -- two additions commute. That is itself an
# argument for the dollar form and it is reported as one.

def avals(rows, rate):
    if rate == 'bands':  return [r['band'] for r in rows]
    return [float(rate)] * len(rows)

def solve(rows, a, form):
    y  = [r['psf_fh'] for r in rows]
    x0 = [r['psf_lh'] for r in rows]
    dv = [r['dv'] for r in rows]
    if form == 'va':
        x = [x0[i] + a[i]*dv[i] for i in range(len(rows))]
        den = sum(v*v for v in x)
        return (sum(x[i]*y[i] for i in range(len(rows)))/den - 1) if den else 0.0
    if form == 'av':
        yy = [y[i] - a[i]*dv[i] for i in range(len(rows))]
        den = sum(v*v for v in x0)
        return (sum(x0[i]*yy[i] for i in range(len(rows)))/den - 1) if den else 0.0
    if form == 'dol':
        return st.mean([y[i] - x0[i] - a[i]*dv[i] for i in range(len(rows))])
    if form == 'none':
        return 0.0
    raise ValueError(form)

def predict(rows, a, form, p):
    out = []
    for i, r in enumerate(rows):
        if form == 'va':  out.append((r['psf_lh'] + a[i]*r['dv']) * (1 + p))
        elif form == 'av': out.append(r['psf_lh']*(1 + p) + a[i]*r['dv'])
        elif form == 'dol': out.append(r['psf_lh'] + a[i]*r['dv'] + p)
        else: out.append(r['psf_lh'] + a[i]*r['dv'])
    return out

GRID = [x/2 for x in range(-40, 161)]      # -20 .. +80 psf per year of TOP difference

def fit(rows, rate, form):
    """Returns (a_spec, premium, sse). rate 'free' grid-searches the vintage rate."""
    if rate == 'free':
        best = None
        for cand in GRID:
            a = [cand]*len(rows)
            p = solve(rows, a, form)
            sse = sum((y - r['psf_fh'])**2 for y, r in zip(predict(rows, a, form, p), rows))
            if best is None or sse < best[2]: best = (cand, p, sse)
        return best
    a = avals(rows, rate)
    p = solve(rows, a, form)
    sse = sum((y - r['psf_fh'])**2 for y, r in zip(predict(rows, a, form, p), rows))
    return (rate, p, sse)

def cv(rows, rate, form, fixed=None, reps=30, folds=5, seed=23):
    """Held-out RMSE, folds grouped BY PAIR so a pair's bedrooms never straddle a fold."""
    pairs = sorted({r['pair'] for r in rows})
    rnd, tot, n = random.Random(seed), 0.0, 0
    for rep in range(reps):
        order = pairs[:]; rnd.shuffle(order)
        assign = {p: i % folds for i, p in enumerate(order)}
        for k in range(folds):
            tr = [r for r in rows if assign[r['pair']] != k]
            te = [r for r in rows if assign[r['pair']] == k]
            if not tr or not te: continue
            if fixed is not None:
                a_spec, p = fixed
            else:
                a_spec, p, _ = fit(tr, rate, form)
            a = avals(te, a_spec)
            for yh, r in zip(predict(te, a, form, p), te):
                tot += (yh - r['psf_fh'])**2; n += 1
    return math.sqrt(tot/n) if n else None

def boot(rows, rate, form, B=2000, seed=17):
    """Cluster bootstrap by pair — a pair's bedrooms move together."""
    by = collections.defaultdict(list)
    for r in rows: by[r['pair']].append(r)
    keys, rnd, out = list(by), random.Random(seed), []
    for _ in range(B):
        samp = []
        for _ in range(len(keys)): samp += by[rnd.choice(keys)]
        out.append(fit(samp, rate, form)[1])
    out.sort()
    return out[int(.025*B)], out[int(.975*B)]

def describe(rows):
    return dict(cells=len(rows), pairs=len({r['pair'] for r in rows}),
                devs=len({r['fh'] for r in rows} | {r['lh'] for r in rows}))

# ── run ───────────────────────────────────────────────────────────────────────────────
RATES = [('$40 (engine, mixed pair)', 40.0), ('$10 (engine, freehold age)', 10.0),
         ('lease bands $%.0f/$%.0f' % (BANDR['old'], BANDR['new']), 'bands'),
         ('free', 'free')]
FORMS = [('vintage, then % premium', 'va'), ('% premium, then vintage', 'av'),
         ('vintage, then $ premium', 'dol'), ('vintage only, no premium', 'none')]

P, rej = universe(MIN_UNITS)
MIXED = build(P, RADIUS_M, 'mixed')
PLA_L = build(P, RADIUS_M, 'LH')
PLA_F = build(P, RADIUS_M, 'FH')
D = describe(MIXED)

print(f'\nWINDOW {CUT}..{LAST}   lease bands DERIVED: ${BANDR["old"]:.1f} / ${BANDR["new"]:.1f}')
print(f'universe {len(P)} developments  ' + str(collections.Counter(v["ty"] for v in P.values())))
print(f'MIXED FH x LH: {D["cells"]} cells · {D["pairs"]} pairs · {D["devs"]} developments')
print(f'placebo LH x LH: {describe(PLA_L)}   placebo FH x FH: {describe(PLA_F)}')

print('\n── THE RACE — held-out RMSE (psf), folds grouped by pair ' + '─'*20)
print(f'{"":30s}{"":26s} {"premium":>10s} {"held-out":>10s}')
NULL = cv(MIXED, 0.0, 'none', fixed=(0.0, 0.0))
print(f'{"no adjustment at all":30s}{"":26s} {"—":>10s} {NULL:>10.1f}')
ENG = cv(MIXED, 40.0, 'va', fixed=(40.0, 0.15))
print(f'{"THE ENGINE AS WRITTEN":30s}{"$40/yr then x1.15":26s} {"15.0%":>10s} {ENG:>10.1f}')
RACE = []
for fn, form in FORMS:
    for rn, rate in RATES:
        if form == 'none' and rate == 'free': pass
        rows = MIXED
        a_spec, p, _ = fit(rows, rate, form)
        e = cv(rows, rate, form)
        prem = f'{p:+.1%}' if form in ('va', 'av') else (f'${p:+,.0f}' if form == 'dol' else '—')
        aa = f'${a_spec:,.1f}/yr' if not isinstance(a_spec, str) else rn
        RACE.append(dict(form=fn, key=form, rate=rn, a=a_spec, prem=p, rmse=e))
        print(f'{fn:30s}{aa:26s} {prem:>10s} {e:>10.1f}')

BEST = min(RACE, key=lambda r: r['rmse'])
print(f'\nBEST: {BEST["form"]}  ·  vintage {BEST["rate"]}  ·  premium '
      f'{BEST["prem"]:+.3f}  ·  RMSE {BEST["rmse"]:.1f}')

# headline in BOTH forms, on the ruled vintage rate (lease bands, reused as measured)
HL = {}
for fn, form in (('percent', 'va'), ('percent, applied first', 'av'), ('dollars', 'dol')):
    a_spec, p, _ = fit(MIXED, 'bands', form)
    lo, hi = boot(MIXED, 'bands', form)
    HL[fn] = dict(p=p, lo=lo, hi=hi, rmse=cv(MIXED, 'bands', form))
    unit = (lambda v: f'{v:+.2%}') if form != 'dol' else (lambda v: f'${v:+,.0f}')
    print(f'  headline {fn:24s} {unit(p):>10s}   95% [{unit(lo)}, {unit(hi)}]   RMSE {HL[fn]["rmse"]:.1f}')

# ── DOLLARS OR PERCENT? The scale test, decided the way the lease study decided it ─────
# He left this open: "whether I should adjust by PSF quantum, adjusting by % (for example 10%
# premium or $200 psf add on)". Two readings settle it and they are reported together.
#   1. Held-out error, fold by fold and PAIRED, so the two forms are scored on identical folds.
#   2. Whether the figure holds steady across price levels — the invariance test, below.

def fold_errors(rows, rate, form, reps=40, folds=5, seed=99):
    pairs = sorted({r['pair'] for r in rows}); rnd, per = random.Random(seed), []
    for _ in range(reps):
        order = pairs[:]; rnd.shuffle(order)
        asg = {p: i % folds for i, p in enumerate(order)}
        for k in range(folds):
            tr = [r for r in rows if asg[r['pair']] != k]
            te = [r for r in rows if asg[r['pair']] == k]
            if not tr or not te: continue
            a_spec, p, _ = fit(tr, rate, form)
            per.append(st.mean([(yh - r['psf_fh'])**2
                                for yh, r in zip(predict(te, avals(te, a_spec), form, p), te)]))
    return per

def transfer(keyfn, groups):
    """THE HARDER TEST, and the one that actually settles the scale question.

    Held-out folds are drawn at random, so every fold looks like the sample it came from —
    which is exactly the situation in which an additive and a multiplicative form are hard to
    tell apart. The question that matters is whether a figure TRAVELS: fit it where the stock
    is cheap and ask it about expensive stock, and the wrong form breaks. So fit on two price
    tiers and predict the third, then the same by region."""
    out = []
    for k in groups:
        tr = [r for r in MIXED if keyfn(r) != k]
        te = [r for r in MIXED if keyfn(r) == k]
        if len(te) < 8: continue
        row = dict(group=str(k), n=len(te), base=st.median([r['psf_lh'] for r in te]))
        for nm, form in (('dol', 'dol'), ('pct', 'va')):
            a_spec, pp, _ = fit(tr, 'bands', form)
            row[nm] = pp
            row[nm + '_err'] = math.sqrt(st.mean(
                [(y - r['psf_fh'])**2
                 for y, r in zip(predict(te, avals(te, a_spec), form, pp), te)]))
        out.append(row)
    return out

_q = sorted(r['psf_lh'] for r in MIXED)
_t1, _t2 = _q[len(_q)//3], _q[2*len(_q)//3]
_tier = lambda r: 'cheapest third' if r['psf_lh'] < _t1 else (
    'middle third' if r['psf_lh'] < _t2 else 'dearest third')
TRANSFER = dict(price=transfer(_tier, ['cheapest third', 'middle third', 'dearest third']),
                region=transfer(lambda r: r['region'], ['CCR', 'RCR', 'OCR']))
for nm, rows in TRANSFER.items():
    print(f'\n── TRANSFER — fit without one {nm} group, then predict it ' + '─'*10)
    for r in rows:
        print(f'  {r["group"]:16s} base ${r["base"]:>6,.0f}  dollars {r["dol_err"]:>6.0f} '
              f'(${r["dol"]:,.0f})   percent {r["pct_err"]:>6.0f} ({r["pct"]:+.1%})   '
              f'{"dollars" if r["dol_err"] < r["pct_err"] else "PERCENT"}')
    print(f'  {"average":16s} {"":13s} dollars {st.mean([r["dol_err"] for r in rows]):>6.0f}'
          f'          percent {st.mean([r["pct_err"] for r in rows]):>6.0f}')

_dol, _pct = fold_errors(MIXED, 'bands', 'dol'), fold_errors(MIXED, 'bands', 'va')
_d = [a - b for a, b in zip(_dol, _pct)]
SCALE_T = dict(dol_rmse=math.sqrt(st.mean(_dol)), pct_rmse=math.sqrt(st.mean(_pct)),
               wins=sum(1 for x in _d if x < 0), folds=len(_d),
               t=st.mean(_d) / (st.stdev(_d) / math.sqrt(len(_d))))
print(f'\n── SCALE — dollars vs percent, PAIRED over {SCALE_T["folds"]} identical folds '
      + '─'*8 + f'\n  dollars RMSE {SCALE_T["dol_rmse"]:.1f} · percent {SCALE_T["pct_rmse"]:.1f} · '
      f'dollars win {SCALE_T["wins"]}/{SCALE_T["folds"]} folds · t = {SCALE_T["t"]:.1f}')

SLICES = {}
def slice_fit(rows, tag, keyfn, order=None, key=None, ci=False):
    print(f'\n── {tag} ' + '─'*40)
    g = collections.defaultdict(list)
    for r in rows: g[keyfn(r)].append(r)
    out = []
    for k in (order or sorted(g, key=lambda x: (x is None, x))):
        sel = g.get(k, [])
        row = dict(label=str(k), **describe(sel), thin=len(sel) < 8)
        if row['thin']:
            print(f'  {str(k):22s} {len(sel):>4d} cells   — too thin')
        else:
            _, row['pct'], _ = fit(sel, 'bands', 'va')
            _, row['dol'], _ = fit(sel, 'bands', 'dol')
            row['free_rate'], row['pct_free'], _ = fit(sel, 'free', 'va')
            if ci: row['lo'], row['hi'] = boot(sel, 'bands', 'va', B=800)
            print(f'  {str(k):22s} {row["cells"]:>4d} cells {row["pairs"]:>4d} pairs   '
                  f'{row["pct"]:+7.2%}   ${row["dol"]:+8,.0f}')
        out.append(row)
    if key == 'gradient':
        floors = dict(LEASE_STEPS)
        for x in out: x['min_left'] = floors.get(x['label'])
    if key: SLICES[key] = out
    return g

print('\n(each slice shows the percentage form and the dollar form side by side)')
# The gradient bands. The FLOOR of each is carried into the JSON so the page's calculator
# reads the steps off the measurement instead of restating them.
LEASE_STEPS = [('90+ yrs left', 90), ('75-89 left', 75), ('60-74 left', 60), ('under 60 left', 0)]
def lease_band(r):
    L = r['left']
    if L is None: return None
    return next(nm for nm, lo in LEASE_STEPS if L >= lo)
slice_fit(MIXED, 'THE GRADIENT — premium by the leasehold side\'s REMAINING LEASE', lease_band,
          order=['90+ yrs left', '75-89 left', '60-74 left', 'under 60 left', None],
          key='gradient', ci=True)
qs = sorted(r['psf_lh'] for r in MIXED)
t1, t2 = qs[len(qs)//3], qs[2*len(qs)//3]
slice_fit(MIXED, 'SCALE TEST — does the % or the $ hold steady across price levels?',
          lambda r: 'low psf' if r['psf_lh'] < t1 else ('mid psf' if r['psf_lh'] < t2 else 'high psf'),
          order=['low psf', 'mid psf', 'high psf'], key='scale')
slice_fit(MIXED, 'REGION', lambda r: r['region'], order=['CCR', 'RCR', 'OCR'], key='region')
slice_fit(MIXED, 'BEDROOM (a match, not the answer — diagnostic only)', lambda r: r['bed'],
          order=BEDS, key='bedroom')

print('\n── PLACEBOS — must read zero ' + '─'*30)
def placebo(rows, form, draws=40, seed=5):
    """Average the premium over RANDOM slot assignments — see build()'s docstring."""
    rnd, out = random.Random(seed), []
    for _ in range(draws):
        flip = []
        for r in rows:
            q = dict(r)
            if rnd.random() < .5:
                q['psf_fh'], q['psf_lh'], q['dv'] = r['psf_lh'], r['psf_fh'], -r['dv']
            flip.append(q)
        out.append(fit(flip, 'bands', form)[1])
    out.sort()
    return st.mean(out), out[0], out[-1]

PLACEBO = {}
for nm, rows in (('LH x LH', PLA_L), ('FH x FH', PLA_F)):
    if len(rows) < 8: print(f'  {nm}: too thin'); continue
    m, lo, hi = placebo(rows, 'va')
    md, _, _ = placebo(rows, 'dol')
    d = describe(rows)
    PLACEBO[nm] = dict(pct=m, lo=lo, hi=hi, dol=md, **d)
    print(f'  {nm}  {d["cells"]:>4d} cells {d["pairs"]:>4d} pairs   premium {m:+.2%} '
          f'(over draws {lo:+.2%}..{hi:+.2%})   ${md:+,.0f}')
_, fa, _ = fit(PLA_F, 'free', 'dol')
af, pf, _ = fit(PLA_F, 'free', 'dol')
print(f'  FH x FH freely fitted vintage rate: ${af:,.1f}/yr of TOP difference '
      f'(engine AGE_PSF_PER_YEAR = 10)')

print('\n── SENSITIVITIES (never the headline) ' + '─'*20)
SENS = []
def sens(label, rows):
    d = describe(rows)
    _, fp, _ = fit(rows, 'bands', 'va'); _, dp, _ = fit(rows, 'bands', 'dol')
    SENS.append(dict(label=label, pct=fp, dol=dp, **d))
    print(f'  {label:16s} {d["cells"]:>4d} cells {d["pairs"]:>4d} pairs   {fp:+7.2%}   ${dp:+8,.0f}')
sens(f'{RADIUS_M} m (headline)', MIXED)
for rad in (800, 1000):
    sens(f'{rad} m', build(P, rad, 'mixed'))
for uf in (100, 50):
    P2, _ = universe(uf); sens(f'{uf}-unit floor', build(P2, RADIUS_M, 'mixed'))

# ── THE 200-UNIT FLOOR STANDS, AND HERE IS WHY (Shawn, 2026-09-08) ─────────────────────
# Dropping it to 100 halves the premium, so it had to be explained rather than waved through.
# His reason: "there are little to no transaction volume which might make it inaccurate due to
# lack of volume averages." The data says exactly that. The pairs the lower floor ADDS run on
# a median of 6 sales on the freehold side against 9 in the headline, 93% of them under ten a
# side against 65%, and fitted ALONE they read a directionless +3% — the same "a boutique
# block's PSF is one odd sale" failure the lease study found below its floor. The n>=5 cell
# screen does not save them: five sales is a floor, not a volume.
P100, _ = universe(100)
ADDED = [r for r in build(P100, RADIUS_M, 'mixed')
         if r['pair'] not in {x['pair'] for x in MIXED}]
_, add_p, _ = fit(ADDED, 'bands', 'va'); _, add_d, _ = fit(ADDED, 'bands', 'dol')
FLOOR = dict(added_cells=len(ADDED), added_pairs=len({r['pair'] for r in ADDED}),
             added_pct=add_p, added_dol=add_d,
             n_fh_headline=st.median([r['n_fh'] for r in MIXED]),
             n_fh_added=st.median([r['n_fh'] for r in ADDED]),
             thin_headline=sum(1 for r in MIXED if min(r['n_fh'], r['n_lh']) < 10)/len(MIXED),
             thin_added=sum(1 for r in ADDED if min(r['n_fh'], r['n_lh']) < 10)/len(ADDED))
print(f'  the pairs the 100-unit floor ADDS, fitted alone: {FLOOR["added_pairs"]} pairs   '
      f'{add_p:+.2%}   ${add_d:+,.0f}   median {FLOOR["n_fh_added"]:.0f} freehold sales '
      f'(headline {FLOOR["n_fh_headline"]:.0f}), {FLOOR["thin_added"]:.0%} under ten a side')

json.dump(dict(window=[CUT, LAST], bands=BANDR, band_bound=BAND_BOUND,
               construction_years=CONSTRUCTION_YEARS, build=BUILD, counts=D, race=RACE, headline=HL,
               placebo=PLACEBO, fh_age_rate=af, floor=FLOOR,
               slices=SLICES, sens=SENS, scale_test=SCALE_T, transfer=TRANSFER,
               mixed=MIXED, placebo_lh=PLA_L, placebo_fh=PLA_F,
               null_rmse=NULL, engine_rmse=ENG),
          open(os.path.join(HERE, 'tenure-pairs.json'), 'w'))
print('\nwrote tenure-pairs.json')
