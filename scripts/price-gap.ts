// PRICE GAP ENGINE — the "P" of MAPS.
//
//   node scripts/price-gap.ts "GRAND DUNMAN" [--bed 3BR] [--comps 3] [--out FILE]
//
// Takes a subject development, finds its tightest nearby comparables, and adjusts
// each comparable's transacted PSF onto the subject's terms so the two can be read
// apples-to-apples. Output feeds the stacked-bar Price Gap chart.
//
// METHOD (Shawn's, 2026-07-19). Adjustments are applied TO THE COMPARABLE, never to
// the subject — the subject is the fixed reference line and every comparable is
// restated as "what this project would be worth if it had the subject's lease,
// tenure, MRT access and rule regime". A comparable that lands ABOVE the subject's
// PSF implies the subject is UNDERVALUED, and vice versa.
//
//   1. Vintage      ONE term, priced off whichever clock both sides share:
//                     - both leasehold -> $40 psf x (subject leaseStart - comp leaseStart).
//                       Lease decay and building age move together, so this carries both.
//                     - a freehold involved -> $40 psf x (subject TOP - comp TOP). A
//                       freehold has no lease start, so TOP is the only clock; in a mixed
//                       comparison it stands in for decay as well as age.
//                     - both freehold -> $10 psf x TOP difference: pure age/condition,
//                       with no lease decay to price.
//                   Without this term a 1985 freehold read like a 2023 one, which is what
//                   let THE SUNNY SPRING (TOP 1998) flip the Grand Dunman verdict on the
//                   first run. (Shawn, 2026-07-20.)
//   2. Tenure       freehold vs leasehold: DIVIDE by 1.15 (or multiply, inverted). A
//                   freehold price is 115% of its leasehold equivalent, so recovering the
//                   equivalent divides -- a x0.85 haircut is a different, larger cut.
//                   Applied AFTER vintage. (Shawn's worked example, 2026-07-20.)
//   3. MRT          walk-band difference: same band $0, <5 vs 5-10 $50,
//                   5-10 vs >10 $200, <5 vs >10 $250
//   4. Harmonisation +7% when the comparable's LEASE START predates the Jun-2023 GFA
//                   harmonisation and the subject's does not. Pre-rule projects quote a
//                   larger strata area (voids counted in GFA), which understates their
//                   PSF against a post-rule project. Keyed on lease start, not project
//                   launch or transaction date (Shawn, 2026-07-19).
//   5. Integrated   +/-5% for a mixed-use/MRT-integrated development vs a plain one
//
// SCREENS, in order: data quality (200+ units, known tenure, 2+ months of caveats within
// 1.5km) -> age (drop freehold more than 15 yrs older than the subject) -> outlier band
// (drop anything still >20% from the subject AFTER adjustment). The last two only fire
// while at least MIN_COMPS survive, and every exclusion is reported.
//
// The headline gap is taken off the MEDIAN of the adjusted comparables, not the mean, so
// a single unrepresentative project cannot swing the verdict (Shawn, 2026-07-20).
//
// Percentage adjustments compound on the running subtotal rather than all being taken
// on the raw base, so the order above is the order applied. Each step is emitted as its
// own delta so the chart can stack them.

import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
// Read-only consumer of the MAPS pipeline, same arrangement as enbloc-analyzer:
// every input below is written by property-analyzer and never by anything here.
const UPSTREAM = path.resolve(ROOT, "..", "property-analyzer");
const D = (f: string) => path.join(UPSTREAM, "data", f);

