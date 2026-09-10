# Price Gap constant calibration — TAKEOVER

**Read this file first, then the docstring of whichever script you are touching, then the page
they build.** Everything below is either a ruling Shawn gave or a result measured against the
market. Nothing here is a default.

Last worked **2026-09-08**. Commits `price-gap 5a82f7c`, `kya-maps-calculator a254024`, both on
main and pushed. Page live on offline staging, hidden behind a **double-tap on the "K" brand mark** (it was the
Live Data chip until 2026-09-10; that chip is xl-only and never rendered on a phone).

**ALL FOUR CONSTANTS ARE MEASURED.** The tenure pass closed on 2026-09-08 — see §10.

| constant | engine says | measured | where |
|---|---|---|---|
| Lease difference | $40 flat | **$25 / $42** by midpoint | §3 |
| MRT distance | $50 / $200 / $250 | **+$67 / +$144 / +$215**, or **$23 per 100 m** | §11 |
| Integrated | +5% | **+11.0%** — MOVED from +6.7% on one month of new data, see §12a | §12 |
| Void · extra penthouse area | **none — 1.00× implicit** | resale buyer pays **52% less** for it than for the floor plate | §13 |
| Tenure · FH vs LH | ÷1.15 | **+17%**, and **+11% → +22%** by the lease left | §10 |

| EC vs private condo | **no constant — reference only** | **+29.4%** at launch, **−0.7%** at resale | §14 |

GFA harmonisation (+7%) was **dropped from the study entirely** on his ruling, 2026-09-06.

---

## 0. RE-RUN OF 2026-09-10 — READ BEFORE QUOTING ANY FIGURE BELOW

Two things happened in one run and they must not be confused.

**1. The estimator changed, on Shawn's ruling.** `fitted()` was the ratio form
`sum(diff)/sum(gap)`; it is now **least squares through the origin**, `sum(diff*gap)/sum(gap^2)`.
Tested, not assumed: the residual spread is FLAT across gap widths (sd ~$100-170 whether a pair
is one year apart or twenty), so variance is constant and this is the efficient estimator. The
ratio form is optimal only if variance grows with the gap. Held-out prediction is identical to
the dollar, so this is a defensibility fix, not an accuracy one. Fitted with an intercept it
lands indistinguishable from zero (t = -0.6, -0.7), so through-origin is the right shape.

**2. The 24-month window rolled forward a month** — `2024-09..2026-08` became
`2024-10..2026-09` — because upstream now carries 2026-09. Nobody asked for this; it happens
automatically on any re-run. It moved everything.

| lease band | up to 2010 | 2011 onward |
|---|---|---|
| old window, ratio — **what was published until today** | $24.9 | $42.9 |
| old window, OLS — the figure Shawn approved as "25/44" | $25.4 | $44.0 |
| new window, ratio | $23.9 | $39.9 |
| **new window, OLS — WHAT IS LIVE NOW** | **$24.7** | **$42.3** |

The estimator adds about +$0.8 / +$2.4; the window roll takes off about -$0.7 / -$1.7. **The
headline is $25 / $42, not the $25 / $44 that was approved.** Both effects are real; they
happened to point opposite ways.

**THE INTEGRATED PREMIUM IS THE WARNING.** One extra month moved it **+6.7% -> +11.0%** on a cut
that went from 7 pairs to 8. Every cut moved the same way (every pair 5.95 -> 9.07). It is the
thinnest figure in the study and it is not stable enough to put in front of a client without
saying so. MRT moved +$66/+$156/+$243 -> +$67/+$144/+$215; tenure +18% -> +17.2%.

**Any figure quoted below this line predates the re-run unless it says otherwise.**

---

## 1. STATUS

**All five are measured, and as of 2026-09-09 all five are LIVE in the engine.**

| | |
|---|---|
| **Lease / vintage term** | **MEASURED AND SHIPPED.** See §3. |
| **Integrated development (+5%)** | **MEASURED AND SHIPPED.** See §12. |
| **MRT walk band ($50/$200/$250)** | **MEASURED AND SHIPPED.** See §11. |
| **Void · extra penthouse area** | **MEASURED AND SHIPPED.** See §13. No engine constant exists. |
| **Tenure · FH vs LH (÷1.15)** | **MEASURED AND SHIPPED.** See §10. |

**AUDITED AND ADOPTED — Shawn, 2026-09-09.** The measured constants are now THE constants:
`engine.ts` exports `loadConstants()` (which resolves the measured set), the CLI defaults to
it, the all-developments batch emits a single column, and the workup panel no longer carries a
toggle. Framing ruling 3 — "results sit BESIDE the constants and never write back until Shawn
audits" — is DISCHARGED by that audit, not overridden.

The figures are still READ FROM the JSONs in this folder at load time and are not hardcoded in
the engine, so re-running a fit still moves the engine. That part of the rule stands forever.

The pre-calibration set is RETIRED, not deleted: `JUDGEMENT` remains in `engine.ts`, travels in
the dataset as `retired`, and the workup shows it beside the live figure under "Replaced".

WHAT DECIDED IT: on held-out pairs of real neighbouring projects the measured form lands 26%
closer to the market — error 289 against the engine set's 389, where no adjustment at all is
412. The engine's $200 mid-to-far rail band sits OUTSIDE the measured 95% range of $120–194.

---

## 2. RUN IT

**THE ORDER IS MANDATORY.** Each script consumes the one before it: `mrt-pairs.py` reads the
lease bands out of `lease-pairs.json`, and `integrated-pairs.py` reads both the lease bands and
the $/100 m slope out of `mrt-pairs.json`. Run them out of order and you will silently calibrate
against stale inputs.

**CHECK FIRST, ALWAYS: `python3 freshness.py`.** It answers the one question that cost a session
on 2026-09-10 — are these figures still the data's answer, or an old snapshot's? It compares every
calibration JSON against the source files behind it two ways: source-file mtime, and the JSON's own
window end against the last month in `psf-history.json`. `build-page.py` runs the same gate and
**REFUSES TO BUILD** when anything is stale, so the page can no longer disagree with its data.
Deliberately re-cutting an older window is `python3 build-page.py --stale-ok`, which says so loudly
rather than going quiet.

