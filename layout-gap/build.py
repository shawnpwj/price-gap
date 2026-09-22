"""Layout Price Gap — per-development data shards for the unit-level dashboard.

Assembles, for each development, everything the dashboard needs to price ONE unit:
  * recent resale/sub-sale caveats (floor, stack, sqft, price, date) -> intra-dev exact-size comps
  * the floor step (two-zone ladder, own or island fallback)
  * the facing premium by facingType (resale market, from the stack facing study) where studied
  * the DSI macro/area read (data.json) for the right panel
  * nearby comparable developments (price-gap-all.json) for the inter-dev path
  * the product classes measured for this dev (layout study) for the feature adjustment

Output -> kya-maps-calculator/layout-gap/index.json  (dev list + island constants)
          kya-maps-calculator/layout-gap/dev/<id>.json  (one shard per dev with recent tx)

Shawn, 2026-09-21: intra-dev = #1 exact-same-size, adjust floor + facing; growth 3%/yr pro-rated
only when >6 months apart; exclude anything >1.5 years apart. Works for ANY development; where a
study is missing, fall back to island constants and FLAG it estimated.
"""
import json, os, sqlite3, glob, math, statistics, collections, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB   = os.path.join(ROOT, 'layout-study', 'data', 'layout-study.db')
OUT  = os.path.join(ROOT, 'kya-maps-calculator', 'layout-gap')
DEVDIR = os.path.join(OUT, 'dev')
FAC_DIR = os.path.join(ROOT, 'launch-picker', 'stack-study', 'facings')
FRES_DIR = os.path.join(ROOT, 'launch-picker', 'stack-study', 'results')

TODAY = datetime.date(2026, 9, 21)
CUTOFF_DAYS = 550          # 1.5 years — older comps are never considered (Shawn 2026-09-21)

def ymd_int(s): return int(s[:4]) * 10000 + int(s[5:7]) * 100 + int(s[8:10])
def days_ago(s):
    y,m,d = int(s[:4]),int(s[5:7]),int(s[8:10])
    return (TODAY - datetime.date(y,m,d)).days

def norm(s): return "".join(c for c in (s or "").lower() if c.isalnum())

# ---------------------------------------------------------------- constants
FZONE = json.load(open(os.path.join(ROOT,'layout-study','out','floor-zones.json')))
# The floor step HAS a published range and the page was saying it did not (Shawn, 2026-09-23: "why
# dont we have confidence range? we do have it"). It is the resale floor benchmark's own curve --
# read at the unit's square footage, fair_low..fair_high is the middle half (p25-p75) of what
# comparable projects sustained per floor. The same curve prints the "L5+ fair 0.192-0.489% per
# floor" line on the floor benchmark panel.
_RFB = json.load(open(os.path.join(ROOT,'launch-picker','config','resale-floor-benchmark.json')))
FLOOR_CURVE = [dict(sqft=r['sqft'], rate=r['rate'], fairLo=r['fair_low'], fairHi=r['fair_high'],
                    lo=r['undervalued_below'], hi=r['overvalued_above'], supported=r['supported'])
               for r in _RFB['curve']]
