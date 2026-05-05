#!/usr/bin/env python
"""
Merge every per-vendor ``build/intermediate/footprints/<vendor>-footprints.json``
into a single ``build/intermediate/footprints/house-footprints.json``.

This is the canonical input to two downstream pipeline steps:

  1. ``house/build_step_models.py`` reads the merged JSON to generate
     parametric STEP 3D models in ``build/step/*.step``.
  2. ``house/altium_pcblib/`` (driven by ``house/build_pcblib.py``) reads the merged
     JSON plus the STEP files to emit ``build/house.PcbLib`` -- the
     final Altium PCB footprint library.

Conflict resolution
-------------------
When two or more vendor JSONs define a row with the same ``name``
(e.g. SAMSUNG CL and TDK CGA both define ``CAPC1005X50N`` because the
body geometry is shared between the two families), the row from the
vendor that appears first in ``settings.house_footprints.priority``
in the active ``BuildConfig`` (loaded by :mod:`hlcl._config` from
``--config <path>`` or ``hlcl/factory-defaults.json``) wins. Losing
rows are dropped; a per-conflict tally and a list of any vendor JSONs
not mentioned in the priority list are printed to stderr.

Vendors not listed in the priority block are still merged in (so a new
vendor's footprints become usable immediately), but with the lowest
priority -- they only contribute footprints no listed vendor defines.

Schema
------
Inputs (per-vendor):

    {
      "schemaVersion": 1,
      "vendor": "panasonic-erj",
      "footprints": [
        {"name": "...", "kind": "...", "density": "...",
         "drawingNote": "...", "bodyMm": {...}},
        ...
      ]
    }

Output (merged, with `vendor` injected per row):

    {
      "schemaVersion": 1,
      "vendorPriority": [...],          # what we used to break ties
      "footprints": [
        {"name": "...", "vendor": "...", "kind": "...", ...},
        ...
      ]
    }

Usage
-----
    python house/build_house_footprints.py

Run *after* every per-vendor generator script has been re-run;
``python build.py house-footprints`` chains the dependency for you
via its ``@vendors`` pseudo-dep.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from typing import Iterable, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, ".."))
# Per-vendor + merged JSONs are intermediates: nothing user-facing reads
# them, they only feed the STEP and .PcbLib generators downstream.
FOOTPRINTS_DIR = os.path.join(REPO_ROOT, "build", "intermediate", "footprints")
OUTPUT_PATH = os.path.join(FOOTPRINTS_DIR, "house-footprints.json")

VENDOR_SUFFIX = "-footprints.json"
HOUSE_BASENAME = "house" + VENDOR_SUFFIX  # excluded from inputs

#: Schema version of the merged JSON. Must match ``vendors/_common.py``.
MERGED_SCHEMA_VERSION = 1


# `hlcl/` is on `sys.path` because every _build.py stub adds it before
# importing `build`; direct invocations of this script also need it so
# the `_config` module resolves.
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import _config  # noqa: E402


def load_priority() -> list[str]:
    """Return the ordered vendor priority list from the active
    BuildConfig. Replaces the previous ``settings.toml`` lookup; the
    canonical setting is now ``settings.house_footprints.priority``
    in the JSON contract."""
    return list(_config.current().settings.house_footprints.priority)


def discover_vendor_files(input_dir: str) -> list[Tuple[str, str]]:
    """Return [(vendor_key, full_path), ...] sorted alphabetically by
    vendor_key. The merge step re-orders these by priority before
    iterating; alphabetical here just produces deterministic output for
    vendors not mentioned in the priority list."""
    if not os.path.isdir(input_dir):
        return []
    out: list[Tuple[str, str]] = []
    for fn in sorted(os.listdir(input_dir)):
        if fn == HOUSE_BASENAME:
            continue
        if not fn.endswith(VENDOR_SUFFIX):
            continue
        vk = fn[: -len(VENDOR_SUFFIX)]
        out.append((vk, os.path.join(input_dir, fn)))
    return out


def read_vendor_json(path: str) -> dict:
    """Load a vendor footprints JSON, validating only what we
    immediately rely on. Anything else (per-row schema correctness)
    is the producer's job (vendors/_common.py validates on emit)."""
    with open(path, "r", encoding="ascii") as f:
        doc = json.load(f)
    schema = doc.get("schemaVersion")
    if schema != MERGED_SCHEMA_VERSION:
        raise ValueError(
            f"{path}: schemaVersion {schema!r} is not supported "
            f"(expected {MERGED_SCHEMA_VERSION}). Update both this "
            "merger and the per-vendor scripts together when bumping."
        )
    fps = doc.get("footprints")
    if not isinstance(fps, list):
        raise ValueError(f"{path}: 'footprints' must be a list")
    return doc


def order_vendors(
    vendors: Iterable[Tuple[str, str]],
    priority: list[str],
) -> Tuple[list[Tuple[str, str]], list[Tuple[str, str]]]:
    """Sort (vendor_key, path) tuples so listed-priority vendors come
    first (in their listed order), then any unlisted vendors in
    alphabetical order at the bottom."""
    rank = {vk: i for i, vk in enumerate(priority)}
    listed = [v for v in vendors if v[0] in rank]
    unlisted = [v for v in vendors if v[0] not in rank]
    listed.sort(key=lambda v: rank[v[0]])
    unlisted.sort(key=lambda v: v[0])
    return listed, unlisted


