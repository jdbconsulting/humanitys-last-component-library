#!/usr/bin/env python
"""
Generate build/output/panasonic-erj.xls for the Panasonic ERJ general-purpose
thick-film chip-resistor family (plus the matching 0R jumper sizes).

Datasheet: reference/panasonic_erj.pdf

ERJ is Panasonic's volume thick-film line. Sizes carried here are
01005 (RESC0402X13), 0201 (RESC0603X23), 0402 (RESC1005X35), 0603
(RESC1608X45), and 0805 (RESC2012X60). The Y / C / X / V suffix
variants below refer to packaging only.

Outputs:

* ``build/output/panasonic-erj.xls`` -- Excel 97-2003 workbook, one
  sheet ``ERJ``, matches the per-row schema documented in the
  top-level README.md ('Database Standards' section). User-facing.
* ``build/output/panasonic-erj.DbLib`` -- INI-format DbLib bound to
  the .xls above, emitted by :mod:`vendors._dblib`. User-facing.
* ``build/intermediate/footprints/panasonic-erj-footprints.json``
  -- per-vendor footprints sidecar consumed by
  ``house/build_house_footprints.py``, the STEP generator, and the
  .PcbLib autogenerator. Intermediate.

Usage:
    python vendors/panasonic/erj/panasonic-erj.py
"""

import os
import sys

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

# Make `vendors/_common.py`, `vendors/_dblib.py`, and the sibling
# `vendors/panasonic/_panasonic_common.py` helpers importable
# regardless of cwd.
_VENDORS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
_PANASONIC_DIR = os.path.normpath(os.path.join(HERE, ".."))
if _PANASONIC_DIR not in sys.path:
    sys.path.insert(0, _PANASONIC_DIR)
import _common as _vendor_common
import _dblib as _vendor_dblib
import _panasonic_common as pc

VENDOR_KEY = "panasonic-erj"
SHEET = "ERJ"

# Footprint roots referenced by every row in this family. Listed
# explicitly (rather than collected from the RESC_BODIES dict) so the
# per-vendor footprints JSON only contains roots this family actually
# emits, even if more land in the shared body table later.
FOOTPRINT_ROOTS = [
    "RESC0402X13",  # 01005 thick film
    "RESC0603X23",  # 0201
    "RESC1005X35",  # 0402
    "RESC1608X45",  # 0603
    "RESC2012X60",  # 0805 thick film (vs ERA-V/K's 0.55 mm body)
]