_UPPERS = [v['upper'] for v in FZONE.values() if v.get('upper')]
ISLAND_UPPER = round(statistics.median(_UPPERS), 3)
ISLAND_UPPER_DEVS = len(_UPPERS)
LOW_MULT = 1.87; LOW_TOP = 4
FEAT = json.load(open(os.path.join(ROOT,'layout-study','out','feature-summary.json')))
FEATURES = {}
def _mid(v):
    if isinstance(v,dict): return v.get('point')
    if isinstance(v,list): return v[len(v)//2]  # [lo, point, hi]
    return v
for o in FEAT:
    b=o['feature_alone']
    FEATURES[o['feature']]=dict(pct=round(_mid(b['pct']),2), quantum=round(_mid(b['quantum'])),
                                devs=b.get('developments_n'), pairs=b.get('sale_pairs_exact'))

# ---------------------------------------------------------------- inter-development constants
# The Price Gap calibration study's measured constants, read from the same JSONs the engine
# reads (price-gap/scripts/engine.ts loadMeasured). The page ports engine.adjust() to JS.
CAL = os.path.join(ROOT, 'price-gap', 'calibration')
def _cal(f): return json.load(open(os.path.join(CAL, f)))
def _calibration():
    lease=_cal('lease-pairs.json')['pw']; age=_cal('age-pairs.json')['24']['pw']
    ten=_cal('tenure-pairs.json'); mrt=_cal('mrt-pairs.json'); integ=_cal('integrated-pairs.json')
    grad=sorted([dict(minLeft=g['min_left'], pct=g['pct'], label=g['label'])
                 for g in ten['slices']['gradient']
                 if not g.get('thin') and isinstance(g.get('pct'),(int,float)) and isinstance(g.get('min_left'),(int,float))],
                key=lambda g:-g['minLeft'])
    cut=next((c for c in integ['cuts'] if c.get('headline')), integ['cuts'][-1])
    return dict(
        lease=dict(bound=lease['bound'], pre=lease['pre'], post=lease['post']),
        ageFH=dict(bound=age['bound'], pre=age['pre'], post=age['post']),
        tenure=dict(headline=ten['headline']['percent']['p'], grad=grad),
        mrt=dict(nearM=mrt['near_m'], farM=mrt['far_m'], bands={b['key']: round(b['adj']) for b in mrt['bands']}),
        integrated=round(cut['pct']/100, 4),
        harmonisation=0.07, harmonisationFrom=2023,   # engine.ts: not measured, same in both sets
        screens=_PGA_RAW['screens'])

# ---------------------------------------------------------------- product classes (layout study)
import glob as _glob
def _load_classes():
    """dev slug -> [{'class':..,'sqft':..,'code':..}]  and  classKey -> [{'dev','name','sqft'}]"""
    perdev={}; index=collections.defaultdict(list)
    for f in _glob.glob(os.path.join(ROOT,'layout-study','data','annotations','*.json')):
        b=os.path.basename(f)
        if any(x in b for x in ('tx-layout','-rooms','feature','screen','layouts')): continue
        try: d=json.load(open(f))
        except Exception: continue
        devid=d.get('development_id') or b[:-5]; L=d.get('layouts')
        if not L: continue
        seen={}
        for code,v in L.items():
            cls=v.get('class'); sq=v.get('sqft')
            if not cls: continue
            key=(cls, round(sq) if sq else None)
            if key in seen: continue
            seen[key]=1
            perdev.setdefault(devid,[]).append(dict(cls=cls, sqft=round(sq) if sq else None, code=code))
        for r in perdev.get(devid,[]):
            index[r['cls']].append(dict(dev=devid, sqft=r['sqft']))
    return perdev, index
PERCLASS, CLASSINDEX = _load_classes()

# ---------------------------------------------------------------- facing premiums per dev
def facing_premiums(devid):
    """facingType -> resale-market % vs the project baseline, with the evidence behind it.

    Shawn, 2026-09-23: "aren't you supposed to give a range for the floor and adjustment? you can
    then put at the description 'based on xxx number of transactions'." The study already measures
    a low and a high and counts the pairs; the shard was throwing both away and shipping the point
    alone, so the page had no way to say how firm a figure was. Now it carries pct / pairs / lo / hi.
    """
    p=os.path.join(FRES_DIR, devid+'.json')
    if not os.path.exists(p): return None, None, None
    fr=json.load(open(p)); base=fr.get('baseline')
    # Band `all`, market DIRECT only — the rule in CLAUDE.md ("band `all`, market direct only").
    # The earlier build averaged every band and fell back to the chained market figure.
    prem={}; stats={}
    for r in ((fr.get('bands') or {}).get('all') or []):
        v = r.get('marketDirect')
        if v is None: continue
        prem[r['facing']] = round(v, 2)
        lo, hi = r.get('marketLo'), r.get('marketHi')
        stats[r['facing']] = dict(pct=round(v,2), pairs=r.get('marketDirectPairs'),
                                  lo=None if lo is None else round(lo,2),
                                  hi=None if hi is None else round(hi,2))
    if base is not None:
        prem[base]=0.0
        stats[base]=dict(pct=0.0, pairs=None, lo=None, hi=None, baseline=True)
    return base, prem, stats

# stack -> facingType, from the facings file (for linking a caveat's stack to a facing)
def stack_facing(devid):
    p=os.path.join(FAC_DIR, devid+'.json')
    if not os.path.exists(p): return {}
    st=(json.load(open(p)).get('stacks') or {})
    out={}
    for k,v in st.items():
        if not (isinstance(v,dict) and 'facingType' in v): continue
        try: kk=str(int(k))
        except (ValueError, TypeError): kk=str(k)
        out[kk]=v['facingType']
    return out

def facing_names(devid):
    """facingType -> the name as it DISPLAYS on the stack analysis page."""
    p=os.path.join(FAC_DIR, devid+'.json')
    if not os.path.exists(p): return {}
    st=(json.load(open(p)).get('stacks') or {})
    return {v['facingType']: v.get('facingDisplay') or v['facingType']
            for v in st.values() if isinstance(v,dict) and 'facingType' in v}

# ---------------------------------------------------------------- island facing table
# For a development the facing study has not read, the agent is ASKED for the facing (Shawn,
# 2026-09-22: "if you dont have facing you SHOULD ask for it from the agent"). The answer is priced
# with the facing study's OWN published market table, stack-study/data/facing-market.json — the same
# file and the same figures the Stack Analysis page prints.
#
# It used to be re-derived here as a plain median of each development's band-`all` figure, and it had
# DRIFTED: this table said road + blocked by another development was -2.52% where the study publishes
# -1.56%, and expressway (buffered) -5.20% against the study's -2.60%. Shawn caught the gap from the
# other side on 2026-09-23, asking why a -1.23% premium was printing as -1.2%. A page that re-computes
# a study's headline figure is a page that can disagree with it, so it reads it instead.
#
# NO SCREEN OF OUR OWN (Shawn, 2026-09-23: "all single development except bin should be included").
# The study has already binned what should be binned -- quiet|blocked-neighbour publishes 8 of its 9
# sources, quiet|open-greenery 2 of 3 -- so a second screen here only threw away figures the study
# stands behind. Everything it publishes is priced, single-development entries included; the page
# shows the development count and the pair count so the agent can see how thin one is.
# lo/hi are the study's own range (the union of the developments' bootstrap intervals).
ISLAND_BASE = 'quiet|blocked-own'
MARKET_FACING = os.path.join(ROOT,'launch-picker','stack-study','data','facing-market.json')
def island_facing():
    names={}
    for f in glob.glob(os.path.join(FAC_DIR,'*.json')):
        try: st=json.load(open(f)).get('stacks') or {}
        except Exception: continue
        for v in st.values():
            if isinstance(v,dict) and v.get('facingType') and v.get('facingDisplay'):
                names.setdefault(v['facingType'], v['facingDisplay'])
    out={ISLAND_BASE: dict(pct=0.0, devs=None, pairs=None, lo=None, hi=None,
                           name=names.get(ISLAND_BASE,'Blocked by your own development'), baseline=True)}
    mkt=(json.load(open(MARKET_FACING)).get('facings') or {})
    for k,v in mkt.items():
        if k==ISLAND_BASE: continue
        priced = v.get('market') is not None
        out[k]=dict(pct=round(v['market'],2) if priced else None, devs=v.get('developments'),
                    pairs=v.get('pairs'),
                    lo=round(v['low'],2) if v.get('low') is not None else None,
                    hi=round(v['high'],2) if v.get('high') is not None else None,
                    name=v.get('label') or names.get(k,k))
    return out

# ---------------------------------------------------------------- DSI (data.json), by name
DATA = json.load(open(os.path.join(ROOT,'kya-maps-calculator','data.json')))['developments']
DSI_BY_NAME={}
for k,v in DATA.items():
    nm = v.get('name') or k
    DSI_BY_NAME[norm(nm)] = v

# ---------------------------------------------------------------- nearby (price-gap-all), by name + latlng
_PGA_RAW = json.load(open(os.path.join(ROOT,'price-gap','out','price-gap-all.json')))
PGA = _PGA_RAW['developments']
PGA_LIST=[]
for k,v in (PGA.items() if isinstance(PGA,dict) else enumerate(PGA)):
    if v.get('lat') and v.get('lng'):
        PGA_LIST.append(v)

PGA_BY_NAME = {norm(v['n']): v for v in PGA_LIST if v.get('n')}
def dev_attrs(name):
    """The inter-development attributes, as the Price Gap engine sees them."""
    v = PGA_BY_NAME.get(norm(name)) if name else None
    if not v: return None
    m = v.get('mrt') or {}
    return dict(t=v.get('t'), ls=v.get('ls'), yrs=v.get('yrs'), top=v.get('top'),
                topEst=bool(v.get('topEst')), u=v.get('u'), int=bool(v.get('int')),
                mrtS=m.get('s'), mrtM=m.get('m'), mrtMin=m.get('min'), r=v.get('r'))

def haversine(a,b,c,d):
    R=6371000; p=math.radians
    return 2*R*math.asin(math.sqrt(math.sin(p(c-a)/2)**2+math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2))

# ---------------------------------------------------------------- build
def main():
    os.makedirs(DEVDIR, exist_ok=True)
    db=sqlite3.connect(DB)
    devs={r[0]:r for r in db.execute(
        "select development_id,canonical_name,lat,lng,district,region,segment,tenure_type,"
        "tenure_years,lease_commencement,top_year,unit_count,mrt_station,mrt_distance_m from developments")}
    NAME2ID={}
    for _id,_r in devs.items():
        if _r[1]: NAME2ID[norm(_r[1])]=_id
    cutoff = None  # computed per-row via days_ago
    index=[]
    n_shard=0
    for devid,(_,name,lat,lng,dist,region,seg,ttype,tyrs,lcom,top,units,mrt,mrtd) in devs.items():
        rows=list(db.execute(
            "select floor,stack,sqft,price,caveat_date,sale_type from transactions "
            "where development_id=? and sale_type in ('resale','sub_sale') and exclusion_flags='[]'",(devid,)))
        recent=[r for r in rows if days_ago(r[4])<=CUTOFF_DAYS]
        base_f, fprem, fstats = facing_premiums(devid)
        sf = stack_facing(devid)
        # floor rate
        up = FZONE.get(name.upper()) if name else None
        if up and up.get('upper'):
            # pooled = the same development refitted over ALL floors; the published rate is the
            # L5+ fit with the low-floor multiplier on top. Both are measured here, so the page can
            # show the spread between them rather than quoting one figure with no evidence.
            frate=dict(upper=up['upper'], lowMult=LOW_MULT, lowTop=LOW_TOP, source='own',
                       pairs=up.get('upper_pairs'), pooled=up.get('pooled'),
                       pooledPairs=up.get('pooled_pairs'), ownMult=up.get('own_mult'),
                       lowPairs=up.get('low_pairs'), multSource=up.get('mult_source'))
        else:
            frate=dict(upper=ISLAND_UPPER, lowMult=LOW_MULT, lowTop=LOW_TOP, source='island',
                       pairs=None, devs=ISLAND_UPPER_DEVS, pooled=None, pooledPairs=None,
                       ownMult=None, lowPairs=None, multSource='island')
        dsi = DSI_BY_NAME.get(norm(name)) if name else None
        # index row (always)
        index.append(dict(id=devid, name=name, region=region, district=dist, segment=seg,
                          tenure=ttype, tenureYears=tyrs, leaseFrom=lcom, top=top, units=units,
                          mrt=mrt, mrtM=mrtd, lat=lat, lng=lng,
                          nRecent=len(recent), hasFacing=bool(fprem), floorSource=frate['source'],
                          hasDsi=bool(dsi), pg=dev_attrs(name)))
        if not recent: continue
        # nearby comparable devs (<=2km, same region), by proximity
        nearby=[]
        if lat and lng:
            for v in PGA_LIST:
                if v.get('n') and norm(v['n'])==norm(name): continue
                d=haversine(lat,lng,v['lat'],v['lng'])
                if d>2000: continue
                allpsf=(v.get('beds') or {}).get('All') or {}
                nearby.append(dict(name=v['n'], id=NAME2ID.get(norm(v['n'])), dist=round(d),
                                   region=v.get('r'), tenure=v.get('t'), leaseFrom=v.get('ls'),
                                   top=v.get('top'), units=v.get('u'), psf=allpsf.get('psf'),
                                   mrtMin=(v.get('mrt') or {}).get('min')))
            nearby.sort(key=lambda x:x['dist']); nearby=nearby[:30]
        # transactions, compact: [floor, stack, sqft, price, ymd, saleType(0=resale,1=subsale), facingType|null]
        def stkey(st):
            try: return str(int(st))
            except (ValueError, TypeError): return str(st)
        tx=[]
        for fl,st,sq,pr,cd,sty in recent:
            k=stkey(st)
            tx.append([fl, k, round(sq), int(pr), ymd_int(cd), 0 if sty=='resale' else 1, sf.get(k)])
        shard=dict(id=devid, name=name, region=region, district=dist, tenure=ttype, tenureYears=tyrs,
                   leaseFrom=lcom, top=top, units=units, mrt=mrt, mrtM=mrtd,
                   floorRate=frate, baselineFacing=base_f, facingPremiums=fprem, facingStats=fstats,
                   facingNames=facing_names(devid) or None, stackFacing=sf or None,
                   pg=dev_attrs(name),
                   dsi=(dict(macro=dsi.get('macro'), area=dsi.get('area'),
                             bedrooms=dsi.get('bedrooms'), defaultBedroom=dsi.get('defaultBedroom'),
                             unitSizes=dsi.get('unitSizes')) if dsi else None),
                   layoutClasses=PERCLASS.get(devid), nearby=nearby, tx=tx)
        json.dump(shard, open(os.path.join(DEVDIR, devid+'.json'),'w'), separators=(',',':'))
        n_shard+=1
    idx=dict(generatedAt=TODAY.isoformat(),
             constants=dict(floorIslandUpper=ISLAND_UPPER, lowMult=LOW_MULT, lowTop=LOW_TOP,
                            # growthTaperFrom / growthMinMonths: no time adjustment under 3 months, the rate tapering in
                            # to the full figure at 6 months (Shawn, 2026-09-23 — replaces the 6-month cliff)
                            growthAnnualPct=3.0, growthTaperFrom=3, growthMinMonths=6, maxCompMonths=18,
                            features=FEATURES, inter=_calibration(), facingIsland=island_facing(),
                            floorCurve=FLOOR_CURVE),
             developments=sorted(index, key=lambda x:(x['name'] or '')))
    json.dump(idx, open(os.path.join(OUT,'index.json'),'w'), separators=(',',':'))
    json.dump({k:v for k,v in CLASSINDEX.items()}, open(os.path.join(OUT,'class-index.json'),'w'), separators=(',',':'))
    print(f"wrote {n_shard} dev shards + index ({len(index)} developments)")
    print(f"island floor upper {ISLAND_UPPER}%/floor; features: {list(FEATURES)}")

if __name__=='__main__':
    main()
