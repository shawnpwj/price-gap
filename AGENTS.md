# Price Gap data rules

- Build the browser index and shards from `scripts/price-gap-all.ts`; never correct a generated JSON shard by hand.
- `property-analyzer/data/units-of-record.json` is the verified unit count. A GLS sheet row is a tender estimate and must not overwrite that count when `price-gap-all.ts` creates an override. One Chuan Grove is the regression example: verified 1,056, GLS row 1,055.
- Rebuild the complete workup dataset after valuation-input or calculation changes and audit changed verdicts before deploying it. Then run `node ../property-analyzer/scripts/check-consistency.mjs`. The workup's date is separate from the main MAPS data date.
- A full rebuild on 6 October 2026 changed 194 bedroom verdicts across 99 developments. Keep that broad refresh off the client-facing site until the valuation changes are audited. For a count-only correction against the current published workups, run `node scripts/sync-site-unit-count.mjs "PROJECT NAME"`; it changes unit metadata from the verified record without recalculating any valuation.
- `../property-analyzer/scripts/check-price-gap-verdicts.mjs` blocks staging/deploy when workup verdicts differ from the approved baseline. After auditing a broad refresh, explicitly record the reviewed release with `--approve "specific review note"`; never update the baseline just to silence the gate.
