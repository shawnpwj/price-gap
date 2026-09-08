// PRICE GAP — ALL DEVELOPMENTS.
//
//   node --max-old-space-size=8000 --experimental-strip-types scripts/price-gap-all.ts
//        [--out FILE] [--only "NAME,NAME"] [--limit N]
//
// Runs the Price Gap engine across every development in dsi-index, for all five bedroom
// views, under BOTH constant sets, and writes one compact dataset for the calculator's
// hidden Price Gap panel to fetch.
//
// WHY A SEPARATE RUNNER. The single-project CLI re-reads ~4 MB of JSON per invocation,
// which is why one workup takes a minute; at 1,845 developments x 5 bedrooms x 2 sets
// that is days. This loads the data once, builds the neighbour index once per site, and
// screens once per (development, bedroom) — the two constant sets then run against the
// IDENTICAL pool, so any difference between the two columns is an adjustment difference
// and never a selection difference.
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
  loadData, loadMeasured, factsFor, screen, neighbours, runOne, JUDGEMENT,
  BEDS, MIN_UNITS, MAX_RADIUS_M, MIN_COMPS, OUTLIER_BAND, AGE_EXCLUDE_YEARS,
  PSF_WINDOW_MONTHS, type Constants,
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
  if (r.comps.some((c: any) => c.steps.some((s: any) => s.label === "Age (TOP)"))) out.push(["ageProxy"]);
  if (r.ageExcluded.length) out.push(["ageExcl", r.ageExcluded.map((a: any) => [a.name, a.top])]);
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
      s: c.steps.map((s: any) => [s.label, s.delta, s.note]),
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
  const MEASURED = await loadMeasured();
  const sets: Constants[] = [JUDGEMENT, MEASURED];

  let subjects = data.dsi.filter((p) => p.lat);
  if (only.length) subjects = subjects.filter((p) => only.includes(p.project.toUpperCase().trim()));
  if (limit) subjects = subjects.slice(0, limit);

  const developments: any[] = [];
  const skipped: any[] = [];
  let done = 0;

  for (const node of subjects) {
    const name = node.project.toUpperCase().trim();
    // Facts that do not vary by bedroom, read once off the "All" view.
    const S0 = factsFor(data, name, node, "All");
    if (!S0.psf) { skipped.push({ n: name, why: "no transactions in the window" }); continue; }
    const nb = neighbours(data, S0);

    const beds: Record<string, any> = {};
    for (const bed of BEDS) {
      const S = factsFor(data, name, node, bed);
      if (!S.psf) continue;
      // Screen ONCE — both constant sets then see the identical pool.
      const screened = screen(data, S, bed, nb);
      const rec: any = {
        psf: S.psf.psf, src: S.psfSource, mo: S.psf.months,
        fb: S.psf.fellBack ? 1 : undefined,
        rej: screened.rejected.slice(0, 8).map((r: any) => [r.name, r.dist, r.why[0]]),
      };
      for (const K of sets) {
        const r = runOne(data, K, S, bed, screened, 3);
        rec[K.key === "judgement" ? "j" : "m"] = packSide(r, S, bed);
      }
      // A bedroom view with no comparable at all carries no verdict either way.
      if (!rec.j.c.length && !rec.m.c.length) continue;
      beds[bed] = rec;
    }
    if (!Object.keys(beds).length) { skipped.push({ n: name, why: "no bedroom view produced a comparable" }); continue; }

    developments.push({
      n: name, st: node.street, d: node.district, r: node.region,
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
               outlierBand: OUTLIER_BAND, ageExcludeYears: AGE_EXCLUDE_YEARS },
    sets: { judgement: setMeta(JUDGEMENT), measured: setMeta(MEASURED) },
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
    screens: payload.screens, sets: payload.sets, counts: payload.counts,
    // name -> [slug, district, region, {bed: [judgement gap%, measured gap%]}]. Small
    // enough to load with the panel, so a verdict shows before the shard arrives.
    dev: {} as Record<string, any>,
  };
  for (const d of developments) {
    const slug = slugOf(d.n);
    const heads: Record<string, number[]> = {};
    for (const [bed, b] of Object.entries<any>(d.beds)) heads[bed] = [b.j.pct, b.m.pct];
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