def build_table():
    table = [pc.HEADERS]

    # ERJ-XGNF (01005)
    # NOTE: there are multiple suffix options for packaging (Y and U)
    # but it appears only Y is commonly used.
    table += pc.make_res_range("Panasonic", "ERJ-XGNF", "Y",
        pc.e24_e96_combined_10_97R6, "1/32W", "15V",
        "1%", "+/-300", "-55:125", "", "01005", "RES", pc.SCHLIB,
        "RESC0402X13", VENDOR_KEY)
    table += pc.make_res_range("Panasonic", "ERJ-XGNF", "Y",
        pc.e24_e96_combined_100_1M, "1/32W", "15V",
        "1%", "+/-200", "-55:125", "", "01005", "RES", pc.SCHLIB,
        "RESC0402X13", VENDOR_KEY)

    # ERJ-1GNF (0201)
    table += pc.make_res_range("Panasonic", "ERJ-1GNF", "C",
        pc.e24_e96_combined_10_1M, "1/20W", "25V",
        "1%", "+/-200", "-55:125", "", "0201", "RES", pc.SCHLIB,
        "RESC0603X23", VENDOR_KEY)

    # ERJ-1GJF (0201) AUTOMOTIVE
    table += pc.make_res_range("Panasonic", "ERJ-1GJF", "C",
        pc.e24_e96_combined_10_1M, "1/20W", "25V",
        "1%", "+/-200", "-55:155", "AEC-Q200 GRADE 1", "0201", "RES", pc.SCHLIB,
        "RESC0603X23", VENDOR_KEY)

    # ERJ-2RC (0402)
    # NOTE: DOESN'T APPEAR TO BE IN STOCK ANYWHERE; intentionally not
    # emitted. See the original panasonic-resistors.py history for the
    # disabled make_res_range invocation.

    # ERJ-2RKF (0402)
    table += pc.make_res_range("Panasonic", "ERJ-2RKF", "X",
        pc.e24_e96_combined_10_1M, "1/10W", "50V",
        "1%", "+/-100", "-55:155", "AEC-Q200 GRADE 0", "0402", "RES", pc.SCHLIB,
        "RESC1005X35", VENDOR_KEY)

    # ERJ-3EKF (0603)
    table += pc.make_res_range("Panasonic", "ERJ-3EKF", "V",
        pc.e24_e96_combined_10_1M, "1/10W", "75V",
        "1%", "+/-100", "-55:155", "AEC-Q200 GRADE 0", "0603", "RES", pc.SCHLIB,
        "RESC1608X45", VENDOR_KEY)

    # ERJ-6ENF (0805)
    table += pc.make_res_range("Panasonic", "ERJ-6ENF", "V",
        pc.e24_e96_combined_10_2M2, "1/8W", "150V",
        "1%", "+/-100", "-55:155", "AEC-Q200 GRADE 0", "0805", "RES", pc.SCHLIB,
        "RESC2012X60", VENDOR_KEY)

    # --- 0-ohm jumpers -------------------------------------------------
    # NOTE: NOT GOING TO ADD 5% RESISTORS TO LIBRARY. USE 1% RESISTORS
    # INSTEAD. Only the 0R jumper variant of the 5% suffixes is carried.

    # ERJ-XGNJ (01005)
    table += pc.make_res_jumper("Panasonic", "ERJ-XGN0R00Y", "0.5A", "01005",
        "RES", pc.SCHLIB, "RESC0402X13", VENDOR_KEY)

    # ERJ-1GNJ (0201)
    table += pc.make_res_jumper("Panasonic", "ERJ-1GN0R00C", "0.5A", "0201",
        "RES", pc.SCHLIB, "RESC0603X23", VENDOR_KEY)

    # ERJ-2GEJ (0402)
    table += pc.make_res_jumper("Panasonic", "ERJ-2GE0R00X", "0.5A", "0402",
        "RES", pc.SCHLIB, "RESC1005X35", VENDOR_KEY)

    # ERJ-3GEYJ (0603)
    table += pc.make_res_jumper("Panasonic", "ERJ-3GEY0R00V", "0.5A", "0603",
        "RES", pc.SCHLIB, "RESC1608X45", VENDOR_KEY)

    # ERJ-6GEYJ (0805)
    table += pc.make_res_jumper("Panasonic", "ERJ-6GEY0R00V", "0.5A", "0805",
        "RES", pc.SCHLIB, "RESC2012X60", VENDOR_KEY)

    return table


def main():
    table = build_table()
    wb = xlwt.Workbook()
    sheet = wb.add_sheet(SHEET)
    for x, line in enumerate(table):
        for y, data in enumerate(line):
            sheet.write(x, y, data)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FOOTPRINTS_DIR, exist_ok=True)
    wb.save(os.path.join(OUTPUT_DIR, VENDOR_KEY + ".xls"))
    _vendor_dblib.write_dblib(
        path=os.path.join(OUTPUT_DIR, VENDOR_KEY + ".DbLib"),
        vendor_key=VENDOR_KEY,
        tables=[SHEET],
    )
    _vendor_common.write_footprints_json(
        os.path.join(FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json"),
        vendor=VENDOR_KEY,
        footprints=pc.build_footprint_rows(FOOTPRINT_ROOTS, VENDOR_KEY),
    )


if __name__ == "__main__":
    main()