```bash
python3 freshness.py          # are the figures current? run before quoting ANY of them
python3 lease-pairs.py        # -> lease-pairs.json
python3 mrt-pairs.py          # -> mrt-pairs.json        (needs lease-pairs.json)
python3 integrated-pairs.py   # -> integrated-pairs.json (needs both of the above)
python3 void-pairs.py         # -> void-pairs.json       (independent — order-free)
python3 tenure-pairs.py       # -> tenure-pairs.json     (needs lease-pairs.json)
python3 build-page.py         # -> ../../kya-maps-calculator/calibration.html
cd ../../property-analyzer && npm run maps:deploy
```

**No constant is ever hardcoded across scripts.** An earlier version copied 25/44 into
`mrt-pairs.py` as literals and they went stale the moment `lease-pairs.py` was re-run. If you
need a measured figure in another script, DERIVE IT from that script's JSON.

Then commit both repos. Every change ends with a staging deploy AND a commit+push —
standing rule, not optional. Report it in one line: the link and the hash.

`lease-pairs.py` is a **read-only** consumer of `../../property-analyzer/data/`, the same
arrangement as the engine and `enbloc-analyzer`. It writes nothing upstream. If a run looks
stale, refresh upstream first (`npm run maps:refresh`) — nothing here regenerates those files.

### The page
`calibration.html` is **hidden**: the only way in is a **double-click on the Live Data chip**
at the top right of the calculator (`kya-maps-calculator/index.html`, `#liveDataChip`). It is
in neither nav. A working document, never a client view.

* **It is GENERATED. Never hand-edit the HTML** — `build-page.py` overwrites it.
* It is in the `FILES` allowlist in `property-analyzer/scripts/deploy-maps.mjs`. That list is
  explicit; a site file missing from it deploys as a dead link.

---

## 3. THE ANSWER

**234 developments · 249 pairs · 416 cells.** 24 months of resale and sub-sale.

| midpoint of the two lease starts | $ psf / yr | 95% | devs | pairs |
|---|---|---|---|---|
| up to 2010 | **$25** | 22.1–27.4 | 160 | 143 |
| 2011 onward | **$43** (a FLOOR) | 37.8–47.9 | 106 | 106 |

Against an engine constant of a flat **$40**, which charges an old pair 1.6× what the market
pays and short-changes a new one. Held-out error: flat 24.0k · **two bands 20.7k** · three
bands 20.9k.

### Say what the figure IS before quoting it

Two condos next door, one leased a few years after the other. **The figure is how much more
per square foot the newer one fetches, FOR EACH YEAR of that difference.**

**THE NEWER BAND IS THE STEEPER ONE.** Shawn read it back as *"2011 onwards stay rather
stagnant"* — the opposite of the finding. Being newer is worth nearly TWICE as much inside
the newer cohort. Lead with the plain-English meaning; bare figures invite this misreading.

**Likeliest cause, stated as a likelihood and never as a finding:** through the 2010s each
successive launch in the same location came out materially dearer than the last. This study
measures the SIZE of the effect, not the cause.

### READ AT THE MIDPOINT — the load-bearing idea

Shawn broke an earlier lease-start banding in one question: *what do I use for a 2005-vs-2025
pair?* If the rate varies with vintage, the whole difference across an interval is the gap
times the rate at its MIDPOINT — so the midpoint form **is** the blend and a pair straddling
any boundary needs no decision. **Never band on `ls_old` again.**

---

## 4. THE SCREENS — every one is a ruling

His method, his words: *find projects exactly next to each other with all else constant, where
the only difference is the lease start year; then compare average PSF bedroom against bedroom.*

| screen | value | why |
|---|---|---|
| distance apart | **500 m** | quality holds to 800m; 500 is where he stopped |
| MRT | **same nearest station** | two projects 400m apart can feed different stations on different lines |
| walk band | **NOT screened** | RETIRED 2026-09-06 — see §6 |
| schools | **identical top-26 primary schools within 1 km** | the 1km catchment is all-or-nothing |
| units | **200+ both sides** | "because I want good volume". Re-tested 2026-09-06 and his ruling holds — see §6 |
| transactions | **5+ each side, in window** | |
| size match | **within 20%**, bedroom by bedroom | 15% cost 44% of the sample for less bias than it removed |
| EC | **allowed once privatised, TOP + 5** | before that it prices like subsidised stock |
| lease gap | **NO MINIMUM** | "I don't need the lease gap to be a certain amount." The old 5-yr screen is retired — see §6 |
| window | **24 months.** 12 is a freshness check only | NOT independent: 54 of 56 clean 12m cells sit inside the 24m set. 24m IS the combined figure. **Never average them** |
| floor, facing | **not controlled** | ruled: "accept the noise". The PSF series carries no floor |
| bands | **on the MIDPOINT, fixed calendar years** | see §3 and §5 |
| scale | **dollars, never a percentage** | quantum only, his ruling |

### Bedroom is the MATCH, not the answer
It is not in the equation. It is the stratum that holds size constant, and the finest size
resolution the data has — PSF is stored project × bedroom × month and there is nothing below
it. Shawn asked whether size alone would do: tested, and pooling to one PSF per project matched
on pooled size **LOSES** pairs (159 vs 231 — matching a whole sales mix within 20% is harder
than matching one bedroom) and lets mix leak at ~−$249 psf per 100% of unmatched size.
`build_pooled()` keeps it as a diagnostic.

---

## 5. THE BANDS DO NOT MOVE AS THE STOCK AGES

Shawn asked whether the ranges should slide forward each year, on the theory that this is
really age and that lease decay will eventually drag PSF down.

**Tested.** `build_between()` runs the identical method on 2021-08..2023-07 sales, three years
earlier (stored in `lease-pairs.json` as `early24`). **The jump sits at the same CALENDAR band
in both runs.**

| midpoint | 2021–23 sales | age then | 2024–26 sales | age now |
|---|---|---|---|---|
| up to 2005 | +$24 | 26 yrs | +$25 | 30 yrs |
| 2006–2008 | +$28 | 18 yrs | +$20 | 21 yrs |
| 2009–2011 | +$26 | 13 yrs | +$25 | 16 yrs |
| **2012–2014** | **+$43** | 11 yrs | **+$49** | 14 yrs |
| 2015+ | +$73 | 8 yrs | +$51 | 12 yrs |

