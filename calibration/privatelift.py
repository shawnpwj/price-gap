"""Internal — Constant Calibration › Private lift (4BR+).

Shawn, 2026-10-17: "can we assess the PSF between private lift and no private lift ... if more or
less what is the estimated % (after adjusting for floor)". 2026-10-18: "take note to ONLY look at
4BR+ evidence", then "you should put this study in calibration, that is where all the data
artifacts are".

A window onto layout-study/out/private-lift/ (built by layout-study/src/private_lift.py). Nothing
here is computed except the closest-first ordering of the pair tables; every figure is the study's.
Shape follows the calibration page's standing layout (memory: calibration-page-evidence-layout):
the transaction base on the hero, and every pair table tied back to its row's figure, closest first.
"""
import csv, json, os, html, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.abspath(os.path.join(HERE, '..', '..', 'layout-study', 'out', 'private-lift'))

NAME = {'jadescape': 'JadeScape', 'parc-clematis': 'Parc Clematis', 'twin-vew': 'Twin Vew',
        'seaside-residences': 'Seaside Residences', 'the-garden-residences': 'The Garden Residences',
        'riverbank-fernvale': 'Riverbank Fernvale', 'clavon': 'Clavon'}
# What the lift unit brings besides the lift, read off the plans 2026-10-17 (the study's SPECS note).
ADDS = {('jadescape', 'D2'): 'lift + lobby + powder room + utility',
        ('jadescape', 'D1'): 'lift + lobby + powder room + utility',
        ('parc-clematis', '4BR-1'): 'lift + foyer + a third bathroom + walk-in wardrobe',
        ('twin-vew', 'D1'): 'lift + lobby + a third bathroom'}
# Why a reading has no figure: said on the page rather than left blank.
WHYNOT = {('twin-vew', 'D2s'): "the no-lift D2s faces the river and the lift D3 does not; no facing figure bridges them",
          ('seaside-residences', 'D1'): 'one resale on each side',
          ('the-garden-residences', 'D3'): 'the no-lift D3 has no resale',
          ('riverbank-fernvale', 'Db'): 'three no-lift resales, none in reach of a lift sale',
          ('clavon', 'D2'): 'one lift resale, none in reach of a no-lift sale'}
MIN_PAIRS = 5


def _load():
    p = os.path.join(OUTD, 'summary.json')
    if not os.path.exists(p): return None, []
    s = json.load(open(p))
    with open(os.path.join(OUTD, 'pairs.csv')) as fh:
        pairs = [r for r in csv.DictReader(fh) if r['sale'] == 'resale']
    return s, pairs

S, PAIRS = _load()


def _pct(v, sign=True):
    if v is None: return '&mdash;'
    s = f'{abs(v):.1f}%'
    return ('&minus;' if v < 0 else ('+' if sign and v > 0 else '')) + s

def _money(v):
    if v is None: return '&mdash;'
    if round(v) == 0: return '$0'
    return ('&minus;$' if v < 0 else '+$') + f'{abs(v):,.0f}'

def _mo(d):
    return datetime.date.fromisoformat(d[:10]).strftime('%b %Y')


def readings():
    """Every 4BR+ row, measured or not, in the study's order."""
    out = []
    for r in (S or {}).get('rows', []):
        if r['bedrooms'] != '4BR+': continue
        e, a = r.get('resale_exact'), r.get('resale_adjusted')
        key = (r['development'], r['base'][0])
        lab = f"{NAME.get(r['development'], r['development'])} {' / '.join(r['base'])} &rarr; {' / '.join(r['private_lift'])}"
        tx = {x[k] for x in PAIRS for k in ('ta', 'tb')
              if x['development'] == r['development'] and x['base'] in r['base'] and x['pl'] in r['private_lift']
              and x['bedrooms'] == '4BR+'}
        out.append(dict(r=r, key=key, label=lab, exact=e, adj=a, tx=tx,
                        measured=bool(a and a['pairs'] >= MIN_PAIRS) or bool(e and e['pairs'] >= MIN_PAIRS),
                        thin_only=bool(a and 0 < a['pairs'] < MIN_PAIRS)))
    return out

# Strongest evidence first: closest sizes, most lift sales; the thin reading last.
ORDER = [('jadescape', 'D2'), ('jadescape', 'D1'), ('parc-clematis', '4BR-1'), ('twin-vew', 'D1')]
SHORT = {('jadescape', 'D2'): 'JadeScape D2 &rarr; DP', ('jadescape', 'D1'): 'JadeScape D1 &rarr; DP',
         ('parc-clematis', '4BR-1'): 'Parc Clematis 4BR &rarr; lift 4BR', ('twin-vew', 'D1'): 'Twin Vew D1 &rarr; D3'}

R = readings()
R.sort(key=lambda x: ORDER.index(x['key']) if x['key'] in ORDER else 99)
SHOWN = [x for x in R if x['adj'] or x['exact']]
NOT = [x for x in R if not (x['adj'] or x['exact'])]


def counts():
    tx = set().union(*[x['tx'] for x in SHOWN]) if SHOWN else set()
    devs = {x['r']['development'] for x in SHOWN}
    lift = {p['tb'] for p in PAIRS if p['bedrooms'] == '4BR+'}
    return dict(tx=len(tx), devs=len(devs), lift_sales=len(lift), pairs=sum((x['adj'] or {}).get('pairs', 0) + (x['exact'] or {}).get('pairs', 0) for x in SHOWN))


