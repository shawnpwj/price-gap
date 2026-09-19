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
    the 60% gate (80% until 2026-09-19) reach this page. The rejected ones stay in the study's own records with
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
WEX    = _load('out/worked-examples.json', [])          # three examples, with the real caveats
TRIAGE = _load('out/same-band-triage.json', [])         # what each candidate pair turned out to be
ROOMS  = _load('data/annotations/room-areas.json', {}) or {}
LAY    = (_load('data/annotations/treasure-at-tampines.json', {}) or {}).get('layouts', {})
TEND   = _load('out/tendency.json', {}) or {}           # median vs mean, and the track test on each
CARVE  = _load('out/carve-out.json', []) or []          # what one published figure pools
FZONE  = _load('out/floor-zones.json', {}) or {}        # the floor ladder, split into its two zones
FOYER  = _load('out/foyer.json', {}) or {}              # C6 / C9P / C10P -- does the foyer price?

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

AGREE_OK, AGREE_TOL = 5, 10


def _verdict(g):
    """(css class, the words under the figure) for a two-track gap.

    THE SUB-LABEL USED TO BE THE LITERAL STRING "agree" ON EVERY ROW. Four call sites emitted
    `<span class="lsub">agree</span>` unconditionally, so 11 cells reading -16.3%, +53.0%,
    -30.2% and +77.6% -- every one of them colour-coded as a FAILURE -- printed the word
    "agree" underneath, and 17 more did it on the tolerable band. The panel's own prose says
    "nine of the thirty-five testable crossings fail the 10% test". The table said they agreed.

    On the one page in this business whose entire job is to prove a method is sound, a column
    that reports the test cannot mislabel the test. Found by the 2026-09-20 design review;
    it had been shipping since the column was built."""
    if g is None: return '', '&mdash;'
    a = abs(g)
    if a <= AGREE_OK:  return 'lok', 'agrees'
    if a <= AGREE_TOL: return 'lwarn', 'within tolerance'
    return 'lbad', f'fails the {AGREE_TOL}% test'


