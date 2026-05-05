# Ohmite KDV Library Notes

Generates `build/output/ohmite-kdv.xls` for Ohmite's **KDV** series:
metal-film, low-resistance chip resistors (current sense) in EIA
sizes 0201, 0402, 0603, 0805, and 1206.

## Files

- `ohmite-kdv.py` — emits the `.xls` workbook and the per-vendor
  footprints JSON. Unlike the Murata vendors there is no scrape
  step: Ohmite has no public product database API, so the orderable
  part-number table is transcribed directly into the script (see
  `OFFERINGS` near the top of the file). Refresh the table by hand
  if Ohmite ships a new datasheet revision.
- `build/output/ohmite-kdv.DbLib` is written by the same
  `python ohmite-kdv.py` invocation that writes the `.xls`, via the
  shared `vendors/_dblib.py` generator. It binds to
  `build/output/ohmite-kdv.xls` next to it (relative path resolution
  via `DatabasePathRelative=1` + `LibrarySearchPath=.`).
- `reference/ohmite_kdv.pdf` — primary family reference datasheet
  (Ohmite doc rev 1/21-2, 553 KB). Source of the body dimensions,
  tolerance/value matrix, marking codes, and tape-and-reel data
  baked into the script.

## Catalogue summary

| KDV size | EIA  | Body L×W×H (mm)  | Power @70°C | Footprint root |
|----------|------|------------------|-------------|----------------|
| KDV02    | 0201 | 0.60 × 0.30 × 0.26 | 1/10 W   | `RESC0603X26`  (NEW; KDV-specific 0.26 mm height) |
| KDV04    | 0402 | 1.00 × 0.50 × 0.35 | 1/8  W   | `RESC1005X35`  (shared with Panasonic ERA-2) |
| KDV06    | 0603 | 1.60 × 0.80 × 0.45 | 1/5  W   | `RESC1608X45`  (shared with Panasonic ERA-3) |
| KDV08    | 0805 | 2.00 × 1.25 × 0.55 | 1/4  W   | `RESC2012X55`  (shared with Panasonic ERA-6V/K -- Panasonic's 1.20 mm wide body wins on priority) |
| KDV12    | 1206 | 3.10 × 1.60 × 0.55 | 1/2  W   | `RESC3216X55`  (shared with Panasonic ERA-8P -- Panasonic's 3.20 mm long body wins on priority) |

## Part-number scheme

```
KDV<size><tolerance>R<value><tape>
    ^^      ^         ^      ^^
    02      D         100    ET   <-- KDV02DR100ET (0201, 0.5%, 100 mΩ)
    04      F         050    ET   <-- KDV04FR050ET (0402, 1%,    50 mΩ)
```

- `size`: 02 / 04 / 06 / 08 / 12 (EIA size)
- `tolerance`: D = 0.5%, F = 1% (G = 2% and J = 5% are build-to-order
  and not in the standard table)
- `value`: 3-digit milliohms (R050 = 50 mΩ … R820 = 820 mΩ)
- `tape`: ET = embossed tape & reel (only standard packaging)

## TCR

Per the spec block on page 1 of the datasheet, TCR is keyed on
*resistance value* (not size):

- 50 – 99 mΩ → ±100 ppm/°C
- 100 mΩ and above → ±50 ppm/°C

The 50/68/82 mΩ rows therefore get the looser ±100 ppm spec; all
other values get ±50 ppm.

## Refreshing the catalogue

The table is hard-coded in `ohmite-kdv.py`. To refresh:

1. Download the latest `ohmite_kdv.pdf` from
   `https://ohmite.com/assets/images/res-kdv.pdf?r=false` (the
   `?r=false` bypass is needed because Ohmite's CDN otherwise
   serves an iframe-viewer HTML wrapper).
2. Inspect page 3's "Standard part numbers" table.
3. Update `RESISTANCE_MOHM_VALUES` and the `OFFERINGS` tuple at
   the top of `ohmite-kdv.py` to match.
4. Re-run `python build.py ohmite-kdv`.
