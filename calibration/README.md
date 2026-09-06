# Price Gap constant calibration — TAKEOVER

**Read this file first, then the docstring of whichever script you are touching, then the page
they build.** Everything below is either a ruling Shawn gave or a result measured against the
market. Nothing here is a default.

Last worked **2026-09-06**. Commits `price-gap 5561e54`, `kya-maps-calculator d2e5c20`, both on
main and pushed. Page live on offline staging, hidden behind a double-click on the Live Data chip.

**THREE OF THE FOUR CONSTANTS ARE MEASURED. TENURE IS NEXT — see §9.**

| constant | engine says | measured | where |
|---|---|---|---|
| Lease difference | $40 flat | **$25 / $43** by midpoint | §3 |
| MRT distance | $50 / $200 / $250 | **+$66 / +$156 / +$243**, or **$23 per 100 m** | §11 |
| Integrated | +5% | **+6.7%** (4.5–9.1), which CONTAINS the +5% | §12 |
| Tenure · FH vs LH | ÷1.15 | — **next** | §10 |

GFA harmonisation (+7%) was **dropped from the study entirely** on his ruling, 2026-09-06.

---

## 1. STATUS

| | |
|---|---|
| **Lease / vintage term** | **MEASURED AND SHIPPED.** See §3. |
| **Integrated development (+5%)** | **MEASURED AND SHIPPED.** See §12. |
| **MRT walk band ($50/$200/$250)** | **MEASURED AND SHIPPED.** See §11. |
| Tenure · FH vs LH (÷1.15) | judgement only — **next**, see §10 |

**NOTHING HAS BEEN WRITTEN BACK TO `../scripts/price-gap.ts` AND NOTHING MAY BE** until
Shawn audits. This folder is a validation table that sits BESIDE the constants. That is
framing ruling 3 and it is the one that matters most.

---

## 2. RUN IT

**THE ORDER IS MANDATORY.** Each script consumes the one before it: `mrt-pairs.py` reads the
lease bands out of `lease-pairs.json`, and `integrated-pairs.py` reads both the lease bands and
the $/100 m slope out of `mrt-pairs.json`. Run them out of order and you will silently calibrate
against stale inputs.

```bash
python3 lease-pairs.py        # -> lease-pairs.json
python3 mrt-pairs.py          # -> mrt-pairs.json        (needs lease-pairs.json)
python3 integrated-pairs.py   # -> integrated-pairs.json (needs both of the above)
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

## 10. NEXT — TENURE, FREEHOLD vs LEASEHOLD

**The only constant left, and the biggest sample available.** Of the 1,844 developments in
`dsi-index.json`, **1,255 are FREEHOLD** and structurally cannot pair on lease start — which is
the real ceiling on this whole workstream, not the pair screens.

**THE PRIZE IS NOT THE CONSTANT, IT IS THE DOUBLE-COUNT.** Framing ruling 2: *lease and tenure
are ONE curve, not two terms* — at the far end of a lease the freehold gap IS the lease gap, so
the engine may be charging for the same thing twice. **The test is whether the lease slope
extrapolates onto the freehold gap.** If it does, the double-count is proven and that matters
more than the ÷1.15.

**THE METHOD IS ALREADY BUILT.** Copy `mrt-pairs.py`'s shape: neighbour pairs at the same station,
one FH and one LH, with the lease difference removed at the measured two-band rate and the
walking difference at the measured $/100 m. Both inputs come out of the JSON, never as literals.
**Build the placebo first** — FH-vs-FH and LH-vs-LH pairs under the same corrections must read
zero — because on this study the placebo has decided every screen ruling.

**BUILDING AGE IS THE CONFOUND TO WATCH.** It is not measured, and an FH-vs-LH pair can differ on
it freely. `AGE_PSF_PER_YEAR = 10` in the engine is also unvalidated. FH-vs-FH pairs decompose it
for free (~555 available) and would validate that constant as a by-product.

After tenure: the study premium, then the bedroom step as QUANTUM matched within project.

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
