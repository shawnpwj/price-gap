"""Internal — Constant Calibration › Layout.

Shawn, 2026-09-18: "i need you to capture all of these data and information somewhere
for me to read and vet through, can you put it in calibration inside 'internal -
constant calbiration' for my own hidden reference?"

Everything the layout-feature study has measured at Treasure at Tampines, laid out to be
audited: the matching rule, every published contrast, every rejected one and why, the
same-package area steps, the bedroom-tier jumps, and the measured room areas.

Reads the layout-study outputs. Nothing here is computed; this is a window onto that repo.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.abspath(os.path.join(HERE, '..', '..', 'layout-study'))

def _load(p, default=None):
    f = os.path.join(STUDY, p)
    if not os.path.exists(f): return default
    return json.load(open(f))

PAIRS  = _load('out/library-layout-pairs.json', [])
STEPS  = _load('out/same-package-area-steps.json', [])
JUMPS  = _load('out/bedroom-jumps.json', [])
EDGES  = _load('out/tier-edge-jumps.json', [])
ROOMS  = _load('data/annotations/room-areas.json', {}) or {}
LAY    = (_load('data/annotations/treasure-at-tampines.json', {}) or {}).get('layouts', {})

def _money(v, sign=False):
    if v is None: return '&mdash;'
    s = f'{abs(v):,.0f}'
    if v < 0: return '&minus;$' + s
    return ('+$' if sign else '$') + s

def _ci(lo, hi):
    if lo is None or hi is None: return '&mdash;'
    return _money(lo) + ' to ' + _money(hi)

BAND = {'COMPARABLE': ('ok', 'publishable'),
        'AREA_ONLY': ('ok', 'publishable &mdash; pure area step'),
        'NEEDS_ROOM_MEASUREMENT': ('warn', 'not publishable &mdash; unexplained area'),
        'NOT_COMPARABLE': ('bad', 'rejected')}

def pairs_table():
    if not PAIRS: return '<p class="expl">layout-study outputs not found.</p>'
    groups = {}
    for r in PAIRS:
        groups.setdefault(r['comparability'].split(' (')[0], []).append(r)
    out = []
    for key in ('COMPARABLE', 'AREA_ONLY', 'NEEDS_ROOM_MEASUREMENT', 'NOT_COMPARABLE'):
        rs = groups.get(key)
        if not rs: continue
        cls, note = BAND[key]
        out.append(f'<tr class="grp {cls}"><td colspan="8"><b>{key.replace("_"," ")}</b> '
                   f'&mdash; {note}</td></tr>')
        for r in sorted(rs, key=lambda x: -x['pairs']):
            out.append(
                '<tr>'
                f'<td>{r["base_layout"]} &rarr; {r["feature_layout"]}</td>'
                f'<td class="num">{r["base_sqft"]:,} &rarr; {r["feature_sqft"]:,}</td>'
                f'<td class="num pad">{r["delta_sqft"]:+}</td>'
                f'<td class="num pad">{r["pairs"]}</td>'
                f'<td class="num"><b>{_money(r["premium_sgd"])}</b></td>'
                f'<td class="num">{r["premium_pct"]}%</td>'
                f'<td class="num">{_ci(r["ci95_low"], r["ci95_high"])}</td>'
                f'<td>{r["feature_difference"]}</td></tr>')
    return ('<table class="t"><thead><tr><th>pair</th><th class="num">sqft step</th>'
            '<th class="num pad">&Delta;sf</th><th class="num pad">pairs</th>'
            '<th class="num">premium</th><th class="num">%</th>'
            '<th class="num">95% CI</th><th>what differs</th></tr></thead><tbody>'
            + ''.join(out) + '</tbody></table>')

def steps_table():
    if not STEPS: return '<p class="expl">no same-package steps computed.</p>'
    def ld(c):
        r = ROOMS.get('layouts', {}).get(c, {}).get('rooms', {})
        return (r.get('living', 0) + r.get('dining', 0)) or None
    rows = []
    for s in sorted(STEPS, key=lambda x: x['delta_sqft']):
        a, b = s['base_layout'], s['feature_layout']
        la, lb = ld(a), ld(b)
        dl = f'{lb-la:+}' if (la and lb) else '&mdash;'
        rows.append('<tr>'
            f'<td>{a} &rarr; {b}</td>'
            f'<td class="num">{s["base_sqft"]:,} &rarr; {s["feature_sqft"]:,}</td>'
            f'<td class="num">{s["delta_sqft"]:+}</td>'
            f'<td class="num">{dl}</td>'
            f'<td class="num">{s["pairs"]}</td>'
            f'<td class="num"><b>{_money(s["med"])}</b></td>'
            f'<td class="num">{s["pct"]}%</td>'
            f'<td class="num">{_ci(s["ci"][0], s["ci"][1])}</td></tr>')
    return ('<table class="t"><thead><tr><th>pair</th><th class="num">sqft step</th>'
            '<th class="num">&Delta; total</th><th class="num">&Delta; living+dining</th>'
            '<th class="num">pairs</th><th class="num">median</th><th class="num">%</th>'
            '<th class="num">95% CI</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>')

def jumps_table():
    rows = []
    for j in EDGES or []:
        rows.append('<tr class="grp ok"><td colspan="6"><b>tier edge</b> &mdash; '
                    f'{j["jump"]}</td></tr>')
        rows.append(f'<tr><td>biggest &rarr; smallest of next tier</td>'
                    f'<td class="num">{j["base_sqft"]:,} &rarr; {j["feature_sqft"]:,}</td>'
                    f'<td class="num">{j["pairs"]}</td>'
                    f'<td class="num">{_money(j["base"])}</td>'
                    f'<td class="num"><b>{_money(j["med"])}</b></td>'
                    f'<td class="num">{j["pct"]}%</td></tr>')
    for j in JUMPS or []:
        rows.append(f'<tr><td>{j["jump"]}</td><td class="num">&mdash;</td>'
                    f'<td class="num">{j["pairs"]}</td>'
                    f'<td class="num">{_money(j["base"])}</td>'
                    f'<td class="num"><b>{_money(j["med"])}</b></td>'
                    f'<td class="num">{j["pct"]}%</td></tr>')
    return ('<table class="t"><thead><tr><th>jump</th><th class="num">sqft</th>'
            '<th class="num">pairs</th><th class="num">base quantum</th>'
            '<th class="num">premium</th><th class="num">%</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table>')

ROOM_ORDER = ['living', 'dining', 'master', 'bedroom_1', 'bedroom_2', 'bedroom_3', 'bedroom_4',
              'bath_1', 'bath_2', 'wc', 'kitchen', 'yard', 'household_shelter', 'store',
              'balcony', 'balcony_2', 'ac_ledge']
def rooms_table():
    L = ROOMS.get('layouts', {})
    if not L: return '<p class="expl">no room measurements yet.</p>'
    cols = [c for c in ROOM_ORDER if any(c in v['rooms'] for v in L.values())]
    head = ''.join(f'<th class="num">{c.replace("_"," ")}</th>' for c in cols)
    rows = []
    for c, v in sorted(L.items(), key=lambda kv: kv[1]['sqft']):
        cells = ''.join(f'<td class="num">{v["rooms"].get(k) or "&mdash;"}</td>' for k in cols)
        rows.append(f'<tr><td><b>{c}</b></td><td class="num">{v["sqft"]:,}</td>'
                    f'<td class="num">{v.get("baths","&mdash;")}</td>{cells}</tr>')
    return ('<div class="scroll"><table class="t"><thead><tr><th>layout</th>'
            '<th class="num">strata</th><th class="num">baths</th>' + head
            + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')

def headline_steps():
    """The two 21 sqft steps that carry the section. B4P -> 678 class comes from the LIBRARY
    (the four 678 layouts combined, 36 pairs); B4P -> B5P alone is too thin to stand."""
    up = next((r for r in PAIRS if r['base_layout']=='B4P'
               and r['feature_layout']=='678class'), None)
    down = next((x for x in STEPS if x['base_layout']=='C8P'
                 and x['feature_layout']=='C9P'), None)
    return (_money(up['premium_sgd'], sign=True) if up else '&mdash;',
            _money(down['med'], sign=True) if down else '&mdash;')

def counts():
    L = ROOMS.get('layouts', {})
    pub = [r for r in PAIRS if r['comparability'].split(' (')[0] in ('COMPARABLE', 'AREA_ONLY')]
    return dict(layouts=len(LAY), measured=len(L), pairs=len(PAIRS), publishable=len(pub),
                rejected=len([r for r in PAIRS
                              if r['comparability'].startswith('NOT_COMPARABLE')]))
