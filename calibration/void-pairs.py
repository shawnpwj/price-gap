#!/usr/bin/env python3
"""VOID SPACE — what the extra strata area of a penthouse is actually worth.

    python3 void-pairs.py        # -> void-pairs.json

THE CONSTANT BEING TESTED. The engine has no void constant. `price-gap.ts` works entirely in
psf and restates every comparable as one number, so it charges the void the same as a bedroom:
the implicit constant is 1.00x. A penthouse whose strata area is 20% bigger than the unit
below reads as a 20% bigger home. This script measures what the market actually pays for that
extra area.

THE PAIR. Same project + same block + SAME STACK. A stack is one vertical line of units, so
the top-floor unit sits on the same floor plate as every unit below it. Where the top unit's
strata area is materially larger, the difference is space the floor plate did not gain --
void over the living room, roof terrace, or an oversized private roof. Floor is the only other
variable and it is normalised out.

    marginal psf = (penthouse price - floor-adjusted base price) / extra sqft
    ratio        = marginal psf / base psf         <- the constant. 1.00 = engine.

SOURCE IS NOT THE MAPS REFRESH. The other three scripts read ../../property-analyzer/data/.
This one reads the REALIS unit-level pull held by the floor study, because it is the only
dataset here that carries a UNIT NUMBER -- and without the unit number there is no stack, and
without the stack there is no same-floor-plate pair. Read-only, same as the others.

BOTH TRACKS ARE REPORTED AND THEY NEVER POOL. New sale is the developer's price list -- one
pricing model, deliberate, and the number an advisory client is deciding against at launch.
Resale is what the next buyer pays for the same void. They answer different questions and
[[newlaunch-resale-separate-rosters]] says they do not mix.

THE PLACEBO DECIDES THE ANSWER. The marginal psf is highly leveraged: the extra area is small
relative to the home, so a 2% error in the base comparator moves the marginal psf by 10-15%.
The threat is a top-floor premium that the linear floor step does not capture -- if the top
floor carries a bonus beyond 0.4%/floor, that bonus lands entirely on the void and inflates
the ratio. So the placebo runs the identical machinery on stacks whose top unit is the SAME
SIZE as the units below: no extra area, so the residual should be zero. Whatever it is not is
bias, and the headline is corrected by it.

WHAT THIS CANNOT SEE. REALIS does not say whether the extra area is void, roof terrace or
private roof. All three are strata area on a floor plate that did not grow, and all three are
priced as space you cannot furnish at full height -- so they measure as one thing here. Naming
which is which needs the floor plan, unit by unit. The figure is "extra penthouse area",
and void is a subset of it. Do not quote it as a ceiling-height number without that check.
"""
import json, os, random, statistics as st
from collections import defaultdict
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, '..', '..', 'launch-picker', 'floor-study', 'data')
OUT  = os.path.join(HERE, 'void-pairs.json')

# ---- screens, every one a ruling -------------------------------------------------------
FLOOR_STEP   = 0.004   # 0.4%/floor -- the floor study's own measured all-region median.
MATCH_DAYS   = 270     # base legs must transact within 9 months of the penthouse sale.
SIZE_TOL     = 0.03    # a base leg must be within 3% of the stack's median size.
MIN_BASE     = 3       # 3 base legs, so the comparator is a median and not one caveat.
EXTRA_LO     = 0.10    # under 10% is a bay window or a measurement difference, not a void.
EXTRA_HI     = 0.55    # over 55% is a duplex or a merged whole-floor unit -- a second
                       # floor plate, which is exactly what this pair is built to exclude.
RATIO_CLIP   = (-0.25, 2.5)   # a ratio outside this is the base comparator failing, not a price.

