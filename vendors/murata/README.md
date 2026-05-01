# Murata Library Notes

## Murata Capacitors

Murata capacitor generation targets the GCM automotive MLCC family and emits `build/murata-capacitors.xls`.

Main files in this folder:

- `murata-capacitors.py` - converts Murata CSV rows into DbLib-compatible `.xls` rows.
- `fetch_gcm_pim.py` - downloads the GCM part list CSV from Murata PIM.
- `gcm_parts.csv` - checked-in input dataset consumed by `murata-capacitors.py`.
- `reference/murata_gcm.pdf` - primary family reference datasheet.

## Murata Ferrites

`murata-ferrite.py` is currently a placeholder for future procedural generation of `build/murata-ferrite.xls`.

At the moment, the ferrite workbook is hand-maintained; the script exists as the future insertion point for generator logic once the ferrite flow is fully automated.
