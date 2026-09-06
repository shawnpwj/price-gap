# Constant Calibration — takeover

Measuring the Price Gap engine's adjustment constants against market data, instead of
leaving them on judgement. Started 2026-09-06 at Shawn's request.

Read this file, then `lease-pairs.py`'s header, then the page it produces. That is the
whole workstream.

---

## Why this exists

`../scripts/price-gap.ts` restates every comparable onto the subject's terms using five
constants. **Every one of them was set by Shawn's judgement and none had ever been measured.**

| term | constant | set | status |
|---|---|---|---|
| Lease / vintage | $40 psf per year | 2026-07-20 | **MEASURED — $27–28/yr, and it should be split by age band** |
| Tenure · FH vs LH | ÷ 1.15 | 2026-07-20 | judgement only |
| MRT walk band | $50 / $200 / $250 | 2026-07-19 | judgement only |
| GFA harmonisation | +7% | 2026-07-19 | judgement only |
| Integrated development | +5% | 2026-07-19 | judgement only |
| Study vs no study | — | — | not in the engine; measurable, see below |
| One bedroom fewer | — | — | not in the engine; read as QUANTUM, not psf |

Shawn also flagged a real problem in the engine that this work should eventually resolve:
**the $40/yr lease term and the ÷1.15 tenure term double-count.** At the far end of a lease
the freehold gap *is* the lease gap. He ruled they are ONE curve, measured together — not two
independent terms.

---

## The three framing rulings (Shawn, 2026-09-06)

1. **Measure all of them.** "The wider the scope the better."
2. **Lease and tenure are the same thing.** One curve, not two terms.
3. **Validation BESIDE the constants, never replacing them.** Nothing in this folder writes
   back to `price-gap.ts`. Measured numbers silently replacing his rulings is the trap this
   rule exists to stop. **Do not change the engine without his explicit audit.**

---

## Method rulings — the pair screen

His method, his words: *find projects exactly next to each other with all else constant, where
the only difference is the lease start year; then compare average PSF bedroom against bedroom.*

Every one of these is a ruling he gave, not a default. Do not quietly change one.

| screen | value | why |
|---|---|---|
| distance apart | **500 m** | pair quality holds out to 800m; 500 is where he stopped |
| MRT | **same nearest station AND same walk band** | two projects 400m apart can feed different stations on different lines |
| schools | **identical set of top-26 primary schools within 1 km** | the 1km catchment is all-or-nothing. Costs only ~22 of 211 pairs |
| units | **200+ both sides** | "because I want good volume" — a boutique block's PSF is one odd sale |
| transactions | **5+ each side, in window** | |
| size match | **within 20%** | 15% cost 44% of the sample for less bias than it removed |
| EC | **allowed once privatised, TOP + 5** | before that it prices like subsidised stock |
| lease gap | **no minimum** | explicitly ruled: "I don't need the lease gap to be a certain amount." The gap band is an OUTPUT, not a screen |
| window | **24 months is the headline; 12 is a freshness check** | ruled 2026-09-06. They are NOT independent — 54 of the 56 clean 12m cells sit inside the 24m set, so 24m IS the combined figure. **Never average them**, that counts the last year twice |
| floor | **not controlled** | ruled: "accept the noise". The PSF series carries no floor |
| bands | **by lease START only** | ruled 2026-09-06. Bedroom and region were tested and neither moves the number; they stay on the page behind an explain mark, never on its face |
| scale | **dollars, never a percentage** | ruled 2026-09-06. Across base-PSF bands the $/yr holds at $26–30 while the %/yr falls away. The dollar is the invariant; the percentage is what made region look like a real split |

### The estimator — THREE MEASURED BANDS, read at the midpoint

**226 developments · 231 pairs · 382 cells.** Read at the MIDPOINT of the two lease starts.

| midpoint of the two lease starts | $ psf / yr | 95% | devs | pairs |
|---|---|---|---|---|
| up to 2010 | **$25** | 22.1–27.5 | 154 | 136 |
| 2011–2013 | **$40** | 28.2–50.6 | 64 | 57 |
| 2014 onward | **$47** | 40.8–52.8 | 56 | 38 |

**COUNTING WORDS — get these right.** *Development* = one condo (226 appear). *Pair* = two
neighbouring developments compared (231). *Cell* = one pair at one bedroom type, 1–4 per pair
(382) — this is the unit the figures are computed on.

