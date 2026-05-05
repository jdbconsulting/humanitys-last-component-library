#!/usr/bin/env python
"""
Generate build/output/panasonic-era-a.xls for the Panasonic ERA-A thin-film
high-precision chip-resistor family.

Datasheet: reference/panasonic_era-a.pdf

ERA-A is the precision thin-film line. Only the 0201 part (ERA-1AEB)
is carried here -- the 0402-1206 ERA-2/3/6/8AEB parts are
intentionally omitted because they're superseded by the newer ERA-V/K
line (higher power, anti-ESD, anti-sulfur). At 0201, ERA-1AEB is the
only thin-film precision option Panasonic ships.

Tolerance: 0.1%. TCR: +/-25 ppm/K. Range: 100 ohm - 10 kohm.

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
    table += pc.make_era_range("PANASONIC", "ERA-1AEB", "C",
        pc.era_100_10k, "1/20W", "25V",
        "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 1", "0201", "RES", pc.SCHLIB,
        ["RESC0603X23N", "RESC0603X23L", "RESC0603X23M"],
        [pc.PCBLIB, pc.PCBLIB, pc.PCBLIB])

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
        footprints=pc.build_footprint_rows(FOOTPRINT_ROOTS),
    )


if __name__ == "__main__":
    main()
