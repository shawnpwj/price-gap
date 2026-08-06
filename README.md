# Price Gap — the "P" of MAPS

A standalone workstream. Split out of `property-analyzer/prototypes/` on 2026-08-06
because it kept being mistaken for dead pipeline code — it is neither dead nor part
of the pipeline.

## What it is

Takes one development, finds its tightest nearby comparables, and restates each
comparable's transacted PSF onto the subject's terms — lease, tenure, MRT access,
rule regime — so the two can be read apples-to-apples.

Adjustments are applied **to the comparable, never to the subject**. The subject is
the fixed reference line. A comparable landing *above* the subject's PSF implies the
subject is **undervalued**, and vice versa. Full method in the header of
`scripts/price-gap.ts`.

## Why it lives outside the calculator

The MAPS site deliberately leaves Price Gap as **TBD — assessed at the viewing**, not
on the page. This produces the workup you bring *to* that viewing: one project at a
time, run by hand, on the day.

So it is a per-client tool, not a nightly build, and that is why it is not wired into
any `maps:*` script.

## Relationship to property-analyzer

Read-only consumer, the same arrangement as `enbloc-analyzer`. It reads eight files
out of `../property-analyzer/data/` and writes nothing back:

```
dsi-index.json      psf-history.json     pricegap-base.json   unit-mix-db.json
mrt-stations.json   pg-project-details.json   gls-forward.json
pricegap-overrides.json   (optional)
```

Those files come from the MAPS refresh. If a run looks stale, refresh upstream first
(`cd ../property-analyzer && npm run maps:refresh`) — nothing in this folder can
regenerate them.

## Run it

```bash
node scripts/build-price-gap.mjs "GRAND DUNMAN"
```

Runs the engine across all five bedroom views and inlines the results into
`scripts/price-gap.template.html`, producing a self-contained
**`out/price-gap.html`** you can open in a browser or send on. Takes a minute or two.

The engine can also be run alone for one bedroom, as JSON:

```bash
node --max-old-space-size=6000 scripts/price-gap.ts "GRAND DUNMAN" --bed 3BR --out /tmp/pg.json
```

`--comps N` controls how many comparables are used.

## Layout

| | |
|---|---|
| `scripts/price-gap.ts` | the engine — all the method and the tunables |
| `scripts/build-price-gap.mjs` | runs the engine five times, fills the template |
| `scripts/price-gap.template.html` | the page shell, `__DATA__` is the injection point |
| `out/` | generated pages. Not tracked — rerun to rebuild. |
