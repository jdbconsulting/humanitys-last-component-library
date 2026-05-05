# Murata BLM Library Notes

This folder generates `build/output/murata-ferrite.xls` (BLM15 / BLM18 /
BLM31 sheets) — the database for Murata's chip ferrite-bead line.
The user-facing build target is `python build.py murata-ferrites`
(plural, preserved from the legacy top-level Makefile target name).

## Files

- `murata-ferrite.py` — converts `blm_parts.csv` + `blm_dimensions.csv`
  into a 3-sheet DbLib-compatible `.xls`. The MPN's first 5
  characters select the worksheet name (BLM15* → sheet `BLM15`,
  BLM18* → `BLM18`, BLM31* → `BLM31`).
- `blm_parts.csv` — one row per orderable Murata BLM-series
  ferrite-bead MPN we carry, with the per-part fields that vary
  (DCR, current, impedance). 564 rows today, covering 42 subseries
  × ~210 unique base MPNs. Edit this file to add or drop parts.
- `blm_dimensions.csv` — per-base-MPN body dimensions
  (Length / Width / Thickness in mm). The `base_mpn` key is `MPN[:10]`
  (= `BLM<size:2><subseries:2><value:3>`); Murata's tolerance /
  temperature-grade / packaging suffix bytes don't change physical
  dimensions. Each row carries the source URL on Murata's site for
  auditability. The build script consults this file to pick the right
  IPC-7351B nominal-height code per part, so subseries and impedance
  variants with different body heights get different
  `INDC<metric>X<height>` footprints (e.g. BLM18KG101 → INDC1608X60,
  BLM18KG331 → INDC1608X80 — same subseries, different height
  because Murata builds them in different SKUs of the package
  family). If `blm_dimensions.csv` is missing or doesn't cover a
  particular base MPN, the script falls back to the family-default
  height and prints a warning per missing base, so newly-added MPNs
  are loud but the build doesn't break.
- `fetch_blm_datasheets.py` — emits the refresh-procedure prompt
  for `blm_dimensions.csv` (Murata's productdetail page is
  JS-rendered and their PDF CDN blocks bots, so the actual scrape
  needs to be performed by a tool that can render Murata's React
  SPA — e.g. Cursor's web-fetch tool, Playwright, or Selenium).
  See the script docstring for the full prompt template.
- `reference/` — per-subseries reference dumps:
  - `murata_ferrite_overview_2024.pdf` — Murata Feb 2024
    ferrite-bead overview deck (BLM family classification,
    automotive-grade matrix, BLM18KG vs BLM18SP comparisons).
  - `<subseries>.md` (one per subseries, e.g. `BLM15PX.md`,
    `BLM18KG.md`) — auto-generated extracts of Murata's productdetail
    spec tables for every base MPN in that subseries, alongside the
    source URLs. Refreshed in lockstep with `blm_dimensions.csv`.

The cross-family Murata MPN-decoder document lives at
`../reference/murata_part_numbering.pdf`.
