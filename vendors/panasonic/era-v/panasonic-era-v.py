#!/usr/bin/env python
"""
Generate build/output/panasonic-era-v.xls for the Panasonic ERA-V / ERA-K
thin-film high-stability chip-resistor family.

Datasheet: reference/panasonic_era-v.pdf (covers both V and K suffixes)

Sizes carried: 0402 (RESC1005X35), 0603 (RESC1608X45), 0805
(RESC2012X55). The V suffix is the standard resistance range; the K
suffix extends the range upwards (high-resistance variants of the
same body). 1206 is intentionally omitted -- at that size we only
carry the 500 V ERA-P, since the incremental cost over ERA-V/K is
not worth losing the voltage headroom.

Tolerance: 0.1%. TCR: +/-25 ppm/K. Anti-ESD, anti-sulfur.

Usage:
    python vendors/panasonic/era-v/panasonic-era-v.py
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

VENDOR_KEY = "panasonic-era-v"
SHEET = "ERA-V"

FOOTPRINT_ROOTS = [
    "RESC1005X35",  # 0402
    "RESC1608X45",  # 0603
    "RESC2012X55",  # 0805 thin film
]


def build_table():
    table = [pc.HEADERS]

    # ERA-2VEB (0402)
    table += pc.make_era_range("PANASONIC", "ERA-2VEB", "X",
        pc.era_47_100K, "1/10W", "75V",
        "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0402", "RES", pc.SCHLIB,
        ["RESC1005X35N", "RESC1005X35L", "RESC1005X35M"],
        [pc.PCBLIB, pc.PCBLIB, pc.PCBLIB])

    # ERA-3VEB (0603)
    table += pc.make_era_range("PANASONIC", "ERA-3VEB", "V",
        pc.era_47_100K, "1/8W", "100V",
        "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0603", "RES", pc.SCHLIB,
        ["RESC1608X45N", "RESC1608X45L", "RESC1608X45M"],
        [pc.PCBLIB, pc.PCBLIB, pc.PCBLIB])

    # ERA-3KEB (0603) - high-resistance extension
    table += pc.make_era_range("PANASONIC", "ERA-3KEB", "V",
        pc.era_102K_330K, "1/8W", "100V",
        "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0603", "RES", pc.SCHLIB,
        ["RESC1608X45N", "RESC1608X45L", "RESC1608X45M"],
        [pc.PCBLIB, pc.PCBLIB, pc.PCBLIB])

    # ERA-6VEB (0805)
    table += pc.make_era_range("PANASONIC", "ERA-6VEB", "V",
        pc.era_47_100K, "1/4W", "150V",
        "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0805", "RES", pc.SCHLIB,
        ["RESC2012X55N", "RESC2012X55L", "RESC2012X55M"],
        [pc.PCBLIB, pc.PCBLIB, pc.PCBLIB])

    # ERA-6KEB (0805) - high-resistance extension
    table += pc.make_era_range("PANASONIC", "ERA-6KEB", "V",
        pc.era_102K_820K, "1/4W", "150V",
        "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0805", "RES", pc.SCHLIB,
        ["RESC2012X55N", "RESC2012X55L", "RESC2012X55M"],
        [pc.PCBLIB, pc.PCBLIB, pc.PCBLIB])

    # NOTE: ERA-8VEB / ERA-8KEB (1206) are intentionally omitted. At
    # 1206, the incremental cost over the 500V ERA-8PEB is not worth
    # the reduced voltage headroom, so we only carry ERA-P in 1206.

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
