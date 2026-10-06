// Refresh one verified unit count in the published Price Gap JSON without
// recalculating valuations. Use this when newer transaction inputs would make a
// full workup rebuild change unrelated client-facing verdicts before review.
// The normal full build in price-gap-all.ts also reads the verified count.
//
// node scripts/sync-site-unit-count.mjs "ONE CHUAN GROVE"
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const requested = process.argv[2]?.trim().toUpperCase();
if (!requested || process.argv.length !== 3) {
  console.error('Usage: node scripts/sync-site-unit-count.mjs "PROJECT NAME"');
  process.exit(2);
}

const records = JSON.parse(fs.readFileSync(path.join(root, 'property-analyzer/data/units-of-record.json'), 'utf8')).units;
const count = records[requested]?.units;
if (!Number.isInteger(count) || count <= 0) {
  console.error(`${requested}: no verified positive unit count in units-of-record.json`);
  process.exit(1);
}

const out = path.join(root, 'kya-maps-calculator/price-gap');
let changed = 0;
for (const filename of fs.readdirSync(out).filter(f => f.endsWith('.json') && f !== 'index.json')) {
  const file = path.join(out, filename);
  const shard = JSON.parse(fs.readFileSync(file, 'utf8'));
  let touched = false;
  if (shard.n?.toUpperCase() === requested && shard.u !== count) {
    shard.u = count;
    touched = true;
  }
  for (const bed of Object.values(shard.beds || {})) {
    for (const comparable of bed?.pg?.c || []) {
      if (comparable.n?.toUpperCase() === requested && comparable.u !== count) {
        comparable.u = count;
        touched = true;
      }
    }
  }
  if (touched) {
    fs.writeFileSync(file, JSON.stringify(shard));
    console.log(`${filename}: ${requested} → ${count} units`);
    changed++;
  }
}
console.log(`${changed} workup file${changed === 1 ? '' : 's'} updated; valuation figures were not recalculated.`);
