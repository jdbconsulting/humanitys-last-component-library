#!/usr/bin/env python
"""
Generate build/output/ohmite-kdv.xls from the Ohmite KDV "Standard part
numbers" table.

Ohmite's KDV is a metal-film, low-resistance chip resistor (current
sense) family in 5 EIA sizes (0201 / 0402 / 0603 / 0805 / 1206) with
two fixed tolerances (D = 0.5%, F = 1%) and a fixed list of 20
standard resistance values (50 mΩ ... 820 mΩ). Unlike the Murata MLCC
catalogues there is no public PIM API to pull from; the orderable
list is the table on page 3 of ``reference/ohmite_kdv.pdf``. We
therefore hard-code that table here and emit one workbook row per
(size, tolerance, resistance) cell that the datasheet marks as
offered (``•`` glyph in the PDF).

Output (in build/):

* ohmite-kdv.xls -- Excel 97-2003 workbook matching the per-row schema
  documented in the top-level README.md ("Database Standards"). One
  worksheet named ``KDV``. ``Comment``, ``MFG``, ``MPN`` columns hold
  the orderable Ohmite part number; ``Library Path`` / ``Footprint
  Path`` columns reference the shared house.SchLib + house.PcbLib.
* footprints/ohmite-kdv-footprints.json -- per-vendor footprints
  sidecar consumed by house/build_house_footprints.py and
  house/altium_pcblib/.

Body / footprint mapping
------------------------
The KDV bodies match this repo's house.PcbLib RESC footprints
exactly for 4 of 5 sizes; KDV02's 0.26 mm height needs a new
footprint (RESC0603X26) that doesn't exist in the Panasonic-derived
RESC catalogue, so we add it here and the build picks it up via the
standard merge step.

  KDV02 (0201)  0.60 x 0.30 x 0.26 mm   -> RESC0603X26  (NEW)
  KDV04 (0402)  1.00 x 0.50 x 0.35 mm   -> RESC1005X35  (Panasonic ERA-2)
  KDV06 (0603)  1.60 x 0.80 x 0.45 mm   -> RESC1608X45  (Panasonic ERA-3)
  KDV08 (0805)  2.00 x 1.25 x 0.55 mm   -> RESC2012X55  (Panasonic ERA-6V/K -- 1.20 mm wide;
                                                         Ohmite's 1.25 wins by 0.05 mm
                                                         tolerance, so the merge keeps Panasonic's
                                                         body in priority order)
  KDV12 (1206)  3.10 x 1.60 x 0.55 mm   -> RESC3216X55  (Panasonic ERA-8P -- 3.20 mm long;
                                                         same minor 0.10 mm length variance,
                                                         resolved by priority)

Part-number scheme
------------------
``KDV<size><tolerance>R<value><tape>``

  size:       02 / 04 / 06 / 08 / 12  (per EIA size)
  tolerance:  D = 0.5%, F = 1%, G = 2%, J = 5%
                (the standard table only ships D and F; G and J are
                 build-to-order, not in the catalogue table)
  value:      3-digit milliohms (R050 = 50 mΩ ... R820 = 820 mΩ).
                The optional 1R0 / R0XX / 1R00 forms in the marking
                table cover 1-Ω-and-up parts the standard table
                doesn't include.
  tape:       ET = embossed tape, only standard option in the table

Per-row TCR
-----------
The series specifications block on page 1 lists the TCR by *resistance
range*, not by size: 50-100 mΩ -> ±100 ppm/°C, 100-1000 mΩ -> ±50
ppm/°C. We follow the convention that the boundary (100 mΩ) gets the
*tighter* spec, since 100 mΩ is well inside the metal-film stable-
TCR regime; 50/68/82 mΩ get the looser ±100 ppm.

Usage:
    python vendors/ohmite/kdv/ohmite-kdv.py
"""

import argparse
import os
import sys
from collections import Counter
from typing import Iterable, List, Tuple

import xlwt

