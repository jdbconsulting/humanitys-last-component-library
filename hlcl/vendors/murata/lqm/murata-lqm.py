#!/usr/bin/env python
"""
Generate ``build/output/murata-lqm.xls`` (and the matching .DbLib +
``murata-lqm-footprints.json``) from
``vendors/murata/lqm/lqm_parts.csv``, written by
``vendors/murata/scrape_lq_pdfs.py`` from Murata's per-subseries
spec PDFs.

Inputs:

* ``vendors/murata/lqm/lqm_parts.csv`` -- one row per orderable LQM_
  MPN. CSV columns:

      subseries, mpn, operating_temp_min_c, operating_temp_max_c,
      jelf_id, tokens

  Inductance value, tolerance, package size, and IPC footprint root
  are decoded from the orderable MPN by the helpers in
  :mod:`vendors.murata._lq_common`. ``tokens`` is the pipe-joined
  list of post-MPN PDF columns; we mine it for DCR / SRF / rated-
  current best-effort (the PDF table layouts vary across subseries).

Outputs:

* ``build/output/murata-lqm.xls`` -- Excel 97-2003 workbook with one
  sheet per EIA case-size we ship (LQM0603 / LQM0805 / LQM1206), 21
  columns each. References ``build/output/house.SchLib`` and
  ``build/output/house.PcbLib`` from the per-row Library/Footprint
  Path columns.

* ``build/output/murata-lqm.DbLib`` -- companion DbLib emitted by
  :func:`vendors._dblib.write_dblib` so Altium can bind against the
  worksheet directly.

* ``build/intermediate/footprints/murata-lqm-footprints.json`` --
  per-vendor footprint specification consumed by
  ``house/build_house_footprints.py``, ``house/build_step_models.py``,
  and the .PcbLib autogenerator. INDC roots emitted match the (metric
  body x nominal-height) pair from each subseries entry in
  :data:`vendors.murata._lq_common.SUBSERIES_GEOMETRY`.

Usage:
    python vendors/murata/lqm/murata-lqm.py
"""

from __future__ import annotations

import csv
import os
import sys
from collections import Counter

import xlwt

HERE = os.path.dirname(os.path.abspath(__file__))
# Three ``..`` jumps: lqm -> murata -> vendors -> hlcl. The build root
# is ``hlcl/build/`` (matching the BLM / GCM / GRM scripts), which is
# what ``hlcl/build.py`` and ``hlcl/house/build_house_footprints.py``
# read from.
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
BUILD_DIR = os.path.join(REPO_ROOT, "build")
INTERMEDIATE_DIR = os.path.join(BUILD_DIR, "intermediate")
OUTPUT_DIR = os.path.join(BUILD_DIR, "output")
FOOTPRINTS_DIR = os.path.join(INTERMEDIATE_DIR, "footprints")
INPUT_CSV = os.path.join(HERE, "lqm_parts.csv")

_VENDORS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
import _common  # noqa: E402
import _dblib  # noqa: E402

_MURATA_DIR = os.path.normpath(os.path.join(HERE, ".."))
if _MURATA_DIR not in sys.path:
    sys.path.insert(0, _MURATA_DIR)
import _lq_common as _lq  # noqa: E402

