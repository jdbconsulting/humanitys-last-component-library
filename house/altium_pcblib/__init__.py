"""
Pure-Python writer for Altium ``.PcbLib`` PCB footprint libraries.

Replaces the .NET 8 ``HouseLibGenerator/`` C# project (which delegated
to ``OriginalCircuit.AltiumSharp`` v1.0.2 + OpenMcdf) with a small
self-contained set of modules. The output is functionally equivalent
to AltiumSharp v1.0.2's writer (i.e. AltiumSharp's reader sees the
same record tree, and Altium opens the file the same way) but the
container layout is simpler and the build is byte-stable across runs
because all GUIDs are derived from content hashes.

Public entry points:

    from altium_pcblib import PcbLibrary, PcbComponent, ...
    lib = PcbLibrary(unique_id="HOUSEPCB", components=[...])
    lib.write("out.PcbLib")

The package is split into cleanly-separated layers so each piece can
be unit-tested or swapped out independently:

    cfb.py            -- MS-CFB v3 container writer (sectors, FAT,
                         mini-FAT, directory tree)
    encoding.py       -- Windows-1252 helpers + parameter list emitter
    binary.py         -- length-prefixed binary block framing
                         (mirrors AltiumSharp's BinaryFormatWriter)
    primitives.py     -- Coord, CoordPoint, Layer, OLE color
    records.py        -- @dataclasses for each PCB primitive type
                         we emit (Pad, Track, Region, ComponentBody)
    writer.py         -- top-level PcbLibrary writer that wires the
                         records into the CFB container
    ipc.py            -- IPC-7351B pad math (port of IpcRules +
                         PadCalculator from the C# project)
    ddl.py            -- DDL-001 drawing constants
    footprint.py      -- chip-footprint factory (port of
                         ChipFootprintBuilder from the C# project)
"""

from .primitives import Coord, CoordPoint, Layer, ole_color
from .records import (
    PcbPad,
    PcbTrack,
    PcbRegion,
    PcbComponentBody,
    PcbComponent,
    PcbModel,
    PcbLibrary,
)
from .writer import write_pcblib

__all__ = [
    "Coord",
    "CoordPoint",
    "Layer",
    "ole_color",
    "PcbPad",
    "PcbTrack",
    "PcbRegion",
    "PcbComponentBody",
    "PcbComponent",
    "PcbModel",
    "PcbLibrary",
    "write_pcblib",
]