// ── Tunables ─────────────────────────────────────────────────────────────────
const LEASE_PSF_PER_YEAR = 40;
const AGE_PSF_PER_YEAR = 10;          // TOP-year difference, FREEHOLD-vs-FREEHOLD only
const FREEHOLD_PREMIUM = 0.15;
// A freehold comparable this much older than the subject is dropped -- but only while
// enough comparables survive (MIN_COMPS). Shawn: exclude much-older freehold comps IF
// there are sufficient comparables.
const AGE_EXCLUDE_YEARS = 15;
// Two sound comparables beat three where the third is filler (Shawn, 2026-07-20).
const MIN_COMPS = 2;
// Post-adjustment comparability band: further than this from the subject and the
// projects are not really comparable, whatever the adjustments say.
const OUTLIER_BAND = 0.20;
// Years from lease commencement to TOP, for a subject still under construction that has
// no completionYear yet. A rough fallback only -- Grand Dunman's real TOP is 2026 while
// this formula guesses 2028, which is why it carries an override in pricegap-overrides.json
// and why an estimated TOP is flagged in the output.
const CONSTRUCTION_YEARS = 6;
const INTEGRATED_PREMIUM = 0.05;
const HARMONISATION_UPLIFT = 0.07;
const HARMONISATION_FROM = 2023;      // lease starts from this year are post-rule
const MRT_BAND_PSF: Record<string, number> = {
  "near|mid": 50, "mid|far": 200, "near|far": 250,
};
// Straight-line metres -> walking minutes. 1.3 accounts for the fact that nobody
// walks through buildings; 80 m/min is the standard planning pace.
const CIRCUITY = 1.3;
const METRES_PER_MIN = 80;

// A comparable must be a real condo a buyer would actually cross-shop, not a
// boutique walk-up whose PSF is set by one odd transaction a year.
// 200, not 100: at 146 units GUILLEMARD SUITES cleared the old bar and landed as a
// comparable no Grand Dunman buyer would ever cross-shop. Shawn's rule — a development
// under ~200 units is too boutique to read as a like-for-like. (2026-07-20.)
const MIN_UNITS = 200;
const MIN_MONTHS_IN_WINDOW = 2;  // months with at least one caveat in the 12m window
const MAX_RADIUS_M = 1500;
const PSF_WINDOW_MONTHS = 12;

const BEDS = ["All", "1BR", "2BR", "3BR", "4BR+"];

