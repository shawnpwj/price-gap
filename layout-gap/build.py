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

# ---------------------------------------------------------------- facing premiums per dev
def facing_premiums(devid):
    """facingType -> resale-market % vs the project baseline, averaged across bands."""
    p=os.path.join(FRES_DIR, devid+'.json')
    if not os.path.exists(p): return None, None
    fr=json.load(open(p)); base=fr.get('baseline'); acc=collections.defaultdict(list)
    for band, rows in (fr.get('bands') or {}).items():
        for r in rows:
            v = r.get('marketDirect'); 
            if v is None: v = r.get('market')
            if v is not None: acc[r['facing']].append(v)
    prem={f: round(statistics.mean(vs),2) for f,vs in acc.items()}
    if base is not None: prem[base]=0.0
    return base, prem

# stack -> facingType, from the facings file (for linking a caveat's stack to a facing)
def stack_facing(devid):
    p=os.path.join(FAC_DIR, devid+'.json')
    if not os.path.exists(p): return {}
    st=(json.load(open(p)).get('stacks') or {})
    return {str(int(k)): v['facingType'] for k,v in st.items() if isinstance(v,dict) and 'facingType' in v}

# ---------------------------------------------------------------- DSI (data.json), by name
DATA = json.load(open(os.path.join(ROOT,'kya-maps-calculator','data.json')))['developments']
DSI_BY_NAME={}
for k,v in DATA.items():
    nm = v.get('name') or k
    DSI_BY_NAME[norm(nm)] = v

# ---------------------------------------------------------------- nearby (price-gap-all), by name + latlng
PGA = json.load(open(os.path.join(ROOT,'price-gap','out','price-gap-all.json')))['developments']
PGA_LIST=[]
for k,v in (PGA.items() if isinstance(PGA,dict) else enumerate(PGA)):
    if v.get('lat') and v.get('lng'):
        PGA_LIST.append(v)

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
                          hasDsi=bool(dsi)))
        if not recent: continue
        # nearby comparable devs (<=2km, same region), by proximity
        nearby=[]
        if lat and lng:
            for v in PGA_LIST:
                if v.get('n') and norm(v['n'])==norm(name): continue
                d=haversine(lat,lng,v['lat'],v['lng'])
                if d>2000: continue
                allpsf=(v.get('beds') or {}).get('All') or {}
                nearby.append(dict(name=v['n'], dist=round(d), region=v.get('r'), tenure=v.get('t'),
                                   leaseFrom=v.get('ls'), top=v.get('top'), units=v.get('u'),
                                   psf=allpsf.get('psf'), mrtMin=(v.get('mrt') or {}).get('min')))
            nearby.sort(key=lambda x:x['dist']); nearby=nearby[:12]
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
                   dsi=(dict(macro=dsi.get('macro'), area=dsi.get('area'),
                             bedrooms=dsi.get('bedrooms'), defaultBedroom=dsi.get('defaultBedroom'),
                             unitSizes=dsi.get('unitSizes')) if dsi else None),
                   nearby=nearby, tx=tx)
        json.dump(shard, open(os.path.join(DEVDIR, devid+'.json'),'w'), separators=(',',':'))
        n_shard+=1
    idx=dict(generatedAt=TODAY.isoformat(),
             constants=dict(floorIslandUpper=ISLAND_UPPER, lowMult=LOW_MULT, lowTop=LOW_TOP,
                            growthAnnualPct=3.0, growthMinMonths=6, maxCompMonths=18,
                            features=FEATURES),
             developments=sorted(index, key=lambda x:(x['name'] or '')))
    json.dump(idx, open(os.path.join(OUT,'index.json'),'w'), separators=(',',':'))
    print(f"wrote {n_shard} dev shards + index ({len(index)} developments)")
    print(f"island floor upper {ISLAND_UPPER}%/floor; features: {list(FEATURES)}")

if __name__=='__main__':
    main()
