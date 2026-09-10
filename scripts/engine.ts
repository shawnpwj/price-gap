// PRICE GAP ENGINE — shared core.
//
// Extracted from price-gap.ts on 2026-09-09 so the single-project CLI and the
// all-developments batch run cannot drift apart. price-gap.ts is now a thin CLI
// over this module; price-gap-all.ts is the batch.
//
// METHOD (Shawn's, 2026-07-19/20) is unchanged and documented at each step below.
// Adjustments are applied TO THE COMPARABLE, never to the subject — the subject is
// the fixed reference line and every comparable is restated as "what this project
// would be worth if it had the subject's lease, tenure, MRT access and rule regime".
// A comparable landing ABOVE the subject's PSF implies the subject is UNDERVALUED.
//
// TWO CONSTANT SETS run side by side (Shawn, 2026-09-09). `judgement` is the set the
// engine has always used, each figure set by judgement. `measured` is the set the
// calibration study fitted against the market (price-gap/calibration/). Neither is
// written into the other: the constants are a parameter, so the whole 1,845-development
// run IS the audit surface for the measured set rather than something that waits on it.

import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const UPSTREAM = path.resolve(ROOT, "..", "property-analyzer");
export const D = (f: string) => path.join(UPSTREAM, "data", f);

// ── Structural screens — shared by BOTH constant sets ────────────────────────
// These are "is this even a comparable building", not "what is a year of lease worth",
// so calibrating a constant never moves them.
export const AGE_EXCLUDE_YEARS = 15;
// The LEASEHOLD twin of the age screen above, and it closes the hole that screen left.
// A freehold comparable more than 15 years older than the subject was already dropped; a
// LEASEHOLD one 30 years older was not, so distance-ranked selection kept handing the
// ladder projects it had to rebuild rather than adjust. AMO RESIDENCE is the case that
// found it: BISHAN PARK CONDOMINIUM (lease 1991 vs 2021) sat 390 m away and needed 83% of
// its own price added to stand in for a 2021 launch, while THE PANORAMA (2013, 757 m) and
// LENTORIA (2022, 1,448 m) needed 15% and 2% and were never reached. The old comparables
// were also manufacturing most of the apparent disagreement between the two constant sets:
// vintage-matched, the two sets agree on Amo. Same 15 years, same "only while MIN_COMPS
// survive" guard, same disclosure. Constant-set INDEPENDENT by design, so both columns
// still see the identical pool. (Shawn, 2026-09-09.)
export const LEASE_GAP_EXCLUDE_YEARS = 15;
export const MIN_COMPS = 2;
export const OUTLIER_BAND = 0.20;
export const CONSTRUCTION_YEARS = 6;
export const MIN_UNITS = 200;
export const MIN_MONTHS_IN_WINDOW = 2;
// EXPANDING RADIUS. A fixed 1.5 km treats a dense stretch of D15 and a thin pocket of D20
// the same way: in the dense one it reaches past every good comparable, in the thin one it
// runs out. Start tight, widen only while short of comparables, and report which ring was
// used. Shawn's instinct, 2026-09-09 — he reached for "1 km from Mayflower, or 1 km from
// Ai Tong" when Amo's own surroundings looked thin. Measured, neither of those catchments
// adds a single project the 1.5 km ring did not already contain (they sit INSIDE it, Amo
// being 562 m from the station), so the honest form of the idea is not a different anchor
// but a wider ring when the tight one is short.
export const RADIUS_LADDER = [1000, 1500, 2000];
export const MAX_RADIUS_M = RADIUS_LADDER[RADIUS_LADDER.length - 1];
// How many comparables the ladder is trying to reach before it stops widening.
export const TARGET_COMPS = 3;

// RANKING IS BY DISTANCE. Shawn, 2026-09-10: "I want the closest match to be based on
// distance, not tenure. because tenure is already filtered to <15 years, so that is fine."
//
// The reasoning is that the SCREENS already do the comparability work — a leasehold more
// than 15 years apart in lease start is excluded outright, as is a freehold more than 15
// years older — so everything that survives is acceptable on vintage, and among acceptable
// candidates the nearest building is the truest comparable. Location is the dominant term
// in what a home is worth, and the screens mean distance can no longer surface the 1991
// lease that started this.
//
// This REPLACES a weighted comparability score (vintage 2.0 / distance 1.0 / station 0.6 /
// tenure 0.8) that ran from 2026-09-09 to 2026-09-10. That score is gone rather than
// retired-in-place: a second ordering nothing calls is a trap, not a record. What it cost
// is measured — median adjustment load rises from 7.7% to 11.3% under distance, because a
// nearer building can be further apart in vintage.
export const PSF_WINDOW_MONTHS = 12;
// THE WORKUP WINDOW LADDER. Shawn, 2026-09-10: "can we use the last 6 - MAXIMUM 12 months
// average psf as the gauge?" It was already 12, never 24 — but 12 flat, so a development
// with plenty of recent trade was still being averaged over a year.
//
// ONE window per workup, never a mix: the subject and all three comparables are read over
// the SAME months, because comparing a subject's last 6 months against a comparable's last
// 12 prices whatever the market did in between. The ladder takes the freshest window that
// yields a full set, and the window travels with the figures.
//
// 6 alone was measured and rejected: on the 3BR view a hard 6-month window leaves 411
// developments with no workup at all against 74 at twelve. 6 -> 9 -> 12 keeps the freshness
// where the data supports it and the coverage where it does not.
export const WORKUP_WINDOW_LADDER = [6, 9, 12];

// The LRT line codes. Punggol/Sengkang East-West-Central, and Bukit Panjang.
export const LRT_LINES = new Set(["PE", "PW", "PTC", "SE", "SW", "STC", "BP"]);
// TWELVE MONTHS IS A HARD CEILING. Shawn, 2026-09-10, choosing it over the rescue with the
// cost stated: nothing is ever averaged over more than a year.
//
// This REVERSES his 2026-09-09 ruling that every development should carry a workup even
// before it transacts. That rescue reached back 24, 36 and 60 months and covered 285
// bedroom views across roughly 60 developments; they now carry no workup at all rather than
// a figure built on caveats up to five years old. He was shown that trade and took it.
//
// The subject walks the SAME ladder as the workup, never past it — see WORKUP_WINDOW_LADDER.
export const SUBJECT_WINDOW_LADDER = WORKUP_WINDOW_LADDER;
export const HARMONISATION_FROM = 2023;   // lease starts from this year are post-rule
export const BEDS = ["All", "1BR", "2BR", "3BR", "4BR+"];