// ── Geo ──────────────────────────────────────────────────────────────────────
const R = 6371000, rad = (x: number) => (x * Math.PI) / 180;
function haversine(aLat: number, aLng: number, bLat: number, bLng: number) {
  const dLat = rad(bLat - aLat), dLng = rad(bLng - aLng);
  const q = Math.sin(dLat / 2) ** 2 + Math.cos(rad(aLat)) * Math.cos(rad(bLat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(q));
}
const walkMinutes = (m: number) => (m * CIRCUITY) / METRES_PER_MIN;
function mrtBand(mins: number): "near" | "mid" | "far" {
  if (mins < 5) return "near";
  if (mins <= 10) return "mid";
  return "far";
}
function mrtDelta(subject: "near" | "mid" | "far", comp: "near" | "mid" | "far"): number {
  if (subject === comp) return 0;
  const order = { near: 0, mid: 1, far: 2 };
  const key = order[subject] < order[comp]
    ? `${subject}|${comp}` : `${comp}|${subject}`;
  const mag = MRT_BAND_PSF[key] ?? 0;
  // Comparable is FURTHER from MRT than subject -> mark the comparable UP toward
  // the subject's better access. Closer -> mark it down.
  return order[comp] > order[subject] ? mag : -mag;
}

// ── Bedroom-bucket PSF over the trailing window ───────────────────────────────
interface PsfPick { psf: number; months: number; bucket: string; fellBack: boolean; window: string[] }

function avgPsf(series: Record<string, Record<string, number>> | undefined, bucket: string, cutoff: string): PsfPick | null {
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

// ── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  const argv = process.argv.slice(2);
  const subjectName = (argv.find((a) => !a.startsWith("--")) || "GRAND DUNMAN").toUpperCase().trim();
  const flag = (name: string, dflt: string) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
  };
  const wantBed = flag("bed", "All");
  const nComps = parseInt(flag("comps", "3"), 10);
  const outFile = flag("out", D("price-gap.json"));

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
  const psfHist = JSON.parse(psfRaw).projects as Record<string, any>;
  const base = JSON.parse(baseRaw).projects as Record<string, any>;
  const mix = JSON.parse(mixRaw).developments as Record<string, any>;
  const mrtAll = JSON.parse(mrtRaw);
  const stations = (Array.isArray(mrtAll) ? mrtAll : mrtAll.stations).filter((s: any) => s.lat && s.lng);
  const overrides = JSON.parse(overrideRaw) as Record<string, any>;
  const details = JSON.parse(detailRaw).projects as Record<string, any>;
  const glsRaw2 = JSON.parse(glsRaw);
  const glsArr = (Array.isArray(glsRaw2) ? glsRaw2 : glsRaw2.sites || []) as any[];
  const gls = new Map<string, any>(
    glsArr.filter((g) => g.devName).map((g) => [String(g.devName).toUpperCase().trim(), g])
  );

  const byName = new Map<string, any>(dsi.filter((p) => p.lat).map((p) => [p.project.toUpperCase().trim(), p]));
  const subject = byName.get(subjectName);
  if (!subject) throw new Error(`Subject "${subjectName}" not found in dsi-index`);

  const cutoffD = new Date();
  cutoffD.setMonth(cutoffD.getMonth() - PSF_WINDOW_MONTHS);
  const cutoff = `${cutoffD.getFullYear()}-${String(cutoffD.getMonth() + 1).padStart(2, "0")}`;

  // Facts for any development: tenure, units, MRT, integrated flag, psf series.
  function factsFor(name: string, node: any) {
    const ov = overrides[name] || {};
    const b = base[name] || {};
    const nearest = stations
      .map((s: any) => ({ name: s.name, m: Math.round(haversine(node.lat, node.lng, s.lat, s.lng)) }))
      .sort((a: any, z: any) => a.m - z.m)[0];
    const mins = walkMinutes(nearest.m);
    // A still-selling launch has no resale history, so its own primary-market psf is
    // the only honest read of what it costs today. Resale is preferred when it exists.
    const resale = avgPsf(psfHist[name], wantBed, cutoff);
    const newSale = avgPsf(b.newSale, wantBed, cutoff);
    let psf = resale && resale.months >= MIN_MONTHS_IN_WINDOW ? resale : (newSale || resale);
    let psfSource = psf === resale ? "resale+subsale" : "new sale";
    // Last resort for a launch that has not transacted at all: the GLS projected price.
    // This is a FORECAST, not a transaction, and is caveated loudly downstream.
    if (!psf) {
      const proj = gls.get(name)?.projectedPsf?.avg;
      if (proj) { psf = { psf: Math.round(proj), months: 0, bucket: wantBed, fellBack: false, window: [] }; psfSource = "projected (GLS forecast)"; }
    }

    // TOP: crawled completionYear first; for a project still under construction fall
    // back to lease commencement + typical build time, flagged as an estimate.
    const det = details[name] || details[ov.pgName] || null;
    const tenure = ov.tenure || b.tenure || null;
    let top: any = null;
    if (ov.top) top = { year: ov.top, estimated: false, source: "override" };
    else if (det?.completionYear) top = { year: det.completionYear, estimated: false, source: "propertyguru" };
    else if (tenure?.leaseStart) top = { year: tenure.leaseStart + CONSTRUCTION_YEARS, estimated: true, source: `lease start ${tenure.leaseStart} + ${CONSTRUCTION_YEARS}yr build` };

    return {
      top,
      name,
      lat: node.lat, lng: node.lng,
      district: node.district, region: node.region,
      tenure,
      units: ov.units ?? mix[name]?.totalUnits ?? det?.totalUnits ?? null,
      // Transacted medians first (measured, and complete for anything that has traded),
      // crawled unit-mix ranges as the fallback.
      sizes: b.sizes || null,
      mixSizes: mix[name]?.bedrooms || null,
      mrt: { station: nearest.name, metres: nearest.m, minutes: Math.round(mins * 10) / 10, band: mrtBand(mins) },
      integrated: ov.integrated ?? false,
      psf,
      psfSource,
    };
  }

  const S = factsFor(subjectName, subject);
  if (!S.psf) throw new Error(`No PSF data for subject ${subjectName} in the last ${PSF_WINDOW_MONTHS} months`);

  // ── Comparable selection: nearest first, expanding outward ──────────────────
  const rejected: any[] = [];
  const candidates = dsi
    .filter((p) => p.lat && p.project.toUpperCase().trim() !== subjectName)
    .map((p) => ({ node: p, name: p.project.toUpperCase().trim(), dist: Math.round(haversine(S.lat, S.lng, p.lat, p.lng)) }))
    .filter((c) => c.dist <= MAX_RADIUS_M)
    .sort((a, b) => a.dist - b.dist);

  // Pass 1 — hard screens (data quality and "is this even a comparable building").
  // The whole eligible set is built rather than stopping at nComps, because the age
  // filter below needs to know how many alternatives exist before it may drop anything.
  const eligible: any[] = [];
  for (const c of candidates) {
    const f = factsFor(c.name, c.node);
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
  // like-for-like even after the $10/yr age adjustment: at a 30-year gap the adjustment
  // is doing more work than the underlying observation can support. Drop those, but ONLY
  // while at least MIN_COMPS survive — an imperfect comparable beats none.
  const tooOld = (c: any) =>
    c.tenure?.type === "FH" && c.top && S.top && (S.top.year - c.top.year) > AGE_EXCLUDE_YEARS;
  const fresh = eligible.filter((c) => !tooOld(c));
  const ageExcluded: any[] = [];
  let pool = eligible;
  if (fresh.length >= MIN_COMPS) {
    pool = fresh;
    for (const c of eligible) {
      if (tooOld(c) && ageExcluded.length < 8) {
        ageExcluded.push({ name: c.name, dist: c.dist, top: c.top.year,
          why: [`freehold, TOP ${c.top.year} — ${S.top.year - c.top.year} yrs older than subject (limit ${AGE_EXCLUDE_YEARS})`] });
      }
    }
  }
  // ── Adjustment stack ────────────────────────────────────────────────────────
  // Every survivor of the age screen is adjusted, not just the nComps nearest, because
  // the outlier band below can only judge a comparable AFTER it has been restated.
  const subjPost = S.tenure?.leaseStart != null && S.tenure.leaseStart >= HARMONISATION_FROM;

  for (const c of pool) {
    const steps: any[] = [];
    let running = c.psf.psf;
    const add = (label: string, delta: number, note: string) => {
      if (!delta) return;
      steps.push({ label, delta: Math.round(delta), note });
      running += delta;
    };

    // 1. Vintage — priced off LEASE START when both sides are leasehold, and off TOP
    // whenever a freehold is involved (a freehold has no lease start to difference).
    // Rate differs by case: a mixed FH-vs-LH comparison uses the full $40/yr, because
    // there the TOP gap is standing in for lease decay as well as age; FH-vs-FH uses
    // $10/yr, which is pure age/condition. (Shawn's worked example, 2026-07-20.)
    const bothLH = S.tenure?.type === "LH" && c.tenure?.type === "LH";
    const bothFH = S.tenure?.type === "FH" && c.tenure?.type === "FH";
    if (bothLH && S.tenure.leaseStart != null && c.tenure.leaseStart != null) {
      const yrs = S.tenure.leaseStart - c.tenure.leaseStart;
      add("Lease", yrs * LEASE_PSF_PER_YEAR,
        `${yrs > 0 ? "+" : ""}${yrs} yrs lease vs subject (${c.tenure.leaseStart} vs ${S.tenure.leaseStart}) x $${LEASE_PSF_PER_YEAR}/yr`);
    } else if (S.top && c.top) {
      const rate = bothFH ? AGE_PSF_PER_YEAR : LEASE_PSF_PER_YEAR;
      const yrs = S.top.year - c.top.year;
      add("Age (TOP)", yrs * rate,
        `TOP ${c.top.year} vs subject ${S.top.year} — ${Math.abs(yrs)} yrs ${yrs > 0 ? "older" : "newer"} x $${rate}/yr` +
        (bothFH ? " (freehold vs freehold)" : "") +
        (c.top.estimated || S.top.estimated ? " (estimated TOP)" : ""));
    }

    // 2. Tenure — applied AFTER vintage, and as a DIVISION by 1.15 rather than a 15%
    // haircut. A freehold price is treated as 115% of its leasehold equivalent, so
    // recovering that equivalent divides; multiplying by 0.85 is a different (and
    // slightly larger) cut. Shawn's worked example: 1812 / 1.15 = 1575, not x0.85 = 1540.
    if (S.tenure && c.tenure && S.tenure.type !== c.tenure.type) {
      const target = c.tenure.type === "FH" ? running / (1 + FREEHOLD_PREMIUM) : running * (1 + FREEHOLD_PREMIUM);
      add("Tenure", target - running,
        c.tenure.type === "FH"
          ? `comparable is freehold, subject is leasehold — divide by ${(1 + FREEHOLD_PREMIUM).toFixed(2)}`
          : `comparable is leasehold, subject is freehold — multiply by ${(1 + FREEHOLD_PREMIUM).toFixed(2)}`);
    }

    // 3. MRT/LRT walk band. Labelled for both rails — the station named in the reason can be
    //    either, and a fixed "MRT" would misdescribe an LRT one. (Shawn, 2026-08-04)
    const md = mrtDelta(S.mrt.band, c.mrt.band);
    add("MRT / LRT access", md,
      `${c.mrt.minutes}min to ${c.mrt.station} vs subject ${S.mrt.minutes}min to ${S.mrt.station}`);

    // 4. Harmonisation.
    const compPre = c.tenure?.leaseStart != null && c.tenure.leaseStart < HARMONISATION_FROM;
    if (subjPost && compPre) {
      add("Harmonisation", HARMONISATION_UPLIFT * running,
        `lease start ${c.tenure.leaseStart} predates the Jun-2023 GFA harmonisation — +${Math.round(HARMONISATION_UPLIFT * 100)}%`);
    }

    // 5. Integrated.
    if (S.integrated !== c.integrated) {
      const dir = c.integrated ? -1 : 1;
      add("Integrated", dir * INTEGRATED_PREMIUM * running,
        c.integrated
          ? `comparable is integrated, subject is not — discount ${Math.round(INTEGRATED_PREMIUM * 100)}%`
          : `subject is integrated, comparable is not — uplift ${Math.round(INTEGRATED_PREMIUM * 100)}%`);
    }

    c.steps = steps;
    c.adjusted = Math.round(running);
    c.gap = c.adjusted - S.psf.psf;
    c.gapPct = c.adjusted ? (c.adjusted - S.psf.psf) / c.adjusted : 0;
  }

  // ── Pass 3: outlier band ────────────────────────────────────────────────────
  // A comparable still more than 20% away from the subject AFTER every adjustment was
  // probably never comparable — the adjustments are not bridging a real difference, they
  // are papering over a different submarket. GUILLEMARD EDGE is the case in point: right
  // distance, right size, wrong market, and it lands 26% low even fully restated.
  // (Shawn, 2026-07-20.)
  //
  // The band is deliberately applied POST-adjustment and set wide. It cannot manufacture
  // a verdict: real gaps here run ~5%, so anything this screen removes was never going to
  // be a near-miss. Every exclusion is disclosed in the output.
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

  // ── Verdict ─────────────────────────────────────────────────────────────────
  // Positive mean gap = comparables restated on the subject's terms are worth MORE
  // than the subject transacts at = the subject is cheap for what it is.
  // MEDIAN, not mean (Shawn, 2026-07-20): with a handful of comparables one atypical
  // project should not be able to drag the verdict across the line on its own.
  const sortedAdj = comps.map((c) => c.adjusted).sort((a, b) => a - b);
  const mid = Math.floor(sortedAdj.length / 2);
  const medianAdj = !sortedAdj.length ? 0
    : sortedAdj.length % 2 ? sortedAdj[mid] : (sortedAdj[mid - 1] + sortedAdj[mid]) / 2;
  const meanAdj = comps.length ? comps.reduce((s, c) => s + c.adjusted, 0) / comps.length : 0;
  const gap = Math.round(medianAdj - S.psf.psf);
  const gapPct = medianAdj ? gap / medianAdj : 0;
  const verdict = Math.abs(gapPct) < 0.03 ? "fairly valued" : gapPct > 0 ? "undervalued" : "overvalued";

  // ── Caveats — these travel WITH the numbers, not as a footnote ──────────────
  const caveats: string[] = [];
  if (S.psf.fellBack) caveats.push(`Subject ${subjectName} had too few ${wantBed} caveats in the last ${PSF_WINDOW_MONTHS} months — its figure uses ALL bedroom types instead.`);
  for (const c of comps) {
    if (c.psf.fellBack) caveats.push(`${c.name} had too few ${wantBed} caveats — its figure uses ALL bedroom types instead, so unit-mix differences are baked into it.`);
    if (c.psf.months < 4) caveats.push(`${c.name} priced off only ${c.psf.months} month(s) of caveats — a thin sample that one atypical unit can move.`);
  }
  if (S.psfSource === "new sale") caveats.push(`${subjectName} is priced off DEVELOPER (new sale) transactions; comparables are priced off the RESALE market. Developer pricing carries a primary-market premium that resale does not.`);
  if (S.psfSource.startsWith("projected")) caveats.push(`${subjectName} has NOT transacted — its figure is a PROJECTED launch price (GLS forecast), not an observed one. Every number downstream of it is a forecast, and the gap should be treated as indicative only until real caveats appear.`);
  if (S.top?.estimated) caveats.push(`${subjectName} has no completion year on record — TOP estimated as ${S.top.year} (${S.top.source}). Any age adjustment against a freehold comparable inherits that estimate.`);
  const agedComps = comps.filter((c) => c.steps.some((s: any) => s.label === "Age (TOP)"));
  if (agedComps.length) caveats.push(`Age is adjusted at $${AGE_PSF_PER_YEAR} psf per year of TOP difference for freehold comparisons — a condition/obsolescence proxy only. It cannot see renovation state, en-bloc potential, or how well a specific building has been maintained.`);
  if (ageExcluded.length) caveats.push(`${ageExcluded.length} freehold comparable(s) were EXCLUDED for being more than ${AGE_EXCLUDE_YEARS} years older than the subject (${ageExcluded.map((a) => `${a.name}, TOP ${a.top}`).join("; ")}). They are listed under comparable selection.`);
  if (bandExcluded.length) caveats.push(`${bandExcluded.length} comparable(s) were EXCLUDED for landing more than ${Math.round(OUTLIER_BAND * 100)}% from the subject even after adjustment (${bandExcluded.map((b) => `${b.name} $${b.adjusted}`).join("; ")}) — the adjustments could not bridge them, which usually means a different submarket. Note this screen is applied to the same quantity being measured; the exclusions are listed so you can overrule them.`);
  if (comps.length < MIN_COMPS) caveats.push(`Only ${comps.length} comparable(s) cleared screening — too few for a stable median. Treat the verdict as directional.`);
  const nearBand = comps.filter((c) => Math.abs(c.gapPct) > OUTLIER_BAND * 0.75);
  if (nearBand.length) caveats.push(`${nearBand.map((c) => c.name).join(", ")} sits close to the ${Math.round(OUTLIER_BAND * 100)}% comparability limit — a borderline comparable that a small change in any single adjustment would exclude.`);
  caveats.push("Monthly averages are unweighted — a month with one caveat counts as much as a month with twenty.");
  caveats.push("These are DEVELOPMENT AVERAGES across whole projects.");

  // The layout/quantum caveat, made concrete from the unit-mix size ranges rather
  // than asserted: a cheaper PSF on a larger unit can still be the bigger cheque.
  const layout: any[] = [];
  const bedForSize = wantBed === "All" ? "3BR" : wantBed;
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
  // NOTE: the layout-efficiency and floor/facing caveats are NOT pushed here — the
  // renderer always appends them (they apply whether or not size data resolved), and
  // emitting them from both ends produced a duplicate bullet.

  const out = {
    generatedAt: new Date().toISOString(),
    subject: S, bedroom: wantBed, window: `${PSF_WINDOW_MONTHS} months from ${cutoff}`,
    comps, rejected: rejected.slice(0, 12), ageExcluded, bandExcluded,
    result: { medianAdjusted: Math.round(medianAdj), meanAdjusted: Math.round(meanAdj), basis: "median", gap, gapPct, verdict },
    layout, caveats,
    assumptions: {
      leasePsfPerYear: LEASE_PSF_PER_YEAR, agePsfPerYear: AGE_PSF_PER_YEAR,
      freeholdPremium: FREEHOLD_PREMIUM,
      integratedPremium: INTEGRATED_PREMIUM, harmonisationUplift: HARMONISATION_UPLIFT,
      mrtBands: MRT_BAND_PSF, minUnits: MIN_UNITS, maxRadiusM: MAX_RADIUS_M,
      ageExcludeYears: AGE_EXCLUDE_YEARS, minComps: MIN_COMPS, outlierBand: OUTLIER_BAND,
    },
  };
  await fs.writeFile(outFile, JSON.stringify(out, null, 1));

  // ── Console summary ─────────────────────────────────────────────────────────
  console.log(`\n${subjectName}  [${wantBed}]  ${S.district} ${S.region}`);
  console.log(`  ${S.tenure?.raw} | TOP ${S.top?.year ?? "?"}${S.top?.estimated ? " (est)" : ""} | ${S.units ?? "?"} units | ${S.mrt.minutes}min to ${S.mrt.station} (${S.mrt.band})`);
  console.log(`  base PSF $${S.psf.psf} from ${S.psfSource}, ${S.psf.months} months${S.psf.fellBack ? " [ALL-BEDROOM FALLBACK]" : ""}\n`);
  for (const c of comps) {
    console.log(`  ${c.name}  (${c.dist}m)  base $${c.psf.psf}${c.psf.fellBack ? " [all-bed]" : ""}  ${c.tenure?.raw}, TOP ${c.top?.year ?? "?"}`);
    for (const s of c.steps) console.log(`      ${s.delta > 0 ? "+" : ""}${s.delta}  ${s.label}  — ${s.note}`);
    console.log(`      = $${c.adjusted} adjusted   gap vs subject ${c.gap > 0 ? "+" : ""}$${c.gap}\n`);
  }
  if (ageExcluded.length) console.log(`  age-excluded: ${ageExcluded.map((a) => `${a.name}(TOP ${a.top})`).join(", ")}\n`);
  console.log(`  MEDIAN adjusted $${Math.round(medianAdj)} (mean would be $${Math.round(meanAdj)}) vs subject $${S.psf.psf}`);
  console.log(`  GAP ${gap > 0 ? "+" : ""}$${gap} psf (${(gapPct * 100).toFixed(1)}%) -> subject is ${verdict.toUpperCase()}`);
  console.log(`\n  rejected nearer candidates: ${rejected.slice(0, 6).map((r) => `${r.name}(${r.dist}m: ${r.why[0]})`).join(", ")}`);
  console.log(`\nOK ${outFile}`);
}

// Typical unit size for a bedroom bucket. Prefers the median of ACTUAL transacted floor
// areas; falls back to the midpoint of the crawled unit-mix range. The two are NOT the
// same quality of number -- a range midpoint can sit far from anything real (KATONG
// REGENCY has no transacted 3BR at all, and its range midpoint reads 2,121 sqft against
// a 947-1,561 sqft band) -- so the source travels with the value and is shown in the UI.
function midSize(facts: any, bed: string): { sqft: number; source: "transacted" | "range"; n?: number } | null {
  const t = facts?.sizes?.[bed];
  if (t?.medianSqft) return { sqft: t.medianSqft, source: "transacted", n: t.n };
  const b = facts?.mixSizes?.[bed];
  if (!b || !b.sizeMinSqft || !b.sizeMaxSqft) return null;
  return { sqft: Math.round((b.sizeMinSqft + b.sizeMaxSqft) / 2), source: "range" };
}

main().catch((e) => { console.error(e); process.exit(1); });