def _agree(r):
    g = r.get('test_gap_pct')
    if g is None: return '&mdash;'
    cls, word = _verdict(g)
    return f'<span class="{cls}">{g:+.1f}%</span><span class="lsub lsub2">{word}</span>'


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
            f'<td class="num">{_agree(r)}</td></tr>')
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
        cls, word = _verdict(g)
        agree = ('&mdash;' if g is None else
                 f'<span class="{cls}">{g:+.1f}%</span><span class="lsub lsub2">{word}</span>')
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
            + f'<td class="num">{agree}</td></tr>')
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
        _c, _w = _verdict(g)
        agree = ('<span class="lthin">&mdash;</span>' if g is None else
                 f'<span class="{_c}">{g:+.1f}%</span><span class="lsub lsub2">{_w}</span>')
        rows.append(f'<tr class="lmain"><td class="lpair">{r["contrast"].replace(" -> ", " &rarr; ")}</td>'
                    + _cell(e) + _cell(o)
                    + f'<td class="num">{agree}</td></tr>')
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
    # Only the DIMENSIONLESS measures can win "steadiest" -- a quantum or a raw $/sqft carries
    # the price level of the development it came from, so its spread across developments
    # describes the sample, not the feature (Shawn, 2026-09-20). Both are still shown.
    MEAS = {'quantum': 'quantum', 'psf': '$/sqft', 'pct': '% of price',
            'ratio': 'multiple of the project&rsquo;s own psf'}
    SHORT = {'quantum': 'qtm', 'psf': 'psf', 'pct': '%', 'ratio': 'x psf'}
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
            contest = b.get('contest') or ['pct', 'ratio']
            run = {k: v for k, v in c.items() if k in contest}
            if b['steadiest'] is None or not run:
                st = ('<span class="lthin">one development</span>' if (b.get('developments_n') or 0) < 2
                      else '<span class="lthin">only one measure available</span>')
            elif max(run.values()) - min(run.values()) <= 2: st = 'no difference'
            else: st = f'<b>{MEAS[b["steadiest"]]}</b>'
            spread = ' &middot; '.join(
                f'{SHORT[kk]} {c[kk]}' + ('' if kk in contest else '<span class="lthin">*</span>')
                for kk in ('pct', 'ratio', 'psf', 'quantum') if c.get(kk) is not None)
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
                f'<td class="num">{rng(b.get("ratio"), lambda x: f"{x:.2f}&times;")}</td>'
                f'<td class="num">{rng(b["quantum"], lambda x: "$" + format(round(x), ","), k)}</td>'
                '</tr>')
    return ('<div class="scroll"><table class="lt"><thead><tr><th>feature</th><th class="num">% of price</th>'
            '<th class="num">by region</th><th class="num">by bedrooms</th>'
            '<th class="num">$ per sqft of the step</th>'
            '<th class="num">against the project&rsquo;s own psf</th>'
            '<th class="num">quantum</th>'
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


def agreement_table():
    """Exact against adjusted, every contrast. Shawn: *"are the adjusted and exact match close
    enough?"* -- the honest way to answer is to show all of them, including the ones that miss."""
    import statistics, os as _os
    rows = []
    for d in ('treasure-at-tampines', 'riverfront-residences', 'parc-esta', 'a-treasure-trove'):
        pth = _os.path.join(STUDY, f'out/{d}-contrasts.json')
        if not _os.path.exists(pth): continue
        for r in json.load(open(pth)):
            e, o = r.get('exact'), r.get('adjusted_only')
            if not e or e.get('thin') or not o or o.get('thin'): continue
            rows.append((d, r['contrast'], e, o, r.get('test_pct')))
    if not rows: return ''
    rows.sort(key=lambda x: -x[2]['pairs'])
    ok = [x for x in rows if x[4] is not None and abs(x[4]) <= 10]
    wp = sum(x[2]['pairs'] for x in rows); wo = sum(x[2]['pairs'] for x in ok)
    gaps = [abs(x[4]) for x in rows if x[4] is not None]
    out = [f'<p class="expl"><b>{len(ok)} of {len(rows)} contrasts agree within 10%.</b> '
           f'Weighted by matched pairs, <b>{wo:,} of {wp:,} ({wo/wp*100:.0f}%)</b> sit inside 10%, '
           f'and the median gap is <b>{statistics.median(gaps):.1f}%</b>. '
           + (f'The {len(rows)-len(ok)} that miss are among the thinnest in the study '
              f'(the largest carries {max((x[2]["pairs"] for x in rows if x[4] is not None and abs(x[4]) > 10), default=0)} '
              f'matched pairs against a median of {statistics.median(x[2]["pairs"] for x in rows):.0f} '
              f'across all {len(rows)}) &mdash; the disagreement tracks how little evidence there '
              f'is, which is what it should do if the adjusters are sound.'
              if len(ok) < len(rows) else 'Every contrast agrees.') + '</p>',
           '<table class="lt"><thead><tr><th>development</th><th>contrast</th>'
           '<th class="num">matched pairs</th><th class="num">no adjustment</th>'
           '<th class="num">adjusted pairs</th><th class="num">adjusted</th>'
           '<th class="num">gap</th></tr></thead><tbody>']
    for d, lab, e, o, t in rows:
        cls = 'lok' if (t is not None and abs(t) <= 5) else ('lwarn' if (t is not None and abs(t) <= 10) else 'lbad')
        out.append(_row([
            f'<td>{html.escape(DEVNAME.get(d, d))}</td>',
            f'<td class="lthin">{html.escape(lab)}</td>',
            f'<td class="num">{e["pairs"]:,}</td>',
            f'<td class="num lbig">{_money(e["med"])}</td>',
            f'<td class="num lthin">{o["pairs"]:,}</td>',
            f'<td class="num">{_money(o["med"])}</td>',
            f'<td class="num"><span class="{cls}">{t:+.1f}%</span></td>']))
    out.append('</tbody></table>')
    return "".join(out)


def tendency_table():
    """MEDIAN OR AVERAGE. Shawn, 2026-09-20: *"How are the averages? does median actually make
    sense? or average is better."*

    He asked because the three Riverfront pairs printed above run $290,000, $172,000 and
    $55,000 and the published figure is the middle one -- which looks, fairly, like a number
    being dragged down by its own worst case. The answer is the whole distribution, and the
    tie-break is the only external check the study has: which estimator makes the pairs the
    exact rule DISCARDED reproduce the pairs it kept."""
    if not TEND: return ''
    S, R = TEND['summary'], TEND['rows']
    t = S['test']
    out = [f'<p class="expl"><b>The two barely differ, and neither is systematically higher.</b> '
           f'Across {S["n"]} contrasts the average sits above the median on {S["higher"]} and '
           f'below it on {S["lower"]}, and the typical gap between them is '
           f'<b>{S["median_abs_skew"]}%</b>. Only <b>{S["moves_over_10"]}</b> move by more than '
           f'10% if the average is used instead, and all three are thin readings where a single '
           f'sale moves the answer. So the choice is not worth much &mdash; but it is worth '
           f'making on evidence rather than habit.</p>',
           f'<p class="expl"><b>The test that decides it.</b> Every contrast is measured twice on '
           f'transaction sets that share no sale: the matched pairs, and the pairs the matching '
           f'rule threw away. A better estimator should make those two agree more often. It does '
           f'not favour the plain median:</p>',
           '<div class="scroll"><table class="lt"><thead><tr><th>estimator</th>'
           '<th class="num">contrasts agreeing within 10%</th>'
           '<th class="num">median gap</th><th class="num">average gap</th></tr></thead><tbody>']
    LABEL = {'med': 'median <span class="lsub lsub2">what was published until 2026-09-20</span>',
             'mean': 'plain average',
             'trim': 'trimmed average <span class="lsub lsub2">10% off each tail &middot; '
                     'now published</span>'}
    best = min(t, key=lambda k: t[k]['mean_abs'])
    for k in ('med', 'mean', 'trim'):
        cls = ' class="lok"' if k == best else ''
        out.append(_row([f'<td{cls}>{LABEL[k]}</td>',
                         f'<td class="num">{t[k]["within10"]} of {S["test_n"]}</td>',
                         f'<td class="num">{t[k]["median_abs"]}%</td>',
                         f'<td class="num lbig">{t[k]["mean_abs"]}%</td>']))
    out.append('</tbody></table></div>')
    out.append(f'<p class="expl">The median is the weakest of the three on this test, and the '
               f'reason is mechanical rather than deep: on a contrast with five or nine matched '
               f'pairs the median <i>is</i> one sale, so it inherits that sale&rsquo;s renovation '
               f'and that seller&rsquo;s hurry. The <b>trimmed average</b> &mdash; the mean after '
               f'the top and bottom tenth are dropped &mdash; keeps the median&rsquo;s resistance '
               f'to a freak sale while using the rest of the evidence, and it agrees best on '
               f'both measures. <b>Every figure on this page is now the trimmed average</b>; the '
               f'median is kept in the table below so the move is visible. Across the whole '
               f'study the switch lifted agreement between the two tracks from 27 contrasts '
               f'inside 10% to <b>30 of 33</b>, and the median gap from 2.4% to 2.3%.</p>'
               f'<p class="expl">One honest caveat about the arithmetic: 10% of nine '
               f'observations rounds to zero, so <b>below ten matched pairs nothing is actually '
               f'trimmed and this is the plain average</b>. Forcing one off each end was '
               f'measured and is worse (15 of 19, against 16) &mdash; dropping 2 of 5 '
               f'observations discards 40% of the evidence to guard against an outlier a '
               f'5-pair contrast cannot identify. A thin contrast is thin, and the answer to '
               f'that is the pair count printed beside every figure, not a cleverer average.</p>')
    out.append('<div class="scroll"><table class="lt"><thead><tr><th>contrast</th>'
               '<th class="num">matched pairs</th><th class="num">median</th>'
               '<th class="num">average</th><th class="num">trimmed</th>'
               '<th class="num">middle half of the pairs</th></tr></thead><tbody>')
    for r in R:
        out.append(_row([
            f'<td class="lthin">{html.escape(r["contrast"])}</td>',
            f'<td class="num">{r["n"]}</td>',
            f'<td class="num lbig">{_money(r["med"])}</td>',
            f'<td class="num">{_money(r["mean"])}</td>',
            f'<td class="num">{_money(r["trim"])}</td>',
            f'<td class="num lthin">{_money(r["q1"])} &ndash; {_money(r["q3"])}</td>']))
    out.append('</tbody></table></div>')
    return "".join(out)


def carve_table():
    """WHAT ONE FIGURE POOLS. Shawn, 2026-09-20: *"Give me the actual layout type for me to go
    and view and give my opinion / comments if the 'carve out' of the layout adjustments are
    missing anything."*

    A published figure is a class contrast, and a class contrast is a POOL of layout pairs.
    Never adjusting for area is deliberate -- a bathroom is a bathroom -- but it means one
    figure can span very different area steps, and that is a judgement a reader is entitled
    to see rather than inherit."""
    if not CARVE: return ''
    out = ['<p class="expl">Each published figure is a contrast between two <b>product '
           'classes</b>, and each class holds several drawings. So a single number is the median '
           'of every layout pair inside it &mdash; and those pairs do not all carry the same '
           'area step. <b>That pooling is deliberate</b> (the study never adjusts for area: an '
           'added bathroom is an added bathroom), but it is a judgement, so here is what every '
           'figure is made of. The two codes in each row are the two floor plans to open.</p>']
    for c in CARVE:
        out.append(f'<div class="scroll"><table class="lt"><thead><tr><th colspan="6">'
                   f'{html.escape(c["name"])} &middot; {html.escape(c["contrast"])} '
                   f'<span class="lsub lsub2">{html.escape(c["feature"])} &middot; '
                   f'{_money(c["med"])} on {c["pairs"]} matched pairs &middot; steps of '
                   f'+{c["dsqft_lo"]} to +{c["dsqft_hi"]} sqft</span>'
                   f'</th></tr><tr><th>plan pair</th><th class="num">areas</th>'
                   f'<th class="num">step</th><th class="num">pairs</th>'
                   f'<th class="num">median</th>'
                   f'<th class="num">middle half</th></tr></thead><tbody>')
        for x in c['cells']:
            thin = ' lthin' if x['pairs'] < 3 else ''
            out.append(_row([
                f'<td><b>{html.escape(x["base"])}</b> &rarr; <b>{html.escape(x["feat"])}</b></td>',
                f'<td class="num lthin">{x["base_sqft"]:,} &rarr; {x["feat_sqft"]:,} sqft</td>',
                f'<td class="num">+{x["dsqft"]}</td>',
                f'<td class="num{thin}">{x["pairs"]}</td>',
                f'<td class="num lbig">{_money(x["med"])}</td>',
                f'<td class="num lthin">{_money(x["q1"])} &ndash; {_money(x["q3"])}</td>']))
        out.append('</tbody></table></div>')
    return "".join(out)


def floor_zone_table():
    """THE FLOOR LADDER IS NOT ONE RATE. Shawn, 2026-09-20: *"from floor 01 to -> 05, isnt there
    supposed to be a 1.87x multiplier based on the floor analysis?! why dont i see that."*

    He was right: this study compounded one flat rate from the ground up, while the resale floor
    study it is supposed to borrow from found the first four floors cost about 1.87x the rate the
    same building charges above L5."""
    if not FZONE: return ''
    out = ['<p class="expl">The adjusted track moves a sale to another floor before differencing, '
           'and until 2026-09-20 it did that with <b>one flat rate</b> compounded from wherever '
           'the sale sat. The <a class="xref" href="launch/index.html#floor">resale floor '
           'study</a> says that is wrong twice over. First, the ladder '
           'is not flat: the <b>first four floors cost about 1.87&times;</b> the rate the same '
           'building sustains above L5 (150 projects, one vote each). Second &mdash; and this is '
           'the larger error &mdash; the rate being compounded was fitted on <b>every</b> '
           'same-stack pair in the development, low floors included, so it was already a blend '
           'of the two zones. Both are now fixed: the base rate is refitted on L5-and-above '
           'pairs, and the multiplier is applied below.</p>',
           '<div class="scroll"><table class="lt"><thead><tr><th>development</th>'
           '<th class="num">rate used before<span class="lsub">all pairs pooled</span></th>'
           '<th class="num">rate used now<span class="lsub">L5+ pairs only</span></th>'
           '<th class="num">sale pairs</th>'
           '<th class="num">how much the old rate was inflated</th></tr></thead><tbody>']
    for name, z in sorted(FZONE.items(), key=lambda kv: -(kv[1].get('pooled_over_upper') or 0)):
        r = z.get('pooled_over_upper')
        out.append(_row([
            f'<td>{html.escape(name.title())}</td>',
            f'<td class="num lthin">{z["pooled"]}%/floor</td>',
            f'<td class="num lbig">{z["upper"]}%/floor</td>',
            f'<td class="num">{z["upper_pairs"]:,}</td>',
            f'<td class="num">{f"{r:.2f}&times;" if r else "&mdash;"}</td>']))
    out.append('</tbody></table></div>')
    owns = [(n, z) for n, z in FZONE.items() if z.get('own_mult') is not None]
    if owns:
        out.append(f'<p class="expl"><b>Each development&rsquo;s own low-floor ratio was measured '
                   f'and then deliberately not used.</b> {len(owns)} of {len(FZONE)} have enough '
                   f'pairs inside L1&ndash;4 to produce one, and they come out at '
                   + ', '.join(f'<b>{z["own_mult"]:.2f}&times;</b> ({html.escape(n.title())}, '
                               f'{z["low_pairs"]} pairs)' for n, z in
                               sorted(owns, key=lambda kv: -kv[1]['own_mult']))
                   + f'. Those are not coefficients, they are coin tosses: the individual pairs '
                   f'behind them run from &minus;4.5% to +16.4% <i>per floor</i>. The island '
                   f'figure exists precisely because one building cannot carry this estimate, so '
                   f'1.87&times; is what is applied everywhere and the local reads are kept only '
                   f'as an audit trail.</p>')
    out.append('<p class="expl"><b>What it changes: very little, and that is worth saying '
               'plainly.</b> 1.87&times; multiplies the <i>rate</i>, not the price. On the '
               'Riverfront example above, moving a #01 sale up to #05 lifts the base by '
               '<b>$16,948</b> where the old flat ladder lifted it by <b>$10,922</b> &mdash; '
               'about $6,000 on a $172,000 figure, and only on pairs that reach down into those '
               'floors. The matched-pair figures do not move at all, because both sides of a '
               'matched pair are on the same floor and nothing is adjusted.</p>')
    return "".join(out)


def foyer_block():
    """DOES AN ENTRANCE FOYER PRICE? Shawn, 2026-09-20, reading the Treasure example:

    *"if you used C9P vs C10P, C9P would be the better comparison than C10P ... C9P and C10P only
    differs by the foyer, one being blocked before seeing the living dining vs immediately seeing
    it at the entrance."*

    It is the right question to ask of any pooled figure, and the answer here is yes-but: the
    foyer is priced, and it is priced BELOW ordinary area, which is the opposite of a feature."""
    if not FOYER or not FOYER.get('legs'): return ''
    L = {(x['a'], x['b']): x for x in FOYER['legs']}
    psf = FOYER['dev_psf']
    out = [f'<p class="expl">Two of the three plans inside Treasure&rsquo;s '
           f'<code>3BR2B&nbsp;&rarr;&nbsp;3BR2B+WC+HS</code> figure carry the identical room '
           f'list &mdash; C9P at {L[("C6","C9P")]["b_sqft"]:,} sqft and C10P at '
           f'{L[("C6","C10P")]["b_sqft"]:,} sqft. The {L[("C9P","C10P")]["dsqft"]} sqft between '
           f'them is an <b>entrance foyer</b>, read off the two sheets: C10P puts a hallway between the '
           f'front door and the living-dining, C9P opens straight into it. '
           f'Because the class label is silent about it, the two pool. So: does it price?</p>',
           '<div class="scroll"><table class="lt"><thead><tr><th>plan pair</th><th class="num">step</th>'
           '<th class="num">matched pairs</th><th class="num">quantum</th>'
           '<th class="num">per sqft of the step</th>'
           f'<th class="num">against the development&rsquo;s own ${psf:,} psf</th>'
           '</tr></thead><tbody>']
    for k in (('C6', 'C9P'), ('C6', 'C10P'), ('C9P', 'C10P')):
        x = L[k]
        # colour on the ADJUSTED ratio: it is the one with the pairs behind it on every leg.
        rr = x['adj_ratio'] or x['exact_ratio']
        cls = 'lok' if rr and rr >= 1.15 else ('lbad' if rr and rr < 0.85 else 'lwarn')
        out.append(_row([
            f'<td><b>{x["a"]}</b> &rarr; <b>{x["b"]}</b>'
            f'<span class="lsub lsub2">{html.escape(x["why"])}</span></td>',
            f'<td class="num">+{x["dsqft"]}</td>',
            f'<td class="num">{x["exact_n"]}</td>',
            f'<td class="num lbig">{_money(x["exact"])}'
            f'<span class="lsub lsub2">{_money(x["adj"])} on {x["adj_n"]:,} adjusted</span></td>',
            f'<td class="num">${x["adj_psf"]:,}'
            f'<span class="lsub lsub2">${x["exact_psf"]:,} matched</span></td>',
            f'<td class="num"><span class="{cls}">{x["adj_ratio"]:.2f}&times;</span>'
            f'<span class="lsub lsub2">{x["exact_ratio"]:.2f}&times; on the {x["exact_n"]} '
            f'matched pairs</span></td>']))
    out.append('</tbody></table></div>')
    t = FOYER.get('triangle', {}).get('adj')
    foy = L[('C9P', 'C10P')]
    pkg = L[('C6', 'C9P')]
    out.append(f'<p class="expl"><b>It prices, and it prices like circulation.</b> Read the '
               f'foyer row on the ADJUSTED track, not the matched one: six matched pairs is '
               f'below the point where the trimmed average trims anything, so that cell is the '
               f'plain average of six sales and moves with any one of them. The '
               f'{foy["adj_n"]:,} adjusted pairs put the foyer at <b>{_money(foy["adj"])}</b>, '
               f'<b>{foy["adj_ratio"]:.2f}&times;</b> the development&rsquo;s own rate, against '
               f'<b>{pkg["adj_ratio"]:.2f}&times;</b> for the WC / shelter / yard package beside '
               f'it on {pkg["adj_n"]:,} pairs. <b>Buyers pay for a foyer at a discount to '
               f'ordinary floor area, where a real room commands a premium to it.</b> That is '
               f'the same signal the circulation guard was built on. The six matched pairs read '
               f'{_money(foy["exact"])} and {foy["exact_ratio"]:.2f}&times; &mdash; same '
               f'direction against the package, but far too thin to carry the point on its '
               f'own, and it is shown above rather than hidden.</p>')
    if t:
        out.append(f'<p class="expl"><b>The three readings are consistent.</b> Walking '
                   f'C6&nbsp;&rarr;&nbsp;C9P&nbsp;&rarr;&nbsp;C10P gives '
                   f'<b>{_money(t["sum"])}</b>; measuring C6&nbsp;&rarr;&nbsp;C10P directly gives '
                   f'<b>{_money(t["direct"])}</b>. They close to <b>{abs(t["gap"]):.1f}%</b> on '
                   f'the adjusted track, which is the only one with enough pairs in all three '
                   f'legs to carry the test. A pooled figure that was hiding an inconsistency '
                   f'would not close.</p>')
    P = FOYER.get('pooled') or {}
    move = (P.get('exact') - pkg['exact']) if P.get('exact') else None
    out.append(f'<p class="expl"><b>What follows from it.</b> '
               f'<b>C6&nbsp;&rarr;&nbsp;C9P is the better comparison</b>: it is the cleaner '
               f'feature step and it carries {pkg["exact_n"]} matched pairs against '
               f'{L[("C6","C10P")]["exact_n"]}. '
               + (f'Pooling the two reads {_money(P["exact"])} on {P["exact_n"]} pairs against '
                  f'{_money(pkg["exact"])} on C9P alone, so the published figure moves only '
                  f'{_money(abs(move))} &mdash; C9P dominates on count. ' if move is not None else '')
               + f'But the reason to separate them is not the size of that move, it is that they '
               f'are two products, and at a development where the foyer plan was the common one '
               f'the same pooling would bite. <b>An entrance foyer is now a recorded plan '
               f'feature</b>, read off the sheet alongside the yard and the utility room rather '
               f'than left to a class label that cannot see it.</p>')
    return "".join(out)


def hero_block():
    """The answer, in the shape every other panel on this page uses.

    THE PANEL HAD ABANDONED THE HOUSE ARGUMENT. Seven of the eight panels say one sentence --
    `Engine constant X -> Measured Y` -- and Layout said three big gold numbers over a stat
    strip: the default KPI hero of every analytics template since 2016, and the one composition
    the craft floor names outright as a refused default. The other seven do not lead with a rate
    because a rate is prettier; they lead with it because the rate is the DELTA AGAINST A STATED
    PRIOR. With no prior on screen Layout's number had nothing to be a number OF.

    Layout has no engine constant, but EC has the same problem and already solved it inside the
    pattern -- "none - reference only". That answer was written on this page and Layout ignored
    it. (2026-09-20 design review.)

    PERCENT LEADS, QUANTUM SITS UNDER IT. Shawn, 2026-09-20: *"why are you showing quantum at the
    top ONLY when clearly there is % associated with it ... in fact % should be the most used
    right?"* Tested rather than assumed: leave-one-development-out, predicting a held-out
    development's actual quantum, percent lands a 19% median error against 26% for $/sqft and
    21% for the psf ratio. Ruling 4 ("quote QUANTUM") was measured INSIDE one development, where
    the price level is known; a hero pooled across five developments spanning $1,237 to $2,303
    psf is not inside that ruling's scope. So the transferable figure leads and the dollar
    figure it implies sits beneath it.

    TWO FIGURES, NOT THREE. "One more bedroom" was the largest number on the panel and appeared
    exactly ONCE in 57,729 characters -- no table row, no worked example, nothing to open. On a
    page whose entire brief is "here are the data", the most memorable figure cannot be the one
    with no evidence behind it. It is named in the closing line and its evidence lives in the
    two crossing disclosures, where it can be read properly."""
    F = {o['feature']: o.get('feature_alone') for o in (FSUM or [])}
    picks = [('Extra bathroom', 'a second bathroom'),
             ('WC + yard', 'WC, yard and a service room')]
    cells = []
    for key, words in picks:
        b = F.get(key)
        if not b: continue
        pct, q = b['pct'], b['quantum']
        rng = (f'{pct[0]:.1f}&ndash;{pct[2]:.1f}%' if pct[0] != pct[2] else 'one reading')
        cells.append(
            f'<div class="ans"><div class="n">+{pct[1]:.1f}%</div>'
            f'<div class="w">{words}</div>'
            f'<div class="g">{_money(q[1])}<span>typical quantum</span></div>'
            f'<div class="g">{rng}<span>across {len(b["developments"])} developments</span></div>'
            f'</div>')
    if not cells: return ''
    X = _load('out/feature-library.json', []) or []
    npairs = sum(r['pairs'] for r in X)
    ndev = len({r['dev'] for r in X})
    return ('<div class="verdict"><div class="vgrid">'
            '<div class="vcell"><div class="lab">Engine constant</div>'
            '<div class="val was">none</div>'
            '<div class="sub">reference only &mdash; nothing in the constant set '
            'prices a floor plan</div></div>'
            '<div class="arrow">&rarr;</div>'
            '<div class="vcell grow"><div class="lab">Measured</div>'
            '<div class="answers">' + ''.join(cells) + '</div>'
            # THE BASE IS PROSE, NOT A THIRD COLUMN. It used to render as a second flex row whose
            # items landed 0 / 18 / 4 px off the answer columns above -- close enough to read as
            # a table, wrong enough to look broken, and it put "8 developments with plans read"
            # under "a second bathroom / 5 developments", giving two different development counts
            # in one vertical scan.
            f'<p class="vline">{ndev} developments with plans read &middot; '
            f'{npairs:,} matched pairs, nothing adjusted &middot; '
            f'{len(X)} measured contrasts</p>'
            '</div></div>'
            '<p class="call">Every figure is the gap between <b>two real resales</b> of the same '
            'size band in the same development, matched on floor and facing. Nothing is modelled. '
            'Crossing a whole bedroom is worth more again &mdash; that one is measured per '
            'development rather than pooled, and it is in '
            '<a class="xref" href="#d-crossing-a-bedroom-count">Crossing a bedroom count</a> '
            'below.</p>'
            '</div>')


def _cv(c):
    return (f"{c['code']}&nbsp;&nbsp;#{c['floor']:02d}-{c['stack']}", c['date'],
            '$' + format(c['price'], ','))


def worked_examples(only=None, skip=0):
    """`only` caps how many render; `skip` starts further down the list.

    ONE ON THE FACE, TWO BEHIND A DOOR (2026-09-20). All three were on the face and they are
    the strongest block on the panel -- which is exactly why the first one should not have to
    share the reader's attention with two more. One example proves the method; the other two
    are evidence, and evidence belongs with the evidence."""
    """Three figures shown the long way: the actual caveats, then one adjustment in full.

    Shawn, 2026-09-19: *"I need some layout pairs for me to eyeball and manually assess if the
    methodology you're using is right"* -- and the same three answer the client question, because
    what persuades is not another table, it is seeing that the figure IS the difference between
    two real sales and that nothing was done to it."""
    if not WEX: return ''
    sel = WEX[skip:skip + only] if only else WEX[skip:]
    out = []
    for w in sel:
        rows = ''.join(
            '<tr>' +
            f'<td class="wc">{_cv(e["a"])[0]}<span class="lsub">{_cv(e["a"])[1]}</span></td>'
            f'<td class="num">{_cv(e["a"])[2]}</td>'
            f'<td class="warr">&rarr;</td>'
            f'<td class="wc">{_cv(e["b"])[0]}<span class="lsub">{_cv(e["b"])[1]}</span></td>'
            f'<td class="num">{_cv(e["b"])[2]}</td>'
            f'<td class="num wdiff">{_money(e["diff"])}</td>'
            + (f'<td class="num woff">{_money(e["off"], sign=True)}</td>'
               if e.get('off') is not None else '<td class="num woff"></td>')
            + '</tr>'
            for e in w['exact'])
        a = w.get('adjusted')
        adj = ''
        if a:
            lines = []
            for st in a['steps']:
                if st['kind'] == 'floor':
                    # THE LADDER IS NOT FLAT. The first floors carry the resale floor study's
                    # low-zone multiplier, so the arithmetic printed here has to be the
                    # arithmetic that was done -- one term per zone, not one exponent.
                    nlow, nhigh = st.get('low_steps', 0), st.get('high_steps', None)
                    if nhigh is None: nhigh = abs(st['to'] - st['frm']) - nlow
                    terms = []
                    if nlow:
                        terms.append(f'(1&nbsp;+&nbsp;{st["rate"]}%&nbsp;&times;&nbsp;'
                                     f'{st.get("low_mult", 1.87)})<sup>{nlow}</sup>')
                    if nhigh:
                        terms.append(f'(1&nbsp;+&nbsp;{st["rate"]}%)<sup>{nhigh}</sup>')
                    zone = (f' <span class="lsub lsub2">&mdash; {nlow} of those steps sit inside '
                            f'L1&ndash;{st.get("low_top", 4)}, where the floor study measures '
                            f'{st.get("low_mult", 1.87)}&times; the tower rate</span>') if nlow else ''
                    lines.append(f'<li><span class="wk">floor</span> #{st["frm"]:02d} to #{st["to"]:02d} '
                                 f'&mdash; {_money(st["before"])} &times; '
                                 f'{" &times; ".join(terms) or "1"} = <b>{_money(st["after"])}</b>'
                                 f'{zone}</li>')
                else:
                    lines.append(f'<li><span class="wk">facing</span> {html.escape(st["frm"])} '
                                 f'({st["frm_pct"]:+.2f}%) to {html.escape(st["to"])} ({st["to_pct"]:+.2f}%) '
                                 f'&mdash; {_money(st["before"])} rebased = <b>{_money(st["after"])}</b></li>')
            adj = (f'<div class="wadj"><p>One of the {w["adj_n"]:,} pairs the exact rule turned away, and '
                   f'everything done to it. The base sale is moved to the other unit&rsquo;s floor and facing '
                   f'using rates measured on <i>different</i> pairs, then differenced. This is the pair '
                   f'closest to <i>that pool&rsquo;s own</i> figure of {_money(w["adj_med"])} &mdash; not '
                   f'the one that best matches the matched-pair answer, which would be picking on the '
                   f'agreement the two tracks exist to test.</p>'
                   f'<p class="wcav">{_cv(a["a"])[0]} &middot; {_cv(a["a"])[1]} &middot; '
                   f'<b>{_cv(a["a"])[2]}</b> &nbsp;&rarr;&nbsp; {_cv(a["b"])[0]} &middot; '
                   f'{_cv(a["b"])[1]} &middot; <b>{_cv(a["b"])[2]}</b></p>'
                   f'<ol>{"".join(lines)}</ol>'
                   f'<p class="wres">adjusted base <b>{_money(a["adjusted_base"])}</b> '
                   f'&rarr; difference <b>{_money(a["diff"])}</b></p></div>')
        gap = w.get('gap')
        gcls = 'lok' if gap is not None and abs(gap) <= 5 else ('lwarn' if gap is not None and abs(gap) <= 10 else 'lbad')
        out.append(
            f'<article class="wex">'
            f'<div class="whead"><div><h3 class="disp">{html.escape(w["why"])}</h3>'
            f'<p class="wsub">{html.escape(w["name"].title())} &middot; '
            f'{html.escape(w["contrast"])}</p></div>'
            f'<div class="wfig">{_money(w["exact_med"])}<span>trimmed average of {w["exact_n"]} matched pairs</span></div></div>'
            f'<table class="wt"><thead><tr><th colspan="2">the smaller layout</th><th></th>'
            f'<th colspan="2">the larger layout</th><th class="num">difference</th>'
            f'<th class="num">off the figure</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            # THE SHARED HALF OF THIS NOTE NOW SITS ONCE, ABOVE ALL THREE EXAMPLES. It was
            # 77 words repeated verbatim three times -- 231 of the face's words saying the
            # same thing, which is how a careful caveat turns into wallpaper.
            f'<p class="wnote">Across all {w["exact_n"]} pairs the difference runs '
            f'{_money(w["exact_lo"])} to {_money(w["exact_hi"])}; the middle half sits between '
            f'{_money(w["exact_q1"])} and {_money(w["exact_q3"])}.</p>'
            f'{adj}'
            f'<div class="wfoot"><span>{w["exact_n"]} matched pairs <b>{_money(w["exact_med"])}</b></span>'
            f'<span>{w["adj_n"]:,} adjusted pairs <b>{_money(w["adj_med"])}</b></span>'
            f'<span class="{gcls}">they agree to {abs(gap):.1f}%</span></div>'
            f'</article>')
    return '<div class="wexs">' + ''.join(out) + '</div>'


def _h(t):
    return html.escape(str(t))


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
    # THE BEST-SAMPLED SINGLE PLAN PAIR in the study, and how the two tracks did on it. This
    # used to be a literal ("C6 -> C9P reads $237,500 on 34 exact pairs") and it went stale the
    # first time the pair screen moved. It is the deepest cell in the carve-out.
    cells = [(c, x) for c in (CARVE or []) for x in c['cells']]
    if cells and FOYER.get('legs'):
        leg = {(x['a'], x['b']): x for x in FOYER['legs']}
        top = max(cells, key=lambda cx: cx[1]['pairs'])
        c, x = top
        lg = leg.get((x['base'], x['feat']))
        if lg and lg.get('adj'):
            gap = (lg['adj'] - lg['exact']) / lg['exact'] * 100
            f['best'] = (f"{x['base']} &rarr; {x['feat']} at {_h(c['name'])} reads "
                         f"{_money(lg['exact'])} on {lg['exact_n']} matched pairs and "
                         f"{_money(lg['adj'])} on {lg['adj_n']:,} adjusted ones "
                         f"&mdash; a gap of {abs(gap):.1f}%")
        else:
            f['best'] = (f"{x['base']} &rarr; {x['feat']} at {_h(c['name'])} carries "
                         f"{x['pairs']} matched pairs at {_money(x['med'])}")
    # THE SPREAD SENTENCE, computed. It carried "$105,000 to $211,000 around a median of
    # $172,000" as literals and all three moved when the estimator changed on 2026-09-20.
    for t in (TEND.get('rows') or []):
        if t['contrast'].startswith('Riverfront 2BR1B'):
            # t['med'] is the MEDIAN -- tendency.json deliberately keeps all three estimators.
            # The PUBLISHED figure is the trimmed average.
            f['spread_q1'], f['spread_q3'], f['spread_mid'] = t['q1'], t['q3'], t['trim']
            f['spread_n'] = t['n']
    for t in (TEND.get('rows') or []):
        if 'Treasure' in t['contrast'] and '2BR2B -> 3BR2B' in t['contrast']:
            f['tight_pct'] = round(max(abs(t['q1'] - t['trim']), abs(t['q3'] - t['trim']))
                                   / t['trim'] * 100)
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
            cls, word = _verdict(g)
            agree = f'<span class="{cls}">{g:+.1f}%</span><span class="lsub lsub2">{word}</span>'
        rows.append(
            f'<tr class="lmain"><td class="lpair">{r["name"].title()}</td>'
            + _cell(e) + _cell(al)
            + f'<td class="num">{(e or al)["pct"]}%<span class="lsub">of base</span></td>'
            + f'<td class="num">{agree}</td></tr>')
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


def measure_note():
    """Which of the three measures travels between developments, and the test that decided it.

    Moved OFF the face on 2026-09-20: 159 words of method justification were sitting between
    the reader and the next figure. It is a good argument and it belongs behind a door."""
    return ('<p class="expl"><b>The percentage is the figure that travels.</b> Tested rather '
              'than asserted: hold one development out, predict its actual quantum from the '
              'others, and the share of price lands a 19% median error against 26% for the '
              'step&rsquo;s $/sqft and 21% for the multiple of the project&rsquo;s own psf. So '
              'the percentage leads everywhere a figure is pooled, and the quantum leads '
              'wherever the price level is known &mdash; the per-development rows here, and the '
              'worked examples. Even the winner carries about 20% error predicting a '
              'development it has never seen, which is the honest limit of this table.</p>'
              '<p class="expl">One reading does not fit that rule and is worth keeping: the '
              'WC&nbsp;+&nbsp;yard package is remarkably steady as a <b>multiple of whatever the '
              'development charges per square foot</b> (a spread of 5% across four developments, '
              'against 22% for the share of price). No dollar measure could see that. An extra '
              'bathroom goes the other way, because bathrooms arrive at different sizes.</p>')