def main() -> int:
    priority = load_priority()
    vendors = discover_vendor_files(FOOTPRINTS_DIR)

    if not vendors:
        print(
            f"error: no per-vendor *{VENDOR_SUFFIX} files found in "
            f"{FOOTPRINTS_DIR}. Run the per-vendor generator scripts "
            "first.",
            file=sys.stderr,
        )
        return 1

    listed, unlisted = order_vendors(vendors, priority)
    ordered = listed + unlisted

    # Read every vendor file up front. Any per-vendor schema issue
    # (mismatched schemaVersion, missing 'footprints' list) raises and
    # the build fails loudly.
    per_vendor_data: list[Tuple[str, list[dict]]] = []
    for vk, path in ordered:
        doc = read_vendor_json(path)
        # Sanity: the vendor field in the file should match its
        # filename-derived key. Mismatch is suspicious but not fatal --
        # warn and prefer the filename (which is the canonical key in
        # settings.house_footprints.priority).
        embedded_vendor = doc.get("vendor")
        if embedded_vendor and embedded_vendor != vk:
            print(
                f"warning: {path} declares vendor={embedded_vendor!r} but "
                f"its filename implies vendor={vk!r}; using {vk!r}",
                file=sys.stderr,
            )
        per_vendor_data.append((vk, doc["footprints"]))

    # Apply priority: first vendor (in `ordered`) to define a given
    # FootprintName wins; everyone else's same-named row is dropped.
    chosen: dict[str, Tuple[str, dict]] = {}            # name -> (vendor_key, fp)
    losers: Counter[str] = Counter()                    # vendor_key -> # rows it lost on
    conflicts: dict[str, list[str]] = {}                # name -> [vendor_key, ...] in priority order
    contribution: Counter[str] = Counter()              # vendor_key -> # rows kept
    seen_in_vendor: set[Tuple[str, str]] = set()        # (vendor_key, name) -- catch in-file duplicates

    for vk, footprints in per_vendor_data:
        for fp in footprints:
            name = fp.get("name")
            if not isinstance(name, str) or not name:
                print(
                    f"warning: skipping nameless footprint in vendor "
                    f"{vk!r}: {fp!r}",
                    file=sys.stderr,
                )
                continue
            if (vk, name) in seen_in_vendor:
                # The per-vendor files are already de-duped, so this
                # would only happen if a vendor script regressed.
                continue
            seen_in_vendor.add((vk, name))
            conflicts.setdefault(name, []).append(vk)
            if name in chosen:
                losers[vk] += 1
                continue
            chosen[name] = (vk, fp)
            contribution[vk] += 1

    # Build the merged document. Inject `vendor` per row so downstream
    # tools can attribute geometry to its source.
    out_rows = []
    for vk, fp in sorted(chosen.values(), key=lambda vf: vf[1]["name"]):
        merged_fp = dict(fp)
        merged_fp["vendor"] = vk  # winner of the priority resolution
        # Drop the redundant top-level vendor field if it's leaked
        # through (it isn't a per-row field in the per-vendor schema,
        # but we defensively scrub).
        out_rows.append(merged_fp)

    out_doc = {
        "schemaVersion": MERGED_SCHEMA_VERSION,
        "vendorPriority": list(priority),
        "footprints": out_rows,
    }

    os.makedirs(FOOTPRINTS_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="ascii") as f:
        json.dump(out_doc, f, indent=2)
        f.write("\n")

    # --- Diagnostics ------------------------------------------------
    print(
        f"Wrote {OUTPUT_PATH}: {len(out_rows)} rows from "
        f"{len(per_vendor_data)} vendor file(s).",
        file=sys.stderr,
    )

    print(file=sys.stderr)
    print("Vendor priority order applied (listed first, then unlisted):", file=sys.stderr)
    for vk, _path in listed:
        print(
            f"  L  {vk}  -- kept {contribution[vk]:>4} rows, lost {losers[vk]:>4}",
            file=sys.stderr,
        )
    for vk, _path in unlisted:
        print(
            f"  U  {vk}  -- kept {contribution[vk]:>4} rows, lost {losers[vk]:>4}  "
            f"[NOT in BuildConfig priority list]",
            file=sys.stderr,
        )

    actual_conflicts = {
        name: vks for name, vks in conflicts.items() if len(vks) >= 2
    }
    if actual_conflicts:
        print(file=sys.stderr)
        print(
            f"Resolved {len(actual_conflicts)} FootprintName conflict(s) "
            "(winner = first vendor listed):",
            file=sys.stderr,
        )
        for name in sorted(actual_conflicts):
            vks = actual_conflicts[name]
            winner = vks[0]
            losers_for_row = vks[1:]
            print(
                f"  {name}: {winner}  (over: {', '.join(losers_for_row)})",
                file=sys.stderr,
            )

    if unlisted:
        print(file=sys.stderr)
        print(
            "NOTE: the following vendor file(s) are NOT mentioned in "
            "`settings.house_footprints.priority`. They were merged at "
            "lowest priority. Add them to the priority list if you want "
            "their tie-break behaviour to be deterministic:",
            file=sys.stderr,
        )
        for vk, _path in unlisted:
            print(f"  - {vk}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
