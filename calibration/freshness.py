#!/usr/bin/env python3
"""Do the calibration JSONs match THE PINNED CUT — and how far has the world moved past it?

TWO DIFFERENT QUESTIONS, and only the first one is an error.

  1. Are the JSONs built at the cut the study declares (cut.py CUT_END)? If not, someone moved
     the pin and did not re-run, or ran one script and not the rest. That is a real defect and
     build-page.py REFUSES to build on it.

  2. How far past the cut has the data run? That is NOT an error. Shawn, 2026-09-10: the study
     is a dated cut, not a live feed — "I want the figures to not be updated by EVERY CRAWL,
     that is going to be disruptive as hell." A crawl bringing newer months is expected and
     must never move a published constant. It is reported so the decision to re-cut is a
     deliberate one, taken when someone chooses it.

WHY THE PIN EXISTS. On 2026-09-10 an ordinary crawl at 15:23 rolled every window forward by a
month and moved every constant — the integrated premium by 65%, on 8 pairs. Nothing was wrong
with the code; the study simply had no vintage. Now it has one.

Run standalone before quoting any figure:   python3 freshness.py
"""
import json, os, sys, cut

HERE  = os.path.dirname(os.path.abspath(__file__))
DATA  = os.path.join(HERE, '..', '..', 'property-analyzer', 'data')
FLOOR = os.path.join(HERE, '..', '..', 'launch-picker', 'floor-study', 'data')

# Which JSONs are cut against psf-history and must end exactly at the pin. void-pairs reads the
# floor study's static REALIS pull, which no crawl touches, so it carries its own window.
PINNED = ['lease-pairs.json', 'mrt-pairs.json', 'integrated-pairs.json',
          'tenure-pairs.json', 'ec-pairs.json']
LOOSE  = {'void-pairs.json': [os.path.join(FLOOR, f) for f in
                              ('realis-newsale-all-sg.json', 'realis-resale-all-sg.json')]}

def _window_end(d):
    """The last month a JSON says it covers. The scripts write this three different ways."""
    for v in (d.get('window'), d.get('late_window'), (d.get('meta') or {}).get('window')):
        if isinstance(v, (list, tuple)) and len(v) == 2: return str(v[1])
        if isinstance(v, str) and ' to ' in v:           return v.split(' to ')[-1].strip()
    return None

def upstream_month():
    p = json.load(open(os.path.join(DATA, 'psf-history.json')))['projects']
    return max(m for v in p.values() for b in v.values() for m in b)

def _months_between(a, b):
    (ay, am), (by, bm) = (int(x[:4]) for x in (a, b)), (int(x[5:7]) for x in (a, b))
    return (by - ay) * 12 + (bm - am)

def check():
    """Complaints only — a JSON that does not sit at the declared cut. Empty means consistent."""
    bad = []
    for name in PINNED:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            bad.append(f'{name}: MISSING — run the script that writes it'); continue
        end = _window_end(json.load(open(path)))
        if end and end != cut.CUT_END:
            bad.append(f'{name}: cut at {end}, but cut.py declares {cut.CUT_END} '
                       f'— re-run the chain, or fix the pin')
    for name, srcs in LOOSE.items():
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            bad.append(f'{name}: MISSING — run the script that writes it'); continue
        for s in srcs:
            if os.path.exists(s) and os.path.getmtime(s) > os.path.getmtime(path):
                bad.append(f'{name}: {os.path.basename(s)} is newer than it')
    return bad

def drift():
    """How many months the data has run past the pin. Information, never an error."""
    have = upstream_month()
    return have, _months_between(cut.CUT_END, have)

def gate(argv=()):
    """build-page.py's gate. Fails ONLY on inconsistency with the pin, never on new data."""
    bad = check()
    have, n = drift()
    if bad:
        print('\nOUT OF STEP WITH THE DECLARED CUT '
              f'({cut.CUT_END}, "{cut.VINTAGE}"):\n')
        for b in bad: print(f'  · {b}')
        print('\nRe-run the chain IN ORDER, then build — see README section 2.\n')
        sys.exit(1)
    note = f'  figures: as of {cut.VINTAGE} (cut at {cut.CUT_END})'
    if n > 0:
        note += (f' · data now runs to {have}, {n} month{"s" if n != 1 else ""} past the cut'
                 f' — re-cut deliberately, never automatically')
    print(note)

if __name__ == '__main__':
    bad = check(); have, n = drift()
    print(f'declared cut: {cut.CUT_END}  ("as of {cut.VINTAGE}")')
    print(f'data on disk: {have}' + (f'  — {n} month(s) past the cut' if n > 0 else '  — level'))
    if bad:
        print('\nOUT OF STEP:')
        for b in bad: print(f'  · {b}')
        sys.exit(1)
    print('\nevery calibration JSON sits at the declared cut.')
    if n > 0:
        print(f'Newer data exists but is deliberately NOT counted. To re-cut: move CUT_END and '
              f'VINTAGE in cut.py together, re-run the chain, and read what moved.')