HERE = os.path.dirname(os.path.abspath(__file__))
# build/ has two subdirs:
#   intermediate/  artifacts the rest of the build chain consumes
#                  (per-vendor footprints JSONs, merged JSON, .step models,
#                  pdflatex aux files); never user-facing.
#   output/        user-facing artifacts (.xls, .DbLib, .PcbLib, .SchLib,
#                  .pdf). Each lives here exactly once -- no duplicates.
BUILD_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "build"))
INTERMEDIATE_DIR = os.path.join(BUILD_DIR, "intermediate")
OUTPUT_DIR = os.path.join(BUILD_DIR, "output")
FOOTPRINTS_DIR = os.path.join(INTERMEDIATE_DIR, "footprints")
DEFAULT_OUTPUT = os.path.join(OUTPUT_DIR, "ohmite-kdv.xls")

# Make the shared `vendors/_common.py` and `vendors/_dblib.py` helpers
# importable regardless of cwd.
_VENDORS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
import _common as _vendor_common
import _dblib as _vendor_dblib

VENDOR_KEY = "ohmite-kdv"
FAMILY_ID = VENDOR_KEY  # catalog id matches on-disk vendor key
DEFAULT_DBLIB_OUTPUT = os.path.join(OUTPUT_DIR, VENDOR_KEY + ".DbLib")
DEFAULT_FOOTPRINTS_OUTPUT = os.path.join(
    FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json"
)

DRAWING_NOTE = "Dimensions from Ohmite KDV datasheet (Doc. rev 1/21-2)"

SCHLIB = r"house.SchLib"
PCBLIB = r"house.PcbLib"


# --- Catalogue data -----------------------------------------------------

# Standard resistance values from the part-numbers table on page 3 of
# the datasheet, in milliohms.
RESISTANCE_MOHM_VALUES: Tuple[int, ...] = (
    50, 68, 82, 100, 120, 150, 180, 200, 220, 240,
    270, 300, 330, 360, 390, 470, 510, 560, 620, 820,
)

# (size_code, tolerance_code, set_of_offered_milliohm_values).
# All cells in the datasheet's "Standard part numbers" table are
# offered EXCEPT KDV02 (0201) at the D (0.5%) tolerance for the three
# lowest values 50/68/82 mΩ -- those rows have a blank under the
# KDV02D- column in the PDF.
_VALUES_KDV02D = tuple(v for v in RESISTANCE_MOHM_VALUES if v >= 100)  # 17 values

OFFERINGS: Tuple[Tuple[str, str, Tuple[int, ...]], ...] = (
    ("02", "D", _VALUES_KDV02D),
    ("02", "F", RESISTANCE_MOHM_VALUES),
    ("04", "D", RESISTANCE_MOHM_VALUES),
    ("04", "F", RESISTANCE_MOHM_VALUES),
    ("06", "D", RESISTANCE_MOHM_VALUES),
    ("06", "F", RESISTANCE_MOHM_VALUES),
    ("08", "D", RESISTANCE_MOHM_VALUES),
    ("08", "F", RESISTANCE_MOHM_VALUES),
    ("12", "D", RESISTANCE_MOHM_VALUES),
    ("12", "F", RESISTANCE_MOHM_VALUES),
)
# Total: 17 + 9*20 = 197 orderable parts.

#: Tolerance code -> percentage string (the per-row 'Tolerance' column).
TOLERANCE_PCT = {
    "D": "0.5%",
    "F": "1%",
    "G": "2%",
    "J": "5%",
}

#: KDV size code -> body geometry + matching house.PcbLib RESC root.
#: ``terminal_mm`` is the band-length term `T` used by the IPC pad
#: math; it's the second-to-last field of the datasheet's Dimensions
#: row (`l1`/`l2`). For consistency with the existing Panasonic-derived
#: RESC2012X55 / RESC3216X55, the 0805/1206 width and 1206 length are
#: snapped to the standard EIA nominals (1.20 mm and 3.20 mm) instead
#: of Ohmite's slightly-different 1.25 mm and 3.10 mm; the merge step
#: enforces consistency by keeping the higher-priority vendor's body
#: dimensions wherever the same footprint root is contributed by
#: more than one vendor (see settings.house_footprints.priority in
#: the active BuildConfig).
KDV_BODIES = {
    # size: (length_mm, width_mm, height_mm, terminal_mm, eia, footprint_root)
    "02": (0.60, 0.30, 0.26, 0.15, "0201", "RESC0603X26"),
    "04": (1.00, 0.50, 0.35, 0.25, "0402", "RESC1005X35"),
    "06": (1.60, 0.80, 0.45, 0.30, "0603", "RESC1608X45"),
    "08": (2.00, 1.20, 0.55, 0.40, "0805", "RESC2012X55"),
    "12": (3.20, 1.60, 0.55, 0.45, "1206", "RESC3216X55"),
}


