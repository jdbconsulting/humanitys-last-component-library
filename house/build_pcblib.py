#!/usr/bin/env python
"""
Pure-Python replacement for ``house/HouseLibGenerator/`` (the C#
project that previously produced ``build/house.PcbLib``).

Reads the merged footprints JSON, applies IPC-7351B + DDL-001 math,
and emits an Altium PCB footprint library with embedded zlib-
compressed STEP 3D models -- functionally equivalent to what the C#
generator produced, but with no .NET dependency.

Usage:
    python house/build_pcblib.py --input  build/footprints/house-footprints.json
                                 --output build/house.PcbLib
                                 --step-dir build/step
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
from altium_pcblib.footprint import FootprintInput, build_chip_footprint  # noqa: E402


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)

    with open(args.input, "r", encoding="ascii") as f:
        doc = json.load(f)

    rows = doc.get("footprints", [])
    if not rows:
        print(f"error: {args.input} has no footprints", file=sys.stderr)
        return 1

    components = []
    models = []
    diagnostics_lines: List[str] = []
    embedded = 0
    missing  = 0
    step_cache: dict[str, str | None] = {}     # root -> step text or None
    step_roots_used: set[str] = set()

    # Per-family counters for the build summary (mirrors the C# tool).
    by_kind = {"C": 0, "R": 0, "I": 0, "FB": 0}

    for row in rows:
        fp_input = FootprintInput.from_json(row)
        component, diag = build_chip_footprint(fp_input)
        if diag:
            diagnostics_lines.append(diag)

        # STEP files are keyed by footprint *root* (name minus the
        # trailing L/N/M density letter), matching what
        # build_step_models.py emits: 3 density variants share a
        # single .step body. Cache to read each file at most once.
        root = fp_input.name[:-1]
        if root not in step_cache:
            step_path = os.path.join(args.step_dir, f"{root}.step")
            if os.path.exists(step_path):
                with open(step_path, "r", encoding="utf-8") as sf:
                    step_cache[root] = sf.read()
            else:
                step_cache[root] = None
        step_text = step_cache[root]
        if step_text is not None:
            embedded += 1
            step_roots_used.add(root)
        else:
            step_text = ""
            missing += 1

        # The model id must match the body's MODELID -- the body
        # builder derived it deterministically from the footprint
        # name; do the same here for the model entry.
        body_model_id = component.component_bodies[0].model_id
        models.append(
            PcbModel(
                id=body_model_id,
                name="ChipBody.STEP",
                is_embedded=True,
                rotation_x=0.0,
                rotation_y=0.0,
                rotation_z=0.0,
                dz=1,                  # v1.0.2 0-coord workaround sentinel
                checksum=0,
                model_source="",
                step_data=step_text,
            )
        )
        components.append(component)
        by_kind[fp_input.kind] = by_kind.get(fp_input.kind, 0) + 1

    library = PcbLibrary(components=components, models=models)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    write_pcblib(library, args.output)

    # ---- Diagnostic report ----------------------------------------
    print(f"Wrote {args.output}: {len(components)} footprints, "
          f"{os.path.getsize(args.output)} bytes.", file=sys.stderr)
    print(f"  By kind: " + "  ".join(
        f"{k}: {by_kind[k]}" for k in ("C", "R", "I", "FB") if by_kind.get(k)
    ), file=sys.stderr)
    print(
        f"  3D models: {embedded} embedded ({len(step_roots_used)} unique "
        f".step files from {args.step_dir}/, shared across L/N/M density "
        f"variants), {missing} missing",
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
