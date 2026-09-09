// PRICE GAP — ALL DEVELOPMENTS.
//
//   node --max-old-space-size=8000 --experimental-strip-types scripts/price-gap-all.ts
//        [--out FILE] [--only "NAME,NAME"] [--limit N]
//
// Runs the Price Gap engine across every development in dsi-index, for all five bedroom
// views, on the MEASURED constants, and writes one compact dataset for the calculator's
// hidden Price Gap panel to fetch.
//
// WHY A SEPARATE RUNNER. The single-project CLI re-reads ~4 MB of JSON per invocation,
// which is why one workup takes a minute; at 1,845 developments x 5 bedrooms that is days.
// This loads the data once, builds the neighbour index once per site, and screens once per
// (development, bedroom).
//
// It ran BOTH constant sets side by side until 2026-09-09, when Shawn audited the
// calibration and adopted the measured set. The engine set is retired, not deleted — its
// figures still travel in the payload as `retired`, so the panel can say what these numbers
// replaced.
//
// The output is deliberately COMPACT: field names are short and the per-comparable
// adjustment steps are stored as tuples, because this file is fetched by the browser.
// Caveats are stored as CODES, not prose — the page renders the standing wording from
// them. The prose lives in one place (the renderer) instead of being repeated ~18,000
// times, and nothing is dropped.

import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import {
  loadData, loadConstants, factsFor, screen, neighbours, runOne, JUDGEMENT,
  BEDS, MIN_UNITS, MAX_RADIUS_M, MIN_COMPS, OUTLIER_BAND, AGE_EXCLUDE_YEARS,
  LEASE_GAP_EXCLUDE_YEARS, PSF_WINDOW_MONTHS, type Constants,
} from "./engine.ts";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const flag = (name: string, dflt: string) => {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : dflt;
};

// Caveat codes. Each is rendered into Shawn's wording by the page; the payload carries
// only the code and whatever names it needs.
function caveatCodes(r: any, S: any, bed: string) {
  const out: any[] = [];
  if (S.psf.fellBack) out.push(["subjFallback"]);
  const fb = r.comps.filter((c: any) => c.psf.fellBack).map((c: any) => c.name);
  if (fb.length) out.push(["compFallback", fb]);
  const thin = r.comps.filter((c: any) => c.psf.months < 4).map((c: any) => [c.name, c.psf.months]);
  if (thin.length) out.push(["thinComp", thin]);
  if (S.psfSource === "new sale") out.push(["newSale"]);
  if (S.psfSource.startsWith("projected")) out.push(["projected"]);
  if (S.top?.estimated) out.push(["estTop", S.top.year, S.top.source]);
  if (S.psfWindow > 12) out.push(["wideWindow", S.psfWindow]);
  if (S._glsOnly) out.push(["glsSite", S.tenure?.leaseStart ?? null, S._awardEstimated ? 1 : 0]);
  else if (S._tenureFromGls) out.push(["tenureFromGls", S.tenure?.leaseStart ?? null]);
  if (S._unadjustable) out.push(["unadjustable"]);
  if (r.comps.some((c: any) => c.steps.some((s: any) => s.label === "Age (TOP)"))) out.push(["ageProxy"]);
  if (r.ageExcluded.length) out.push(["ageExcl", r.ageExcluded.map((a: any) => [a.name, a.top])]);
  if (r.leaseExcluded.length) out.push(["leaseExcl", r.leaseExcluded.map((l: any) => [l.name, l.leaseStart])]);
  if (r.bandExcluded.length) out.push(["bandExcl", r.bandExcluded.map((b: any) => [b.name, b.adjusted])]);
  if (r.comps.length < MIN_COMPS) out.push(["fewComps", r.comps.length]);
  const near = r.comps.filter((c: any) => Math.abs(c.gapPct) > OUTLIER_BAND * 0.75).map((c: any) => c.name);
  if (near.length) out.push(["nearBand", near]);
  const ranged = r.layout.filter((l: any) => l.compSizeSource === "range").map((l: any) => l.name);
  if (ranged.length) out.push(["rangeSized", ranged, bed === "All" ? "3BR" : bed]);
  return out;
}

