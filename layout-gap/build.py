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
ISLAND_UPPER = round(statistics.median([v['upper'] for v in FZONE.values() if v.get('upper')]), 3)
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
    """facingType -> resale-market % vs the project baseline, averaged across bands."""
    p=os.path.join(FRES_DIR, devid+'.json')
    if not os.path.exists(p): return None, None
    fr=json.load(open(p)); base=fr.get('baseline')
    # Band `all`, market DIRECT only — the rule in CLAUDE.md ("band `all`, market direct only").
    # The earlier build averaged every band and fell back to the chained market figure.
    prem={}
    for r in ((fr.get('bands') or {}).get('all') or []):
        v = r.get('marketDirect')
        if v is not None: prem[r['facing']] = round(v, 2)
    if base is not None: prem[base]=0.0
    return base, prem

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
# 2026-09-22: "if you dont have facing you SHOULD ask for it from the agent"). The answer is
# priced with this table: each facingType's median across the studied developments, band `all`,
# market DIRECT only, all measured against the same baseline (quiet|blocked-own = 0). Measured
# elsewhere on other pairs, never fitted to the pairs being priced. Fewer than 2 developments =
# no island figure (listed so the agent can still answer, but not priced).
ISLAND_BASE = 'quiet|blocked-own'
def island_facing():
    acc=collections.defaultdict(list); names={}
    for f in glob.glob(os.path.join(FRES_DIR,'*.json')):
        fr=json.load(open(f))
        if fr.get('baseline')!=ISLAND_BASE: continue
        for r in ((fr.get('bands') or {}).get('all') or []):
            if r.get('marketDirect') is not None and r['facing']!=ISLAND_BASE:
                acc[r['facing']].append(r['marketDirect'])
    for f in glob.glob(os.path.join(FAC_DIR,'*.json')):
        try: st=json.load(open(f)).get('stacks') or {}
        except Exception: continue
        for v in st.values():
            if isinstance(v,dict) and v.get('facingType') and v.get('facingDisplay'):
                names.setdefault(v['facingType'], v['facingDisplay'])
    out={ISLAND_BASE: dict(pct=0.0, devs=None, name=names.get(ISLAND_BASE,'Blocked by your own development'), baseline=True)}
    for k,vs in acc.items():
        out[k]=dict(pct=round(statistics.median(vs),2) if len(vs)>=2 else None, devs=len(vs), name=names.get(k,k))
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
        base_f, fprem = facing_premiums(devid)
        sf = stack_facing(devid)
        # floor rate
        up = FZONE.get(name.upper()) if name else None
        if up and up.get('upper'):
            frate=dict(upper=up['upper'], lowMult=LOW_MULT, lowTop=LOW_TOP, source='own', pairs=up.get('upper_pairs'))
        else:
            frate=dict(upper=ISLAND_UPPER, lowMult=LOW_MULT, lowTop=LOW_TOP, source='island', pairs=None)
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
                   floorRate=frate, baselineFacing=base_f, facingPremiums=fprem,
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
                            growthAnnualPct=3.0, growthMinMonths=6, maxCompMonths=18,
                            features=FEATURES, inter=_calibration(), facingIsland=island_facing()),
             developments=sorted(index, key=lambda x:(x['name'] or '')))
    json.dump(idx, open(os.path.join(OUT,'index.json'),'w'), separators=(',',':'))
    json.dump({k:v for k,v in CLASSINDEX.items()}, open(os.path.join(OUT,'class-index.json'),'w'), separators=(',',':'))
    print(f"wrote {n_shard} dev shards + index ({len(index)} developments)")
    print(f"island floor upper {ISLAND_UPPER}%/floor; features: {list(FEATURES)}")

if __name__=='__main__':
    main()