The 2012–2014 band aged four years and kept paying the high rate. If it were age, the high band
would have slid ~3 years later. **This is calendar vintage. Do not re-cut the bands by age.**
Age ranges may be shown in brackets as description only.

**On decay — right mechanism, wrong gradient.** Decay bites on lease REMAINING, knee at 60–65
years. Here the older side has a median 74 years left and only **16 of 382 cells** are below the
knee, so decay is nearly absent. And it runs the OTHER way: the band with MORE lease left pays
MORE. Decay will arrive around the end of this decade as the OLDEST band steepening — a new
figure for old stock, never a sliding boundary. Re-run then.

---

## 6. WHAT WAS TESTED — all recomputed 2026-09-06

| tested | reads | verdict |
|---|---|---|
| bedroom, 2BR vs 3BR | $0.2 apart, p=0.95 | no difference |
| region, up to 2010 | RCR $26 · OCR $27, p=0.89 | no difference |
| **region, 2011 onward** | **RCR $62 · OCR $37, p<0.001** | **REAL** — why that band's interval is wide. Splitting does not predict better (27 RCR pairs), so one figure, disclosed on the page |
| the CCR | 19 cells | not measurable — all Marina Bay / Sentosa. A submarket, not a region |
| fitted curve or knee | moved with the sample | **NOT identified — do not report one.** See §7 |
| dropping the 200-unit floor | added pairs read $33, no gradient | floor stays; his original ruling holds |
| matching on size not bedroom | 159 pairs vs 231, mix leaks −$249 psf per 100% size | bedroom is the better control |
| minimum lease gap | no change at any threshold | retired; it protected an estimator this page does not use. Removing it roughly tripled the sample |
| walk-band match | cost 20 new-end pairs at 258–414 m | retired |
| **unit sizes shrank, so psf overstates it** | raised again 2026-09-06 and re-tested in DOLLARS, not psf. Sizes did shrink at the same 2011 break (3BR 1,245 → 1,014 sqft, 2BR ~900 → 714), but priced per home the gap is $27,052 vs $39,525 a year — +46% against +78% in psf. Size closes about 40% of it | **REJECTED as the explanation, twice.** Pairs are already size-matched within 20% bedroom-by-bedroom, so the rate carries no size contamination: 3BR alone reads $27.5 → $42.1. **Shawn ruled 2026-09-06 that none of this goes on the page — psf figures, nothing else.** Do not raise it a third time |

### Why the newer band is nearly double — and HOW to show it
The test: if something other than vintage explained the jump, then looking only at pairs alike
in that respect would make the jump SHRINK. It does not.

| looking only at… | up to 2010 | 2011 onward | the jump |
|---|---|---|---|
| all pairs | $25 | $44 | **+$19** |
| small units, under 900 sqft | $18 | $43 | **+$25** |
| large units, 900 sqft+ | $26 | $45 | **+$19** |
| close lease gaps, 1–4 yrs | $26 | $44 | **+$18** |
| wide lease gaps, 5 yrs+ | $25 | $44 | **+$20** |

**The last column is the whole argument and the table must read at a glance.** An earlier
version packed two figures into one cell as "$18 · $26" with the key in prose — Shawn could not
read it and said so. One row per split, one number per cell, a jump column.

A higher base price explains only part (1.61% → 2.45%: narrows in percent, does not close).

---

## 7. FOUR SHAPES DIED. DO NOT RESURRECT ANY OF THEM.

1. **Flat $40** (the engine). Wrong at both ends at once.
2. **Two bands on `ls_old`** ($25 pre-2010 / $44 2010s). Killed by the straddle question in §3.
   **Note the coincidence:** the current answer is also $25/$43 but banded on the MIDPOINT,
   which is a different and correct thing. Do not confuse them.
3. **A straight line on the midpoint.** Ran low at BOTH ends.
4. **A fitted knee** (flat, then rising). Fixed the line on 168 pairs — then MOVED when the
   screen widened to 231. The best knee is now anywhere in 1998–2008 and the fit changes under
   2% across that whole span.

**The LEVEL (~$25) is the robust finding; a fitted tail is not.** The slope moved 1.40 → 3.57 →
1.67 across three sample changes. That instability is itself the result. Report measured bands.

---

## 8. TRAPS

1. **NOTHING IN THE PAGE PROSE MAY BE HARDCODED.** An earlier build carried p-values and
   coefficients as literals; two went stale AND FLIPPED and were still displayed as fact after
   the screen changed. Every figure is now computed in `build-page.py`. **If you add a claim,
   compute it.**
2. **The page is generated.** Never hand-edit `calibration.html`.
3. **Do not quietly change a screen in §4.** Every value is a ruling. Changing one silently
   throws away an audit he already gave.
4. **`lease-pairs.py` is read-only** on `property-analyzer/data/`.
5. **New sale is excluded** from `psf-history.json` by his 2026-07-14 ruling. This is why young
   stock is thin — it has barely resold.
6. **The honest limit:** in a leasehold-vs-leasehold pair, lease start and building age are
   perfectly confounded. What is measured is the **blended vintage** effect — which is exactly
   what the engine's term does, so it is a valid like-for-like validation. It is **not** a
   decomposition into lease and bricks.


### TRAPS ADDED 2026-09-06 (the MRT and integrated passes)

* **DO NOT HARDCODE A MEASURED FIGURE INTO ANOTHER SCRIPT.** 25/44 was copied into
  `mrt-pairs.py` and went stale the moment `lease-pairs.py` was re-run. Derive from the JSON.
* **RUN THE SCRIPTS IN ORDER** — lease → mrt → integrated → build-page. See §2.
* **THE PLACEBO DECIDES THE SCREENS, NOT JUDGEMENT.** Every screen ruling on the MRT and
  integrated passes was settled by what the placebo did. A relaxation that buys pairs and breaks
  the placebo is buying bias. Dropping the school screen (−6.9), size 20%→30% (−9.0) and
  same-station (−1.7 → **+26.8**) were all rejected on that basis alone.
* **DO NOT BUILD A RANGE OUT OF THE THINNEST CELL.** The integrated premium was published as
  "+6.5% to +9.9%"; the upper bound came from an 8-pair cell in a non-monotonic column that drops
  2.1 points when three pairs are added. Shawn caught it. It is now a single figure with an
  interval.