**READ AT THE MIDPOINT.** Shawn broke the earlier lease-start bands in one question: *what do I
use for a 2005-vs-2025 pair?* If the rate varies with vintage, the whole difference across an
interval is the gap times the rate at its midpoint — so the midpoint form IS the blend, and a
pair straddling any boundary needs no special handling. Do not go back to banding on `ls_old`.

**TWO FITTED SHAPES DIED. DO NOT RESURRECT THEM.**
A straight line on the midpoint ($20.9 + $1.40) ran low at both ends. A fitted knee (flat, then
rising) fixed that on 168 pairs — and then MOVED when the screen widened to 231. The best knee is
now anywhere in 1998–2008 and the fit changes under 2% across that whole span: **the knee is not
identified.** Held-out error: flat 24.0k · line 21.4k · quadratic 20.2k · knee 20.7k · **bands
20.9k**. The bands tie the fitted shapes and claim nothing the pairs cannot carry.

**THE NEWEST BAND IS A FLOOR, NOT A FIGURE.** 56 developments, 38 pairs, and the rate was still
climbing when the evidence ran out. Quote $47 as the least it can be.

**NO MINIMUM LEASE GAP.** The old 5-year screen protected the per-pair MEAN, which divides each
difference by its own gap. The fitted estimator weights by gap instead, so a 3-year pair carries
3 years of leverage. Band rates are flat across every threshold. Do not put it back.

**BEDROOM IS THE MATCH, NOT THE ANSWER.** Not in the equation — it is the stratum holding size
constant, and the finest size resolution the data has. Pooling to one PSF per project matched on
pooled size LOSES pairs (159 vs 231) and lets mix leak at ~-$214 psf per 100% of size.
`build_pooled()` keeps it as a diagnostic.

### The screens, and what widening them does

**WALK BAND RETIRED (Shawn, 2026-09-06).** It required both sides in the same 5/10-minute walk
band of their shared station. With distance already screened at 500 m that is redundant, and it
cut arbitrarily — throwing out pairs 258–414 m apart on the same station because one sat at 640 m
from the MRT and the other at 900 m. Cost 20 pairs at the new end alone (The Trilinq/Parc Clematis
258 m, Oue Twin Peaks/Irwell Hill 329 m, Queens Peak/Stirling 387 m). 168 → 231 pairs.

**THE 200-UNIT FLOOR STAYS, AND THE DATA BACKS HIS ORIGINAL RULING.** Lowering it to 100 adds 33
pairs, and those added pairs fitted alone read **$32.9 with a slope of $0.11** — a high, flat,
directionless reading. Exactly the "a boutique block's PSF is one odd sale" problem he named on
2026-09-06. Below 100 units nothing further arrives; they have no transaction depth.

**THE REAL CEILING IS FREEHOLD, NOT THE SCREENS.** Of 1,844 developments in `dsi-index.json`,
**1,255 are freehold** and structurally cannot pair on lease start. 446 are eligible leasehold at
the 200-unit floor. That is what the tenure pass unlocks, and it is the reason it is next.

## Run it

```bash
python3 lease-pairs.py     # -> lease-pairs.json, and prints every cut to stdout
python3 build-page.py      # -> ../../kya-maps-calculator/calibration.html
```

Then deploy and commit, per the standing rule:

```bash
cd ../../property-analyzer && npm run maps:deploy
```

`lease-pairs.py` is a read-only consumer of `../../property-analyzer/data/`, the same
arrangement as the engine and `enbloc-analyzer`. It writes nothing upstream. If a run looks
stale, refresh upstream first (`npm run maps:refresh`) — nothing here can regenerate those files.

### The page

`calibration.html` is **hidden**: the only way in is a **double-click on the Live Data chip**
at the top right of the calculator. It is in neither nav and nothing else links to it, because
it is a working document and never a client view. See `../../kya-maps-calculator/index.html`,
`#liveDataChip`.

Two traps around it:
* **It is generated. Never hand-edit the HTML** — `build-page.py` overwrites it.
* **It had to be added to the `FILES` allowlist in `property-analyzer/scripts/deploy-maps.mjs`.**
  That list is explicit; a site file missing from it deploys as a dead link.

---

## Where the data comes from

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

## What the lease pass found

