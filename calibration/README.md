# Lease-term calibration — TAKEOVER

**Read this file, then `lease-pairs.py`'s docstring, then the page it builds. That is the
whole workstream.** Everything below is either a ruling Shawn gave or a result measured
against the market. Nothing here is a default.

Last worked: **2026-09-06**. Commits `price-gap 2ba534b`, `kya-maps-calculator 938568b`,
both on main and pushed. Page live on offline staging.

---

## 1. STATUS

| | |
|---|---|
| **Lease / vintage term** | **MEASURED AND SHIPPED.** See §3. |
| **MRT walk band ($50/$200/$250)** | **MEASURED AND SHIPPED.** See §10. |
| Tenure · FH vs LH (÷1.15) | judgement only — **next**, see §9 |
| GFA harmonisation (+7%) | judgement only |
| Integrated development (+5%) | judgement only |

**NOTHING HAS BEEN WRITTEN BACK TO `../scripts/price-gap.ts` AND NOTHING MAY BE** until
Shawn audits. This folder is a validation table that sits BESIDE the constants. That is
framing ruling 3 and it is the one that matters most.

---

## 2. RUN IT

```bash
python3 lease-pairs.py     # -> lease-pairs.json, prints every cut to stdout
python3 build-page.py      # -> ../../kya-maps-calculator/calibration.html
cd ../../property-analyzer && npm run maps:deploy
```

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

**226 developments · 231 pairs · 382 cells.** 24 months of resale and sub-sale.

| midpoint of the two lease starts | $ psf / yr | 95% | devs | pairs |
|---|---|---|---|---|
| up to 2010 | **$25** | 22.1–27.5 | 154 | 136 |
| 2011 onward | **$44** (a FLOOR) | 38.6–49.8 | 103 | 95 |

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
   **Note the coincidence:** the current answer is also $25/$44 but banded on the MIDPOINT,
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

## 10. NEXT, IN HIS PRIORITY ORDER

1. **Tenure (÷1.15).** Framing ruling 2 says lease and tenure are ONE curve, not two terms —
   at the far end of a lease the freehold gap IS the lease gap, and the engine double-counts.
   Use leasehold-vs-freehold neighbour pairs under the §4 screens. The test that matters: does
   the lease figure, extended, land on the freehold gap? If it does, the double-count is proven.
   **This is also the biggest available win on sample size: of 1,844 developments in
   `dsi-index.json`, 1,255 are FREEHOLD and structurally cannot pair on lease start.** That is
   the real ceiling on this whole workstream, not the screens.
2. **Pure building age.** Freehold-vs-freehold neighbour pairs. Validates `AGE_PSF_PER_YEAR = 10`
   for free, and is the only way to decompose the blended vintage figure in §8.6.
3. **Study premium.** RealSmart carries labelled types ("2BR" vs "2BR + Study") with size bands.
   456 project × bedroom cells have both; 211 have bands disjoint enough to assign cleanly. The
   real question is whether a study earns PSF *after controlling for size* — a study unit is
   mostly just a bigger unit.
4. **Bedroom step.** Median 3BR minus median 2BR **within the same project and window**, matched
   pairs. Report as **quantum, not psf**, never as differenced medians across projects.
5. **MRT bands, harmonisation, integrated.** Not scoped.

Only after he audits does anything reach `price-gap.ts`.

---

## 10. MRT WALK BAND — MEASURED

`mrt-pairs.py` → `mrt-pairs.json` → `build-page.py`. **The lease study inverted:** station held
constant, walk band varies, lease removed at the MEASURED $25/$44 midpoint rate — never the flat $40.

**290 developments · 450 pairs · 716 cells.**

| walk to the nearest station | measured | 95% | devs | engine |
|---|---|---|---|---|
| under 5 min vs 5–10 min | **+$49** | +16 to +84 | 100 | $50 — right |
| 5–10 min vs over 10 min | **+$111** | +67 to +153 | 78 | $200 |
| under 5 min vs over 10 min | **+$122** | +56 to +195 | 33 | $250 |

**QUOTE $21 PSF PER EXTRA 100 M.** Independent of where the band lines fall. Placebo **+$1.7**.

### The screen is the STATION'S CATCHMENT, not the distance between the pair

Shawn's correction. Requiring the projects within 500 m of *each other* is self-defeating here:
they differ in walking distance by at most the distance between them, so it caps the measurement.
The under-5-vs-over-10 row had **3 pairs** under that screen and **25** under this one.
Catchment 2000 m; **pair cap 1200 m, set where the PLACEBO breaks** (+1.7 at 1200 m, +8.6 at 1800).
Leasehold only — freehold was built and dropped, 7–13 pairs a cell and incoherent.

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