// Straight-line metres -> walking minutes, for the judgement set's walk-minute bands.
const CIRCUITY = 1.3;
const METRES_PER_MIN = 80;

export type Band = "near" | "mid" | "far";

export interface Constants {
  key: "judgement" | "measured";
  label: string;
  blurb: string;
  // Vintage. `leaseRate(midpoint)` is $/psf per year of lease-start difference; the
  // measured set reads it at the MIDPOINT of the two lease starts, which is what makes
  // a pair straddling a band boundary need no decision (calibration §3).
  leaseRate: (midpointYear: number) => number;
  leaseRateLabel: string;
  ageRateFH: number;                       // freehold-vs-freehold, $/yr of TOP difference
  // Tenure, applied AFTER vintage, as a proportion of the running subtotal.
  // `leaseLeft` is the leasehold side's remaining years where it is known.
  tenurePremium: (leaseLeft: number | null) => number;
  tenureLabel: string;
  // MRT. The band CUTS differ between the sets and must travel with the magnitudes:
  // the judgement set bands on walk minutes (5/10 min), the measured study banded on
  // straight-line metres (400/800 m) and its figures are only valid on those cuts.
  mrtBandOf: (metres: number) => Band;
  mrtBandCutLabel: string;
  mrtBandPsf: Record<string, number>;
  harmonisationUplift: number;
  integratedPremium: number;
}

const roundTo = (x: number, n: number) => Math.round(x * 10 ** n) / 10 ** n;

// RETIRED 2026-09-09 on Shawn's audit. Kept, not deleted: it is the record of what the
// engine used to charge, it is what the calibration page compares against, and the reasoning
// behind each figure is worth more than the figure. It is no longer a live option — nothing
// runs against it, and the workup no longer offers it as a second column.
//
// Why it was retired: on held-out pairs of real neighbouring projects the measured form is
// 26% closer to the market (error 289 against this set's 389; no adjustment at all is 412).
// Its $200 mid-to-far rail band sits OUTSIDE the measured 95% range of $120-194; the rest of
// its figures are inside their ranges but centred wrong.
export const JUDGEMENT: Constants = {
  key: "judgement",
  label: "Engine constants (retired)",
  blurb: "What the engine charged before the calibration study. Retired 2026-09-09; kept as the record of what was replaced.",
  leaseRate: () => 40,
  leaseRateLabel: "$40 psf per year, flat",
  ageRateFH: 10,
  tenurePremium: () => 0.15,
  tenureLabel: "divide by 1.15",
  mrtBandOf: (m) => {
    const mins = (m * CIRCUITY) / METRES_PER_MIN;
    return mins < 5 ? "near" : mins <= 10 ? "mid" : "far";
  },
  mrtBandCutLabel: "walk minutes — under 5 / 5–10 / over 10",
  mrtBandPsf: { "near|mid": 50, "mid|far": 200, "near|far": 250 },
  harmonisationUplift: 0.07,
  integratedPremium: 0.05,
};

// Every measured figure below is READ FROM the calibration JSONs at load time by
// loadMeasured(), never hardcoded — an earlier calibration script copied 25/44 in as
// literals and they went stale the moment the fit was re-run. These are the shapes only.
// THE constants. Measured against the market by the calibration study and adopted on
// Shawn's audit, 2026-09-09 — the ruling the study had been waiting on since it opened.
// Read from the calibration JSONs at load time and never hardcoded here: an earlier script
// copied 25/44 in as literals and they went stale the moment the fit was re-run.
export const loadConstants = () => loadMeasured();

export async function loadMeasured(): Promise<Constants> {
  const C = (f: string) => path.join(ROOT, "calibration", f);
  const [lease, mrt, tenure, integ] = await Promise.all(
    ["lease-pairs.json", "mrt-pairs.json", "tenure-pairs.json", "integrated-pairs.json"]
      .map(async (f) => JSON.parse(await fs.readFile(C(f), "utf8")))
  );
  // Lease: two bands read at the MIDPOINT of the two lease starts (calibration §3).
  const bands = tenure.bands as { old: number; new: number };
  const bound = tenure.band_bound as number;
  // Tenure: the headline is the "vintage, then % premium" fit, which is the order the
  // engine applies. Where the leasehold side's remaining lease is known, the measured
  // gradient is used instead — the freehold premium is not one number, it widens as
  // the lease shortens (11% at 90+ years left, 22% at 60–74).
  // The study fitted three lease-left bands and marked the remaining two THIN, with no
  // figure at all — under-60-left has 4 pairs. Those are dropped, not filled in, and a
  // shorter lease than the last measured band CLAMPS to it rather than extrapolating
  // the widening past where anything was observed.
  const grad = (tenure.slices.gradient as any[])
    .filter((g) => !g.thin && typeof g.pct === "number" && typeof g.min_left === "number")
    .map((g) => ({ minLeft: g.min_left as number, pct: g.pct as number, label: g.label as string }))
    .sort((a, b) => b.minLeft - a.minLeft);
  const headline = tenure.headline.percent.p as number;
  // MRT: bands on the study's own 400 m / 800 m cuts, with its own fitted magnitudes.
  const nearM = mrt.near_m as number, farM = mrt.far_m as number;
  const mrtBandPsf: Record<string, number> = {};
  for (const b of mrt.bands as any[]) mrtBandPsf[b.key] = roundTo(b.adj, 0);
  // Integrated: the tightest cut, which is the one the README quotes as the answer.
  const cut = (integ.cuts as any[]).slice(-1)[0];

  return {
    key: "measured",
    label: "Measured constants",
    blurb: "Each figure fitted against matched pairs of real neighbouring projects. Adopted on Shawn's audit, 2026-09-09.",
    leaseRate: (mid) => (mid >= bound ? bands.new : bands.old),
    leaseRateLabel: `$${Math.round(bands.old)} / $${Math.round(bands.new)} psf per year, by the midpoint of the two lease starts (${bound} boundary)`,
    // Freehold-vs-freehold age, measured alongside the tenure fit.
    ageRateFH: tenure.fh_age_rate as number,
    tenurePremium: (leaseLeft) => {
      if (leaseLeft == null) return headline;
      for (const g of grad) if (leaseLeft >= g.minLeft) return g.pct;
      return grad[grad.length - 1].pct;
    },
    tenureLabel: `+${(headline * 100).toFixed(1)}%, widening from +${(grad[0].pct * 100).toFixed(0)}% (${grad[0].label}) to +${(grad[grad.length - 1].pct * 100).toFixed(0)}% (${grad[grad.length - 1].label}) as the lease shortens`,
    mrtBandOf: (m) => (m < nearM ? "near" : m <= farM ? "mid" : "far"),
    mrtBandCutLabel: `straight-line metres — under ${nearM} / ${nearM}–${farM} / over ${farM}`,
    mrtBandPsf,
    // NOT measured. Shawn dropped GFA harmonisation from the calibration study on
    // 2026-09-06, so the engine's +7% stands unchanged in BOTH sets and any difference
    // between the two columns is never coming from this line.
    harmonisationUplift: 0.07,
    integratedPremium: roundTo(cut.pct / 100, 4),
  };
}