* **CHECK WHETHER A FLAG IS ACTUALLY POPULATED BEFORE MEASURING WHAT IT CONTROLS.** The engine's
  `integrated` flag reads from an override file that flags nothing, so its ±5% has never fired on
  a single comparable. That was worth more than the measurement.
* **THE PAGE IS GENERATED AND IT IS CLICK-THROUGH.** Four panels, hash-linkable, term bar in the
  sticky header. Never hand-edit `calibration.html`.

## 9. WHERE THE DATA COMES FROM

Everything needed was already on disk. The non-obvious parts, which cost time to find:

| need | file | note |
|---|---|---|
| tenure, lease start | `pricegap-base.json` | tenure exists NOWHERE else in the dataset; parsed from URA PMI free text |
| lat/lng, region, district | `dsi-index.json` → `projects` | |
| **top-26 primary schools, with rank AND coords** | `dsi-index.json` → `schools` | not in `area-schools.json`, which is keyed by name and carries no coords |
| units, TOP year, EC flag | `pg-project-details.json` → `projects` | `projectType == "Executive Condominium"`; note the nested `projects` key |
| PSF per project × bedroom × month | `psf-history.json` | resale + subsale only. **New sale is deliberately excluded** (Shawn, 2026-07-14) |
| **transaction counts and median sqft** | `quantum-history.json` | `[medianPrice, medianSqft, n]` per month — this is what makes the n≥5 and ±20% size screens possible |
| labelled unit types incl. "+ Study" | `project-unitmix-realsmart.json` | for the study premium, not yet used |

**There is no caveat-level store anywhere.** Everything in `data/` is pre-aggregated to
project × bedroom × month medians. The 2026-07-27 lease-decay study fetched 72,548 caveats
fresh and did not persist them. Any true unit-level hedonic needs a re-fetch from URA PMI —
the pattern is `property-analyzer/scripts/fetch-demand-ura.ts`, 60-month serving depth,
`URA_ACCESS_KEY` is in `.env.local`.

---

## 10. TENURE — FREEHOLD vs LEASEHOLD — MEASURED

`tenure-pairs.py` → `tenure-pairs.json` → `build-page.py`. **105 developments · 78 pairs ·
102 cells**, on the identical lease-study screens.

### THE ANSWER — it is not a constant

| lease left on the leasehold side | freehold is worth | 95% | pairs |
|---|---|---|---|
| 90+ years | **+11.3%** | 3.0–14.7 | 15 |
| 75–89 | **+20.7%** | 15.9–25.1 | 43 |
| 60–74 | **+21.6%** | 14.9–32.1 | 16 |
| **all pairs, one figure** | **+18.1%** | 14.1–22.4 | 78 |

**THIS IS THE DOUBLE-COUNT, AND IT IS PROVEN.** Framing ruling 2 said lease and tenure are ONE
curve. If they were separate, that column would be flat. It roughly doubles as the lease runs
down, and it survives refitting the vintage rate freely. A flat ÷1.15
overcharges freehold against new leasehold and undercharges it against old.

### THE FOUR RULINGS THAT SHAPED IT (Shawn, 2026-09-08)

1. **THE CLOCK IS TOP, NOT LEASE START** — *"lets match on TOP year instead of lease start
   year."* A freehold has no lease start, and 999-year stock (which he ruled is **freehold**)
   carries real lease starts back to 1827.
2. **NO TOP SCREEN** — *"we dont need to match TOP, the question is also how do we adjust for
   TOP differences."* The vintage rate is part of the answer, not a nuisance to screen away.
3. **THE HORSE RACE** — *"It could be $10psf per year to match TOP followed by 15% premium. OR
   we could do 44psf per year adjustment then adjust by 15% premium. Whichever makes more
   sense. I want the data and number to tell."* So the rate, the form AND the order are all
   fitted and ranked on held-out error.
4. **REUSE $25/$43 AS MEASURED**, read at the midpoint of the two lease-start equivalents.
   Derived from `lease-pairs.json`, never a literal.
5. **DERIVE THE SUBJECT'S REMAINING LEASE FROM ITS TOP YEAR** — *"can't the lease left on
   subject be auto calculated? based on TOP year"* — which forced the build gap to be
   measured. See below. On the page that field is **LOCKED** and fills itself; the lock is the
   only way to take it over, because the inference is right often enough that overriding it by
   habit would do more harm than good.
6. **PERCENT ONLY, NO QUANTUM** — *"Change it all to %, i dont need quantum."* See the scale
   section below.
7. **THE CALCULATOR RUNS BOTH WAYS** — freehold in, leasehold out, and the reverse. One
   equation read either way: `freehold = (leasehold + age) × (1 + premium)`.

### THE RACE — held-out RMSE in psf, lower is better

| age gap removed at | premium | reads | error |
|---|---|---|---|
| nothing at all | none | — | 412 |
| **$40/yr — the engine as written** | ÷1.15 after | 15.0% | **389** |
| $40/yr | % after | +17.9% | 390 |
| $10/yr | % after | +11.4% | 335 |
| **the measured $25/$43** | % after | **+18.1%** | 289 |
| the measured $25/$43 | % **before** | +17.0% | 284 |
| the measured $25/$43 | a flat dollar figure | +$328 | 269 |
| freely fitted ($13/yr) | none | — | 391 |

* **THE ENGINE AS WRITTEN IS BARELY BETTER THAN DOING NOTHING** — 389 against 412 — and the
  $40 is why: on a completion-year clock it scores worse than $10 does.
* **PERCENT, NOT DOLLARS — and this REVERSED on 2026-09-08.** He ruled it: *"Change it all
  to %, i dont need quantum."* A deliberate exception to the dollars-never-percent rule that
  governs the lease study, and the measurement backs it. Random held-out folds mildly favour a
  flat dollar figure, but a random fold looks like the sample it came from — exactly where an
  addition and a ratio cannot be separated. **The test that separates them is TRANSFER:** fit
  without one price tier and predict that tier, then the same by region.

  | held out | percent misses by | dollars miss by |
  |---|---|---|
  | cheapest third ($1,252) | **121** | 211 |
  | middle third ($1,798) | 345 | **313** |
  | dearest third ($2,316) | 393 | **313** |
  | *average* | 286 | 279 |
  | CCR / RCR / OCR average | **304** | 306 |

  Level overall, and it splits the way a percentage would predict — percent wins on the
  cheapest stock and in the OCR, where a flat dollar figure is far too large a share of the
  price. Region also reads flat in percent and roughly 2× in dollars. **Do not re-run this
  as a fold count and conclude dollars; that was the mistake the first pass made.** The
  sample spans $1,252–$2,316 psf and settles neither end.
