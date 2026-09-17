#!/usr/bin/env python
"""
Generate build/output/panasonic-era-a.xls for the Panasonic ERA-A thin-film
high-precision chip-resistor family.

Datasheet: reference/panasonic_era-a.pdf

ERA-A precision thin film: ERA-1AEB 0201 (100 ohm..10 kohm),
ERA-2AEB 0402 (47 ohm..100 kohm), ERA-2ARB 0402 (200 ohm..47 kohm).
Tolerance 0.1%; TCR 25 ppm/K for AEB and 10 ppm/K for ARB.
ERA-A remains useful alongside the higher-power V/K line.

Usage:
    python vendors/panasonic/era-a/panasonic-era-a.py
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

_VENDORS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
_PANASONIC_DIR = os.path.normpath(os.path.join(HERE, ".."))
if _PANASONIC_DIR not in sys.path:
    sys.path.insert(0, _PANASONIC_DIR)
import _common as _vendor_common
import _dblib as _vendor_dblib
import _panasonic_common as pc

VENDOR_KEY = "panasonic-era-a"
SHEET = "ERA-A"

FOOTPRINT_ROOTS = [
    "RESC0603X23",  # 0201
]


def build_table():
    table = [pc.HEADERS]

    # ERA-1AEB (0201)
    table += pc.make_era_range("Panasonic", "ERA-1AEB", "C",
        pc.era_100_10k, "1/20W", "25V",
        "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 1", "0201", "RES", pc.SCHLIB,
        "RESC0603X23", VENDOR_KEY)

    table += pc.make_era_range("Panasonic", "ERA-2ARB", "X",
        [v for v in pc.e24_e96_combined_100_1M if 200 <= v <= 47000],
        "0.063W", "50V", "0.1%", "+/-10", "-55:155", "AEC-Q200 GRADE 1",
        "0402", "RES", pc.SCHLIB, "RESC1005X40_ERA2A", VENDOR_KEY)
    table += pc.make_era_range("Panasonic", "ERA-2AEB", "X",
        pc.era_47_100K, "0.063W", "50V", "0.1%", "+/-25", "-55:155",
        "AEC-Q200 GRADE 1", "0402", "RES", pc.SCHLIB, "RESC1005X40_ERA2A", VENDOR_KEY)

    return table


def era2_footprints():
    if "0402" not in _vendor_common.enabled_sizes(VENDOR_KEY):
        return []
    return _vendor_common.expand_footprint_rows([{
        "root": "RESC1005X40_ERA2A", "kind": "R",
        "drawingNote": "Panasonic ERA-A 24-Apr-2024 p.3; maximum height; nominal L/W and terminals",
        "bodyMm": {"lengthNominal": 1.0, "widthNominal": .5,
                   "heightNominal": .4, "terminalLengthNominal": .25},
        "model": {"type": "wide-bottom", "topTerminalLengthMm": .15},
    }], VENDOR_KEY)


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
        footprints=pc.build_footprint_rows(FOOTPRINT_ROOTS, VENDOR_KEY) + era2_footprints(),
    )


if __name__ == "__main__":
    main()
