"""Future launches for the Layout Price Gap page — the GLS sites not yet launched, and the size a new unit of
each bedroom type is built at today.

Shawn, 2026-10-22: "we SHOULD allow for FUTURE new launches land plot to be included as part of the price
gap ... use current harmonized 4BR sizes ... allow selection options from agents, to allow the projection
on FUTURE PRICING ... show details like, buying price, number of developers, breakeven price and then
projected selling price range. and use midpoint." Rulings the same day: the launch is restated ONTO this
unit (as every other comparison on the page); the size is the REGION median (OCR / RCR / CCR) of recent
private launches, "doesnt have to be the nearest"; no time step — it is launch-year pricing.

Input  property-analyzer/data/gls-forward.json            the GLS sheet: land psf, bids, developer, breakeven,
                                                           projected launch psf low / mid / high
       kya-maps-calculator/upcoming-launch-projections.json  each site's nearest station (where it has one)
       property-analyzer/data/mrt-stations.json            otherwise the nearest operational station
       property-analyzer/data/launch-unit-mix-raw.json     recent launches' PropNex categories, sizes, units
       kya-maps-calculator/layout-gap/index.json           each launch's region
Output kya-maps-calculator/layout-gap/gls.json

The launch sizes are post-harmonisation floor areas, compared quantum to quantum with this unit's sale or
asking price — never put on a per-square-foot basis. ECs are left out of the private medians.

Run:  python3 price-gap/layout-gap/gls.py
"""
import json, os, re, math, statistics, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PA = os.path.join(ROOT, 'property-analyzer', 'data')
SITE = os.path.join(ROOT, 'kya-maps-calculator')
J = lambda *p: json.load(open(os.path.join(*p)))
norm = lambda s: re.sub(r'[^a-z0-9]', '', re.sub(r'^the\s+', '', (s or '').lower()))


def haversine(a, b, c, d):
    r = math.radians
    x = math.sin(r(c - a) / 2) ** 2 + math.cos(r(a)) * math.cos(r(c)) * math.sin(r(d - b) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(x))


def year_of(s):
    m = re.search(r'(\d{2,4})\s*$', (s or '').strip())
    if not m: return None
    y = int(m.group(1)); return y + 2000 if y < 100 else y


gls = J(PA, 'gls-forward.json')['sites']
proj = J(SITE, 'upcoming-launch-projections.json')['projects']
stations = [s for s in J(PA, 'mrt-stations.json')['stations'] if s.get('status') == 'operational']

sites = []
for s in gls:
    if s.get('launched') or not s.get('projectedPsf') or s.get('lat') is None: continue
    if s.get('type') == 'ec': continue                       # an EC is a different product; the page values private units
    p = proj.get(s['displayName']) or {}
    mrt = p.get('mrt')
    if mrt and mrt.get('distM') is not None:
        mrt = dict(name=mrt.get('name'), rail=mrt.get('rail'), distM=round(mrt['distM']))
    else:
        best = min(stations, key=lambda t: haversine(s['lat'], s['lng'], t['lat'], t['lng']))
        mrt = dict(name=re.sub(r' (MRT|LRT) Station$', '', best['name']), rail='LRT' if 'LRT' in best['name'] else 'MRT',
                   distM=round(haversine(s['lat'], s['lng'], best['lat'], best['lng'])))
    award = year_of(s.get('awardDate')) if s.get('awarded') else None
    launch = int(s['launchYear']) if str(s.get('launchYear') or '').isdigit() else None
    sites.append(dict(
        id='gls-' + re.sub(r'[^a-z0-9]+', '-', s['displayName'].lower()).strip('-'),
        name=s['displayName'], site=s.get('siteName'), devName=s.get('devName') or None,
        lat=s['lat'], lng=s['lng'], region=s.get('region'), units=s.get('units'), type=s.get('type'),
        camp=s.get('camp'), awarded=bool(s.get('awarded')), awardDate=s.get('awardDate'), launchYear=launch,
        # the lease runs from the award; a site not yet tendered is taken as awarded the year before launch
        leaseFrom=award or (launch - 1 if launch else None), leaseEst=award is None,
        purchasePsf=s.get('purchasePsf'), breakevenPsf=s.get('breakevenPsf'),
        developer=s.get('developer'), bidders=s.get('bidders'),
        proj=s['projectedPsf'], mrt=mrt))