* **BEFORE OR AFTER DOES NOT MATTER** — 288.6 against 283.5, inside the noise. And **a dollar
  premium is order-free**, because two additions commute. Choosing dollars deletes the
  question he asked.
* **A FREEHOLD PREMIUM GENUINELY EXISTS BEYOND VINTAGE** — the best no-premium row is 387.

### THE CHECKS

* **BOTH PLACEBOS READ ZERO.** LH×LH $+1 (276 pairs), FH×FH $−1 (90 pairs). **The slot must
  be randomised**: assigning the freehold slot ALPHABETICALLY read a false +2.9% on the FH set,
  purely because alphabetically-earlier freeholds happened to sit newer. That is not an
  estimator bias and it must not be reported as one.
* **BY-PRODUCT — the engine's `AGE_PSF_PER_YEAR = 10` reads $18.** FH×FH pairs measure it
  directly, since nothing else separates them.
* **REGION:** flat in percent across CCR/RCR/OCR, but roughly double in the CCR in dollars.
  This is the ONE reading that argues for the percentage form, which is why the percentage
  stays on the page beside every dollar figure. **Bedroom:** 2BR and 3BR agree; 1BR and 4BR+
  too thin.

### THE 200-UNIT FLOOR STANDS — and this one needed proving

Dropping it to 100 units nearly HALVES the premium (+18.1% → +10.9%), so it could not be
waved through. **His ruling:** *"the problem with <200 units is that there are little to no
transaction volume which might make it inaccurate due to lack of volume averages."*

The data says exactly that. The 81 pairs the lower floor adds run on a median of **6 sales**
on the freehold side against 9 in the headline, **93% of them under ten a side** against 65%,
and fitted alone they read a directionless **+3.9%**. Freehold stock is mostly boutique, so this
floor bites harder here than on the lease study. **A five-transaction cell minimum is a floor,
not a volume.** Distance, by contrast, barely moves it: 800 m gives +16.0%, 1 km +15.5%.

### A FIFTH CONSTANT FELL OUT: THE BUILD GAP IS 4 YEARS, NOT 6

He asked whether the calculator could work out the subject's remaining lease from its TOP year.
It can, and answering it measured something nobody had checked: **`CONSTRUCTION_YEARS = 6` in
the engine is 4 in the market.** Across the **573** leasehold developments carrying both dates
the median TOP-minus-lease-start gap is **4 years** (quartiles 4–5), and **98%** of leasehold
stock is on a 99-year lease. So `lease left = 99 − (this year − TOP) − 4`, good to a year or
two against gradient steps fifteen years wide. The page derives it and says `FROM TOP`; typing
in the field takes it over and the tag flips to `ENTERED`.

**The engine uses that 6 elsewhere** — to invent a TOP year for any development with no
completion year on record — so it is worth fixing there whatever is done with the tenure
figure. Both figures are DERIVED in `tenure-pairs.py` (`BUILD`), never literals.

**It barely moves this study**, which is why the headline could be restated on the measured
gap without argument: the premium reads +17.1% at an offset of 6, **+18.1% at the measured 4**,
+18.4% at 3.

### THE CONFOUND TO KNOW, AND IT IS THE REAL LIMIT

**Freehold is the OLDER side in 73 of the 102 cells**, median 6 years, and the age adjustment
that removes it is a median **$224 psf — 12% of the base, the same size as the premium being
measured**. The answer leans on the vintage rate being right. Fitting that rate freely instead
of importing the measured bands gives **+14.6%**, so read +18.1% as the top of a range that
starts there. **The 90+ step is the unsettled one** — it has moved twice as the method tightened
(9.0% → 11.3% when the build gap was measured). The climb is the finding; that step's level
is not. The two lower steps have barely moved. Floor, facing and building quality stay uncontrolled by ruling.

## 11. MRT WALK BAND — MEASURED

`mrt-pairs.py` → `mrt-pairs.json` → `build-page.py`. **The lease study inverted:** station held
constant, walk band varies, lease removed at the MEASURED $25/$43 midpoint rate — never the flat $40.

**290 developments · 450 pairs · 716 cells.**

**THE LINES ARE 400 m AND 800 m**, applied straight to the map distance — 80 m a minute, five
minutes and ten. **NOT** the engine's 308/615, which inflates every distance by a 1.3 circuity
first. See "the lines" below.

| walk to the nearest station | measured | 95% | devs | engine |
|---|---|---|---|---|
| under 5 min vs 5–10 min | **+$65** | +38 to +94 | 125 | $50 — inside the interval |
| 5–10 min vs over 10 min | **+$157** | +120 to +194 | 77 | $200 — OUTSIDE it |
| under 5 min vs over 10 min | **+$239** | +182 to +296 | 30 | $250 — inside the interval |

**Only the middle constant is wrong.** Quote **$23 psf per extra 100 m** whenever the two homes
are not a typical band pair. Placebo **−$10.1**.

### THE LINES ARE THE WEAK PART — and this is the honest uncertainty

Three independent things put them at 400/800 rather than 308/615:

1. **FACE VALIDITY.** At 308 m the bar files **J GATEWAY** (308 m, beside JEM) and **BARTLEY
   RIDGE** (315 m, on top of Bartley station) as five-to-ten-minute walks. That is plainly wrong.
2. **GROUND TRUTH.** CityLife@Tampines measures 869 m here against a real Google route of
   700 m / 10 min — these metres already run ~1.24× the real route, so a further 1.3 circuity
   DOUBLE-COUNTS. Ten real minutes is ~868 m in this study's units.
3. **COHERENCE.** Per-100 m spread across the three rows: **400/800 → 6.0** (tightest tested),
   308/615 → 6.5, 434/868 → 10.9, 354/708 → 19.0.