**$27 psf per year on the 24-month window, not $40.**

**Correction, 2026-09-06 — the windows are not independent.** An earlier version of this file
called the 12m/24m agreement "two independent windows". It is not: **54 of the 56 clean 12-month
cells are inside the 24-month set.** The 24m window CONTAINS the 12m one, so it is the combined
figure and the two must never be pooled or averaged. What the agreement is actually worth is
narrower but real — adding the 41 older cells moves the answer $28.5 → $27.3, so the extra depth
does not drag it. Report 24m as the headline, 12m as a freshness check.

**But a single number is the wrong shape. It tracks the AGE of the stock:**

| older project's lease start | $/yr | %/yr |
|---|---|---|
| pre-2010 | **+$25** | +1.6% |
| 2010s | **+$44** | +2.6% |

Established by cross-tabbing gap band against lease-start band. Read **down** a column (gap
fixed, age varying) and the rate climbs; read **across** a row (age fixed, gap varying) and
there is no trend past four years. So it is age, and the answer slices by lease-start band.

Not a price-level artefact: base PSF rises only 19% across those bands while the rate rises 63%.
Consistent with the 2026-07-27 decay study — this pool all sits ABOVE the 60–65y remaining knee,
where decay is mild.

### Three findings that will bite anyone who re-runs this

1. **1–4 year gaps read high. They are excluded from every headline.** THE BAYSHORE vs COSTA
   DEL SOL reads +$142/yr off a 4-year gap — that is Costa Del Sol being a different class of
   development, not lease. Diagnostic only.
2. **The 2BR/3BR split collapses once those are removed** — 2BR $28.5, 3BR $27.8, permutation
   **p = 0.83**. The first pass showed 2BR well above 3BR and that was short-gap noise.
   **Bedroom does not move the lease rate.** Do not re-report the split without the short gaps
   removed. 1BR (7 cells) and 4BR+ (4 cells) are unreadable at any window.
3. **Region does not move it either — in dollars.** RCR $31.8 vs OCR $28.9, permutation
   **p = 0.30**. In PERCENT they separate (2.02% vs 1.56%, p = 0.006) and that separation is fake:
   splitting by the base PSF of the older project shows $/yr flat at $26 / $30 / $30 across the
   three readable price bands while %/yr falls 2.11 → 1.96 → 1.50. **The dollar is the invariant.**
   Region was price level wearing a region's name. This is why the page carries no percentages.
4. **The CCR is not measurable this way and Shawn ruled it stays that way.** Every qualifying
   pair is Marina Bay or Sentosa Cove, one negative. That is a submarket, not a region. A CCR
   figure has to come from somewhere other than neighbour pairs.

### The honest limit

In a leasehold-vs-leasehold pair, **lease start and building age are perfectly confounded** — a
2010 lease is also a newer building. What is measured is the *blended vintage* effect, which is
exactly what the engine's term does, so it is a valid like-for-like validation of that constant.
It is **not** a decomposition into lease and bricks. Separating them needs freehold-vs-freehold
pairs, which are abundant (~555 at 400m) and have not been run.

Also uncontrolled, by ruling: floor, facing, and development quality beyond size and unit count.

---

## Next, in order

1. **Tenure (÷1.15).** Same curve extended, per ruling 2. Use leasehold-vs-freehold neighbour
   pairs (~284 at 400m / 100+ units). The test that matters: does the lease slope, extrapolated,
   land on the freehold gap? If it does, the two terms collapse into one and the engine's
   double-count is proven.
2. **Pure building age.** Freehold-vs-freehold neighbour pairs. Validates `AGE_PSF_PER_YEAR = 10`
   for free, and is the only way to decompose the blended vintage figure above.
3. **Study premium.** RealSmart carries labelled types ("2BR" vs "2BR + Study") with size bands.
   **456** project × bedroom cells have both; **211** have bands disjoint enough to assign a
   caveat cleanly. The real question is whether a study earns PSF *after controlling for size* —
   a study unit is mostly just a bigger unit.
4. **Bedroom step.** Median 3BR minus median 2BR **within the same project and window**, matched
   pairs. Report as **quantum, not psf**, and never as differenced medians across projects.
5. **MRT bands, harmonisation, integrated.** Not scoped yet.

Only after he audits all of it does anything reach `price-gap.ts`.
