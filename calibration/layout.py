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
    the 60% gate (80% until 2026-09-19) reach this page. The rejected ones stay in out/library-layout-pairs.csv with
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
import json, os, html

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
PGATE  = _load('out/parc-esta-gate.json', [])
FSUM   = _load('out/feature-summary.json', [])
FLIB   = _load('out/feature-library.json', [])          # every feature reading, both routes
TRIAGE = _load('out/same-band-triage.json', [])         # what each candidate pair turned out to be
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

BAND = {'COMPARABLE': ('ok', 'passed the 60% gate')}

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
    rather than a figure -- present, visibly, but not quoted.

    Shawn, 2026-09-19: lead with TRANSACTIONS ASSESSED. The sale-pair count is a cross product --
    one caveat pairs with every qualifying caveat on the other side -- so it reads as more or less
    evidence than there is. The transaction line is the distinct caveats; the pair line stays
    underneath because the thinness rule (5 pairs) is still counted in pairs."""
    if not s: return '<td class="num lthin">&mdash;<span class="lsub">no transactions</span></td>'
    if s.get('thin'):
        return (f'<td class="num lthin">&mdash;<span class="lsub">{s.get("txns", 0)} transactions</span>'
                f'<span class="lsub lsub2">{s["pairs"]} sale pair'
                f'{"" if s["pairs"] == 1 else "s"}, too thin</span></td>')
    return (f'<td class="num lbig">{_money(s["med"])}'
            f'<span class="lsub">{s.get("txns", 0):,} transactions</span>'
            f'<span class="lsub lsub2">{s["pairs"]:,} sale pairs</span></td>')

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
            f'<td class="num lbig">{_money(j["med"])}'
            f'<span class="lsub">{j.get("txns", 0):,} transactions</span>'
            f'<span class="lsub lsub2">{j["pairs"]:,} sale pairs</span></td>'
            + (f'<td class="num lbig">{_money(ao["med"])}'
               f'<span class="lsub">{ao.get("txns", 0):,} transactions</span>'
               f'<span class="lsub lsub2">{ao["pairs"]:,} sale pairs</span></td>'
               if ao else '<td class="num">&mdash;</td>')
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

def parc_features_table():
    """Parc Esta feature pairs that PASS the measured 60% gate -- nothing else (Shawn: "for all
    not comparable and needs room measurement, remove them"). The failures stay in
    out/parc-esta-gate.json with the rooms that took the rest of the step."""
    ok = [r for r in PGATE if r['verdict'] == 'COMPARABLE']
    if not ok: return '<p class="expl">No Parc Esta feature pair passes the gate.</p>'
    rows = []
    for r in ok:
        feat = ' + '.join(k.replace('_', ' ').replace('bath 2', 'second bathroom') for k in r['added'])
        rows.append(f'<tr class="lmain"><td class="lpair">{r["base_layout"]} &rarr; {r["feature_layout"]}'
                    f'<span class="lsub">{r["base_class"]} &rarr; {r["feature_class"]}</span></td>'
                    + _cell(r.get('exact')) + _cell(r.get('adjusted_only'))
                    + f'<td class="num">{round(r["share"]*100)}%<span class="lsub">of the step is the {feat}</span></td></tr>')
    return ('<div class="scroll"><table class="lt"><thead><tr><th>pair</th>'
            '<th class="num">exact match</th><th class="num">adjusted</th>'
            '<th class="num">gate</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')

def feature_summary_table():
    """Shawn, 2026-09-19: *"dont kill the pairs, but i want aggregation of 'just bathroom that fits
    the gate', bathroom that does not fit the gates and hence its xxx sqft extra for bathroom +
    others."*

    So every feature gets TWO rows, not one. The first is the feature on its own -- the pairs where
    the added rooms are most of the area step. The second is the same feature where the step brought
    other space with it, and it is named by the SIZE of that step, never by a list of the rooms."""
    if not FSUM: return '<p class="expl">no feature summary built.</p>'
    NAMES = {'study': 'Study', 'extra bathroom': 'Extra bathroom', 'WC + utility (+ yard)': 'WC + utility + yard',
             'shelter + yard + WC + enclosed kitchen': 'Shelter + yard + WC + enclosed kitchen',
             'study -> bedroom': 'Study &rarr; bedroom', 'one more bedroom (same package)': 'One more bedroom, same package'}
    MEAS = {'quantum': 'quantum', 'psf': '$/sqft', 'pct': '% of price'}
    SHORT = {'quantum': 'qtm', 'psf': 'psf', 'pct': '%'}
    def k(x): return f"${x/1000:.0f}k" if x >= 10000 else f"${round(x):,}"
    def rng(v, f, g=None):
        # A class-linked row has no step in sqft, so it has no $/sqft either -- that is a real
        # absence, not a missing value, and it shows as a dash rather than breaking the table.
        if not v: return '<span class="lthin">&mdash;</span>'
        g = g or f
        return f(v[1]) + (f'<span class="lsub">{g(v[0])}&ndash;{g(v[2])}</span>' if v[0] != v[2]
                          else '<span class="lsub">one layout pair</span>')
    def split(g, suf):
        if not g: return '&mdash;'
        return ''.join(f'<span class="lsplit">{kk}{suf} <b>{v["median"]:.1f}%</b> '
                       f'<span class="lthin">({v.get("txns", v["n"]):,} tx)</span></span>'
                       for kk, v in g.items())
    rows = []
    for o in FSUM:
        name = NAMES.get(o["feature"], o["feature"])
        for which, b in (('alone', o.get('feature_alone')), ('area', o.get('feature_plus_area'))):
            if not b: continue
            c = {k: v for k, v in (b['cv'] or {}).items() if v is not None}
            if b['steadiest'] is None or not c: st = '<span class="lthin">one layout pair</span>'
            elif max(c.values()) - min(c.values()) <= 2: st = 'no difference'
            else: st = f'<b>{MEAS[b["steadiest"]]}</b>'
            spread = ' &middot; '.join(f'{SHORT[kk]} {c[kk]}' for kk in ('pct', 'psf', 'quantum')
                                       if c.get(kk) is not None)
            devs = ', '.join(d.replace('-', ' ').title() for d in b['developments'])
            sq = b.get('step_sqft')
            if which == 'alone':
                head = (f'{name}<span class="lsub ltx">the feature on its own</span>')
            else:
                # NAMED BY THE SIZE OF THE STEP, which is what he asked for
                span = (f'+{sq[0]}&ndash;{sq[2]} sqft' if sq and sq[0] != sq[2]
                        else (f'+{sq[1]} sqft' if sq else 'a larger step'))
                head = (f'{name}<span class="lsub ltx lwide">{span} &mdash; the feature '
                        f'+ other areas</span>')
            rows.append(
                f'<tr class="lmain {"lb-alone" if which=="alone" else "lb-area"}">'
                f'<td class="lpair fsum">{head}'
                f'<span class="lsub lsub2">{b.get("transactions", 0):,} transactions assessed &middot; '
                f'{b.get("sale_pairs_exact", 0):,} + {b.get("sale_pairs_adjusted", 0):,} sale pairs</span>'
                f'<span class="lsub lsub2">{b["pairs"]} layout pair{"s" if b["pairs"] != 1 else ""} '
                f'&middot; {devs}</span></td>'
                f'<td class="num lbig">{rng(b["pct"], lambda x: f"{x:.1f}%")}</td>'
                f'<td class="num">{split(b.get("by_region", {}), "")}</td>'
                f'<td class="num">{split(b.get("by_beds", {}), "BR")}</td>'
                f'<td class="num">{rng(b["psf"], lambda x: "$" + format(round(x), ","))}</td>'
                f'<td class="num">{rng(b["quantum"], lambda x: "$" + format(round(x), ","), k)}</td>'
                f'<td class="num">{st}<span class="lsub">{spread}</span></td></tr>')
    return ('<div class="scroll"><table class="lt"><thead><tr><th>feature</th><th class="num">% of price</th>'
            '<th class="num">by region</th><th class="num">by bedrooms</th>'
            '<th class="num">$ per unit sqft</th><th class="num">quantum</th><th class="num">steadiest</th>'
            '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')

DEVNAME = {'parc-esta': 'Parc Esta', 'riverfront-residences': 'Riverfront', 'treasure-at-tampines': 'Treasure',
           'a-treasure-trove': 'A Treasure Trove', 'affinity-at-serangoon': 'Affinity', 'symphony-suites': 'Symphony',
           'high-park-residences': 'High Park', 'stirling-residences': 'Stirling', 'riversails': 'Riversails',
           'jadescape': 'JadeScape', 'penrose': 'Penrose', 'sims-urban-oasis': 'Sims Urban Oasis',
           'the-tre-ver': 'The Tre Ver'}


_PRIMARY = {'bathroom': 'Extra bathroom', 'bedroom': 'One more bedroom', 'study': 'Study', 'WC': 'WC'}
_ANCILLARY = ('shelter', 'store', 'utility')


def _parse(feat):
    parts = [p.strip().lstrip('+') for p in feat.split(',') if p.strip().startswith('+')]
    prim, anc, yard = [], [], False
    for p in parts:
        if p == 'yard': yard = True
        elif p in _ANCILLARY: anc.append(p)
        elif 'bathroom' in p: prim.append('bathroom')
        elif 'bedroom' in p: prim.append('bedroom')
        elif p in ('study', 'WC'): prim.append(p)
        else: anc.append(p)
    return prim, sorted(set(anc)), yard


def _canon(feat):
    """The SAME grouping the summary rows use (src/feature_rows.name_of), so the two tables agree.

    The primary room names the group; a yard joins the name because the yard is what moves the
    figure; a shelter, a store or a utility room is ancillary and shows on the reading instead."""
    prim, anc, yard = _parse(feat)
    if not prim:
        base = 'WC' if 'WC' in feat else (' + '.join(anc) or feat)
        return (base + (' + yard' if yard else '')).strip()
    head = ' + '.join(_PRIMARY.get(p, p) for p in dict.fromkeys(prim))
    return head + (' + yard' if yard else '')


def library_table():
    """EVERY feature reading, grouped by what the step actually ADDS.

    Shawn, 2026-09-19, having caught the WC error himself: the page had been showing one row per
    feature NAME, and a name is not a product. A class label carries (beds, baths, WC, shelter,
    study) and is silent about a yard, a utility room or a store -- so "WC" stood for five
    different packages worth 5.7% to 23.5%. This table groups by the package and shows every
    reading behind it, so a thin one cannot hide inside a median."""
    if not FLIB: return '<p class="expl">feature library not built.</p>'
    by = {}
    for r in FLIB: by.setdefault(_canon(r['feature']), []).append(r)
    order = sorted(by, key=lambda k: -sum(x['pairs'] for x in by[k]))
    out = ['<table class="lt"><thead><tr>'
           '<th>what the step adds</th><th>development</th><th>class contrast</th>'
           '<th class="num">step</th><th class="num">exact pairs</th>'
           '<th class="num">quantum</th><th class="num">% of price</th>'
           '<th class="num">two-track test</th></tr></thead><tbody>']
    for feat in order:
        rows = sorted(by[feat], key=lambda x: -x['pairs'])
        passing = [x for x in rows if x['test'] is not None and abs(x['test']) <= 10]
        for i, r in enumerate(rows):
            t = r['test']
            cls = 'lok' if (t is not None and abs(t) <= 5) else ('lwarn' if (t is not None and abs(t) <= 10) else 'lbad')
            test = f'<span class="{cls}">{t:+.1f}%</span>' if t is not None else '&mdash;'
            head = (f'<b>{html.escape(feat)}</b><span class="lsub ltx">{len(rows)} reading'
                    f'{"" if len(rows)==1 else "s"} &middot; {sum(x["pairs"] for x in rows)} exact pairs'
                    f'{f" &middot; {len(passing)} pass the test" if rows else ""}</span>') if i == 0 else ''
            step = f"+{r['step']}" if r.get('step') else '<span class="lthin">class&#8209;linked</span>'
            out.append(_row([
                f'<td>{head}</td>',
                f'<td>{html.escape(DEVNAME.get(r["dev"], r["dev"]))}</td>',
                f'<td class="lthin">{html.escape(r["contrast"])}'
                + (f'<span class="lsub">with {html.escape(" + ".join(_parse(r["feature"])[1]))}</span>'
                   if _parse(r['feature'])[1] else '') + '</td>',
                f'<td class="num">{step}</td>',
                f'<td class="num">{r["pairs"]:,}<span class="lsub">{r["tx"]:,} tx</span></td>',
                f'<td class="num lbig">{_money(r["med"])}</td>',
                f'<td class="num">{r["pct"]:.1f}%</td>',
                f'<td class="num">{test}</td>'], cls='lb-area' if i else '')) 
    out.append('</tbody></table>')
    return "".join(out)


def triage_table():
    """What the 40 same-bedroom-band candidates actually turned out to be.

    The point of showing this is that TEN of them were never figures: the same product class on
    both sides, i.e. a price for square feet. Those are exactly the rows a size-driven screen
    would have published as feature premiums."""
    if not TRIAGE: return ''
    order = ['FEATURE', 'AREA-ONLY', 'MIXED', 'UNCERTAIN', 'READ', 'CLOSED']
    what = {'FEATURE': 'a real feature contrast &mdash; priced above',
            'AREA-ONLY': 'the SAME product class on both sides &mdash; a price for square feet, dropped by ruling 5',
            'MIXED': 'one strata area carries two classes &mdash; superseded by the development&rsquo;s tx&nbsp;&rarr;&nbsp;layout link',
            'UNCERTAIN': 'the plans do not separate cleanly &mdash; held out rather than guessed',
            'READ': 'sheet not yet read',
            'CLOSED': 'development retired from the study'}
    n = {k: [r for r in TRIAGE if r['state'] == k] for k in order}
    out = ['<table class="lt"><thead><tr><th>outcome</th><th class="num">pairs</th>'
           '<th class="num">sale pairs behind them</th><th>what it means</th></tr></thead><tbody>']
    for k in order:
        v = n.get(k) or []
        if not v: continue
        out.append(_row([f'<td><b>{k.title()}</b></td>',
                         f'<td class="num lbig">{len(v)}</td>',
                         f'<td class="num">{sum(x["pairs"] for x in v):,}</td>',
                         f'<td class="lthin">{what[k]}</td>']))
    out.append('</tbody></table>')
    return "".join(out)


def facts():
    """Every number the layout prose quotes, COMPUTED.

    build-page.py's standing rule: "EVERY FIGURE ON THIS PAGE IS COMPUTED HERE. Nothing is
    hardcoded in the prose -- an earlier version carried p-values and coefficients as literals and
    they went stale the moment the pair screen changed." The 2026-09-19 rewrite quoted a dozen
    figures inline and broke that within a day. They are derived here instead.

    The exceptions, and they are deliberate: the figures describing what was WRONG (the withdrawn
    11.6% / $173,484, its two component pairs, and the 160 sqft cap) are historical facts about a
    past state of this page. They do not move when the data does, and recomputing them from
    current files would quietly rewrite the record of the error."""
    import statistics
    f = {}
    scr = _load('out/size-screen.json', []) or []
    f['screen_now'] = len(scr)
    same = [r for r in scr if r.get('verdict') == 'same-band']
    f['sameband'] = len(same)
    tri = TRIAGE or []
    f['triage_total'] = len(tri)
    f['area_only'] = len([r for r in tri if r['state'] == 'AREA-ONLY'])
    f['feature'] = len([r for r in tri if r['state'] == 'FEATURE'])
    # the WC family: how well does step size explain the premium
    wc = [r for r in (FLIB or []) if '+WC' in r['feature'] and r.get('step')]
    wcall = [r for r in (FLIB or []) if '+WC' in r['feature']]
    steps = _load('out/wc-library.json', []) or []
    xy = [(r['step'], r['pct']) for r in steps if r.get('step')]
    if len(xy) > 2:
        xs = [a for a, _ in xy]; ys = [b for _, b in xy]
        mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
        cov = sum((a-mx)*(b-my) for a, b in xy)
        vx = sum((a-mx)**2 for a in xs); vy = sum((b-my)**2 for b in ys)
        r = cov/(vx*vy)**.5 if vx and vy else 0
        f['wc_r'] = round(r, 3); f['wc_r2'] = round(r*r*100)
        f['wc_n'] = len(xy)
    wc_alone = [r for r in (FLIB or []) if r['feature'].strip() == '+WC']
    if wc_alone:
        f['wc_alone_pct'] = round(statistics.median(r['pct'] for r in wc_alone), 1)
    # the WC rows as feature-summary now carries them, and the bathroom
    for o in (FSUM or []):
        n = o['feature']; b = o.get('feature_alone')
        if not b: continue
        if n == 'WC':          f['rung_svc'] = b
        if n == 'WC + yard':   f['rung_yard'] = b
        if n == 'Extra bathroom': f['bath_row'] = b
    # bathroom spread
    bath = [r for r in (FLIB or []) if r['feature'].strip() == '+1 bathroom']
    bp = [r for r in bath if r['test'] is not None and abs(r['test']) <= 10]
    if bath:
        big = [r for r in bp if r['dev'] in ('riverfront-residences', 'parc-esta')]
        small = [r for r in bp if r['dev'] == 'high-park-residences']
        f['bath_n'] = len(bath)
        f['bath_pass_pairs'] = sum(r['pairs'] for r in bp)
        if big:
            f['bath_big_pairs'] = sum(r['pairs'] for r in big)
            f['bath_big_lo'] = min(r['pct'] for r in big); f['bath_big_hi'] = max(r['pct'] for r in big)
        if small:
            f['bath_small_lo'] = min(r['pct'] for r in small); f['bath_small_hi'] = max(r['pct'] for r in small)
    # the study, at Parc Esta, split by bedroom count
    for r in (PARC or []):
        c = r.get('contrast', '')
        e = r.get('exact')
        if not e or e.get('thin'): continue
        if c == '2BR2B -> 2BR2B+S': f['study2'] = e; f['study2_test'] = r.get('test_pct')
        if c == '3BR2B -> 3BR2B+S': f['study3'] = e; f['study3_test'] = r.get('test_pct')
    # what the page still pools the study at, and what it still publishes for the bathroom
    for o in (FSUM or []):
        if o['feature'] == 'study' and o.get('feature_alone'):
            f['study_pooled'] = o['feature_alone']['pct'][1]
        if o['feature'] == 'extra bathroom':
            if o.get('feature_alone'): f['bath_pub_alone'] = o['feature_alone']['pct'][1]
            if o.get('feature_plus_area'): f['bath_pub_area'] = o['feature_plus_area']['pct'][1]
    # the two area-only pairs worth naming
    for r in tri:
        if r['state'] != 'AREA-ONLY': continue
        if r['dev'] == 'affinity-at-serangoon' and r['a'] == 850: f['ao_aff'] = r
        if r['dev'] == 'symphony-suites' and r['a'] == 893: f['ao_sym'] = r
    return f


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
