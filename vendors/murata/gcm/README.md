# Murata GCM Library Notes

This folder generates `build/output/murata-gcm.xls`, the database for
Murata's **GCM** chip multilayer ceramic capacitor (MLCC) series.

GCM is Murata's automotive-qualified MLCC line (AEC-Q200), shipped
across EIA 0201–1210 chip sizes. The sibling [`grm/`](../grm) folder
covers the commercial GRM counterpart on identical body geometries;
see `../README.md` for the full Murata family table.

> **Naming history.** The build target was previously called
> `murata-capacitors` and emitted `build/murata-capacitors.xls`, but
> the script always only covered the GCM series. The reorg renamed
> the target / xls / DbLib / footprints JSON to `murata-gcm` (and
> moved the script + checked-in CSV here under `gcm/`) so the name
> matches the contents.

## Files

- `murata-gcm.py` — converts the GCM PIM CSV rows into
  DbLib-compatible `.xls` rows + the per-vendor footprints JSON
  sidecar. Output paths: `build/output/murata-gcm.xls`,
  `build/output/murata-gcm.DbLib`,
  `build/intermediate/footprints/murata-gcm-footprints.json`.
- `gcm_parts.csv` — checked-in input dataset, one row per orderable
  MPN. Pulled from Murata's PIM REST endpoint via the parent
  folder's shared fetcher.
- `build/output/murata-gcm.DbLib` is written by the same
  `python murata-gcm.py` invocation that writes the `.xls`, via the
  shared `vendors/_dblib.py` generator. It binds to
  `build/output/murata-gcm.xls` next to it (relative path resolution
  via `DatabasePathRelative=1` + `LibrarySearchPath=.`).
- `reference/murata_gcm.pdf` — primary family reference datasheet.

## Refreshing the parts list

The CSV is checked in so the default build is offline / reproducible.
To pull the latest catalogue from Murata's PIM API:

```bash
python vendors/murata/fetch_gcm_pim.py
```

That writes `vendors/murata/gcm/gcm_parts.csv` by default. The fetch
typically takes 60-120 seconds. The fetcher is shared with the GRM
target — same script, just different `--part-prefix` / `--output`
flags (see [`../grm/README.md`](../grm/README.md)).
