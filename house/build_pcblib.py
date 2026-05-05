#!/usr/bin/env python
"""
Pure-Python replacement for ``house/HouseLibGenerator/`` (the C#
project that previously produced ``build/house.PcbLib``).

Reads the merged footprints JSON, applies IPC-7351B + HLCL-001 math,
and emits an Altium PCB footprint library with embedded zlib-
compressed STEP 3D models -- functionally equivalent to what the C#
generator produced, but with no .NET dependency.

Usage:
    python house/build_pcblib.py \\
        --input    build/intermediate/footprints/house-footprints.json \\
        --output   build/output/house.PcbLib \\
        --step-dir build/intermediate/step
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Iterable, List

# Make ``altium_pcblib`` importable regardless of cwd.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from altium_pcblib import PcbLibrary, PcbModel, write_pcblib  # noqa: E402
from altium_pcblib.footprint import (  # noqa: E402
    FootprintInput,
    build_chip_footprint,
    _deterministic_guid as _deterministic_guid_for_root,
)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)

    with open(args.input, "r", encoding="ascii") as f:
        doc = json.load(f)

    rows = doc.get("footprints", [])
    if not rows:
        print(f"error: {args.input} has no footprints", file=sys.stderr)
        return 1

    components = []
    models: list[PcbModel] = []
    diagnostics_lines: List[str] = []
    missing = 0

    # One PcbModel entry per *unique footprint root* (sans the L/N/M
    # density letter). The 3 density variants of e.g. CAPC0402X20
    # share the same 3D body, so they reference the same MODELID and
    # the library carries only ONE embedded copy of CAPC0402X20.step
    # rather than three identical copies.
    #
    # Without this dedup, Altium's general model-resolution code
    # (used by the Components pane and PcbDoc placement -- everywhere
    # except the PcbLib editor's dedicated 3D View) collapses
    # entries that share a NAME and a CHECKSUM into one cached
    # model, and only the body whose MODELID happened to match the
    # winner of that dedup actually resolves. Every other body falls
    # through to an extruded polygon-outline placeholder.
    root_models: dict[str, PcbModel] = {}     # root -> PcbModel
    root_step_cache: dict[str, str | None] = {}

    # Per-family counters for the build summary (mirrors the C# tool).
    by_kind = {"C": 0, "R": 0, "I": 0, "FB": 0}

    for row in rows:
        fp_input = FootprintInput.from_json(row)
        component, diag = build_chip_footprint(fp_input)
        if diag:
            diagnostics_lines.append(diag)

        root = fp_input.name[:-1]

        # Read STEP for this root if we haven't yet.
        if root not in root_step_cache:
            step_path = os.path.join(args.step_dir, f"{root}.step")
            if os.path.exists(step_path):
                with open(step_path, "r", encoding="utf-8") as sf:
                    root_step_cache[root] = sf.read()
            else:
                root_step_cache[root] = None
        step_text = root_step_cache[root]
        if step_text is None:
            step_text = ""
            missing += 1

        # Create a single PcbModel per root (first time we see it),
        # and rewrite this body's MODELID to point at that shared
        # model. This makes 3 density variants of the same footprint
        # share one Library/Models entry instead of having three
        # near-identical ones.
        if root not in root_models:
            shared_model_id = _deterministic_guid_for_root(root)
            root_models[root] = PcbModel(
                id=shared_model_id,
                name=f"{root}.step",
                step_data=step_text,
            )
        shared_model = root_models[root]
        component.component_bodies[0].model_id = shared_model.id

        components.append(component)
        by_kind[fp_input.kind] = by_kind.get(fp_input.kind, 0) + 1

    models = list(root_models.values())
    embedded = sum(3 for m in models if m.step_data)  # 3 density variants per root

    library = PcbLibrary(components=components, models=models)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    write_pcblib(library, args.output)

    # ---- Diagnostic report ----------------------------------------
    print(f"Wrote {args.output}: {len(components)} footprints, "
          f"{os.path.getsize(args.output)} bytes.", file=sys.stderr)
    print(f"  By kind: " + "  ".join(
        f"{k}: {by_kind[k]}" for k in ("C", "R", "I", "FB") if by_kind.get(k)
    ), file=sys.stderr)
    n_unique_models = len(models)
    print(
        f"  3D models: {n_unique_models} unique embedded entries "
        f"in Library/Models (one per footprint root, shared across "
        f"L/N/M density variants of that root); {missing} missing "
        f".step files in {args.step_dir}/",
        file=sys.stderr,
    )
    if diagnostics_lines:
        print(f"Mask-bridge notices ({len(diagnostics_lines)}):", file=sys.stderr)
        for line in diagnostics_lines:
            print(line, file=sys.stderr)

    return 0


def _parse_args(argv: Iterable[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument(
        "--input", required=True,
        help="Merged footprints JSON (output of build_house_footprints.py).",
    )
    ap.add_argument(
        "--output", required=True,
        help="Destination .PcbLib path.",
    )
    ap.add_argument(
        "--step-dir", required=True,
        help="Directory of parametric .step files to embed (one per footprint, "
             "named <FootprintName>.step). Missing files produce an empty "
             "model stream and a warning on stderr.",
    )
    return ap.parse_args(list(argv) if argv is not None else None)


if __name__ == "__main__":
    sys.exit(main())
