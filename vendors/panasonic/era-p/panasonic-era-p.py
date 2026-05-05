#!/usr/bin/env python
"""
Generate build/output/panasonic-era-p.xls for the Panasonic ERA-P thin-film
high-voltage chip-resistor family.

Datasheet: reference/panasonic_era-p.pdf

ERA-P is the 1206-only, 500 V limiting variant of the ERA precision
thin-film line. Tolerance: 0.1%. TCR: +/-25 ppm/K. Anti-ESD (4 kV
HBM Class 3), anti-sulfur. The increased voltage rating is the only
reason we carry a 1206 ERA at all -- at smaller sizes the ERA-V/K
parts cover the same precision niche at lower cost.

Usage:
    python vendors/panasonic/era-p/panasonic-era-p.py
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

VENDOR_KEY = "panasonic-era-p"
SHEET = "ERA-P"

FOOTPRINT_ROOTS = [
    "RESC3216X55",  # 1206 thin film
]


def build_table():
    table = [pc.HEADERS]

    # ERA-8PEB (1206)
    table += pc.make_era_range("PANASONIC", "ERA-8PEB", "V",
        pc.era_160K_1M, "1/4W", "500V",
        "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "1206", "RES", pc.SCHLIB,
        ["RESC3216X55N", "RESC3216X55L", "RESC3216X55M"],
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