FAMILY_ID = "murata-lqm"
VENDOR_KEY = "murata-lqm"
FOOTPRINTS_JSON = os.path.join(FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json")
OUTPUT_XLS = os.path.join(OUTPUT_DIR, VENDOR_KEY + ".xls")
OUTPUT_DBLIB = os.path.join(OUTPUT_DIR, VENDOR_KEY + ".DbLib")

DRAWING_NOTE = (
    "Dimensions from Murata LQ-series part-numbering reference and "
    "per-subseries spec PDFs (vendors/murata/scrape_lq_pdfs.py)"
)


def main() -> int:
    if not os.path.exists(INPUT_CSV):
        print(
            f"error: {INPUT_CSV} not found. Run "
            f"`python hlcl/vendors/murata/scrape_lq_pdfs.py` to generate it.",
            file=sys.stderr,
        )
        return 1

    rows_by_sheet: dict[str, list[list]] = {}
    fp_roots_with_base: list[tuple[str, str]] = []
    pkg_counts: Counter = Counter()
    fp_root_counts: Counter = Counter()
    skipped_unknown = Counter()
    skipped_disabled = 0
    skipped_undecodable = 0

    with open(INPUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for csv_row in reader:
            base = _lq.subseries_base(csv_row.get("subseries", ""))
            if base not in _lq.SUBSERIES_GEOMETRY:
                skipped_unknown[base] += 1
                continue
            geom = _lq.SUBSERIES_GEOMETRY[base]
            if geom["eia"] not in _common.enabled_sizes(FAMILY_ID):
                skipped_disabled += 1
                continue
            built = _lq.row_for_part(csv_row, family_id=FAMILY_ID, is_lqm=True)
            if built is None:
                skipped_undecodable += 1
                continue
            row, fp_root, sheet_name = built
            rows_by_sheet.setdefault(sheet_name, []).append(row)
            fp_roots_with_base.append((fp_root, base))
            pkg_counts[geom["eia"]] += 1
            fp_root_counts[fp_root] += 1

    sheet_order = sorted(rows_by_sheet)
    if not sheet_order:
        print(
            f"warning: no LQM rows survived the BuildConfig filter (CSV had "
            f"{sum(skipped_unknown.values()) + skipped_disabled + skipped_undecodable} "
            f"candidate rows total).",
            file=sys.stderr,
        )

    wb = xlwt.Workbook()
    sheets = {name: wb.add_sheet(name) for name in sheet_order}
    for name in sheet_order:
        for col, h in enumerate(_lq.HEADERS):
            sheets[name].write(0, col, h)
        for r_idx, row in enumerate(sorted(rows_by_sheet[name], key=lambda r: r[0]), start=1):
            for col, cell in enumerate(row):
                sheets[name].write(r_idx, col, cell)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FOOTPRINTS_DIR, exist_ok=True)
    wb.save(OUTPUT_XLS)
    if sheet_order:
        _dblib.write_dblib(OUTPUT_DBLIB, vendor_key=VENDOR_KEY, tables=sheet_order)
    rows = _lq.build_footprint_rows(fp_roots_with_base, FAMILY_ID, DRAWING_NOTE)
    _common.write_footprints_json(FOOTPRINTS_JSON, vendor=VENDOR_KEY, footprints=rows)

    total = sum(len(rows_by_sheet[s]) for s in sheet_order)
    densities = _common.density_codes(FAMILY_ID)
    print(
        f"Wrote {OUTPUT_XLS}: {total} rows across {len(sheet_order)} sheet(s).",
        file=sys.stderr,
    )
    for name in sheet_order:
        print(f"  {name}: {len(rows_by_sheet[name]):>4} rows", file=sys.stderr)
    print(
        f"Wrote {FOOTPRINTS_JSON}: {len(set(r for r, _ in fp_roots_with_base))} "
        f"unique INDC roots x {len(densities)} density variants "
        f"({'/'.join(densities) or '<none>'}).",
        file=sys.stderr,
    )
    if skipped_disabled:
        print(
            f"  ({skipped_disabled} parts dropped: package size disabled in BuildConfig)",
            file=sys.stderr,
        )
    if skipped_undecodable:
        print(
            f"  ({skipped_undecodable} parts dropped: MPN didn't decode "
            "to a known inductance value)",
            file=sys.stderr,
        )
    if skipped_unknown:
        print(file=sys.stderr)
        print(
            f"WARNING: {sum(skipped_unknown.values())} parts dropped from "
            f"{len(skipped_unknown)} subseries not in SUBSERIES_GEOMETRY:",
            file=sys.stderr,
        )
        for sub, n in sorted(skipped_unknown.items()):
            print(f"  {sub}: {n} parts", file=sys.stderr)
        print(
            "  Add an entry to vendors/murata/_lq_common.py:SUBSERIES_GEOMETRY "
            "to ship these.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
