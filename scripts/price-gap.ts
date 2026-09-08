// PRICE GAP ENGINE — the "P" of MAPS. Single-project CLI.
//
//   node scripts/price-gap.ts "GRAND DUNMAN" [--bed 3BR] [--comps 3] [--set measured] [--out FILE]
//
// The method now lives in ./engine.ts, shared with scripts/price-gap-all.ts so the
// one-project workup and the all-developments batch cannot drift apart. Read the
// header of engine.ts for the adjustment ladder and every ruling behind it.
//
// --set picks the constant set: `judgement` (default — what the engine has always
// used) or `measured` (what the calibration study fitted). Neither is written into
// the other; the set is a parameter. See engine.ts and calibration/README.md.

import { promises as fs } from "fs";
import { D, loadData, loadMeasured, factsFor, screen, runOne, JUDGEMENT, PSF_WINDOW_MONTHS } from "./engine.ts";

async function main() {
  const argv = process.argv.slice(2);
  const subjectName = (argv.find((a) => !a.startsWith("--")) || "GRAND DUNMAN").toUpperCase().trim();
  const flag = (name: string, dflt: string) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
  };
  const wantBed = flag("bed", "All");
  const nComps = parseInt(flag("comps", "3"), 10);
  const setName = flag("set", "judgement");
  const outFile = flag("out", D("price-gap.json"));

  const data = await loadData();
  const K = setName === "measured" ? await loadMeasured() : JUDGEMENT;

  const node = data.byName.get(subjectName);
  if (!node) throw new Error(`Subject "${subjectName}" not found in dsi-index`);
  const S = factsFor(data, subjectName, node, wantBed);
  if (!S.psf) throw new Error(`No PSF data for subject ${subjectName} in the last ${PSF_WINDOW_MONTHS} months`);

  const screened = screen(data, S, wantBed);
  const out = runOne(data, K, S, wantBed, screened, nComps);
  await fs.writeFile(outFile, JSON.stringify(out, null, 1));

  // ── Console summary ─────────────────────────────────────────────────────────
  const { comps, result, ageExcluded, rejected } = out;
  console.log(`\n${subjectName}  [${wantBed}]  ${S.district} ${S.region}   — ${K.label}`);
  console.log(`  ${S.tenure?.raw} | TOP ${S.top?.year ?? "?"}${S.top?.estimated ? " (est)" : ""} | ${S.units ?? "?"} units | ${S.mrt.minutes}min to ${S.mrt.station}`);
  console.log(`  base PSF $${S.psf.psf} from ${S.psfSource}, ${S.psf.months} months${S.psf.fellBack ? " [ALL-BEDROOM FALLBACK]" : ""}\n`);
  for (const c of comps) {
    console.log(`  ${c.name}  (${c.dist}m)  base $${c.psf.psf}${c.psf.fellBack ? " [all-bed]" : ""}  ${c.tenure?.raw}, TOP ${c.top?.year ?? "?"}`);
    for (const s of c.steps) console.log(`      ${s.delta > 0 ? "+" : ""}${s.delta}  ${s.label}  — ${s.note}`);
    console.log(`      = $${c.adjusted} adjusted   gap vs subject ${c.gap > 0 ? "+" : ""}$${c.gap}\n`);
  }
  if (ageExcluded.length) console.log(`  age-excluded: ${ageExcluded.map((a: any) => `${a.name}(TOP ${a.top})`).join(", ")}\n`);
  console.log(`  MEDIAN adjusted $${result.medianAdjusted} (mean would be $${result.meanAdjusted}) vs subject $${S.psf.psf}`);
  console.log(`  GAP ${result.gap > 0 ? "+" : ""}$${result.gap} psf (${(result.gapPct * 100).toFixed(1)}%) -> subject is ${result.verdict.toUpperCase()}`);
  console.log(`\n  rejected nearer candidates: ${rejected.slice(0, 6).map((r: any) => `${r.name}(${r.dist}m: ${r.why[0]})`).join(", ")}`);
  console.log(`\nOK ${outFile}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