def dt(y): y = int(y); return date(y // 10000, (y // 100) % 100, y % 100)

def load(fn):
    d = json.load(open(os.path.join(SRC, fn)))
    P, B = d['projects'], d['blocks']
    return [dict(proj=P[r[0]], blk=B[r[5]], price=r[1], sqft=r[2], psf=r[3], d=dt(r[4]),
                 fl=r[6], stk=r[7], ten=r[8], dist=r[10], reg=r[11]) for r in d['rows']], d['window']

def stacks_of(rows):
    S = defaultdict(list)
    for r in rows:
        if r['fl'] and r['stk']: S[(r['proj'], r['blk'], r['stk'])].append(r)
    return S

def pairs(rows, lo, hi, want_extra=True):
    """want_extra False = the placebo: top unit the SAME SIZE as the stack below."""
    out = []
    for k, v in stacks_of(rows).items():
        top = max(x['fl'] for x in v)
        ph  = [x for x in v if x['fl'] == top]
        low = [x for x in v if x['fl'] < top]
        if not low: continue
        med  = st.median([x['sqft'] for x in low])
        pool = [x for x in low if abs(x['sqft'] - med) / med <= SIZE_TOL]
        phm  = st.median([x['sqft'] for x in ph]); extra = phm - med; xr = extra / med
        if want_extra:
            if not (lo <= xr <= hi): continue
        else:
            if abs(xr) > SIZE_TOL: continue
        for p in ph:
            base = [x for x in pool if abs((x['d'] - p['d']).days) <= MATCH_DAYS]
            if len(base) < MIN_BASE: continue
            adj  = st.median([x['price'] * (1 + FLOOR_STEP * (top - x['fl'])) for x in base])
            bpsf = adj / med
            rec = dict(proj=k[0], blk=k[1], stk=k[2], dist=p['dist'], reg=p['reg'],
                       ten='FH' if 'Freehold' in p['ten'] or 'freehold' in p['ten'] else 'LH',
                       floor=top, base_sqft=round(med), ph_sqft=round(phm),
                       extra=round(extra), extra_pct=round(xr, 3), n_base=len(base),
                       base_price=round(adj), ph_price=p['price'], base_psf=round(bpsf),
                       ph_psf=round(p['price'] / phm), date=p['d'].isoformat())
            if want_extra:
                m = (p['price'] - adj) / extra
                rec.update(void_psf=round(m), ratio=round(m / bpsf, 4),
                           headline_drop=round(p['price'] / phm / bpsf - 1, 4))
            else:
                rec.update(residual=round(p['price'] / adj - 1, 4))
            out.append(rec)
    return out

def clip(ps): return [p for p in ps if RATIO_CLIP[0] < p['ratio'] < RATIO_CLIP[1]]

def boot(vals, N=6000, seed=7):
    random.seed(seed); n = len(vals)
    ms = sorted(st.median(random.choices(vals, k=n)) for _ in range(N))
    return ms[int(.025 * N)], ms[int(.975 * N)]

def summarise(ps, label):
    rs = [p['ratio'] for p in ps]
    q  = st.quantiles(rs, n=4)
    lo, hi = boot(rs)
    return dict(label=label, pairs=len(ps), devs=len({p['proj'] for p in ps}),
                ratio=round(st.median(rs), 3), lo=round(lo, 3), hi=round(hi, 3),
                p25=round(q[0], 3), p75=round(q[2], 3),
                discount=round(100 * (1 - st.median(rs)), 1),
                void_psf=round(st.median([p['void_psf'] for p in ps])),
                base_psf=round(st.median([p['base_psf'] for p in ps])),
                extra=round(st.median([p['extra'] for p in ps])),
                extra_pct=round(st.median([p['extra_pct'] for p in ps]), 3),
                headline_drop=round(100 * st.median([p['headline_drop'] for p in ps]), 1))

def cut(ps, key, buckets, label):
    rows = []
    for name, fn in buckets:
        s = [p for p in ps if fn(p)]
        if len(s) < 12: continue
        r = summarise(s, name); r['cut'] = label; rows.append(r)
    return rows

def sensitivity(rows, lo, hi):
    """Re-run the whole thing at other floor steps. If the answer moves with the assumption,
    it is the assumption's answer, not the market's."""
    global FLOOR_STEP
    keep, out = FLOOR_STEP, []
    for fs in (0.003, 0.004, 0.005, 0.006):
        FLOOR_STEP = fs
        ps = clip(pairs(rows, lo, hi))
        out.append(dict(floor_step=fs, pairs=len(ps),
                        ratio=round(st.median([p['ratio'] for p in ps]), 3)))
    FLOOR_STEP = keep
    return out

# ---- run -------------------------------------------------------------------------------
NS, WIN = load('realis-newsale-all-sg.json')
RS, _   = load('realis-resale-all-sg.json')

res = {'meta': dict(
    source='REALIS residential transaction search, ALL Singapore, strata, Apartment+Condominium',
    held_by='launch-picker/floor-study/data/ (unit-level: the only local pull with a unit number)',
    window=WIN, floor_step=FLOOR_STEP, match_days=MATCH_DAYS, size_tol=SIZE_TOL,
    min_base=MIN_BASE, extra_band=[EXTRA_LO, EXTRA_HI], engine_constant=1.00,
    generated=date.today().isoformat())}

for track, rows in (('newsale', NS), ('resale', RS)):
    ps = clip(pairs(rows, EXTRA_LO, EXTRA_HI))
    pl = pairs(rows, EXTRA_LO, EXTRA_HI, want_extra=False)
    pl = [p for p in pl if abs(p['residual']) < .35]
    resid = st.median([p['residual'] for p in pl]) if len(pl) >= 12 else 0.0
    plo, phi = boot([p['residual'] for p in pl]) if len(pl) >= 12 else (0, 0)

    # placebo correction: strip the unexplained top-floor bonus off the penthouse leg first.
    corr = []
    for p in ps:
        m = (p['ph_price'] / (1 + resid) - p['base_price']) / p['extra']
        c = dict(p); c['ratio'] = round(m / p['base_psf'], 4); c['void_psf'] = round(m)
        if RATIO_CLIP[0] < c['ratio'] < RATIO_CLIP[1]: corr.append(c)

    devs = defaultdict(list)
    for p in ps: devs[p['proj']].append(p)

    res[track] = dict(
        headline   = summarise(ps, 'all'),
        corrected  = summarise(corr, 'placebo-corrected'),
        placebo    = dict(pairs=len(pl), devs=len({p['proj'] for p in pl}),
                          residual_pct=round(100 * resid, 2),
                          lo=round(100 * plo, 2), hi=round(100 * phi, 2)),
        sensitivity= sensitivity(rows, EXTRA_LO, EXTRA_HI),
        cuts       = (cut(ps, 'x', [('10-17% of the floor plate', lambda p: p['extra_pct'] < .175),
                                    ('17-25%',  lambda p: .175 <= p['extra_pct'] < .25),
                                    ('25-35%',  lambda p: .25 <= p['extra_pct'] < .35),
                                    ('35-55%',  lambda p: p['extra_pct'] >= .35)], 'extra area')
                    + cut(ps, 'reg', [(g, (lambda g: lambda p: p['reg'] == g)(g))
                                      for g in sorted({p['reg'] for p in ps})], 'region')
                    + cut(ps, 'bpsf', [('under $1,500 psf', lambda p: p['base_psf'] < 1500),
                                       ('$1,500-2,000',     lambda p: 1500 <= p['base_psf'] < 2000),
                                       ('$2,000-2,600',     lambda p: 2000 <= p['base_psf'] < 2600),
                                       ('over $2,600',      lambda p: p['base_psf'] >= 2600)], 'price tier')
                    + cut(ps, 'ten', [('Leasehold', lambda p: p['ten'] == 'LH'),
                                      ('Freehold',  lambda p: p['ten'] == 'FH')], 'tenure')),
        devs       = sorted((dict(proj=k, dist=v[0]['dist'], reg=v[0]['reg'], pairs=len(v),
                                  base_sqft=round(st.median([x['base_sqft'] for x in v])),
                                  ph_sqft=round(st.median([x['ph_sqft'] for x in v])),
                                  extra=round(st.median([x['extra'] for x in v])),
                                  base_psf=round(st.median([x['base_psf'] for x in v])),
                                  void_psf=round(st.median([x['void_psf'] for x in v])),
                                  ratio=round(st.median([x['ratio'] for x in v]), 3),
                                  spread=round(max(x['ratio'] for x in v) - min(x['ratio'] for x in v), 3),
                                  year=st.median([int(x['date'][:4]) for x in v]))
                             for k, v in devs.items() if len(v) >= 2), key=lambda r: r['ratio']),
        pairs      = sorted(ps, key=lambda p: (p['proj'], p['blk'], p['stk'])))

json.dump(res, open(OUT, 'w'), indent=1)
h, c, pl = res['newsale']['headline'], res['newsale']['corrected'], res['newsale']['placebo']
print(f"wrote {os.path.relpath(OUT, HERE)}")
print(f"  NEW SALE  {h['pairs']} pairs / {h['devs']} devs -> ratio {h['ratio']} ({h['lo']}-{h['hi']})"
      f"  corrected {c['ratio']}  discount {c['discount']}%")
print(f"  placebo   {pl['pairs']} same-size top-floor pairs -> residual {pl['residual_pct']}% "
      f"({pl['lo']} to {pl['hi']})")
r = res['resale']
print(f"  RESALE    {r['headline']['pairs']} pairs / {r['headline']['devs']} devs -> "
      f"ratio {r['headline']['ratio']}  corrected {r['corrected']['ratio']}  "
      f"placebo {r['placebo']['residual_pct']}%")
