#!/usr/bin/env python3
"""THE CUT — the one place that decides which months the calibration counts.

SHAWN'S RULING, 2026-09-10: *"I want the figures to not be updated by EVERY CRAWL, that is going
to be disruptive as hell. Just say WHEN is it as of, will do. as of 2H2026."*

Before this, every script ended its window at whatever the last month in psf-history.json
happened to be. That meant ANY re-run silently re-cut the study against whatever the crawl had
last dragged in, and every constant moved — the lease bands, the MRT bands, the tenure premium,
and the integrated premium worst of all, which jumped +6.7% to +11.0% on a single extra month.
Figures that move under you are figures you cannot put in a deck.

**The constants are now a DATED CUT, not a live feed.** They change when someone deliberately
moves CUT_END, re-runs the chain and re-reads the numbers — never because a crawl ran.

TO RE-CUT (a deliberate act, not a routine one):
  1. change CUT_END and VINTAGE below, together
  2. re-run the chain in order — see README section 2
  3. READ WHAT MOVED before publishing. freshness.py prints the drift; the last re-cut moved
     the integrated premium by 65%.
"""

# The last month the study counts. PINNED — a crawl bringing newer data does NOT move it.
CUT_END = '2026-09'

# How the page says it. Kept in step with CUT_END BY HAND, because it is the sentence a client
# reads and nobody should be able to change the figures without changing that sentence.
VINTAGE = '2H2026'

def last_month(psf=None):
    """The window end every script must use. Ignores anything newer than the pinned cut.

    Pass psf-history's projects dict to have the pin sanity-checked against reality: a CUT_END
    later than anything on disk is a typo, and it would silently shorten every window."""
    if psf is not None:
        have = max(m for p in psf.values() for b in p.values() for m in b)
        if have < CUT_END:
            raise SystemExit(
                f'cut.py: CUT_END is {CUT_END} but the data only runs to {have}. '
                f'Fix the pin, or refresh upstream.')
    return CUT_END