def answer_table():
    """One row per reading: the floor-adjusted PSF gap, its $ on the lift unit, the raw price gap,
    what size alone would give, and the exact (same floor, same facing) figure beside it."""
    h = ['<div class="scroll"><table class="fig look"><thead><tr><th>Pair (same development)</th>'
         '<th>What the lift unit adds</th><th class="num">PSF gap<br>floor-adjusted</th>'
         '<th class="num">in $</th><th class="num">price gap</th><th class="num">size alone<br>would give</th>'
         '<th class="num">same floor<br>and facing</th><th class="num">pairs<br>(lift sales)</th>'
         '<th class="num">transactions</th></tr></thead><tbody>']
    for x in SHOWN:
        a, e, r = x['adj'], x['exact'], x['r']
        warn = '<span class="lsub"><span class="lwarn">thin</span></span>' if x['thin_only'] else ''
        seg = r.get('segment') or ''
        size = f"{(a or e)['size_pct']:+.0f}% bigger"
        h.append('<tr>'
                 f'<th>{x["label"]}<span class="lsub">{seg}</span>{warn}</th>'
                 f'<td>{html.escape(ADDS.get(x["key"], ""))}<span class="lsub">{size}</span></td>'
                 f'<td class="num big">{_pct(a["psf_pct"]) if a else "&mdash;"}</td>'
                 f'<td class="num">{_money(a["psf_dollars"]) if a else "&mdash;"}</td>'
                 f'<td class="num quiet">{_money(a["price_gap"]) if a else "&mdash;"}</td>'
                 f'<td class="num quiet">{_pct((a or e)["size_could_explain_pct"])}</td>'
                 f'<td class="num quiet">{(_pct(e["psf_pct"]) + " on " + str(e["pairs"])) if e else "none"}</td>'
                 f'<td class="num quiet">{a["pairs"] if a else 0} ({a["pl_sales"] if a else 0})</td>'
                 f'<td class="num quiet">{len(x["tx"])}</td></tr>')
    h.append('</tbody></table></div>')
    return ''.join(h)


def notmeasured_list():
    if not NOT: return ''
    li = ''.join(f'<li><b>{x["label"]}</b>: {html.escape(WHYNOT.get(x["key"], "no resale pair"))}</li>' for x in NOT)
    return f'<ul class="plain">{li}</ul>'


def pair_tables():
    """Every pair behind each row, closest to that row's figure first: what this pair reads, what
    the figure says, the gap. The no-lift side is shown at the lift unit's floor (adjusted PSF)."""
    out = []
    for x in SHOWN:
        r, a = x['r'], x['adj']
        fig = a['psf_pct'] if a else x['exact']['psf_pct']
        rows = [p for p in PAIRS if p['development'] == r['development'] and p['base'] in r['base']
                and p['pl'] in r['private_lift'] and p['bedrooms'] == '4BR+']
        rows.sort(key=lambda p: abs(float(p['psf_pct']) - fig))
        body = []
        for i, p in enumerate(rows, 1):
            moved = (f"moved L{p['a_floor']}&rarr;L{p['b_floor']}" if p['a_floor'] != p['b_floor'] else 'same floor') \
                    + ('' if p['a_face'] == p['b_face'] else ', facing moved')
            body.append('<tr>'
                        f'<td class="num quiet">{i}</td>'
                        f'<td>{p["base"]} #{int(p["a_floor"]):02d} &middot; {_mo(p["a_date"])}<span class="lsub">${int(p["a_price"]):,} &middot; {moved}</span></td>'
                        f'<td class="num">${int(p["psf_a"]):,}</td>'
                        f'<td>{p["pl"]} #{int(p["b_floor"]):02d} &middot; {_mo(p["b_date"])}<span class="lsub">${int(p["b_price"]):,}</span></td>'
                        f'<td class="num">${int(p["psf_b"]):,}</td>'
                        f'<td class="num big">{_pct(float(p["psf_pct"]))}</td>'
                        f'<td class="num quiet">{_pct(fig)}</td>'
                        f'<td class="num quiet">{_pct(float(p["psf_pct"]) - fig)}</td>'
                        f'<td class="num quiet">{"exact" if p["track"] == "EXACT" else "adjusted"}</td></tr>')
        out.append(f'<details><summary>{x["label"]} &middot; {len(rows)} pairs</summary>'
                   '<div class="scroll"><table class="fig"><thead><tr><th class="num">#</th>'
                   '<th>No-lift sale</th><th class="num">psf, at the lift unit&rsquo;s floor</th>'
                   '<th>Lift sale</th><th class="num">psf</th><th class="num">this pair reads</th>'
                   '<th class="num">the figure says</th><th class="num">off by</th><th class="num">track</th>'
                   '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div></details>')
    return ''.join(out)


def hero_answers():
    """(figure, what, developments, transactions) per measured reading, for build-page.hero()."""
    return [(_pct(x['adj']['psf_pct']), SHORT.get(x['key'], x['label']) + ('<br>thin' if x['thin_only'] else ''),
             None, len(x['tx'])) for x in SHOWN if x['adj']]


def size_line():
    s = (S or {}).get('size_slope') or {}
    return (f"PSF ~ size<sup>{s.get('elasticity')}</sup> inside one development: "
            f"{s.get('pairs', 0)} same-class no-lift pairs across {s.get('developments', 0)} developments, "
            "every bedroom count &mdash; 4BR+ alone has one such pair")