# recent launches' unit sizes, by region and PropNex category, private only
raw = J(PA, 'launch-unit-mix-raw.json')['launches']
gi = {}
for s in gls:
    for k in (s.get('devName'), s.get('displayName')):
        if k: gi[norm(k)] = s
ii = {norm(d['name']): d for d in J(SITE, 'layout-gap', 'index.json')['developments'] if d.get('name')}
cats = {}
for name, d in raw.items():
    g = gi.get(norm(name)) or gi.get(norm(d.get('appName')))
    if g and g.get('type') == 'ec': continue
    dv = ii.get(norm(name)) or ii.get(norm(d.get('appName')))
    region = (dv or {}).get('segment') or (g or {}).get('region')
    if not region: continue
    for r in d['rows']:
        cat = re.sub(r'\s+', ' ', r['type']).strip().upper().replace('WITH STUDY, PENTHOUSE', 'PENTHOUSE, WITH STUDY')
        if 'PENTHOUSE' in cat or 'DUAL KEY' in cat: continue
        cats.setdefault(region, {}).setdefault(cat, []).append(dict(launch=d.get('appName') or name, lo=r['min'], hi=r['max'],
                                                                    mid=round((r['min'] + r['max']) / 2), units=r['units']))
medians = {reg: {c: round(statistics.median(x['mid'] for x in v)) for c, v in cs.items()} for reg, cs in cats.items()}
for reg in cats:
    for c in cats[reg]: cats[reg][c].sort(key=lambda x: x['mid'])

# The same launches by ROOM PACKAGE, off the plans read by eye (layout-study/data/annotations):
# "4BR2B+WC", "4BR3B+WC+S". Shawn, 2026-10-22: match the future unit to this unit's room package,
# not just its bedroom count. Only eye-read layouts count (class_read set); a double-volume strata-void
# print is left out, its area carries the void. A launch's size for a package is the median of its
# layouts of that package; the region figure is the median across launches.
ANN = os.path.join(ROOT, 'layout-study', 'data', 'annotations')
ann = {norm(os.path.splitext(f)[0].replace('-', ' ')): os.path.join(ANN, f) for f in os.listdir(ANN) if f.endswith('.json')}
pkg_key = lambda v: f"{v['beds']}BR{v['baths']}B" + ('+WC' if v.get('wc') else '') + ('+S' if v.get('study') else '')
pkgs = {}
for reg, cs in cats.items():
    for launch in {x['launch'] for v in cs.values() for x in v}:
        p = ann.get(norm(launch))
        if not p: continue
        by = {}
        for v in json.load(open(p))['layouts'].values():
            if not v.get('class_read') or (v.get('beds') or 0) < 2 or v.get('strata_void') or not v.get('sqft'): continue
            if v.get('baths') is None: continue
            by.setdefault(pkg_key(v), []).append(v['sqft'])
        for k, sq in by.items():
            pkgs.setdefault(reg, {}).setdefault(k, []).append(dict(launch=launch, lo=round(min(sq)), hi=round(max(sq)),
                                                                     mid=round(statistics.median(sq)), n=len(sq)))
pkg_medians = {reg: {k: round(statistics.median(x['mid'] for x in v)) for k, v in ks.items()} for reg, ks in pkgs.items()}
for reg in pkgs:
    for k in pkgs[reg]: pkgs[reg][k].sort(key=lambda x: x['mid'])

out = dict(generatedAt=datetime.date.today().isoformat(),
           note='Projected launch psf is the GLS sheet\'s low / mid / high (breakeven +10% / +20% / +30%); '
                'sizes are recent private launches\' PropNex categories, post-harmonisation; packages are the '
                'same launches\' eye-read plans by room package.',
           sites=sites, sizes=cats, medians=medians, packages=pkgs, packageMedians=pkg_medians)
json.dump(out, open(os.path.join(SITE, 'layout-gap', 'gls.json'), 'w'), separators=(',', ':'))
print(f"gls: {len(sites)} future sites; launch sizes for {', '.join(f'{r} {len(c)} categories' for r, c in cats.items())}")
print('medians', {r: {c: m for c, m in v.items() if c in ('2-BEDROOM', '3-BEDROOM', '4-BEDROOM')} for r, v in medians.items()})