**THE COST:** the placebo weakens from −1.7 to −10.1 (still inside its own interval). And across
defensible placements the bottom row runs **$162 to $304** — wider than any interval reported.
**That spread, not the confidence intervals, is the real uncertainty.** Only OneMap closes it.

### WHY THE BOTTOM ROW LOOKED LOW AT THE OLD LINES

Most under-5-vs-over-10 pairs barely straddle the line — median 143 m against 712 m, not a
doorstep against a fifteen-minute walk — so the band average was diluted. Split by the walking a
pair actually spans: under 500 m reads −$19, 500–700 m reads +$99, **over 700 m reads +$323.**

### The screen is the STATION'S CATCHMENT, not the distance between the pair

Shawn's correction. Requiring the projects within 500 m of *each other* is self-defeating here:
they differ in walking distance by at most the distance between them, so it caps the measurement.
The under-5-vs-over-10 row had **3 pairs** under that screen and **25** under this one.
Catchment 2000 m; **pair cap 1500 m, set where the PLACEBO breaks** (clean to 1500, +8.6 at 1800).
Leasehold only — freehold was built and dropped, 7–13 pairs a cell and incoherent.

**SAME NEAREST STATION STAYS — tested and confirmed 2026-09-06.** Shawn asked whether the pair
really needs to share a station. Dropping it doubles the sample (509 → 1118 pairs) and **wrecks
the placebo: −1.7 → +26.8.** It is also what makes the metres usable at all, since both sides are
measured to the SAME point and the error cancels. And it does not rescue his Tampines example
anyway: under an any-station rule Treasure sits 654 m from Simei while Citylife sits 869 m from
Tampines, so all three land in the same far band with no contrast to measure.

**RELAXATIONS RULED ON THE PLACEBO, nothing else.** Adopted: pair cap 1200 → 1500 m, transactions
5 → 3, both keeping it clean. **Rejected because they broke it:** dropping the school screen
(−6.9), size match 20% → 30% (−9.0), both together (−14.0). A screen that breaks the placebo is
buying pairs with bias.

### THE BANDS CANNOT BE ADDED — and this is the question he asked

$49 + $111 = $160 but the direct pair reads $122. The rows span **different walking**: 231 m,
438 m, 567 m. Scale for it — 160 × (567/670) = $136 vs $122 measured, inside the interval.
**Per 100 m all three agree: 21.4 · 25.3 · 21.6.**

**PER-100M COHERENCE PICKS THE THRESHOLDS, NOT ADDITIVITY.** A +15% threshold set (354/708 m)
looks additive but reads 15.4 / 31.3 / 33.1 per 100 m — a factor of two on one quantity. The
as-built lines spread 3.9. Additivity can be satisfied by accident; per-metre consistency cannot.

### THE MINUTES ARE NOT RELIABLE. THE METRES ARE.

CityLife@Tampines reads 14.1 min against a real 10-min / 700 m Google route. A station is ONE
POINT when Tampines (DT32+EW2) spans hundreds of metres; some geocodes are ~100 m off. **The tell:
the straight line (869 m) exceeded the actual route (700 m), which is impossible.** Both sides of
a pair are measured to the SAME point, so the error largely cancels in the difference — which is
why the metres hold and the minutes do not. **Band names label the metres, not walking times.**
Fix: OneMap routing + exit locations (`fetch-area.ts` already calls OneMap). ~a day, still unruled.

### OPEN

* **The school screen.** It kills THE TRILINQ vs CLAVON — a genuine mid-vs-far pair on Clementi —
  because Trilinq has Nan Hua Primary within 1 km and Clavon has none. Relax it for MRT or keep it?
  Unruled. Keeping it is the recommendation: it is most of what holds location constant now that
  pairs can sit 1200 m apart.
* **`lease-pairs.py` counts all 223 stations, including the 37 under construction.** `mrt-pairs.py`
  filters to operational. May move a few lease pairs. Unfixed.
* **`lease-pairs.py`'s docstring is STALE** — it still describes the fitted-hinge shape
  ($25.3 flat then +$3.57/yr) that §7 records as dead and not identified.

---

## 12. INTEGRATED DEVELOPMENT — MEASURED

`integrated-pairs.py` → `integrated-pairs.json` → `build-page.py`. An integrated development against
a plain condo at the **same nearest station**; the lease difference removed at the measured
two-band rate and the walking difference at the measured $/100 m. Both inputs are measured here,
neither assumed.

**THE ENGINE'S FLAG IS INERT.** `price-gap.ts` reads `integrated: ov.integrated ?? false` from
`pricegap-overrides.json`, which carries two entries and flags NEITHER. The ±5% has never fired on
a single comparable. **The list of 14 is a classification Shawn audited on 2026-09-06 — a
judgement, not a datum.** Excluded by his ruling: Marina One Residences and both Midtown entries,
all CCR. Excluded as not actually integrated: The Tre Ver, One-North Residences, The Clement
Canopy, City Gate.

| reading only pairs where… | premium | 95% | pairs | adjustment carried | in psf |
|---|---|---|---|---|---|
| every pair | +6.0% | +2.7 to +9.5 | 42 | $485 | +$91 |
| <10 yr lease gap | +7.5% | +4.5 to +11.0 | 26 | $400 | +$120 |
| **<5 yr lease gap** | **+9.9%** | +6.8 to +13.9 | 11 | $172 | +$180 |
| <10 yr gap, within 400 m | **+6.5%** | +3.6 to +9.9 | 13 | $223 | +$119 |
| <5 yr gap, within 400 m | +6.7% | +4.5 to +9.1 | 7 | $118 | +$128 |

**THE ANSWER IS +6.7%, interval +4.5% to +9.1%** — the `<5 yr gap, within 400 m` cut. It carries
the least correction of anything here ($118), it sits in the flat 150–400 m zone where the answer
does not move, and **the broadest cut of all 42 pairs lands beside it at +6.0%.** The two ends of
the reliability range converge on 6–7%; only the unrestricted-distance cuts read higher, and the
sweep below shows why.

**THE ENGINE'S +5% FALLS INSIDE THAT INTERVAL — it is at the low end but NOT demonstrably wrong.**
An earlier version of this page claimed it was "more likely too low than too high" on the strength
of a +6.5% to +9.9% range. That range was built on the unrestricted-distance cuts, which are
inflated by the very leak documented below, and its upper bound came from an 8-pair cell that
moves 2.1 points when three pairs are added. **Do not rebuild a range that way.**