# --- Part-number / formatting helpers ----------------------------------


def part_number(size: str, tolerance: str, milliohm: int) -> str:
    """Build the orderable MPN: ``KDV{size}{tol}R{value:03d}ET``.

    Examples:
        KDV02DR100ET   (0201, 0.5%, 100 mΩ)
        KDV04FR050ET   (0402, 1%,    50 mΩ)
        KDV12DR820ET   (1206, 0.5%, 820 mΩ)
    """
    return f"KDV{size}{tolerance}R{milliohm:03d}ET"


def resistance_label(milliohm: int) -> str:
    """Human-readable resistance string for the ``Value`` column.
    Sub-Ω parts use 'mΩ' (e.g. '50mΩ', '820mΩ'); 1 Ω+ would use 'Ω' but
    the standard table only lists sub-Ω parts so the second branch is
    just defensive."""
    if milliohm >= 1000:
        ohms = milliohm / 1000.0
        if ohms == int(ohms):
            return f"{int(ohms)}\u03a9"
        return f"{ohms:g}\u03a9"
    return f"{milliohm}m\u03a9"


def tcr_for(milliohm: int) -> str:
    """TCR by resistance range, per the spec block on page 1 of the
    datasheet: 50-99 mΩ -> ±100 ppm/°C; 100 mΩ and above -> ±50 ppm/°C.
    The 100 mΩ boundary is included in the tighter spec (metal film
    resistors are linear well below 100 mΩ; the looser TCR is purely
    a fab-yield concession at the bottom of the range)."""
    return "+/-100 ppm" if milliohm < 100 else "+/-50 ppm"


def power_for(size: str) -> str:
    """Rated power at 70°C ambient, per the spec block."""
    return {
        "02": "1/10W",
        "04": "1/8W",
        "06": "1/5W",
        "08": "1/4W",
        "12": "1/2W",
    }[size]


# --- Workbook column schema --------------------------------------------

# Same column layout as every other vendor's .xls -- documented in
# README.md "Database Standards". KDV ships as a single packaging
# variant (ET = embossed tape & reel) so MFG 2/MPN 2 .. MFG 5/MPN 5 are
# left blank for forward compatibility with the Murata-style
# multi-pack scheme. Slot numbering starts at 2 (the unsuffixed
# MFG/MPN above is slot 1, by convention).
HEADERS = [
    "Comment", "Description", "MFG", "MPN",
    "MFG 2", "MPN 2", "MFG 3", "MPN 3",
    "MFG 4", "MPN 4", "MFG 5", "MPN 5",
    "Package", "Value",
    "Tolerance", "Tcr", "Tr", "Qual", "Voltage", "Power",
    "Library Path", "Library Ref",
    "Footprint Path", "Footprint Ref",
    "Footprint Path 2", "Footprint Ref 2",
    "Footprint Path 3", "Footprint Ref 3",
]


def build_row(size: str, tolerance: str, milliohm: int) -> List[str]:
    """Return one .xls row matching ``HEADERS``."""
    if size not in KDV_BODIES:
        raise ValueError(f"unknown KDV size code {size!r}")
    L, W, H, T, eia, fp_root = KDV_BODIES[size]

    mpn = part_number(size, tolerance, milliohm)
    value_str = resistance_label(milliohm)
    tol_str = TOLERANCE_PCT[tolerance]
    tcr_str = tcr_for(milliohm)
    pwr_str = power_for(size)

    description = (
        f"RESISTOR CURRENT-SENSE METAL-FILM "
        f"{value_str} {tol_str} {pwr_str} {eia}"
    )

    fp_cells = _vendor_common.xls_footprint_columns(PCBLIB, fp_root, FAMILY_ID)

    return [
        mpn,                          # Comment
        description,                  # Description
        "OHMITE",                     # MFG
        mpn,                          # MPN
        "", "", "", "", "", "", "", "",  # MFG 2/MPN 2 .. MFG 5/MPN 5 (no alternate pack)
        eia,                          # Package
        value_str,                    # Value
        tol_str,                      # Tolerance
        tcr_str,                      # Tcr
        "-55:155",                    # Tr (operating temp range, page 1)
        "",                           # Qual (commercial; AEC-Q200 not claimed by KDV)
        "",                           # Voltage (n/a for current-sense resistors)
        pwr_str,                      # Power
        SCHLIB, "RES",                # Library Path / Ref
    ] + fp_cells


