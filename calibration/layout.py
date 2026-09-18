"""Internal — Constant Calibration › Layout.

Shawn, 2026-09-18: "i need you to capture all of these data and information somewhere
for me to read and vet through, can you put it in calibration inside 'internal -
constant calbiration' for my own hidden reference?"

Everything the layout-feature study has measured at Treasure at Tampines, laid out to be
audited: the matching rule, every published contrast, every rejected one and why, the
bedroom-tier jumps and the measured room areas.

Shawn, 2026-09-18, three cuts, all of them "I dont need this":
  * "remove ALL area only" -- no pair without a feature difference is shown.
  * "for all not comparable and needs room measurement, remove them" -- only pairs that pass
    the 80% gate reach this page. The rejected ones stay in out/library-layout-pairs.csv with
    their reasons; the gate is auditable there, it is just not on his screen.
  * "i dont need the specfiic sizing ... what matters is 3BR Prem to 4BR compact" -- bedroom
    crossings are labelled by PRODUCT CLASS, with no strata areas, because the class is what
    aggregates across developments. See layout-study/src/product_class.py.

And, 2026-09-18: "we DONT need same floor exactly. we also dont need same facing ... can you
have one where its EXACT match, and then one that we adjust for facing / floor". So every
figure is shown TWICE -- the exact match, and the adjusted pool -- side by side, never blended.
The "agree" column is the test: it compares the exact figure against ONLY the pairs the exact
rule throws away, which share no transaction with it. See layout-study/src/adjusted.py.

Reads the layout-study outputs. Nothing here is computed; this is a window onto that repo.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.abspath(os.path.join(HERE, '..', '..', 'layout-study'))

def _load(p, default=None):
    f = os.path.join(STUDY, p)
    if not os.path.exists(f): return default
    return json.load(open(f))

PAIRS  = _load('out/two-track.json', [])
JUMPS  = _load('out/class-jumps.json', [])
XDEV   = _load('out/all-developments-crossings.json', [])
XPOOL  = _load('out/crossings-pooled.json', [])
PARC   = _load('out/parc-esta-contrasts.json', [])
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

BAND = {'COMPARABLE': ('ok', 'passed the 80% gate')}

def _row(cells, cls=""):
    return f'<tr class="{cls}">' + "".join(cells) + "</tr>"

def _agree(r):
    g = r.get('test_gap_pct')
    if g is None: return '&mdash;'
    cls = 'lok' if abs(g) <= 5 else ('lwarn' if abs(g) <= 10 else 'lbad')
    return f'<span class="{cls}">{g:+.1f}%</span>'

def _cell(s):
    """Shawn, 2026-09-18: "i recommend having both exact and adjusted shown at all times."
    Both columns always appear. A track under the 5-pair minimum shows its count and a dash
    rather than a figure -- present, visibly, but not quoted."""
    if not s: return '<td class="num lthin">&mdash;<span class="lsub">no pairs</span></td>'
    if s.get('thin'):
        return (f'<td class="num lthin">&mdash;<span class="lsub">{s["pairs"]} pair'
                f'{"" if s["pairs"] == 1 else "s"}, too thin</span></td>')
    return f'<td class="num lbig">{_money(s["med"])}<span class="lsub">{s["pairs"]} pairs</span></td>'

def _two(r, key_exact='exact', key_adj='all'):
    return _cell(r.get(key_exact)) + _cell(r.get(key_adj))

def pairs_table():
    """One line per pair, both tracks, with what-differs on its own full-width line beneath."""
    if not PAIRS: return '<p class="expl">layout-study outputs not found.</p>'
    rs = [r for r in PAIRS if r['comparability'].split(' (')[0] == 'COMPARABLE']
    if not rs: return '<p class="expl">no pair passed the gate.</p>'
    out = []
    for r in sorted(rs, key=lambda x: -((x.get('exact') or {}).get('pairs', 0)
                                        + (x.get('all') or {}).get('pairs', 0))):
        why = r['comparability'].split('(',1)[1].rstrip(')') if '(' in r['comparability'] else ''
        e = r.get('exact')
        out.append(
            '<tr class="lmain">'
            f'<td class="lpair">{r["base_layout"]} &rarr; {r["feature_layout"]}</td>'
            f'<td class="num">{r["base_sqft"]:,} &rarr; {r["feature_sqft"]:,}'
            f'<span class="lsub">{r["delta_sqft"]:+} sqft</span></td>'
            + _two(r) +
            f'<td class="num">{_agree(r)}<span class="lsub">agree</span></td></tr>')
        out.append(f'<tr class="lwhy"><td colspan="5"><b>{r["base_class"]} &rarr; '
                   f'{r["feature_class"]}</b> &nbsp;&middot;&nbsp; {r["feature_difference"]}'
                   + (f' &nbsp;&middot;&nbsp; <i>{why}</i>' if why else '')
                   + (f' &nbsp;&middot;&nbsp; 95% CI exact {_ci(e["ci"][0], e["ci"][1])}'
               if e and not e.get('thin') else '') + '</td></tr>')
    return ('<table class="lt"><thead><tr><th>pair</th><th class="num">strata</th>'
            '<th class="num">exact match</th><th class="num">adjusted</th>'
            '<th class="num">test</th></tr></thead><tbody>'
            + ''.join(out) + '</tbody></table>')

def jumps_table():
    """Shawn, 2026-09-18: "i dont need the specfiic sizing ... remove all the sizes because when
    you start aggregating it across developments, the sizing dont matter, what matters is 3BR Prem
    to 4BR compact is the premium we're trying to find out."

    Every class of one bedroom count against every class of the next, each named -- Shawn: "we
    need to still show bedroom minus one, but we should indicate what that bedroom minus one
    entails". Classes are what the plan draws -- bedrooms,
    bathrooms, WC, study ("3BR2B+WC") -- Shawn's amendment of the same day, because Parc Esta
    prints no tier banner. See layout-study/src/product_class.py. No strata areas anywhere."""
    if not JUMPS: return '<p class="expl">no class jumps computed.</p>'
    rows, last = [], None
    for j in JUMPS:
        if j.get('thin'): continue
        grp = j['base_class'].split('BR')[0] + 'BR &rarr; ' + j['feature_class'].split('BR')[0] + 'BR'
        if grp != last:
            rows.append(f'<tr class="lgrp ok"><td colspan="5">{grp}'
                        f'<span class="lnote">which class of the smaller count, to which of the next</span></td></tr>')
            last = grp
        ao = j.get('adjusted_all') or j.get('adjusted_only')
        g = (round((j['test_gap']) / abs(j['med']) * 100, 1)
             if j.get('test_gap') is not None and j['med'] else None)
        cls = '&mdash;' if g is None else (
            'lok' if abs(g) <= 5 else ('lwarn' if abs(g) <= 10 else 'lbad'))
        agree = '&mdash;' if g is None else f'<span class="{cls}">{g:+.1f}%</span>'
        rows.append(
            f'<tr class="lmain"><td class="lpair">{j["jump"].replace(" -> ", " &rarr; ")}</td>'
            f'<td class="num">{_money(j["base"])}<span class="lsub">base quantum</span></td>'
            f'<td class="num lbig">{_money(j["med"])}<span class="lsub">{j["pairs"]} pairs</span></td>'
            + (f'<td class="num lbig">{_money(ao["med"])}<span class="lsub">{ao["pairs"]} pairs'
               f'</span></td>' if ao else '<td class="num">&mdash;</td>')
            + f'<td class="num">{agree}<span class="lsub">agree</span></td></tr>')
        rows.append(f'<tr class="lwhy"><td colspan="5">'
                    f'{" + ".join(j["base_layouts"])} &rarr; {" + ".join(j["feature_layouts"])}'
                    f' &nbsp;&middot;&nbsp; 95% CI exact {_ci(j["ci"][0], j["ci"][1])}</td></tr>')
    return ('<table class="lt"><thead><tr><th>crossing</th><th class="num">base quantum</th>'
            '<th class="num">exact match</th><th class="num">adjusted</th>'
            '<th class="num">test</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>')

def parc_table():
    """Parc Esta, the second development read off the plans (2026-09-18). Bedroom crossings only:
    its feature contrasts (B -> BP one bathroom, BP -> BD study, C -> CP WC + utility, D -> DP WC +
    store) all step 100+ sqft, far more than the added rooms occupy, so they fail the
    comparability gate the same way Treasure's D1 -> D8P did and are kept off the page.
    A crossing shows when EITHER track carries 5+ pairs -- Shawn: both tracks, always."""
    if not PARC: return '<p class="expl">Parc Esta not run.</p>'
    beds = lambda c: int(c.split('BR')[0])
    rows, last = [], None
    for r in PARC:
        a, b = r['contrast'].split(' -> ')
        if beds(b) != beds(a) + 1: continue
        e, o = r.get('exact'), r.get('adjusted_only')
        if (not e or e['thin']) and (not o or o['thin']): continue
        grp = f'{beds(a)}BR &rarr; {beds(b)}BR'
        if grp != last:
            rows.append(f'<tr class="lgrp ok"><td colspan="4">{grp}</td></tr>'); last = grp
        g = r.get('test_pct')
        agree = ('<span class="lthin">&mdash;</span>' if g is None else
                 f'<span class="{"lok" if abs(g) <= 5 else ("lwarn" if abs(g) <= 10 else "lbad")}">{g:+.1f}%</span>')
        rows.append(f'<tr class="lmain"><td class="lpair">{r["contrast"].replace(" -> ", " &rarr; ")}</td>'
                    + _cell(e) + _cell(o)
                    + f'<td class="num">{agree}<span class="lsub">agree</span></td></tr>')
        base = lambda cs: " + ".join(sorted({c.split("-")[0] for c in cs}))   # -P/-R: same drawing
        rows.append(f'<tr class="lwhy"><td colspan="4">{base(r["base_layouts"])} &rarr; '
                    f'{base(r["feature_layouts"])} &nbsp;&middot;&nbsp; with their ground/top-floor variants</td></tr>')
    return ('<div class="scroll"><table class="lt"><thead><tr><th>crossing</th>'
            '<th class="num">exact match</th><th class="num">adjusted</th>'
            '<th class="num">test</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')

def xdev_table():
    """Shawn, 2026-09-18: "Can you now move on to the rest of the developments."

    Bedroom COUNT to bedroom COUNT, every development with a facing read. The class (bathrooms,
    WC, study) is absent on purpose: it is read off the plans, and only Treasure has been read. Deriving it from strata area would break that ruling and would also be wrong -- at
    Treasure, D3 (base) and D7P (premium) are both 1,270 sqft."""
    if not XDEV: return '<p class="expl">no cross-development run yet.</p>'
    rows, last = [], None
    for r in sorted(XDEV, key=lambda x: (x['crossing'], -((x.get('exact') or {}).get('pairs', 0)))):
        e, al, g = r.get('exact'), r.get('adjusted_all'), r.get('test_gap_pct')
        if (not e or e['thin']) and (not al or al['thin']): continue
        if r['crossing'] != last:
            pool = next((p for p in XPOOL if p['crossing'] == r['crossing']), None)
            note = (f'{pool["developments"]} developments &middot; median '
                    f'{pool["median_pct"]}% &middot; quantum {_money(pool["quantum_lo"])} to '
                    f'{_money(pool["quantum_hi"])}' if pool else '')
            rows.append(f'<tr class="lgrp ok"><td colspan="5">{r["crossing"].replace(" -> ", " &rarr; ")}'
                        f'<span class="lnote">{note}</span></td></tr>')
            last = r['crossing']
        if g is None: agree = '<span class="lthin">&mdash;</span>'
        else:
            cls = 'lok' if abs(g) <= 5 else ('lwarn' if abs(g) <= 10 else 'lbad')
            agree = f'<span class="{cls}">{g:+.1f}%</span>'
        rows.append(
            f'<tr class="lmain"><td class="lpair">{r["name"].title()}</td>'
            + _cell(e) + _cell(al)
            + f'<td class="num">{(e or al)["pct"]}%<span class="lsub">of base</span></td>'
            + f'<td class="num">{agree}<span class="lsub">agree</span></td></tr>')
    return ('<div class="scroll"><table class="lt"><thead><tr><th>development</th>'
            '<th class="num">exact match</th><th class="num">adjusted</th>'
            '<th class="num">step</th><th class="num">test</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>')

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