**REPORTED IN PERCENT — a deliberate exception to the dollars-never-percent rule** (Shawn,
2026-09-06). It applies here and nowhere else because **the engine's constant is itself a
percentage**: a dollar figure cannot be set against +5% without a base, and the base moves between
cuts. The dollars stay on the page in the last column.

**THE PLACEBO IS OFF THE FACE AND BEHIND AN EXPLAIN MARK** (his ruling) — plain vs plain reads
−1.1% across 240 pairs, interval covering zero, leaning very slightly negative, which if anything
makes the figures above conservative. It is not deleted; a page may not show a number it cannot
explain.

### THE DISTANCE CUT IS NOT NEUTRAL — swept 2026-09-06 because Shawn asked

Holding the lease gap fixed and sweeping how far apart the two may sit in station-distance:

| the two may sit… | <10 yr gap | prs | <5 yr gap | prs | placebo |
|---|---|---|---|---|---|
| within 150 m | +7.7% | 8 | +6.6% | 6 | −1.4% |
| within 200 m | +5.6% | 11 | +6.7% | 7 | −1.2% |
| within 400 m | +6.5% | 13 | **+6.7%** | 7 | −1.1% |
| within 600 m | +7.8% | 15 | +8.6% | 9 | −0.7% |
| anywhere | +7.5% | 26 | **+9.9%** | 11 | −0.6% |

**Inside the tight lease-gap column the premium climbs 6.6% → 9.9% as the limit loosens, while
the placebo beside it stays flat.** That is what UNREMOVED WALKING EFFECT LEAKING INTO THE ANSWER
looks like: the further apart the two sit, the more of the gap between them is the walk and not
the building. **THE TIGHT ROWS ARE THE CONSERVATIVE ONES and they sit near +7%.** The 400 m cut is
not special — anything from 150 to 400 m reads the same ~6.7%.

### THE SAMPLE CANNOT MEANINGFULLY GROW — tested 2026-09-06

Shawn asked. Loosening every screen barely moves it and **the ≤5-year cut stays at 11 pairs under
all of them**: pair cap 1500→2000 or →3000 (11), transactions 3→2 (11), size 20%→30% (11), adding
the All-bedrooms bucket (11). The binding constraint is not a screen — **there are simply few
MRT-integrated condos in Singapore with resale volume.** The only lever is extending the
classification, and a sweep of every unflagged development within 200 m of its station turned up
just two defensible additions: **ARTRA** (Redhill) and **CANNINGHILL PIERS** (Fort Canning, CCR,
one partner). Neither has been added; both need his audit first.

### THE CONFOUND — the reason this is a range

**Integrated developments are systematically NEWER than their neighbours: +9.0 years of lease gap
against −0.5 for the placebo pairs.** So they carry ~$485 of adjustment each, roughly double the
placebo's, and the answer is what survives a large subtraction. **The less adjustment a cut
carries, the higher and tighter the answer** — the signature of a diluted estimate, not an absent
effect.

**PASIR RIS 8 is the case to understand** (Shawn found this by asking what it was being compared
against). A 2021 lease against neighbours from 1996–2013; its individual answers run **−$424 (vs
Coco Palms) to +$306 (vs Eastvale)**. It carries more pairs than any other integrated development
and reads about zero. **That is noise around a large correction, not evidence that being on the
station is worth nothing.** The same applies to Sengkang Grand and Compass Heights.

### OPEN

* **Populate `pricegap-overrides.json`** so the flag stops being inert. Not done — it writes to a
  file the engine reads, and framing ruling 3 says nothing is written back until Shawn audits.

---

## 13. VOID SPACE — MEASURED

> **THE PAGE IS RESALE ONLY. Shawn's ruling, 2026-09-07:** *"i dont need the developer price list
> actually, I dont need all the developer numbers and figures. ALL i care about is RESALE. Remove
> all developer stuff, these are noise."* The new-sale track is still measured by `void-pairs.py`
> and still documented below — the developer placebo (+1.12%) is the evidence that the resale
> placebo passing means something — but **it does not reach the page.** Do not put it back
> without asking.
>
> **The page shows the RAW resale figure (0.476×, 52% off), not the placebo-corrected one.** The
> resale residual is −0.24% with an interval straddling zero, so there is nothing to correct for,
> and correcting by a figure that cannot be told from zero is worse than leaving it alone. The
> correction is only load-bearing on the developer track, which is off the page.

**1,681 penthouse sales · 125 developments** on the developer track,
119 sales · 60 developments on resale.

| track | base psf | extra-area psf | ratio | 95% | discount |
|---|---|---|---|---|---|
| New sale (price list) | $1,705 | **$374** | **0.23×** | 0.22–0.24 | 77% |
| Resale (same stacks) | $1,832 | $833 | **0.49×** | 0.38–0.59 | 51% |

**THE ENGINE HAS NO CONSTANT FOR THIS.** `price-gap.ts` works entirely in psf and restates each
comparable as one number, so it charges the void the same as a bedroom — an implicit **1.00×**.
A penthouse reads 12% cheaper per square foot than the unit directly
below it and nothing about the home got worse. Any comparison that reaches for a penthouse's
headline psf is reading a blend, not a price.

**Quote a quarter.** Not two decimals — see the sensitivity below.

### The pair
Same project + same block + **same stack**. A stack is one vertical line of units, so the
top-floor unit stands on the same floor plate as everything below it. Where its strata area is
larger, the difference is space the floor plate never gained.

    marginal psf = (penthouse price − floor-adjusted base price) ÷ extra sqft
    ratio        = marginal psf ÷ base psf

Screens: base legs within 3% of the stack's median size and within
270 days of the penthouse sale; **3+ base legs**, so the
comparator is a median; extra area **10–55%**
of the floor plate — under that is a bay window, over it is a **duplex**, which is a second floor
plate and exactly what the pair exists to exclude.

### The placebo decided the answer
The marginal psf is **leveraged**: the extra area is small against the home, so a 2% error in the
base comparator swings it by more than 10%. The threat is a top-floor bonus the linear floor step
does not capture — it would land entirely on the void.

