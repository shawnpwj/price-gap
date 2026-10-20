"""Layout plans for the Layout Price Gap page — which unit is which layout, its rooms, and its drawing.

Shawn, 2026-10-20: "save all the layouts, and then what can happen is next time when i select a unit for
price gap analysis, the layout will be placed in automatically when the unit number / size is selected."

The unit number decides, not the size: several layouts often share a size (mirror prints, a utility
variant). Each plan sheet's own schedule ("#02-07 to #11-07") says which stacks and floors are which
layout; the layout study reads those schedules (sheet_ocr.py, reliable) and the rooms (eye-read per base
drawing where done, an OCR draft otherwise). This joins them to the drawings on disk.

Input  layout-study/data/annotations/<dev>.json   layouts{code:{sqft,beds,baths,wc,study,class,sched,drawing}}
       layout-study/out/plans/<dir>/<code>.{jpg,png}  the PropNex sheets
Output kya-maps-calculator/layout-gap/plans.json   {dev:{layouts:{code:{...rooms, img}}, sched:[[stack,lo,hi,code]]}}
       kya-maps-calculator/layout-plans/<dev>/<n>.jpg  each drawing, at most 1600 px, JPEG — OFFLINE SITE ONLY
       (the sheets are PropNex's, recorded "redistribution prohibited"; deploy-maps.mjs never sends this
       folder to the client-facing live project, and git ignores it)

Run:  python3 price-gap/layout-gap/plans.py            every development with a schedule
      python3 price-gap/layout-gap/plans.py <dev> ...   just these (after a crawl batch)
"""
import json, os, glob, sys, subprocess, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ANN = os.path.join(ROOT, 'layout-study', 'data', 'annotations')
SHEETS = os.path.join(ROOT, 'layout-study', 'out', 'plans')
SITE = os.path.join(ROOT, 'kya-maps-calculator')
OUT_JSON = os.path.join(SITE, 'layout-gap', 'plans.json')
OUT_IMG = os.path.join(SITE, 'layout-plans')
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())


def sheet_dir(dev):
    """The folder of sheets for a development: same name, else the longest folder name it starts with
    (affinity-at-serangoon -> affinity, riverfront-residences -> riverfront)."""
    if os.path.isdir(os.path.join(SHEETS, dev)): return os.path.join(SHEETS, dev)
    n = norm(dev); hits = [d for d in os.listdir(SHEETS) if norm(d) and n.startswith(norm(d))]
    return os.path.join(SHEETS, max(hits, key=len)) if hits else None


def stack_key(st):
    """The page reads #10-07 as stack "7": numbers lose their leading zeros, letters stay upper case."""
    st = str(st).strip()
    return str(int(st)) if st.isdigit() else st.upper()


def find_sheet(files, code, drawing):
    stem = lambda f: os.path.splitext(f)[0]
    for want in (code, drawing):
        if not want: continue
        for f in files:
            if stem(f) == want: return f
    for want in (drawing, code.split('\t')[0]):
        if not want: continue
        for f in files:
            if stem(f).split('\t')[0] == want: return f
    return None


def schedule(v):
    """[[stack, lo, hi], ...] from either form a note uses: `sched` rows (the gather sheets), or the early
    studies' `stacks` list with a `floors` range "02-12" (Treasure at Tampines, Parc Esta)."""
    if v.get('sched'): return v['sched']
    st, fl = v.get('stacks'), v.get('floors')
    if not st or not fl: return []
    m = re.match(r'\s*(\d+)\s*-\s*(\d+)', str(fl))
    if not m: return []
    return [[s, int(m.group(1)), int(m.group(2))] for s in st]


def export(only=None):
    out = json.load(open(OUT_JSON)) if (only and os.path.exists(OUT_JSON)) else {}
    missing = []
    for f in sorted(glob.glob(os.path.join(ANN, '*.json'))):
        dev = os.path.basename(f)[:-5]
        if dev.endswith('-tx-layout') or (only and dev not in only): continue
        L = (json.load(open(f)).get('layouts') or {})
        if not isinstance(L, dict) or not any(isinstance(v, dict) and schedule(v) for v in L.values()): continue
        sd = sheet_dir(dev); files = sorted(os.listdir(sd)) if sd else []
        layouts, sched, n = {}, [], 0
        os.makedirs(os.path.join(OUT_IMG, dev), exist_ok=True)
        for code, v in L.items():
            if not isinstance(v, dict) or not schedule(v): continue
            n += 1
            name = code.split('\t')[0].strip()
            src = find_sheet(files, code, v.get('drawing'))
            img = None
            if src:
                img = f'layout-plans/{dev}/{n}.jpg'
                dst = os.path.join(SITE, img)
                if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(os.path.join(sd, src)):
                    subprocess.run(['sips', '-Z', '1600', '-s', 'format', 'jpeg', '-s', 'formatOptions', '80',
                                    os.path.join(sd, src), '--out', dst], check=True, capture_output=True)
            else:
                missing.append((dev, name))
            layouts[name] = {
                'sqft': round(v['sqft']) if v.get('sqft') else None,
                'bed': v.get('beds'), 'bath': v.get('baths'),
                'wc': 1 if v.get('wc') else 0, 'study': 1 if v.get('study') else 0,
                'cls': v.get('class'), 'type': v.get('marketed_type'),
                # rooms read by eye off the drawing, or still the OCR draft
                'eye': bool(v.get('class_read') or v.get('class_ruling') or v.get('rooms_read')),
                'img': img}
            for s in schedule(v):
                try: sched.append([stack_key(s[0]), int(s[1]), int(s[2]), name])
                except (ValueError, TypeError, IndexError): pass
        if layouts: out[dev] = {'layouts': layouts, 'sched': sched}
    json.dump(out, open(OUT_JSON, 'w'), separators=(',', ':'))
    print(f"plans: {len(out)} developments, {sum(len(d['layouts']) for d in out.values())} layouts, "
          f"{sum(1 for d in out.values() for l in d['layouts'].values() if l['img'])} drawings; "
          f"{len(missing)} layouts with no drawing on disk")
    return missing


if __name__ == '__main__':
    export(set(sys.argv[1:]) or None)
