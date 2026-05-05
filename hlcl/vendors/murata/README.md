# Murata Library Notes

This folder is a per-family aggregator. Every active Murata generator
lives in its own subfolder under `vendors/murata/<family>/` with its
own `_build.py` registry stub, generator script, checked-in input
dataset, and `reference/` subfolder. The top-level [`build.py`](../../build.py)
auto-discovers every `vendors/*/*/_build.py` via wildcard glob.

| Family                                      | Folder        | Build target                      | Notes                                                                                                                   |
| ------------------------------------------- | ------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **GCM** (automotive MLCC, AEC-Q200)         | [`gcm/`](gcm) | `python build.py murata-gcm`      | renamed from the legacy `murata-capacitors`; the old script always only covered the GCM series despite the broader name |
| **GRM** (commercial / general-purpose MLCC) | [`grm/`](grm) | `python build.py murata-grm`      | tens of thousands of SKUs across the same EIA range as GCM; not automotive-qualified                                    |
| **BLM** (chip ferrite beads)                | [`blm/`](blm) | `python build.py murata-ferrites` | three sheets (BLM15 / BLM18 / BLM31), per-base-MPN dimensions cached in `blm/blm_dimensions.csv`                        |

There is also an auto-derived `python build.py murata` aggregate that
builds all three families above in one shot.

## Files at this level

- [`fetch_gcm_pim.py`](fetch_gcm_pim.py) — shared CSV downloader that
  drives both GCM and GRM. The default output is
  `gcm/gcm_parts.csv`; pass
  `--part-prefix GRM --output grm/grm_parts.csv --acquisition-num 60000`
  for the GRM catalogue.
- [`reference/murata_part_numbering.pdf`](reference/murata_part_numbering.pdf)
  — Murata's master MPN-decoder document. Covers BLM, GCM, GRM, and
  the rest of Murata's chip portfolio in one place, so it lives here
  rather than under any one family folder.

## Adding a new Murata family

1. `mkdir vendors/murata/<family>` plus a `reference/` subfolder for
   the family datasheet.
2. Drop in `<vendor-key>.py` (one of the existing scripts is a good
   template; pick GCM/GRM if the data comes from Murata's PIM, or
   BLM if you need per-base-MPN dimensions cached in CSV).
3. Add `vendors/murata/<family>/_build.py` (10 lines; copy any sibling
   `_build.py` and adjust the script basename + target name).
4. Add the new vendor key to the default `settings.house_footprints.priority`
   list in `src/lib/schema.ts` so footprint conflicts resolve
   deterministically. Re-running `npm run dev` regenerates
   `hlcl/factory-defaults.json` with the new entry baked in.

The top-level [`build.py`](../../build.py) picks up the new family
automatically via its `vendors/*/*/_build.py` glob.
