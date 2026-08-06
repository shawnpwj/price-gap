// Build the standalone Price Gap prototype page: runs the engine for every bedroom
// bucket and inlines the results into the template.
//
//   node scripts/build-price-gap.mjs "GRAND DUNMAN"
//
// Output: out/price-gap.html (self-contained, open it in a browser).
import { execFileSync } from "child_process";
import { promises as fs } from "fs";
import path from "path";
import os from "os";
import { fileURLToPath } from "url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const BEDS = ["All", "1BR", "2BR", "3BR", "4BR+"];
const subject = process.argv[2] || "GRAND DUNMAN";

const tmp = await fs.mkdtemp(path.join(os.tmpdir(), "pricegap-"));
const out = {};
for (const bed of BEDS) {
  const f = path.join(tmp, `${bed}.json`);
  execFileSync("node", ["--max-old-space-size=6000", path.join(ROOT, "scripts", "price-gap.ts"),
    subject, "--bed", bed, "--out", f], { stdio: ["ignore", "ignore", "inherit"] });
  out[bed] = JSON.parse(await fs.readFile(f, "utf8"));
}
const tpl = await fs.readFile(path.join(HERE, "price-gap.template.html"), "utf8");
const dest = path.join(ROOT, "out", "price-gap.html");
await fs.mkdir(path.dirname(dest), { recursive: true });
await fs.writeFile(dest, tpl.replace("__DATA__", JSON.stringify(out)));
await fs.rm(tmp, { recursive: true, force: true });
console.log(`OK ${dest}  (${subject}, ${BEDS.length} bedroom views)`);