def all_rows(enabled_sizes: frozenset) -> Iterable[List[str]]:
    """Iterate every offered (size, tolerance, value) cell whose
    package size is enabled in the active BuildConfig."""
    for size, tolerance, values in OFFERINGS:
        eia = KDV_BODIES[size][4]
        if eia not in enabled_sizes:
            continue
        for v in values:
            yield build_row(size, tolerance, v)


# --- Per-vendor footprint JSON output ----------------------------------


def _used_footprint_roots(enabled_sizes: frozenset) -> List[Tuple[str, float, float, float, float]]:
    """Return [(root, L, W, H, T), ...] for every footprint root the
    KDV catalogue references whose package size is enabled in the
    active BuildConfig. Each root maps to a single body geometry
    (the KDV size's nominal dimensions)."""
    roots = {}
    for size, body in KDV_BODIES.items():
        L, W, H, T, eia, root = body
        if eia not in enabled_sizes:
            continue
        roots[root] = (L, W, H, T)
    return [(root, L, W, H, T) for root, (L, W, H, T) in sorted(roots.items())]


def write_footprints_json(path: str, enabled_sizes: frozenset) -> int:
    """Emit one JSON entry per (footprint root, resolved density)
    pair. Densities come from the active BuildConfig (override-aware)
    so a user who disabled the M variant gets just L+N rows here
    without any per-script branching. Returns the number of unique
    footprint roots emitted."""
    roots = _used_footprint_roots(enabled_sizes)
    body_specs = [
        {
            "root": root,
            "kind": "R",
            "drawingNote": DRAWING_NOTE,
            "bodyMm": {
                "lengthNominal":         L,
                "widthNominal":          W,
                "heightNominal":         H,
                "terminalLengthNominal": T,
            },
        }
        for root, L, W, H, T in roots
    ]
    rows = _vendor_common.expand_footprint_rows(body_specs, FAMILY_ID)
    _vendor_common.write_footprints_json(
        path, vendor=VENDOR_KEY, footprints=rows,
    )
    return len(roots)


# --- main ---------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", default=DEFAULT_OUTPUT,
                    help="Output .xls path")
    ap.add_argument("--footprints-output", default=DEFAULT_FOOTPRINTS_OUTPUT,
                    help="Output path for the per-vendor footprints "
                         "JSON sidecar.")
    args = ap.parse_args()

    enabled_sizes = _vendor_common.enabled_sizes(FAMILY_ID)

    wb = xlwt.Workbook()
    sheet = wb.add_sheet("KDV")
    for col, h in enumerate(HEADERS):
        sheet.write(0, col, h)

    by_size = Counter()
    by_eia = Counter()
    row_idx = 0
    for row in all_rows(enabled_sizes):
        row_idx += 1
        for col, cell in enumerate(row):
            sheet.write(row_idx, col, cell)
        # Recover size / EIA from the MPN for the diagnostic summary.
        mpn = row[0]
        size = mpn[3:5]
        by_size[size] += 1
        by_eia[KDV_BODIES[size][4]] += 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FOOTPRINTS_DIR, exist_ok=True)
    wb.save(args.output)
    _vendor_dblib.write_dblib(DEFAULT_DBLIB_OUTPUT, vendor_key=VENDOR_KEY, tables=["KDV"])
    fp_count = write_footprints_json(args.footprints_output, enabled_sizes)

    densities = _vendor_common.density_codes(FAMILY_ID)
    print(f"Wrote {args.output}: {row_idx} rows.", file=sys.stderr)
    print(
        f"Wrote {args.footprints_output}: {fp_count} unique RESC "
        f"footprints x {len(densities)} density variants ({'/'.join(densities) or '<none>'}).",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    print("Emitted by KDV size:", file=sys.stderr)
    for s in sorted(by_size):
        eia = KDV_BODIES[s][4]
        print(f"  KDV{s} ({eia}): {by_size[s]:>4}", file=sys.stderr)
    print(file=sys.stderr)
    print("Emitted by EIA size:", file=sys.stderr)
    for e in sorted(by_eia):
        print(f"  {e}: {by_eia[e]:>4}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
