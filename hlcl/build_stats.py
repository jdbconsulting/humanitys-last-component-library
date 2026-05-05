"""
Aggregate build statistics for the configurator's library-stats banner.

After ``build.build_all()`` finishes, the in-browser configurator wants
two numbers that can only be known once the build has actually emitted
something to ``build/``:

  * ``components``         -- total orderable MPN rows the build emitted,
                              summed across every vendor ``*.xls`` file
                              under ``build/output/``. Requires
                              ``xlrd`` (any modern version is fine: 2.x
                              dropped ``.xlsx`` support but kept ``.xls``,
                              which is exactly what we emit).
  * ``unique_footprints``  -- distinct footprint definitions in
                              ``build/intermediate/footprints/house-footprints.json``,
                              i.e. after the priority-resolved merge.

(The third banner cell -- "Families" -- is intentionally NOT computed
here. It's just the number of enabled families in the live config and
the configurator reads it directly from ``BuildConfig.families`` so it
stays accurate whether or not a build has ever run.)

The numbers are derived from on-disk build artefacts rather than from
the live registry / config, so:

  * They reflect what the build actually produced, not what the
    config asked for. A vendor that aborted partway through an
    in-process error contributes zero rows here, even though its
    family flag is still ``enabled = true`` in the BuildConfig.
  * The same statistics function works against a build directory
    sitting on disk (CLI use) and one in Pyodide's MEMFS (browser
    use) -- both are just paths.

The function is invoked from :mod:`hlcl_runner` (TS) after
``build.build_all`` returns; it isn't wired into ``build.build_all``
itself because computing it has a small but non-zero cost (xlrd reads
every emitted .xls back from disk) and not every consumer cares about
the totals.
"""

from __future__ import annotations

import json
import os
from typing import Any


_FOOTPRINTS_DIRNAME = os.path.join("build", "intermediate", "footprints")
_OUTPUT_DIRNAME = os.path.join("build", "output")
_HOUSE_FP_BASENAME = "house-footprints.json"


def _count_xls_data_rows(path: str) -> int:
    """Return the number of *data* rows (excluding the header) across
    every sheet of the .xls workbook at ``path``.

    xlrd is imported lazily so a host without xlrd installed can still
    import this module (e.g. just to call
    :func:`count_unique_footprints`); the failure surfaces only when
    the caller actually wants the component count.
    """
    import xlrd  # type: ignore[import-untyped]

    book = xlrd.open_workbook(path, on_demand=True)
    try:
        total = 0
        for sheet_name in book.sheet_names():
            sheet = book.sheet_by_name(sheet_name)
            # Every vendor .xls in this repo has exactly one header row
            # at index 0 (see vendors/_common.py and per-vendor scripts);
            # subtracting one keeps the count user-meaningful.
            if sheet.nrows > 0:
                total += sheet.nrows - 1
            book.unload_sheet(sheet_name)
        return total
    finally:
        # `release_resources` is a hard requirement when on_demand=True
        # otherwise the underlying mmap stays open. In Pyodide's MEMFS
        # this matters for a clean rebuild.
        book.release_resources()


def count_components(root: str) -> int:
    """Sum data rows across every ``build/output/*.xls`` workbook.

    A workbook that fails to open is logged via ``RuntimeError`` (so the
    caller surfaces it in the UI console), not silently ignored -- a
    corrupt .xls is a real regression.
    """
    out_dir = os.path.join(root, _OUTPUT_DIRNAME)
    if not os.path.isdir(out_dir):
        return 0
    total = 0
    for fn in sorted(os.listdir(out_dir)):
        if not fn.endswith(".xls"):
            continue
        path = os.path.join(out_dir, fn)
        try:
            total += _count_xls_data_rows(path)
        except Exception as e:  # noqa: BLE001 -- we want any xlrd error reported
            raise RuntimeError(f"failed to count rows in {path}: {e}") from e
    return total


def count_unique_footprints(root: str) -> int:
    """Return the number of entries in the merged
    ``house-footprints.json``, or 0 if the merger hasn't run."""
    path = os.path.join(root, _FOOTPRINTS_DIRNAME, _HOUSE_FP_BASENAME)
    if not os.path.isfile(path):
        return 0
    with open(path, "r", encoding="ascii") as f:
        doc = json.load(f)
    fps = doc.get("footprints")
    return len(fps) if isinstance(fps, list) else 0


def compute_build_stats(root: str) -> dict[str, Any]:
    """Walk the on-disk build outputs at ``root`` and return the
    build-derived stats pair (the third banner cell, "Families", is
    read straight off the live config in TS land).

    ``root`` is the same path passed to :func:`build.build_all` (the
    HLCL project root that contains ``build/``). For the in-browser
    Pyodide build that's ``/hlcl``; for the CLI build it's
    typically ``hlcl/``.
    """
    return {
        "components": count_components(root),
        "unique_footprints": count_unique_footprints(root),
    }