// ── Geo ──────────────────────────────────────────────────────────────────────
const R = 6371000, rad = (x: number) => (x * Math.PI) / 180;
export function haversine(aLat: number, aLng: number, bLat: number, bLng: number) {
  const dLat = rad(bLat - aLat), dLng = rad(bLng - aLng);
  const q = Math.sin(dLat / 2) ** 2 + Math.cos(rad(aLat)) * Math.cos(rad(bLat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(q));
}
export const walkMinutes = (m: number) => (m * CIRCUITY) / METRES_PER_MIN;

function mrtDelta(K: Constants, subject: Band, comp: Band): number {
  if (subject === comp) return 0;
  const order = { near: 0, mid: 1, far: 2 };
  const key = order[subject] < order[comp] ? `${subject}|${comp}` : `${comp}|${subject}`;
  const mag = K.mrtBandPsf[key] ?? 0;
  // Comparable is FURTHER from the station than the subject -> mark it UP toward the
  // subject's better access. Closer -> mark it down.
  return order[comp] > order[subject] ? mag : -mag;
}

// A month key N months back from today, in the "YYYY-MM" form the psf series is keyed on.
export function monthsAgoFrom(n: number): string {
  const d = new Date(); d.setMonth(d.getMonth() - n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

// ── Bedroom-bucket PSF over the trailing window ───────────────────────────────
export interface PsfPick { psf: number; months: number; bucket: string; fellBack: boolean; window: string[] }

export function avgPsf(series: Record<string, Record<string, number>> | undefined, bucket: string, cutoff: string): PsfPick | null {
  if (!series) return null;
  const pick = (b: string) => {
    const byMonth = series[b];
    if (!byMonth) return null;
    const months = Object.keys(byMonth).filter((m) => m >= cutoff).sort();
    if (!months.length) return null;
    // Unweighted mean of monthly means: the stored series is already collapsed to a
    // monthly average and does not retain caveat counts, so a heavy month cannot be
    // weighted up. Flagged in the output caveats.
    const psf = months.reduce((s, m) => s + byMonth[m], 0) / months.length;
    return { psf: Math.round(psf), months: months.length, bucket: b, fellBack: false, window: months };
  };
  const want = pick(bucket);
  if (want && want.months >= MIN_MONTHS_IN_WINDOW) return want;
  if (bucket === "All") return want;
  const all = pick("All");
  if (all) return { ...all, bucket: "All", fellBack: true };
  return want;
}

// Typical unit size for a bedroom bucket. Prefers the median of ACTUAL transacted floor
// areas; falls back to the midpoint of the crawled unit-mix range. The two are NOT the
// same quality of number -- a range midpoint can sit far from anything real (KATONG
// REGENCY has no transacted 3BR at all, and its range midpoint reads 2,121 sqft against
// a 947-1,561 sqft band) -- so the source travels with the value and is shown in the UI.
export function midSize(facts: any, bed: string): { sqft: number; source: "transacted" | "range"; n?: number } | null {
  const t = facts?.sizes?.[bed];
  if (t?.medianSqft) return { sqft: t.medianSqft, source: "transacted", n: t.n };
  const b = facts?.mixSizes?.[bed];
  if (!b || !b.sizeMinSqft || !b.sizeMaxSqft) return null;
  return { sqft: Math.round((b.sizeMinSqft + b.sizeMaxSqft) / 2), source: "range" };
}

// ── Data ─────────────────────────────────────────────────────────────────────
// Read ONCE and reused across every subject, bedroom and constant set. The original
// CLI re-read ~4 MB of JSON per invocation, which is the whole reason a single project
// took a minute; the batch loads this once and runs 1,845 of them.
export interface Data {
  dsi: any[]; byName: Map<string, any>;
  psfHist: Record<string, any>; base: Record<string, any>; mix: Record<string, any>;
  stations: any[]; overrides: Record<string, any>; details: Record<string, any>;
  gls: Map<string, any>; cutoff: string; cutoffs: Record<number, string>;
}

export async function loadData(): Promise<Data> {
  const [dsiRaw, psfRaw, baseRaw, mixRaw, mrtRaw, detailRaw, glsRaw, overrideRaw] = await Promise.all([
    fs.readFile(D("dsi-index.json"), "utf8"),
    fs.readFile(D("psf-history.json"), "utf8"),
    fs.readFile(D("pricegap-base.json"), "utf8"),
    fs.readFile(D("unit-mix-db.json"), "utf8"),
    fs.readFile(D("mrt-stations.json"), "utf8"),
    // completionYear (TOP) for 1734/1740 crawled projects — the age yardstick for
    // freehold, which carries no lease-start date to difference against.
    fs.readFile(D("pg-project-details.json"), "utf8"),
    // projectedPsf — the launch-pricing fallback when a project has not sold a unit yet.
    fs.readFile(D("gls-forward.json"), "utf8"),
    fs.readFile(D("pricegap-overrides.json"), "utf8").catch(() => "{}"),
  ]);
  const dsi = JSON.parse(dsiRaw).projects as any[];
  const mrtAll = JSON.parse(mrtRaw);
  const glsRaw2 = JSON.parse(glsRaw);
  const glsArr = (Array.isArray(glsRaw2) ? glsRaw2 : glsRaw2.sites || []) as any[];
  const cutoffs: Record<number, string> = {};
  for (const m of [...new Set([...SUBJECT_WINDOW_LADDER, ...WORKUP_WINDOW_LADDER])]) cutoffs[m] = monthsAgoFrom(m);
  return {
    dsi,
    byName: new Map(dsi.filter((p) => p.lat).map((p) => [p.project.toUpperCase().trim(), p])),
    psfHist: JSON.parse(psfRaw).projects,
    base: JSON.parse(baseRaw).projects,
    mix: JSON.parse(mixRaw).developments,
    // MRT ONLY — an LRT halt is not rail access for this purpose. Shawn, 2026-09-10: "i want
    // you to look at MRT only dont consider LRT an MRT at all."
    //
    // It was taking the nearest station of ANY kind, so PRIVE was credited with 183 m to Cove
    // LRT and read as having the same rail access as WATERTOWN, which sits on the Punggol
    // MRT interchange. 53 developments (3%) had an LRT halt as their nearest station, and
    // they cluster in Punggol and Sengkang — exactly where that comparison is made.
    //
    // A station counts as LRT only when EVERY one of its codes is an LRT line, so an
    // interchange keeps its MRT identity: Bukit Panjang is ["DT1","BP6"] and stays MRT,
    // while Cove is ["PE1"] and drops out.
    stations: (Array.isArray(mrtAll) ? mrtAll : mrtAll.stations)
      .filter((s: any) => s.lat && s.lng)
      .filter((s: any) => {
        const codes: string[] = s.codes || [];
        if (!codes.length) return true;          // no codes recorded — keep it rather than guess
        return !codes.every((c) => LRT_LINES.has(String(c).replace(/[^A-Za-z]/g, "").toUpperCase()));
      }),
    overrides: JSON.parse(overrideRaw),
    details: JSON.parse(detailRaw).projects,
    gls: new Map(glsArr.filter((g) => g.devName).map((g) => [String(g.devName).toUpperCase().trim(), g])),
    cutoff: cutoffs[PSF_WINDOW_MONTHS], cutoffs,
  };
}

// Nearest station is a property of the SITE, not of a constant set or a bedroom, so it
// is memoised across the whole batch — it is an O(stations) scan per development and
// the batch would otherwise repeat it 10 times per project.
const nearestCache = new Map<string, { name: string; m: number }>();
function nearestStation(data: Data, name: string, node: any) {
  let hit = nearestCache.get(name);
  if (!hit) {
    hit = data.stations
      .map((s: any) => ({ name: s.name, m: Math.round(haversine(node.lat, node.lng, s.lat, s.lng)) }))
      .sort((a: any, z: any) => a.m - z.m)[0];
    nearestCache.set(name, hit!);
  }
  return hit!;
}

// Facts for any development: tenure, units, MRT, integrated flag, psf series.
// Constant-set-independent by design — the MRT BAND is applied later, because the two
// sets cut the bands differently and the underlying metres are the same either way.
export function factsFor(data: Data, name: string, node: any, bed: string, widen = false, windowMonths = PSF_WINDOW_MONTHS) {
  const ov = data.overrides[name] || {};
  const b = data.base[name] || {};
  const nearest = nearestStation(data, name, node);
  // A still-selling launch has no resale history, so its own primary-market psf is
  // the only honest read of what it costs today. Resale is preferred when it exists.
  // Widening applies to the SUBJECT only, and stops at the first window that finds a price.
  // `window` is the workup's own window; the widening ladder is the deeper rescue beyond it.
  // The subject starts on the workup's own window and only reaches past it as a rescue —
  // filtering the ladder alone would have read the subject at 12 while its comparables sat
  // at 6, which is exactly the mixed-period comparison the single window exists to prevent.
  const windows = widen
    ? [windowMonths, ...SUBJECT_WINDOW_LADDER.filter((w) => w > windowMonths)]
    : [windowMonths];
  let psf: PsfPick | null = null, psfSource = "", psfWindow = PSF_WINDOW_MONTHS;
  for (const w of windows) {
    const cut = data.cutoffs[w] ?? monthsAgoFrom(w);
    const resale = avgPsf(data.psfHist[name], bed, cut);
    const newSale = avgPsf(b.newSale, bed, cut);
    const pick = resale && resale.months >= MIN_MONTHS_IN_WINDOW ? resale : (newSale || resale);
    if (pick) { psf = pick; psfSource = pick === resale ? "resale+subsale" : "new sale"; psfWindow = w; break; }
  }
  // Last resort for a launch that has not transacted at all: the GLS projected price.
  // This is a FORECAST, not a transaction, and is caveated loudly downstream.
  if (!psf) {
    const proj = data.gls.get(name)?.projectedPsf?.avg;
    if (proj) { psf = { psf: Math.round(proj), months: 0, bucket: bed, fellBack: false, window: [] }; psfSource = "projected (GLS forecast)"; }
  }

  // TOP: crawled completionYear first; for a project still under construction fall
  // back to lease commencement + typical build time, flagged as an estimate.
  const det = data.details[name] || data.details[ov.pgName] || null;
  const tenure = ov.tenure || b.tenure || null;
  let top: any = null;
  if (ov.top) top = { year: ov.top, estimated: false, source: "override" };
  else if (det?.completionYear) top = { year: det.completionYear, estimated: false, source: "propertyguru" };
  else if (tenure?.leaseStart) top = { year: tenure.leaseStart + CONSTRUCTION_YEARS, estimated: true, source: `lease start ${tenure.leaseStart} + ${CONSTRUCTION_YEARS}yr build` };

  return {
    top, name, lat: node.lat, lng: node.lng,
    district: node.district, region: node.region,
    tenure,
    units: ov.units ?? data.mix[name]?.totalUnits ?? det?.totalUnits ?? null,
    // Transacted medians first (measured, and complete for anything that has traded),
    // crawled unit-mix ranges as the fallback.
    sizes: b.sizes || null,
    mixSizes: data.mix[name]?.bedrooms || null,
    mrt: { station: nearest.name, metres: nearest.m, minutes: Math.round(walkMinutes(nearest.m) * 10) / 10 },
    integrated: ov.integrated ?? false,
    psf, psfSource, psfWindow,
    // Set by the batch for a site that exists only in the GLS pipeline, so the caveats can
    // say that the lease start is an estimate off the award date rather than a fact.
    _glsOnly: ov._glsOnly ?? false, _awardEstimated: ov._awardEstimated ?? false,
    _tenureFromGls: ov._tenureFromGls ?? false,
    // With neither a tenure nor a TOP there is no clock to difference against, so the
    // vintage term — the largest adjustment on the ladder — cannot run at all and every
    // comparable passes through untouched. A gap computed that way is not a weak reading,
    // it is not a reading: it compares a 2026 launch to a 2002 lease as if they were the
    // same thing. Flagged here and the verdict is suppressed downstream.
    // The real test is not "has a tenure" but "has a CLOCK to difference against". A
    // freehold with no completion year has a tenure and still cannot be restated: the
    // vintage term reads off TOP for anything involving a freehold, and there is no TOP.
    // MANDALAY MANSION reported +29.9% that way, off comparables nothing had touched.
    _unadjustable: !top && !(tenure?.type === "LH" && tenure.leaseStart != null),
  };
}

// ── Comparable screening — INDEPENDENT of the constant set ───────────────────
// Screens ask "is this even a comparable building", not "what is a year of lease
// worth", so both constant sets see the identical pool and any difference between
// the two columns is an adjustment difference, never a selection difference.
// `candidates` may be supplied precomputed: which developments are within the radius
// is a property of the SITE and does not change with the bedroom, so the batch builds
// the neighbour index once instead of 1,845 x 1,845 haversines per bedroom view.
export function neighbours(data: Data, S: any, radius = MAX_RADIUS_M) {
  return data.dsi
    .filter((p) => p.lat && p.project.toUpperCase().trim() !== S.name)
    .map((p) => ({ node: p, name: p.project.toUpperCase().trim(), dist: Math.round(haversine(S.lat, S.lng, p.lat, p.lng)) }))
    .filter((c) => c.dist <= radius)
    .sort((a, b) => a.dist - b.dist);
}

// Vintage distance in years between two developments, on whichever clock they share — the
// same rule the vintage ADJUSTMENT uses, so ranking and adjusting agree about what "far
// apart" means. Null where neither clock is readable.
export function vintageGap(S: any, c: any): number | null {
  if (S.tenure?.type === "LH" && c.tenure?.type === "LH" &&
      S.tenure.leaseStart != null && c.tenure.leaseStart != null)
    return Math.abs(S.tenure.leaseStart - c.tenure.leaseStart);
  if (S.top && c.top) return Math.abs(S.top.year - c.top.year);
  return null;
}

// How comparable this candidate is, once the screens have had their say. Lower is better,
// and it is simply the distance: the screens decide WHETHER a candidate is comparable, and
// among those that are, the nearest wins. Kept as a function rather than inlining `dist` so
// the ordering has one definition and the panel can name what it sorted on.
export function comparability(S: any, c: any): number {
  return c.dist;
}

// Screen at ONE radius. `screen()` below drives this up the ladder.
function screenAt(data: Data, S: any, bed: string, candidates: ReturnType<typeof neighbours>, radius: number, windowMonths: number) {
  const rejected: any[] = [];

  // Pass 1 — hard screens (data quality and "is this a real cross-shopped condo").
  // The whole eligible set is built rather than stopping at nComps, because the age
  // filter below needs to know how many alternatives exist before it may drop anything.
  const eligible: any[] = [];
  for (const c of candidates) {
    const f = factsFor(data, c.name, c.node, bed, false, windowMonths);
    const why: string[] = [];
    if (!f.psf) why.push("no transactions in window");
    else if (f.psf.months < MIN_MONTHS_IN_WINDOW) why.push(`only ${f.psf.months} month(s) with caveats`);
    if (f.units != null && f.units < MIN_UNITS) why.push(`${f.units} units (< ${MIN_UNITS})`);
    if (f.units == null) why.push("unit count unknown");
    if (!f.tenure) why.push("tenure unknown");
    if (why.length) { rejected.push({ name: c.name, dist: c.dist, why }); continue; }
    eligible.push({ ...f, dist: c.dist });
  }

  // Pass 2 — age screen. A freehold comparable far older than the subject is a poor
  // like-for-like even after the age adjustment: at a 30-year gap the adjustment is
  // doing more work than the underlying observation can support. Drop those, but ONLY
  // while at least MIN_COMPS survive — an imperfect comparable beats none.
  const tooOld = (c: any) =>
    c.tenure?.type === "FH" && c.top && S.top && (S.top.year - c.top.year) > AGE_EXCLUDE_YEARS;
  // Pass 2b — the same idea on the leasehold side, priced off lease start rather than TOP.
  // Symmetric: a comparable far NEWER than the subject is as poor a like-for-like as one
  // far older, and the ladder is doing just as much work either way.
  const tooFarLease = (c: any) =>
    S.tenure?.type === "LH" && c.tenure?.type === "LH" &&
    S.tenure.leaseStart != null && c.tenure.leaseStart != null &&
    Math.abs(S.tenure.leaseStart - c.tenure.leaseStart) > LEASE_GAP_EXCLUDE_YEARS;

  const ageExcluded: any[] = [];
  const leaseExcluded: any[] = [];
  // Both screens together where the pool can afford it; the age screen alone where it
  // cannot; everything where even that is too thin. An imperfect comparable beats none,
  // and the tighter screen is the first thing to give way rather than the last.
  const both = eligible.filter((c) => !tooOld(c) && !tooFarLease(c));
  const ageOnly = eligible.filter((c) => !tooOld(c));
  const pool = both.length >= MIN_COMPS ? both : ageOnly.length >= MIN_COMPS ? ageOnly : eligible;

  for (const c of eligible) {
    if (pool.includes(c)) continue;
    if (tooOld(c) && ageExcluded.length < 8)
      ageExcluded.push({ name: c.name, dist: c.dist, top: c.top.year,
        why: [`freehold, TOP ${c.top.year} — ${S.top.year - c.top.year} yrs older than subject (limit ${AGE_EXCLUDE_YEARS})`] });
    else if (tooFarLease(c) && leaseExcluded.length < 8) {
      const d = S.tenure.leaseStart - c.tenure.leaseStart;
      leaseExcluded.push({ name: c.name, dist: c.dist, leaseStart: c.tenure.leaseStart,
        why: [`lease starts ${c.tenure.leaseStart} — ${Math.abs(d)} yrs ${d > 0 ? "older" : "newer"} than subject's ${S.tenure.leaseStart} (limit ${LEASE_GAP_EXCLUDE_YEARS})`] });
    }
  }
  // RANK BY DISTANCE. Everything above decides who is ELIGIBLE; this decides which three of
  // the eligible a development is judged against, and among candidates the screens have
  // already accepted, the nearest is the truest. (Shawn, 2026-09-10.)
  const ranked = [...pool].sort((a, b) => comparability(S, a) - comparability(S, b));
  return { rejected, eligible, pool: ranked, ageExcluded, leaseExcluded, radius, windowMonths };
}

// Walk the radius ladder: take the tightest ring that yields TARGET_COMPS, and if none does,
// keep the widest attempt — a comparable 1.8 km away beats no comparable at all. The ring
// actually used travels with the result, because "we had to go to 2 km to find three" is
// itself information about how unusual the development is.
// Walk the radius ladder, and inside each ring the WINDOW ladder. Radius is the outer loop
// because distance is what makes a comparable comparable (Shawn, 2026-09-10) — a nearer
// building read over 12 months beats a further one read over 6. Inside a ring, the freshest
// window that yields a full set wins, so most workups land on 6 months and only the thin
// ones reach for 12. Everything a workup shows is read over the SAME window.
export function screen(data: Data, S: any, bed: string, precomputed?: ReturnType<typeof neighbours>,
                       subjectNode?: any) {
  let last: ReturnType<typeof screenAt> | null = null;
  // A window only qualifies if the SUBJECT can be priced in it too. Without this the ring
  // could settle on 6 months off its comparables while the subject had nothing until 12,
  // and the workup would compare two different periods — the exact thing one window per
  // workup exists to prevent.
  const subjectPriced = (windowMonths: number) =>
    !subjectNode || !!factsFor(data, S.name, subjectNode, bed, false, windowMonths).psf;
  for (const radius of RADIUS_LADDER) {
    const cands = (precomputed ?? neighbours(data, S, MAX_RADIUS_M)).filter((c) => c.dist <= radius);
    for (const windowMonths of WORKUP_WINDOW_LADDER) {
      const got = screenAt(data, S, bed, cands, radius, windowMonths);
      last = got;
      if (got.pool.length >= TARGET_COMPS && subjectPriced(windowMonths)) return got;
    }
  }
  return last!;
}

// Remaining lease of the LEASEHOLD side of a mixed pair — the input to the measured
// tenure gradient. The freehold premium is not one number: it widens as the lease
// shortens, because at the far end of a lease the freehold gap IS the lease gap.
function leaseLeftOf(S: any, c: any): number | null {
  const lh = S.tenure?.type === "LH" ? S.tenure : c.tenure?.type === "LH" ? c.tenure : null;
  if (!lh?.leaseStart || !lh.years) return null;
  return lh.leaseStart + lh.years - new Date().getFullYear();
}

// ── The adjustment stack ─────────────────────────────────────────────────────
// Percentage adjustments compound on the running subtotal rather than all being taken
// on the raw base, so the order below is the order applied. Each step is emitted as its
// own delta so the chart can stack them.
export function adjust(K: Constants, S: any, pool: any[]) {
  const subjPost = S.tenure?.leaseStart != null && S.tenure.leaseStart >= HARMONISATION_FROM;
  const sBand = K.mrtBandOf(S.mrt.metres);

  return pool.map((c0) => {
    const c = { ...c0 };
    const steps: any[] = [];
    let running = c.psf.psf;
    // `calc` is the arithmetic in structured form — how many years at what rate, or what
    // percentage of which subtotal — so the panel can print the working instead of asking
    // the reader to take the delta on trust. Shawn, 2026-09-09: "show the calculation for
    // each Like Lease 429 is based on how many years etc."
    // `base` is the running subtotal the step was applied TO, which is what a percentage
    // step needs: they compound on the subtotal, not on the raw transacted price.
    const add = (label: string, delta: number, note: string, calc?: any) => {
      if (!Math.round(delta)) return;
      steps.push({ label, delta: Math.round(delta), note, base: Math.round(running), calc });
      running += delta;
    };

    // 1. Vintage — ONE term, priced off LEASE START when both sides are leasehold and
    // off TOP whenever a freehold is involved (a freehold has no lease start to
    // difference, so TOP is the only clock it has; in a mixed comparison it stands in
    // for lease decay as well as age). Freehold-vs-freehold uses the pure age rate,
    // which has no lease decay to price. Without this term a 1985 freehold read like a
    // 2023 one, which is what let THE SUNNY SPRING flip the first Grand Dunman run.
    const bothLH = S.tenure?.type === "LH" && c.tenure?.type === "LH";
    const bothFH = S.tenure?.type === "FH" && c.tenure?.type === "FH";
    if (bothLH && S.tenure.leaseStart != null && c.tenure.leaseStart != null) {
      const yrs = S.tenure.leaseStart - c.tenure.leaseStart;
      // Read at the MIDPOINT of the two lease starts. If the rate varies with vintage,
      // the whole difference across an interval is the gap times the rate at its
      // midpoint — so a pair straddling a band boundary needs no decision.
      const mid = (S.tenure.leaseStart + c.tenure.leaseStart) / 2;
      const rate = K.leaseRate(mid);
      add("Lease", yrs * rate,
        `${yrs > 0 ? "+" : ""}${yrs} yrs lease vs subject (${c.tenure.leaseStart} vs ${S.tenure.leaseStart}) x $${Math.round(rate)}/yr` +
        (K.key === "measured" ? ` (midpoint ${Math.round(mid)})` : ""),
        { kind: "rate", yrs, rate, from: c.tenure.leaseStart, to: S.tenure.leaseStart,
          midpoint: K.key === "measured" ? Math.round(mid) : null, clock: "lease start" });
    } else if (S.top && c.top) {
      const rate = bothFH ? K.ageRateFH : K.leaseRate((S.top.year + c.top.year) / 2);
      const yrs = S.top.year - c.top.year;
      add("Age (TOP)", yrs * rate,
        `TOP ${c.top.year} vs subject ${S.top.year} — ${Math.abs(yrs)} yrs ${yrs > 0 ? "older" : "newer"} x $${Math.round(rate)}/yr` +
        (bothFH ? " (freehold vs freehold)" : "") +
        (c.top.estimated || S.top.estimated ? " (estimated TOP)" : ""),
        { kind: "rate", yrs, rate, from: c.top.year, to: S.top.year, clock: "TOP",
          estimated: !!(c.top.estimated || S.top.estimated) });
    }

    // 2. Tenure — applied AFTER vintage, and as a DIVISION rather than a haircut. A
    // freehold price is treated as (1+p) of its leasehold equivalent, so recovering
    // that equivalent divides; multiplying by (1-p) is a different, larger cut.
    if (S.tenure && c.tenure && S.tenure.type !== c.tenure.type) {
      const left = leaseLeftOf(S, c);
      const p = K.tenurePremium(left);
      const target = c.tenure.type === "FH" ? running / (1 + p) : running * (1 + p);
      const leftNote = left != null && K.key === "measured" ? `, ${left} yrs of lease left` : "";
      add("Tenure", target - running,
        c.tenure.type === "FH"
          ? `comparable is freehold, subject is leasehold — divide by ${(1 + p).toFixed(3)}${leftNote}`
          : `comparable is leasehold, subject is freehold — multiply by ${(1 + p).toFixed(3)}${leftNote}`,
        { kind: c.tenure.type === "FH" ? "divide" : "multiply", factor: 1 + p, pct: p, leaseLeft: left });
    }

    // 3. MRT walk band. Labelled MRT and only MRT: an LRT halt is no longer counted as rail
    // access at all, so the station named here is always an MRT one. This supersedes the
    // both-rails labelling of 2026-08-04. (Shawn, 2026-09-10.)
    const cBand = K.mrtBandOf(c.mrt.metres);
    add("MRT access", mrtDelta(K, sBand, cBand),
      `${c.mrt.metres}m (${c.mrt.minutes}min) to ${c.mrt.station} vs subject ${S.mrt.metres}m (${S.mrt.minutes}min) to ${S.mrt.station}`,
      { kind: "band", compBand: cBand, subjBand: sBand, compM: c.mrt.metres, subjM: S.mrt.metres,
        compStation: c.mrt.station, subjStation: S.mrt.station, cuts: K.mrtBandCutLabel });

    // 4. Harmonisation. Keyed on LEASE START, not launch or transaction date. Pre-rule
    // projects quote a larger strata area (voids counted in GFA), which understates
    // their PSF against a post-rule project. IDENTICAL in both constant sets — Shawn
    // dropped harmonisation from the calibration study on 2026-09-06, so no difference
    // between the two columns is ever coming from this line.
    const compPre = c.tenure?.leaseStart != null && c.tenure.leaseStart < HARMONISATION_FROM;
    if (subjPost && compPre) {
      add("Harmonisation", K.harmonisationUplift * running,
        `lease start ${c.tenure.leaseStart} predates the Jun-2023 GFA harmonisation — +${(K.harmonisationUplift * 100).toFixed(0)}%`,
        { kind: "pct", pct: K.harmonisationUplift, why: `lease start ${c.tenure.leaseStart} is pre-Jun-2023` });
    }

    // 5. Integrated.
    if (S.integrated !== c.integrated) {
      const dir = c.integrated ? -1 : 1;
      add("Integrated", dir * K.integratedPremium * running,
        c.integrated
          ? `comparable is integrated, subject is not — discount ${(K.integratedPremium * 100).toFixed(1)}%`
          : `subject is integrated, comparable is not — uplift ${(K.integratedPremium * 100).toFixed(1)}%`,
        { kind: "pct", pct: dir * K.integratedPremium,
          why: c.integrated ? "the comparable is integrated and this is not" : "this is integrated and the comparable is not" });
    }

    c.steps = steps;
    c.adjusted = Math.round(running);
    c.gap = c.adjusted - S.psf.psf;
    c.gapPct = c.adjusted ? (c.adjusted - S.psf.psf) / c.adjusted : 0;
    c.band = cBand;
    return c;
  });
}

// ── One subject, one bedroom, one constant set ───────────────────────────────
// `screened` is passed in so a batch can screen once and run both constant sets
// against the identical pool.
export function runOne(data: Data, K: Constants, S: any, bed: string, screened: ReturnType<typeof screen>, nComps = 3) {
  const { rejected, ageExcluded, leaseExcluded } = screened;
  // Every survivor of the age screen is adjusted, not just the nComps nearest, because
  // the outlier band below can only judge a comparable AFTER it has been restated.
  const pool = adjust(K, S, screened.pool);

  // ── Outlier band ───────────────────────────────────────────────────────────
  // A comparable still more than 20% away from the subject AFTER every adjustment was
  // probably never comparable — the adjustments are not bridging a real difference,
  // they are papering over a different submarket. GUILLEMARD EDGE is the case in point:
  // right distance, right size, wrong market, and it lands 26% low even fully restated.
  // Applied POST-adjustment and set wide: real gaps run ~5%, so anything this screen
  // removes was never a near-miss. Every exclusion is disclosed. (Shawn, 2026-07-20.)
  const offBand = (c: any) => Math.abs(c.adjusted - S.psf.psf) / S.psf.psf > OUTLIER_BAND;
  const inBand = pool.filter((c) => !offBand(c));
  const bandExcluded: any[] = [];
  let finalPool = pool;
  if (inBand.length >= MIN_COMPS) {
    finalPool = inBand;
    for (const c of pool) {
      if (offBand(c) && bandExcluded.length < 8) {
        const pct = Math.round(((c.adjusted - S.psf.psf) / S.psf.psf) * 100);
        bandExcluded.push({ name: c.name, dist: c.dist, adjusted: c.adjusted,
          why: [`adjusted $${c.adjusted} is ${pct > 0 ? "+" : ""}${pct}% vs subject — beyond the ${Math.round(OUTLIER_BAND * 100)}% comparability band`] });
      }
    }
  }
  const comps = finalPool.slice(0, nComps);

  // ── Verdict ────────────────────────────────────────────────────────────────
  // Positive gap = comparables restated on the subject's terms are worth MORE than the
  // subject transacts at = the subject is cheap for what it is. MEDIAN, not mean
  // (Shawn, 2026-07-20): with a handful of comparables one atypical project should not
  // be able to drag the verdict across the line on its own.
  const sortedAdj = comps.map((c) => c.adjusted).sort((a, b) => a - b);
  const mid = Math.floor(sortedAdj.length / 2);
  const medianAdj = !sortedAdj.length ? 0
    : sortedAdj.length % 2 ? sortedAdj[mid] : (sortedAdj[mid - 1] + sortedAdj[mid]) / 2;
  const meanAdj = comps.length ? comps.reduce((s, c) => s + c.adjusted, 0) / comps.length : 0;
  const gap = Math.round(medianAdj - S.psf.psf);
  const gapPct = medianAdj ? gap / medianAdj : 0;
  const verdict = S._unadjustable ? "not assessable"
    : Math.abs(gapPct) < 0.03 ? "fairly valued" : gapPct > 0 ? "undervalued" : "overvalued";

  // ── Caveats — these travel WITH the numbers, not as a footnote ─────────────
  const caveats: string[] = [];
  if (S.psf.fellBack) caveats.push(`Subject ${S.name} had too few ${bed} caveats in the last ${PSF_WINDOW_MONTHS} months — its figure uses ALL bedroom types instead.`);
  for (const c of comps) {
    if (c.psf.fellBack) caveats.push(`${c.name} had too few ${bed} caveats — its figure uses ALL bedroom types instead, so unit-mix differences are baked into it.`);
    if (c.psf.months < 4) caveats.push(`${c.name} priced off only ${c.psf.months} month(s) of caveats — a thin sample that one atypical unit can move.`);
  }
  if (S._unadjustable) caveats.push(`${S.name} has no date to difference against — no completion year on record, and no lease start either — so the vintage adjustment — the largest term on the ladder — could not run and the comparables below are UNRESTATED. No verdict is given: the figures show what the neighbours transact at, not what this is worth.`);
  if (S.psfWindow > PSF_WINDOW_MONTHS) caveats.push(`${S.name} has no transactions in the last ${PSF_WINDOW_MONTHS} months — its figure reaches back ${S.psfWindow} months. The comparables are all priced off the last ${PSF_WINDOW_MONTHS}, so the subject's side of this comparison is older than theirs and the gap carries whatever the market did in between.`);
  if (S.psfSource === "new sale") caveats.push(`${S.name} is priced off DEVELOPER (new sale) transactions; comparables are priced off the RESALE market. Developer pricing carries a primary-market premium that resale does not.`);
  if (S.psfSource.startsWith("projected")) caveats.push(`${S.name} has NOT transacted — its figure is a PROJECTED launch price (GLS forecast), not an observed one. Every number downstream of it is a forecast, and the gap should be treated as indicative only until real caveats appear.`);
  if (S.top?.estimated) caveats.push(`${S.name} has no completion year on record — TOP estimated as ${S.top.year} (${S.top.source}). Any age adjustment against a freehold comparable inherits that estimate.`);
  if (comps.some((c) => c.steps.some((s: any) => s.label === "Age (TOP)")))
    caveats.push(`Age is adjusted at $${Math.round(K.ageRateFH)} psf per year of TOP difference for freehold comparisons — a condition/obsolescence proxy only. It cannot see renovation state, en-bloc potential, or how well a specific building has been maintained.`);
  if (leaseExcluded.length) caveats.push(`${leaseExcluded.length} leasehold comparable(s) were EXCLUDED for a lease start more than ${LEASE_GAP_EXCLUDE_YEARS} years from the subject's (${leaseExcluded.map((l: any) => `${l.name}, lease ${l.leaseStart}`).join("; ")}). Restating a lease that far apart is the constant doing the valuation rather than the market.`);
  if (ageExcluded.length) caveats.push(`${ageExcluded.length} freehold comparable(s) were EXCLUDED for being more than ${AGE_EXCLUDE_YEARS} years older than the subject (${ageExcluded.map((a: any) => `${a.name}, TOP ${a.top}`).join("; ")}). They are listed under comparable selection.`);
  if (bandExcluded.length) caveats.push(`${bandExcluded.length} comparable(s) were EXCLUDED for landing more than ${Math.round(OUTLIER_BAND * 100)}% from the subject even after adjustment (${bandExcluded.map((b) => `${b.name} $${b.adjusted}`).join("; ")}) — the adjustments could not bridge them, which usually means a different submarket. Note this screen is applied to the same quantity being measured; the exclusions are listed so you can overrule them.`);
  if (comps.length < MIN_COMPS) caveats.push(`Only ${comps.length} comparable(s) cleared screening — too few for a stable median. Treat the verdict as directional.`);
  const nearBand = comps.filter((c) => Math.abs(c.gapPct) > OUTLIER_BAND * 0.75);
  if (nearBand.length) caveats.push(`${nearBand.map((c) => c.name).join(", ")} sits close to the ${Math.round(OUTLIER_BAND * 100)}% comparability limit — a borderline comparable that a small change in any single adjustment would exclude.`);
  caveats.push("Monthly averages are unweighted — a month with one caveat counts as much as a month with twenty.");
  caveats.push("These are DEVELOPMENT AVERAGES across whole projects.");

  // The layout/quantum caveat, made concrete from the unit-mix size ranges rather than
  // asserted: a cheaper PSF on a larger unit can still be the bigger cheque.
  const layout: any[] = [];
  const bedForSize = bed === "All" ? "3BR" : bed;
  const sMid = midSize(S, bedForSize);
  for (const c of comps) {
    const cMid = midSize(c, bedForSize);
    if (sMid && cMid) {
      const sQ = Math.round(S.psf.psf * sMid.sqft), cQ = Math.round(c.adjusted * cMid.sqft);
      layout.push({
        name: c.name, bed: bedForSize,
        subjectSqft: sMid.sqft, subjectSizeSource: sMid.source, subjectSizeN: sMid.n ?? null,
        compSqft: cMid.sqft, compSizeSource: cMid.source, compSizeN: cMid.n ?? null,
        subjectQuantum: sQ, compQuantum: cQ, deltaSqft: cMid.sqft - sMid.sqft,
        note: `${bedForSize}: subject ~${sMid.sqft} sqft vs ${c.name} ~${cMid.sqft} sqft. On adjusted PSF that is ~$${(sQ / 1e6).toFixed(2)}M vs ~$${(cQ / 1e6).toFixed(2)}M — a ${Math.abs(cMid.sqft - sMid.sqft)} sqft difference in what you are actually buying.`,
      });
    }
  }
  const rangeSized = layout.filter((l) => l.compSizeSource === "range");
  if (rangeSized.length) caveats.push(`${rangeSized.map((l) => l.name).join(", ")} has no transacted ${bedForSize} in the window — its size is the MIDPOINT OF A PUBLISHED RANGE, not a median of real sales, so the implied quantum for it is indicative only.`);

  return {
    generatedAt: new Date().toISOString(),
    subject: S, bedroom: bed, constants: K.key,
    window: `${PSF_WINDOW_MONTHS} months from ${data.cutoff}`,
    radius: screened.radius,
    comps, rejected: rejected.slice(0, 12), ageExcluded, leaseExcluded, bandExcluded,
    result: { medianAdjusted: Math.round(medianAdj), meanAdjusted: Math.round(meanAdj), basis: "median", gap, gapPct, verdict },
    layout, caveats,
    assumptions: {
      set: K.key, setLabel: K.label,
      lease: K.leaseRateLabel, ageFH: K.ageRateFH, tenure: K.tenureLabel,
      mrtCuts: K.mrtBandCutLabel, mrtBands: K.mrtBandPsf,
      integratedPremium: K.integratedPremium, harmonisationUplift: K.harmonisationUplift,
      minUnits: MIN_UNITS, maxRadiusM: MAX_RADIUS_M,
      ageExcludeYears: AGE_EXCLUDE_YEARS, leaseGapExcludeYears: LEASE_GAP_EXCLUDE_YEARS,
      minComps: MIN_COMPS, outlierBand: OUTLIER_BAND,
    },
  };
}
