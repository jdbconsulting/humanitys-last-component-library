# Samsung CL Library Notes

Generates `build/output/samsung-capacitors.xls` for Samsung's **CL**
general-purpose MLCC line. The .xls's single worksheet is named `CL`.

## Files

- `samsung-capacitors.py` — decodes Samsung CL part numbers from the
  input MPN list into DbLib-compatible `.xls` rows + the per-vendor
  footprints JSON sidecar. Output paths:
  `build/output/samsung-capacitors.xls`,
  `build/output/samsung-capacitors.DbLib`,
  `build/intermediate/footprints/samsung-capacitors-footprints.json`.
- `filtered_samsung_mlcc.csv` — checked-in MPN list, one Samsung CL
  part per line (we only consume the second column). Each entry is the
  **14-character design-intent base** of a CL part number (CLxxYzzzVVTHWFG…
  through the inner-electrode/termination/plating code) — i.e. the full
  orderable 15-char MPN with the trailing slot-15 packaging code
  intentionally stripped. The script appends the four canonical
  packaging codes itself (see "Packaging variants" below). Each base
  MPN encodes its electrical and mechanical parameters in fixed
  character positions per Samsung's CL-series naming guide; the
  decoder tables live at the top of `samsung-capacitors.py`.
- `reference/samsung_mlcc.pdf` — primary family reference datasheet.
- `reference/samsung_standard_mlcc_dimensions*.png` — body-dimension
  cheat sheets (as-shipped + as-drawn variants).

## Packaging variants

A real orderable Samsung CL SKU is always 15 characters: the 14-char
design-intent base (in the CSV) plus a single slot-15 packaging code.
The script emits the base MPN in the `MPN` column and four concrete
orderable variants in `MPN 2` … `MPN 5`, mirroring the same mechanism
`vendors/murata/gcm/murata-gcm.py` uses for Murata's `#` wildcard:

| Slot  | Suffix | Tape               | Reel          |
| ----- | ------ | ------------------ | ------------- |
| MPN 2 | `C`    | Cardboard (paper)  | 7″ (φ178 mm)  |
| MPN 3 | `L`    | Cardboard (paper)  | 13″ (φ330 mm) |
| MPN 4 | `E`    | Embossed (plastic) | 7″ (φ178 mm)  |
| MPN 5 | `F`    | Embossed (plastic) | 13″ (φ330 mm) |

This is the {7″/13″ reel} × {paper/embossed tape} matrix from
`reference/samsung_mlcc.pdf` p. 8 (slot-15 packaging-code table) and
p. 123 (size/thickness → tape-media table). Per the latter, chips
with body T ≤ ~0.85 mm only ship in paper tape (so for those parts
only the C / L slots resolve to real SKUs at distributors); chips
with T ≥ 1.0 mm — every 1206/1210 part above ~1 µF, plus thicker
0805s — only ship in embossed tape (only E / F resolve). Emitting
all four unconditionally keeps the workbook flat (one row per
electrical part) and lets Altium Part Choices / the BOM lookup
report which of the four exist for each row. This is the same
"emit all, let the resolver filter" strategy `murata-gcm.py` uses
with its `PACK_SUFFIXES = ("L", "K", "D", "J")`.

Slot-15 has more legal codes than the four listed above (e.g. `8`/`H`
are 7″ paper quantity-option alternates of `C`; `D`/`3` are 13″ paper
alternates of `L`; `G` is a 7″ embossed alternate of `E`; plus 10″
reel `S`/`O`, aligned-chip `Z`/`Y`/`W`/`R`/`7`, 1-mm-pitch `J`/`2`,
and bulk `B`). We pick one canonical letter per (media, reel-size)
combo to keep the column count flat — same rationale Murata uses.
