#!/usr/bin/env python3
"""Is every calibration JSON still current with the data on disk?

WHY THIS EXISTS. On 2026-09-10 the upstream crawl refreshed psf-history.json at 15:23 and
nobody re-ran the calibration. For seven hours the page published $25 / $43 — the answer from
a snapshot taken four days earlier, missing a whole month of transactions — with no warning
anywhere. It was found by accident, in the middle of a conversation, one question before those
figures were going to a client.

Nothing about that was visible: the JSONs sat on disk looking finished, and the page stamped
its own window honestly. A figure is only true for the data it was cut from, and until now
NOTHING checked that the two still agreed.

TWO TESTS, because they catch different failures:
  * MTIME  — a source file is newer than the JSON built from it. Catches the crawl-then-forget
             case above, whatever the data actually contains.
  * MONTH  — the JSON's own window ends before the last month present upstream. Catches a JSON
             rebuilt against a stale or partial pull, where the mtime looks fine.

Run it standalone before quoting any figure:   python3 freshness.py
build-page.py imports check() and REFUSES TO BUILD when anything is stale, so the page can
never again disagree with the data behind it. Override for a deliberate re-cut of an older
window with  --stale-ok  (it prints what it is ignoring; it does not go quiet).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', '..', 'property-analyzer', 'data')
FLOOR = os.path.join(HERE, '..', '..', 'launch-picker', 'floor-study', 'data')

# calibration JSON -> the source files its script reads, and where its window is recorded.
# EC is pulled live from the URA API rather than read off disk, so it has no mtime source —
# the month test still covers it.
SOURCES = {
    'lease-pairs.json':      ([os.path.join(DATA, f) for f in
                               ('psf-history.json', 'dsi-index.json')],           'psf'),
    'mrt-pairs.json':        ([os.path.join(DATA, f) for f in
                               ('psf-history.json', 'dsi-index.json',
                                'mrt-stations.json')],                            'psf'),
    'integrated-pairs.json': ([os.path.join(DATA, f) for f in
                               ('psf-history.json', 'dsi-index.json')],           'psf'),
    'tenure-pairs.json':     ([os.path.join(DATA, f) for f in
                               ('psf-history.json', 'dsi-index.json')],           'psf'),
    'void-pairs.json':       ([os.path.join(FLOOR, f) for f in
                               ('realis-newsale-all-sg.json',
                                'realis-resale-all-sg.json')],                    None),
    'ec-pairs.json':         ([],                                                 'psf'),
}

def _window_end(d):
    """The last month a JSON says it covers. The scripts write this three different ways."""
    for v in (d.get('window'), d.get('late_window'), (d.get('meta') or {}).get('window')):
        if isinstance(v, (list, tuple)) and len(v) == 2: return str(v[1])
        if isinstance(v, str) and ' to ' in v:           return v.split(' to ')[-1].strip()
    return None

def _upstream_month():
    """The last month present in psf-history.json — the transaction spine of the study."""
    p = json.load(open(os.path.join(DATA, 'psf-history.json')))['projects']
    return max(m for v in p.values() for b in v.values() for m in b)

def check():
    """Returns a list of complaints. Empty means every figure is current."""
    latest, bad = _upstream_month(), []
    for name, (srcs, kind) in SOURCES.items():
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            bad.append(f'{name}: MISSING — run the script that writes it'); continue
        built = os.path.getmtime(path)
        for s in srcs:
            if os.path.exists(s) and os.path.getmtime(s) > built:
                age = (os.path.getmtime(s) - built) / 3600
                bad.append(f'{name}: {os.path.basename(s)} is {age:,.1f}h newer than it')
        if kind == 'psf':
            end = _window_end(json.load(open(path)))
            if end and end < latest:
                bad.append(f'{name}: covers to {end}, but the data now runs to {latest}')
    return bad

def gate(argv=()):
    """Hard gate for build-page.py. Prints and exits rather than building something stale."""
    bad = check()
    if not bad:
        print(f'  freshness: current to {_upstream_month()}')
        return
    head = 'STALE — the figures no longer match the data on disk:'
    if '--stale-ok' in argv:
        print(f'  freshness: {head}')
        for b in bad: print(f'    · {b}')
        print('  building anyway (--stale-ok). The page will publish figures from an older cut.')
        return
    print(f'\n{head}\n')
    for b in bad: print(f'  · {b}')
    print('\nRe-run the chain IN ORDER, then build:\n'
          '  python3 lease-pairs.py && python3 mrt-pairs.py && python3 integrated-pairs.py \\\n'
          '    && python3 void-pairs.py && python3 tenure-pairs.py && python3 build-page.py\n'
          'Deliberately re-cutting an older window? python3 build-page.py --stale-ok\n')
    sys.exit(1)

if __name__ == '__main__':
    bad = check()
    if bad:
        print('STALE:')
        for b in bad: print(f'  · {b}')
        sys.exit(1)
    print(f'current — every calibration JSON matches the data on disk (to {_upstream_month()})')