Run the same machinery on stacks whose top unit is the **same size** as those below: no extra area,
so the residual should be zero. Across **3,514 such sales it reads +1.12%**
(1.07 to 1.19) — a real top-floor bonus on developer price lists. Stripping it
off the penthouse leg first takes the answer from 0.29× to **0.23×**.
That corrected figure is the one on the page.

The same placebo on **resale reads -0.24%** across
885 sales — nil. The top-floor bonus is something developers charge and the
resale market does not repeat.

### Sensitivity — some of this IS the floor step
| floor step | ratio |
|---|---|
| 0.3%/floor | 0.32× |
| 0.4%/floor ← measured | 0.29× |
| 0.5%/floor | 0.26× |
| 0.6%/floor | 0.23× |

Range 0.23–0.32,
and the placebo correction lands at the bottom of it. Same bias, two roads.

### The finding worth money
**The spread inside one development is wider than the spread between developments.** Affinity at
Serangoon runs a spread of 1.20 across its own top-floor stacks, Mayfair Gardens 1.10, Sims Urban
Oasis 1.01. At Parc Clematis and Normanton Park some stacks charged **nothing at all** for
140–270 extra sqft. The advice is not "penthouses are good value" — it is **find the stack where
the void was given away**.

### WHAT THIS CANNOT SEE — read before quoting
REALIS records strata area, not what is under the ceiling. **Void, roof terrace and private roof
measure as one thing here.** All three are area on a floor plate that did not grow and all three
price like it. Quote it as **extra penthouse area**; ceiling height is a subset that has not been
separated. Naming which is which needs the floor plan, unit by unit.

### SOURCE IS NOT THE MAPS REFRESH
Every other script here reads `../../property-analyzer/data/`. This one reads the **REALIS
unit-level pull** held by the floor study (`launch-picker/floor-study/data/realis-*-all-sg.json`),
because it is the only local dataset carrying a **unit number** — and without the unit number there
is no stack, without the stack there is no same-floor-plate pair. 2015-01 to 2026-08, all
Singapore, strata, apartment and condominium. Read-only, same arrangement as the others.

### The calculator on the panel
**Shawn's ruling, 2026-09-07: ask for two things and return a quantum range, with the **midpoint** beneath it.

The midpoint is the **measured median (0.49×)**, not (lo+hi)/2. They land within a cent of each
other here, but they are different quantities and the median is the one with evidence behind it.** An earlier version
carried the floor step, the placebo correction, a cheap/at-market/dear verdict and a fair-price
comparison — all of it correct and all of it in the way. It was cut back.

`What should the penthouse cost` takes the **unit below** (sqft and psf), the **penthouse sqft**,
and **how many floors below** it sits.

**The floor lift is not optional and it goes first.** The measurement lifts every base leg to the
penthouse's own floor at 0.4%/floor before taking the median; a calculator that skips it
understates the floor plate and drops the entire error onto the void, which is small enough to be
swamped by it.

**It is applied at every floor gap, one included** — 0.4% for one floor, 4% for ten. Shawn's
ruling, 2026-09-07: *"you should adjust by 0.4% as well no? dont say its immaterial."* Do not
special-case a single floor, and do not describe the one-floor lift as too small to bother with.
The adjustment is the method; its size is not the point. He caught this in the same pass that
restored the field, which had been cut in the simplification. The floor plate is priced at the psf it already sells for; only the **extra area** is
repriced, at the **95% interval on the resale median — 0.38–0.59×**. Output is one line: the
quantum range.

**The band is the interval on the median, not the quartiles.** His call, same day: the quartile
range (0.24–0.78) was too wide to act on. Read it as where the market's *typical* ratio sits, not
where one particular penthouse could land — a single stack can still fall outside it, and the
per-development table shows several that do.

The basis is deliberately **resale, not the price list**. The question the tool answers is what the
space is worth, not what a developer is charging for it. The 0.23× developer figure stays on the
panel above as evidence and out of the calculator.

`void-pairs.py` **depends on none of the other three and they depend on none of it**, so it may be
run at any point in the mandatory order. `void-evidence.csv` is the flat pair-level export.


---

## 14. EC vs PRIVATE CONDO — reference only, never a constant

**Shawn's ruling, 2026-09-10: back pocket.** It exists to normalise a new EC onto private pricing
when he judges what one is worth paying. It does **not** travel downstream into the engine, into a
constant, or into a client figure. The panel says so on its face and nothing reads `ec-pairs.json`
but `build-page.py`.

`ec-pairs.py` → `ec-pairs.json` → the **EC vs Private** panel.

| | |
|---|---|
| At launch | private is **+29.4%** over the EC beside it — 11,768 pairs, 16 EC launches, 95% [17, 34] |
| At resale | **−0.7%** — 24,210 pairs, 56 ECs, 95% [−3.5, +2.3], an interval covering zero |
| By EC age | 5–10 yr **−2.3%** · 10–15 yr **+1.6%** · 15 yr+ **+6.0%** — a mature EC trades *above* |

**THE DATA IS PULLED HERE, NOT READ OFF DISK.** The floor study's REALIS files
(`launch-picker/floor-study/data/realis-{newsale,resale}-all-sg.json`) were pulled as
"Apartment + Condominium" and contain **zero EC transactions**. `ec-pairs.py` calls URA PMI
directly (all four batches, five years, every sale type) and caches the raw pull to
`.ura-raw.json`, which is gitignored — delete it to re-pull.

**THE LAUNCH CUT MATCHES ON DISTRICT, NOT DISTANCE**, because the URA feed carries no coordinates
for an uncompleted project: Rivelle, Aurelle, Copen Grand, Lumina Grand, Novo Place and Otto Place
all read blank. A distance match drops exactly the launches this exists to measure.

**THE BOOTSTRAP IS CLUSTERED BY EC PROJECT.** One EC caveat contributes three comparables and one
project contributes hundreds of caveats, so a pair-level bootstrap returned ±0.2% — a statement
about the resampling, not about the market.

His three slides read 25–36%; the measured column runs +12% to +47% with a median of +29.4%, so
the slides sit mid-market. Rivelle against Pinery size-for-size is +31.6%, and on the two headline
PSFs the slide quotes ($1,934 against $2,548) it is +32%.
