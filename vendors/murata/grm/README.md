# Murata GRM Library Notes

This folder generates `build/output/murata-grm.xls`, the database for Murata's
**GRM** chip multilayer ceramic capacitor (MLCC) series.

GRM is Murata's general-purpose / commercial MLCC line for consumer
electronics and industrial equipment. Same physical chip body as the
automotive-qualified [GCM series](../gcm/) (sibling under
`vendors/murata/`), but a different catalogue: GRM ships tens of
thousands of SKUs across the same EIA 0201–1210 chip range, covers
more dielectrics (CH, SL, B, R, CJ, CK in addition to the IEC names),
and is _not_ AEC-Q200 qualified — the `Qual` column is left blank.

## Files

- `murata-grm.py` — converts the GRM CSV rows into DbLib-compatible
  `.xls` rows + the per-vendor footprints JSON sidecar. Largely a
  clone of [`../gcm/murata-gcm.py`](../gcm/murata-gcm.py); see the
  docstring at the top of `murata-grm.py` for the three policy
  differences (Qual=blank, extended `TCR_BY_DIELECTRIC` table, output
  paths under `build/output/murata-grm.*`).
- `grm_parts.csv` — checked-in input dataset, one row per orderable
  MPN. Pulled from Murata's PIM REST endpoint via the parent folder's
  shared fetcher.
- `build/output/murata-grm.DbLib` is written by the same
  `python murata-grm.py` invocation that writes the `.xls`, via the
  shared `vendors/_dblib.py` generator. It binds to
  `build/output/murata-grm.xls` next to it (relative path resolution
  via `DatabasePathRelative=1` + `LibrarySearchPath=.`).
- `reference/murata_grm.pdf` — primary family reference datasheet
  (full series catalogue, ~669 KB).

## Refreshing the parts list

The CSV is checked in so the default build is offline / reproducible.
To pull the latest catalogue from Murata's PIM API:

```bash
python vendors/murata/fetch_gcm_pim.py \
    --part-prefix GRM \
    --output vendors/murata/grm/grm_parts.csv \
    --acquisition-num 60000
```

Notes:

- `fetch_gcm_pim.py` lives in the parent `vendors/murata/` folder
  and is shared with the GCM target — the script is generic, only
  the `--part-prefix` and `--output` flags differ between series.
- The `--acquisition-num 60000` override is required because the
  GRM catalogue exceeds the 10,000-row default cap (it ships well
  over 30,000 orderable MPNs across all dielectrics and reels).
- The fetch typically takes 3–5 minutes for the full GRM catalogue;
  Murata's backend is synchronous and slow.

## Relationship to GCM

GCM and GRM are checked into the same repo because their electrical
data complements each other (GRM has the broadest dielectric and
voltage selection in commercial markets; GCM offers the same body
sizes with AEC-Q200 qualification when automotive use is required).
Both build into the same shared `build/output/house.PcbLib` footprint set,
so a board can mix-and-match GCM and GRM parts on identical
footprints. The `house/settings.toml` priority list resolves any
footprint-name conflict in GCM's favour.
