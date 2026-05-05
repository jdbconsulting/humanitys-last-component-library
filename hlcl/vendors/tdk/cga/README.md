# TDK CGA Library Notes

Generates `build/output/tdk-capacitors.xls` for TDK's **CGA**
automotive-grade MLCC line (commercial-equivalent of the C-series,
up to 75 VDC).

## Files

- `tdk-capacitors.py` — decodes TDK CGA part numbers into
  DbLib-compatible `.xls` rows + the per-vendor footprints JSON
  sidecar. Output paths: `build/output/tdk-capacitors.xls`,
  `build/output/tdk-capacitors.DbLib`,
  `build/intermediate/footprints/tdk-capacitors-footprints.json`.
- `tdk_automotive_pn.csv` — checked-in MPN list (one CGA part
  number per line) consumed by the script.
- `tdk_automotive.csv` — TDK's own per-PIM-row automotive
  capability table; reference data, not currently parsed by the
  generator.
- `reference/` — empty placeholder for upstream datasheets when
  added.