function packSide(r: any, S: any, bed: string) {
  return {
    c: r.comps.map((c: any) => ({
      n: c.name, d: c.dist, b: c.psf.psf, a: c.adjusted, g: c.gap,
      t: c.tenure?.type ?? null, ls: c.tenure?.leaseStart ?? null, top: c.top?.year ?? null,
      u: c.units ?? null, mo: c.psf.months, fb: c.psf.fellBack ? 1 : undefined,
      // [label, delta, note] — the note is what lets the panel explain a bar without
      // the reader having to reconstruct the arithmetic.
      // [label, delta, subtotal-it-applied-to, structured arithmetic]. The engine's prose
      // note is NOT carried: the panel builds both the working line and the chart tooltip
      // from `calc`, so the wording lives in one place and the shards stay small.
      s: c.steps.map((s: any) => [s.label, s.delta, s.base, s.calc ?? null]),
    })),
    med: r.result.medianAdjusted, mean: r.result.meanAdjusted,
    gap: r.result.gap, pct: Math.round(r.result.gapPct * 1000) / 10, v: r.result.verdict,
    // Implied quantum on the subject's own typical size for this bedroom — a cheaper
    // PSF on a larger unit can still be the bigger cheque.
    q: r.layout.length ? { sf: r.layout[0].subjectSqft, src: r.layout[0].subjectSizeSource,
                           sub: r.layout[0].subjectQuantum } : null,
    cav: caveatCodes(r, S, bed),
  };
}

function setMeta(K: Constants) {
  return {
    key: K.key, label: K.label, blurb: K.blurb,
    lease: K.leaseRateLabel, ageFH: K.ageRateFH, tenure: K.tenureLabel,
    mrtCuts: K.mrtBandCutLabel, mrt: K.mrtBandPsf,
    harmonisation: K.harmonisationUplift, integrated: K.integratedPremium,
  };
}

