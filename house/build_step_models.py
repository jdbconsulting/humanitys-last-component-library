#!/usr/bin/env python
"""
Generate parametric STEP 3D models for every unique chip body listed
in ``build/footprints/house-footprints.json``.

The body geometry of a chip footprint is identical across the three
IPC-7351B density variants (``L`` / ``N`` / ``M`` — those only change
the pad geometry, not the component itself). So we deduplicate by
*footprint root* — the FootprintName with its trailing density letter
stripped — and emit one STEP file per root:

    build/step/CAPC0402X20.step    <-- shared by CAPC0402X20{L,N,M}
    build/step/RESC0402X13.step    <-- shared by RESC0402X13{L,N,M}
    ...

The HouseLibGenerator C# project (run by ``make house-pcblib``) loads
each footprint's STEP file by stripping the same density suffix, so
all three density variants in the .PcbLib end up referencing — and
embedding — the same STEP body.

If two footprints share a root but disagree on body dimensions (which
would be a regression in either the per-vendor JSONs or the merge
step) the build aborts loudly rather than silently using whichever
came first.

Two consumers read these files:

1. The HouseLibGenerator C# project, which zlib-compresses each STEP
   and embeds it into the matching ``PcbComponentBody.StepModel`` of
   every L/N/M variant of that root. After ``make all``, no external
   STEP files are required for the .PcbLib to render in Altium.

2. Humans, for inspection. Open them in any STEP viewer to check the
   geometry independently of Altium.

The geometry generator lives in ``house/stepgen/`` and is intentionally
pure-stdlib Python (so the generator can eventually be ported to a
browser via Pyodide for an open-source web UI). See
``house/stepgen/__init__.py`` for the design constraints.

Schema-version contract: this script reads
``build/footprints/house-footprints.json`` schemaVersion 1 (written by
``house/build_house_footprints.py``). Schema bumps must be reflected
here too.
"""

from __future__ import annotations

import json
import os
import sys

# Allow ``import stepgen`` when run as a top-level script. Doing this
# instead of making the whole ``house/`` directory a package keeps the
# existing flat-script convention (``build_house_footprints.py``,
# vendor scripts) intact.
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import stepgen  # noqa: E402

REPO_ROOT = os.path.normpath(os.path.join(HERE, ".."))
INPUT_PATH = os.path.join(REPO_ROOT, "build", "footprints", "house-footprints.json")
OUTPUT_DIR = os.path.join(REPO_ROOT, "build", "step")

KIND_TO_GEN = {
    "C":  stepgen.capc,   # chip ceramic capacitor
    "R":  stepgen.resc,   # chip resistor
    "I":  stepgen.indc,   # chip inductor
    "FB": stepgen.indc,   # ferrite bead -- same body shape, blue colour
}


def main() -> int:
    if not os.path.exists(INPUT_PATH):
        print(
            f"error: {INPUT_PATH} not found; run `make house-footprints` first",
            file=sys.stderr,
        )
        return 1

    with open(INPUT_PATH, "r", encoding="ascii") as f:
        doc = json.load(f)

    schema = doc.get("schemaVersion")
    if schema != 1:
        print(
            f"error: house-footprints.json schemaVersion {schema!r} is not "
            "supported by this generator; expected 1. Update build_step_models.py "
            "and house/stepgen/ at the same time as the schema bump.",
            file=sys.stderr,
        )
        return 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Sweep stale .step files so this directory is exactly the set of
    # roots we're about to write. Catches both per-density legacy files
    # (e.g. CAPC0402X20L.step from before the dedup) and orphans left
    # behind when a footprint is removed from a vendor JSON. The .stamp
    # file the Makefile maintains is intentionally left alone.
    for fn in os.listdir(OUTPUT_DIR):
        if fn.endswith(".step"):
            try:
                os.remove(os.path.join(OUTPUT_DIR, fn))
            except OSError:
                pass

    # Group footprints by root (FootprintName minus trailing density
    # letter). The vendor-side schema validator in vendors/_common.py
    # already enforces that every name ends with L / N / M, so the
    # strip is unambiguous. Same root => same body geometry.
    groups: dict[str, dict] = {}
    skipped_kind: list[str] = []
    geometry_conflicts: list[str] = []
    for fp in doc.get("footprints", []):
        name = fp["name"]
        kind = fp["kind"]
        body = fp["bodyMm"]
        if kind not in KIND_TO_GEN:
            skipped_kind.append(f"{name} (kind={kind!r})")
            continue
        root = name[:-1]
        body_key = (
            kind,
            body["lengthNominal"],
            body["widthNominal"],
            body["heightNominal"],
            body["terminalLengthNominal"],
        )
        if root in groups:
            if groups[root]["body_key"] != body_key:
                # Two L/N/M variants of the same root somehow have
                # different bodies. That would mean either a vendor
                # script is mis-emitting rows or the merge picked
                # winners with mismatched geometry. Fail the build.
                geometry_conflicts.append(
                    f"{root}: {groups[root]['names']} -> {groups[root]['body_key']}; "
                    f"{name} -> {body_key}"
                )
            groups[root]["names"].append(name)
        else:
            groups[root] = {"body_key": body_key, "names": [name]}

    if geometry_conflicts:
        print(
            "error: footprints sharing a root disagree on body geometry "
            "(L/N/M variants of the same chip must have identical bodies):",
            file=sys.stderr,
        )
        for c in geometry_conflicts:
            print(f"  - {c}", file=sys.stderr)
        return 2

    counts = {"C": 0, "R": 0, "I": 0, "FB": 0}
    footprint_users = 0
    for root in sorted(groups):
        info = groups[root]
        kind, L, W, H, T = info["body_key"]
        try:
            step_text = KIND_TO_GEN[kind](L, W, H, T, footprint_name=root)
        except ValueError as exc:
            # bad/degenerate dimensions; raise loudly so the build fails
            # rather than silently producing a bad STEP.
            print(f"error: failed to generate {root}: {exc}", file=sys.stderr)
            return 2

        out_path = os.path.join(OUTPUT_DIR, f"{root}.step")
        with open(out_path, "w", encoding="ascii", newline="\n") as f:
            f.write(step_text)
        counts[kind] += 1
        footprint_users += len(info["names"])

    total = sum(counts.values())
    print(
        f"Wrote {total} STEP file(s) to {OUTPUT_DIR}/  "
        f"(shared by {footprint_users} L/N/M footprint variants)",
        file=sys.stderr,
    )
    print(
        f"  CAPC: {counts['C']}    RESC: {counts['R']}    INDC: {counts['I'] + counts['FB']}",
        file=sys.stderr,
    )

    if skipped_kind:
        print(file=sys.stderr)
        print(
            f"NOTE: {len(skipped_kind)} footprint(s) skipped because the chip "
            "kind has no STEP generator yet (add it to "
            "house/stepgen/chip.py and KIND_TO_GEN below):",
            file=sys.stderr,
        )
        for s in skipped_kind:
            print(f"  - {s}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
