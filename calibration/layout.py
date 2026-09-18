"""Internal — Constant Calibration › Layout.

Shawn, 2026-09-18: "i need you to capture all of these data and information somewhere
for me to read and vet through, can you put it in calibration inside 'internal -
constant calbiration' for my own hidden reference?"

Everything the layout-feature study has measured at Treasure at Tampines, laid out to be
audited: the matching rule, every published contrast, every rejected one and why, the
bedroom-tier jumps and the measured room areas.

Shawn, 2026-09-18: "I dont neeed area only, remove ALL area only." Nothing here shows a
premium for a pair with no feature difference. The area-only diagnostic still exists in
layout-study (out/diagnostic-area-only-steps.json) and is deliberately not read.

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
        'NEEDS_ROOM_MEASUREMENT': ('warn', 'not publishable &mdash; unexplained area'),
        'NOT_COMPARABLE': ('bad', 'rejected')}

def _row(cells, cls=""):
    return f'<tr class="{cls}">' + "".join(cells) + "</tr>"

def pairs_table():
    """One line per pair, with what-differs on its own full-width line underneath so the
    numbers are not fighting a sentence for space."""
    if not PAIRS: return '<p class="expl">layout-study outputs not found.</p>'
    groups = {}
    for r in PAIRS:
        groups.setdefault(r['comparability'].split(' (')[0], []).append(r)
    out = []
    for key in ('COMPARABLE', 'NEEDS_ROOM_MEASUREMENT', 'NOT_COMPARABLE'):
        rs = groups.get(key)
        if not rs: continue
        cls, note = BAND[key]
        out.append(f'<tr class="lgrp {cls}"><td colspan="5">{key.replace("_"," ")}'
                   f'<span class="lnote">{note}</span></td></tr>')
        for r in sorted(rs, key=lambda x: -x['pairs']):
            why = r['comparability'].split('(',1)[1].rstrip(')') if '(' in r['comparability'] else ''
            out.append(
                '<tr class="lmain">'
                f'<td class="lpair">{r["base_layout"]} &rarr; {r["feature_layout"]}</td>'
                f'<td class="num">{r["base_sqft"]:,} &rarr; {r["feature_sqft"]:,}<span class="lsub">'
                f'{r["delta_sqft"]:+} sqft</span></td>'
                f'<td class="num">{r["pairs"]}<span class="lsub">pairs</span></td>'
                f'<td class="num lbig">{_money(r["premium_sgd"])}<span class="lsub">'
                f'{r["premium_pct"]}%</span></td>'
                f'<td class="num">{_ci(r["ci95_low"], r["ci95_high"])}</td></tr>')
            out.append(f'<tr class="lwhy"><td colspan="5">{r["feature_difference"]}'
                       + (f' &nbsp;&middot;&nbsp; <i>{why}</i>' if why else '') + '</td></tr>')
    return ('<table class="lt"><thead><tr><th>pair</th><th class="num">strata</th>'
            '<th class="num">matched</th><th class="num">premium</th>'
            '<th class="num">95% CI</th></tr></thead><tbody>'
            + ''.join(out) + '</tbody></table>')

def jumps_table():
    rows = []
    if EDGES:
        rows.append('<tr class="lgrp ok"><td colspan="5">tier edge'
                    '<span class="lnote">biggest of one tier to the cheapest usable of the next'
                    '</span></td></tr>')
        for j in EDGES:
            rows.append(
                f'<tr class="lmain"><td class="lpair">{j["jump"].replace(" -> ", " &rarr; ")}</td>'
                f'<td class="num">{j["base_sqft"]:,} &rarr; {j["feature_sqft"]:,}'
                f'<span class="lsub">{j["delta_sqft"]:+} sqft</span></td>'
                f'<td class="num">{j["pairs"]}<span class="lsub">pairs</span></td>'
                f'<td class="num">{_money(j["base"])}<span class="lsub">base</span></td>'
                f'<td class="num lbig">{_money(j["med"])}<span class="lsub">{j["pct"]}%</span>'
                f'</td></tr>')
            if j.get('rung'):
                rows.append(f'<tr class="lwhy"><td colspan="5"><i>{j["rung_note"]}</i></td></tr>')
    if JUMPS:
        rows.append('<tr class="lgrp"><td colspan="5">other jumps'
                    '<span class="lnote">bedroom step and its area together, not decomposable'
                    '</span></td></tr>')
        for j in JUMPS:
            rows.append(
                f'<tr class="lmain"><td class="lpair">{j["jump"].replace(" -> ", " &rarr; ")}</td>'
                f'<td class="num">&mdash;</td>'
                f'<td class="num">{j["pairs"]}<span class="lsub">pairs</span></td>'
                f'<td class="num">{_money(j["base"])}<span class="lsub">base</span></td>'
                f'<td class="num lbig">{_money(j["med"])}<span class="lsub">{j["pct"]}%</span>'
                f'</td></tr>')
    return ('<table class="lt"><thead><tr><th>jump</th><th class="num">strata</th>'
            '<th class="num">matched</th><th class="num">base quantum</th>'
            '<th class="num">premium</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>')

ROOM_ORDER = ['living', 'dining', 'master', 'bedroom_1', 'bedroom_2', 'bedroom_3', 'bedroom_4',
              'bath_1', 'bath_2', 'wc', 'kitchen', 'yard', 'household_shelter', 'store',
              'balcony', 'balcony_2', 'ac_ledge']
SHORT = {'household_shelter': 'shelter', 'bedroom_1': 'bed 1', 'bedroom_2': 'bed 2',
         'bedroom_3': 'bed 3', 'bedroom_4': 'bed 4', 'bath_1': 'bath 1', 'bath_2': 'bath 2',
         'ac_ledge': 'a/c', 'balcony_2': 'balc 2'}
def rooms_table():
    L = ROOMS.get('layouts', {})
    if not L: return '<p class="expl">no room measurements yet.</p>'
    cols = [c for c in ROOM_ORDER if any(c in v['rooms'] for v in L.values())]
    head = ''.join(f'<th class="num">{SHORT.get(c, c)}</th>' for c in cols)
    rows = []
    for c, v in sorted(L.items(), key=lambda kv: kv[1]['sqft']):
        cells = ''.join(
            f'<td class="num{" lhit" if k in ("yard","household_shelter","wc") and v["rooms"].get(k) else ""}">'
            f'{v["rooms"].get(k) or "&middot;"}</td>' for k in cols)
        rows.append(f'<tr class="lmain"><td class="lpair">{c}</td>'
                    f'<td class="num">{v["sqft"]:,}</td>{cells}</tr>')
    return ('<div class="scroll"><table class="lt lroom"><thead><tr><th>layout</th>'
            '<th class="num">strata</th>' + head + '</tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>')

def counts():
    L = ROOMS.get('layouts', {})
    pub = [r for r in PAIRS if r['comparability'].split(' (')[0] == 'COMPARABLE']
    return dict(layouts=len(LAY), measured=len(L), pairs=len(PAIRS), publishable=len(pub),
                rejected=len([r for r in PAIRS
                              if r['comparability'].startswith('NOT_COMPARABLE')]))