async function main() {
  const t0 = Date.now();
  const outFile = flag("out", path.join(ROOT, "out", "price-gap-all.json"));
  const only = flag("only", "").split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
  const limit = parseInt(flag("limit", "0"), 10);

  const data = await loadData();
  // ONE set. The engine constants were retired on Shawn's audit, 2026-09-09 — the workup no
  // longer carries a second column, and the shards halve because of it.
  const K = await loadConstants();

  // ── Sites that exist ONLY in the GLS pipeline ──────────────────────────────
  // Shawn, 2026-09-09: "why is thomson reserve not having ANY form of comparable? all
  // development should have even if there is no transaction for the specific development
  // yet (not launch yet)." He is right, and the cause was narrow: the batch iterates
  // dsi-index, and an un-launched site is not in it. THOMSON RESERVE (the Thomson View
  // en-bloc, 1,240 units, launching 2026) lives only in gls-forward.json.
  //
  // Only TWO sites are genuinely in this class. Six other unmatched GLS names — Continuum,
  // The Botany, Parktown Residences, Upperhouse, RiverGreen, Rivelle — are just the sheet's
  // short forms of developments that ARE in dsi-index and already have workups under their
  // real names, so they are matched here rather than duplicated.
  //
  // The subject price is the sheet's PROJECTED psf, at Shawn's call. Note this is NOT what
  // the New Launches table shows: that cell prefers breakeven x margin, which puts Thomson
  // Reserve at $2,753 (2,202 x 1.25) against the sheet's projected $2,532. Left alone here —
  // the discrepancy is real and is his to rule on, not something to quietly reconcile.
  const dsiNames = new Set(data.dsi.map((p) => p.project.toUpperCase().trim()));
  // The same canonical form the calculator's New Launches table uses to match a sheet name
  // to a scored development: drop a leading "The", drop a trailing " at <location>" or
  // " @ <x>", fold Residences/Residence together, then strip punctuation. Without the last
  // two, "Parktown Residences" and "Rivelle" read as brand-new sites when PARKTOWN RESIDENCE
  // and RIVELLE TAMPINES are already in dsi-index with workups of their own.
  const canon = (n: string) => n.toUpperCase().trim()
    .replace(/^THE\s+/, "")
    .replace(/\s+(?:AT|@)\s+.*$/, "")
    .replace(/RESIDENCES\b/, "RESIDENCE")
    .replace(/[^A-Z0-9]/g, "");
  const dsiByCanon = new Map<string, string>();
  for (const p of data.dsi) {
    const full = p.project.toUpperCase().trim();
    for (const k of new Set([canon(p.project), canon(full.replace(/\s+(?:AT|@)\s+.*$/, ""))])) {
      if (!dsiByCanon.has(k)) dsiByCanon.set(k, full);
    }
  }
  // A sheet name that is a PREFIX of exactly one dsi name is that development —
  // "Rivelle" -> RIVELLE TAMPINES, "Upperhouse" -> UPPERHOUSE AT ORCHARD BOULEVARD.
  const prefixMatch = (c: string) => {
    const hits = [...dsiByCanon.keys()].filter((k) => k.startsWith(c) && c.length >= 6);
    return hits.length === 1 ? dsiByCanon.get(hits[0]) : null;
  };
  // A 99-year lease on a fresh site commences at award; the sheet's award date is the only
  // record of it for a project that has never transacted.
  const awardYearOf = (site: any) =>
    Number(String(site.awardDate || "").match(/\b(20\d{2})\b/)?.[1])
    || (Number(site.launchYear) ? Number(site.launchYear) - 1 : null);

  // ── Subjects in dsi-index that have NO tenure of their own ────────────────
  // pricegap-base derives tenure from CAVEATS, so a development that has never transacted
  // has none — and without a tenure or a TOP the vintage term cannot run at all. Every
  // comparable then passes through completely unadjusted and the gap is nonsense: LUCERNE
  // GRAND read -55.3% against 2002-2010 leases that were never restated, and the lease-gap
  // screen could not fire either because it needs the subject's own lease start.
  // Where the GLS sheet knows the award date, that is the missing lease start. Found while
  // tracing the sheet's margin change, 2026-09-09.
  for (const [gname, site] of data.gls) {
    const target = dsiNames.has(gname) ? gname
      : dsiByCanon.get(canon(gname)) ?? prefixMatch(canon(gname));
    if (!target) continue;
    if (data.base[target]?.tenure?.type || data.overrides[target]?.tenure) continue;
    const y = awardYearOf(site);
    if (!y) continue;
    data.overrides[target] = {
      ...(data.overrides[target] || {}),
      tenure: { raw: `99 yrs lease commencing from ${y}`, type: "LH", years: 99, leaseStart: y },
      units: data.overrides[target]?.units ?? site.units ?? undefined,
      _tenureFromGls: true, _awardEstimated: !String(site.awardDate || "").match(/\b20\d{2}\b/),
    };
    process.stderr.write(`  ~ ${target}: no tenure of its own, taking lease start ${y} from the GLS award date\n`);
  }

  const glsOnly: any[] = [];
  for (const [gname, site] of data.gls) {
    if (dsiNames.has(gname) || !site.lat || !site.lng) continue;
    // A name the sheet writes differently is not a missing development.
    const c = canon(gname);
    if (dsiByCanon.has(c) || prefixMatch(c)) continue;
    if (!(site.projectedPsf?.avg)) continue;
    // A 99-year lease on a fresh site commences at award. Where the sheet carries no award
    // date, launch year minus one is the working estimate and is flagged as one — it moves
    // the vintage term by a single year, which is $43 psf at the measured rate.
    const awardYear = awardYearOf(site);
    if (!awardYear) continue;
    data.overrides[gname] = {
      ...(data.overrides[gname] || {}),
      tenure: { raw: `99 yrs lease commencing from ${awardYear}`, type: "LH", years: 99, leaseStart: awardYear },
      units: site.units ?? null,
      top: undefined,
      _glsOnly: true, _awardEstimated: !String(site.awardDate || "").match(/\b20\d{2}\b/),
    };
    glsOnly.push({ project: gname, street: site.siteName || site.location || "", district: "",
                   region: site.region || "", lat: site.lat, lng: site.lng, _gls: true });
  }
  if (glsOnly.length) process.stderr.write(`  + ${glsOnly.length} GLS-only site(s): ${glsOnly.map((g) => g.project).join(", ")}\n`);

  let subjects = data.dsi.filter((p) => p.lat).concat(glsOnly);
  if (only.length) subjects = subjects.filter((p) => only.includes(p.project.toUpperCase().trim()));
  if (limit) subjects = subjects.slice(0, limit);

  const developments: any[] = [];
  const skipped: any[] = [];
  let done = 0;

  for (const node of subjects) {
    const name = node.project.toUpperCase().trim();
    // Facts that do not vary by bedroom, read once off the "All" view.
    const S0 = factsFor(data, name, node, "All", true);
    if (!S0.psf) { skipped.push({ n: name, why: "no transactions in the window" }); continue; }
    const nb = neighbours(data, S0);

    const beds: Record<string, any> = {};
    for (const bed of BEDS) {
      const S = factsFor(data, name, node, bed, true);
      if (!S.psf) continue;
      // Screen once per bedroom view; the ladder then runs against that pool.
      const screened = screen(data, S, bed, nb);
      const rec: any = {
        psf: S.psf.psf, src: S.psfSource, mo: S.psf.months,
        fb: S.psf.fellBack ? 1 : undefined,
        // The window the subject's own price had to reach back to, and the ring the
        // comparables were found in. Both are quality information, not bookkeeping.
        win: S.psfWindow, rad: screened.radius,
        rej: screened.rejected.slice(0, 8).map((r: any) => [r.name, r.dist, r.why[0]]),
      };
      rec.pg = packSide(runOne(data, K, S, bed, screened, 3), S, bed);
      if (!rec.pg.c.length) continue;      // no comparable at all is no reading
      beds[bed] = rec;
    }
    if (!Object.keys(beds).length) { skipped.push({ n: name, why: "no bedroom view produced a comparable" }); continue; }

    developments.push({
      n: name, st: node.street, d: node.district, r: node.region,
      gls: node._gls ? 1 : undefined,
      lat: Math.round(node.lat * 1e5) / 1e5, lng: Math.round(node.lng * 1e5) / 1e5,
      t: S0.tenure?.type ?? null, ls: S0.tenure?.leaseStart ?? null, yrs: S0.tenure?.years ?? null,
      raw: S0.tenure?.raw ?? null,
      top: S0.top?.year ?? null, topEst: S0.top?.estimated ? 1 : undefined,
      u: S0.units ?? null, int: S0.integrated ? 1 : undefined,
      mrt: { s: S0.mrt.station, m: S0.mrt.metres, min: S0.mrt.minutes },
      beds,
    });

    if (++done % 100 === 0) process.stderr.write(`  ${done}/${subjects.length}  ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
  }

  const payload = {
    generatedAt: new Date().toISOString(),
    window: `${PSF_WINDOW_MONTHS} months from ${data.cutoff}`,
    method: "Adjustments are applied TO THE COMPARABLE, never to the subject. A comparable landing ABOVE the subject's PSF implies the subject is undervalued.",
    screens: { minUnits: MIN_UNITS, maxRadiusM: MAX_RADIUS_M, minComps: MIN_COMPS,
               outlierBand: OUTLIER_BAND, ageExcludeYears: AGE_EXCLUDE_YEARS,
               leaseGapExcludeYears: LEASE_GAP_EXCLUDE_YEARS },
    constants: setMeta(K),
    // The retired set travels with the data so the panel can say what these figures replaced.
    retired: setMeta(JUDGEMENT),
    counts: { developments: developments.length, skipped: skipped.length, subjects: subjects.length },
    skipped: skipped.slice(0, 200),
    developments,
  };
  await fs.mkdir(path.dirname(outFile), { recursive: true });
  await fs.writeFile(outFile, JSON.stringify(payload));

  // ── Shard for the browser ──────────────────────────────────────────────────
  // The whole dataset is ~25 MB, which is fine on disk and far too heavy to fetch when
  // a panel opens. Sharding by district was the obvious cut and it is the wrong one:
  // D15 alone is 4 MB. The panel only ever shows ONE development, so the shard is one
  // development — ~14 KB, which arrives before the panel has finished expanding.
  const siteDir = flag("site", path.resolve(ROOT, "..", "kya-maps-calculator", "price-gap"));
  await fs.rm(siteDir, { recursive: true, force: true });
  await fs.mkdir(siteDir, { recursive: true });

  const used = new Set<string>();
  const slugOf = (n: string) => {
    const base = n.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "x";
    let s = base, i = 2;
    while (used.has(s)) s = `${base}-${i++}`;
    used.add(s);
    return s;
  };

  const index: any = {
    generatedAt: payload.generatedAt, window: payload.window, method: payload.method,
    screens: payload.screens, constants: payload.constants, retired: payload.retired,
    counts: payload.counts,
    // name -> [slug, district, region, {bed: [judgement gap%, measured gap%]}]. Small
    // enough to load with the panel, so a verdict shows before the shard arrives.
    dev: {} as Record<string, any>,
  };
  for (const d of developments) {
    const slug = slugOf(d.n);
    const heads: Record<string, number[]> = {};
    for (const [bed, b] of Object.entries<any>(d.beds)) heads[bed] = b.pg.pct;
    index.dev[d.n] = [slug, d.d, d.r, heads];
    await fs.writeFile(path.join(siteDir, `${slug}.json`), JSON.stringify(d));
  }
  await fs.writeFile(path.join(siteDir, "index.json"), JSON.stringify(index));

  const bytes = (await fs.stat(outFile)).size;
  const idxBytes = (await fs.stat(path.join(siteDir, "index.json"))).size;
  const shardBytes = (await Promise.all([...used].map(async (s) =>
    (await fs.stat(path.join(siteDir, `${s}.json`))).size)));
  const maxShard = Math.max(...shardBytes);
  console.log(`\n${developments.length} developments, ${skipped.length} skipped, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  console.log(`  full dataset  ${(bytes / 1e6).toFixed(1)} MB -> ${outFile}`);
  console.log(`  site index    ${(idxBytes / 1e3).toFixed(0)} KB`);
  console.log(`  ${used.size} shards, largest ${(maxShard / 1e3).toFixed(0)} KB, mean ${(shardBytes.reduce((a, b) => a + b, 0) / used.size / 1e3).toFixed(0)} KB -> ${siteDir}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
