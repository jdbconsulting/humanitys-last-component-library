"""
Pure-Python writer for the Microsoft Compound File Binary v3 format
(MS-CFB), the container that Altium ``.PcbLib`` files use.

Replaces the ``OpenMcdf``-via-AltiumSharp dependency. Implements only
what we need to emit:

  * 512-byte regular sectors (sector shift 9), 64-byte mini sectors
    (mini sector shift 6), 4096-byte mini-stream cutoff -- exactly
    what AltiumSharp+OpenMcdf produce.
  * Regular FAT only (no transactional features, no DIFAT extension).
  * Mini-FAT for streams shorter than the cutoff.
  * Directory tree as a balanced BST per storage (sort order: name
    length, then UTF-16 uppercase code units; all entries marked
    black -- the simplest red-black tree that satisfies the spec's
    invariants).

Public API:

    cf = CompoundFile()
    cf.add_stream("FileHeader", header_bytes)
    cf.add_stream("Library/Header", b"\\x01\\x00\\x00\\x00")
    cf.add_storage("Library/Models")
    ...
    cf.write("out.PcbLib")

Stream paths use ``/`` separators. Storages along the path are
created implicitly when an intermediate component does not yet exist
(``add_stream("a/b/c", ...)`` will auto-create storages ``a`` and
``a/b``). Calling ``add_storage`` on an already-existing path is a
no-op. Empty storages are permitted (Altium's footprint storages
include an empty ``UniqueIdPrimitiveInformation`` substorage).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# --- Constants ----------------------------------------------------------

# CFB v3 layout. We don't expose these as parameters because we don't
# need other variants. The mini-stream cutoff matches what Altium emits.
SECTOR_SIZE = 512
MINI_SECTOR_SIZE = 64
MINI_STREAM_CUTOFF = 4096
HEADER_SIZE = 512
DIR_ENTRY_SIZE = 128
DIR_ENTRIES_PER_SECTOR = SECTOR_SIZE // DIR_ENTRY_SIZE  # 4
FAT_ENTRIES_PER_SECTOR = SECTOR_SIZE // 4               # 128
DIFAT_HEADER_SLOTS = 109                                # entries in the file header

# Special FAT entry values (per MS-CFB §2.1).
FAT_FREESECT   = 0xFFFFFFFF  # marks unused FAT slot
FAT_ENDOFCHAIN = 0xFFFFFFFE  # last sector of a chain
FAT_FATSECT    = 0xFFFFFFFD  # this slot is itself a FAT sector
FAT_DIFSECT    = 0xFFFFFFFC  # this slot is a DIFAT sector
FAT_MAXREGSECT = 0xFFFFFFFA  # highest legal regular sector index

# Directory-entry object types (per MS-CFB §2.6.1).
OBJ_UNKNOWN = 0
OBJ_STORAGE = 1
OBJ_STREAM  = 2
OBJ_ROOT    = 5

# Directory-entry node colors. We mark every entry black, which the
# spec explicitly endorses ("It is recommended that all entries other
# than the root entry be marked as black to satisfy the red-black
# rules without rebalancing").
NODE_BLACK = 1

# Sentinel for "no sibling/child link".
NOSTREAM = 0xFFFFFFFF

# Magic bytes identifying a CFB file ("Compound Document File" v3).
CFB_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


# --- Directory tree -----------------------------------------------------


@dataclass
class _DirEntry:
    """Mutable scaffolding for a directory entry. Resolved into a
    serialised 128-byte record by ``_pack`` once all sibling/child
    links are known."""

    name: str
    obj_type: int                            # OBJ_STORAGE / OBJ_STREAM / OBJ_ROOT
    children: List["_DirEntry"] = field(default_factory=list)
    data: bytes = b""                        # only meaningful for streams

    # Filled in during finalise:
    dir_index: int = -1                      # this entry's index in the dir array
    left: int = NOSTREAM
    right: int = NOSTREAM
    child_root: int = NOSTREAM
    start_sector: int = FAT_FREESECT          # for streams (or the mini-stream on root)
    stream_size: int = 0                      # bytes (for streams; root holds mini-stream size)

    def add_child(self, child: "_DirEntry") -> None:
        if any(c.name.lower() == child.name.lower() for c in self.children):
            raise ValueError(f"duplicate child {child.name!r} in {self.name!r}")
        self.children.append(child)


def _cfb_name_sort_key(name: str) -> Tuple[int, Tuple[int, ...]]:
    """Sort order for directory siblings, per MS-CFB §2.6.4: shorter
    names come first; otherwise UTF-16 codepoint compare on the
    uppercased form. Python's ``str.upper()`` gives us locale-
    independent uppercase that matches what OpenMcdf does for ASCII
    names (which is all we have)."""
    upper = name.upper()
    return (len(name), tuple(ord(c) for c in upper))


def _build_balanced_bst(entries: List[_DirEntry]) -> Optional[_DirEntry]:
    """Convert a sorted list of entries into a balanced BST. Root is
    the middle element; recurse on left/right halves. Modifies each
    entry's ``left`` / ``right`` link in place and returns the root.
    O(n) time, O(log n) recursion depth.
    """
    if not entries:
        return None

    def _recurse(lo: int, hi: int) -> Optional[_DirEntry]:
        if lo > hi:
            return None
        mid = (lo + hi) // 2
        node = entries[mid]
        l = _recurse(lo, mid - 1)
        r = _recurse(mid + 1, hi)
        node.left = l.dir_index if l else NOSTREAM
        node.right = r.dir_index if r else NOSTREAM
        return node

    return _recurse(0, len(entries) - 1)


# --- Top-level compound-file writer ------------------------------------


class CompoundFile:
    """Build up a CFB image by adding storages and streams, then
    serialise it with ``write()`` or ``to_bytes()``.

    Stream / storage paths use forward slashes. The implicit root
    storage is unnamed; ``add_stream("Library/Data", ...)`` adds a
    stream named ``Data`` inside an auto-created storage ``Library``
    inside root.
    """

    def __init__(self) -> None:
        # Root entry's "name" is mandated to be "Root Entry" per MS-CFB §2.6.4.
        self._root = _DirEntry(name="Root Entry", obj_type=OBJ_ROOT)

    # ----- Tree manipulation --------------------------------------

    def add_storage(self, path: str) -> None:
        """Add an empty storage at ``path``. Intermediate path
        components are created if missing. Calling on a path that is
        already a storage is a no-op; calling on a path that is
        already a stream raises ``ValueError``."""
        self._resolve_path(path, create_kind=OBJ_STORAGE)

    def add_stream(self, path: str, data: bytes) -> None:
        """Add a stream at ``path`` with the given byte content.
        Intermediate storages along the path are created if missing.
        Calling on a path that already exists raises ``ValueError``.
        ``data`` may be empty."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError(f"stream data for {path!r} must be bytes, got {type(data).__name__}")
        # Walk the path, creating storages for all-but-last component.
        parts = [p for p in path.split("/") if p]
        if not parts:
            raise ValueError("stream path cannot be empty")
        parent = self._root
        for comp in parts[:-1]:
            existing = next((c for c in parent.children if c.name.lower() == comp.lower()), None)
            if existing is None:
                node = _DirEntry(name=comp, obj_type=OBJ_STORAGE)
                parent.add_child(node)
                parent = node
            else:
                if existing.obj_type != OBJ_STORAGE:
                    raise ValueError(f"path component {comp!r} (in {path!r}) is not a storage")
                parent = existing
        leaf_name = parts[-1]
        if any(c.name.lower() == leaf_name.lower() for c in parent.children):
            raise ValueError(f"stream {path!r} already exists")
        leaf = _DirEntry(name=leaf_name, obj_type=OBJ_STREAM, data=bytes(data))
        leaf.stream_size = len(data)
        parent.add_child(leaf)

    def _resolve_path(self, path: str, create_kind: int) -> _DirEntry:
        parts = [p for p in path.split("/") if p]
        if not parts:
            return self._root
        parent = self._root
        node = None
        for i, comp in enumerate(parts):
            existing = next((c for c in parent.children if c.name.lower() == comp.lower()), None)
            if existing is None:
                if i < len(parts) - 1 and create_kind != OBJ_STORAGE:
                    # Intermediate components must be storages.
                    new = _DirEntry(name=comp, obj_type=OBJ_STORAGE)
                else:
                    new = _DirEntry(name=comp, obj_type=create_kind)
                parent.add_child(new)
                parent = new
                node = new
            else:
                if i == len(parts) - 1 and existing.obj_type != create_kind:
                    raise ValueError(
                        f"{path!r} already exists as object type {existing.obj_type}, "
                        f"cannot recreate as {create_kind}"
                    )
                parent = existing
                node = existing
        return node

    # ----- Serialisation -----------------------------------------

    def write(self, output_path: str) -> None:
        """Serialise the compound file to ``output_path``."""
        with open(output_path, "wb") as f:
            f.write(self.to_bytes())

    def to_bytes(self) -> bytes:
        """Serialise the compound file to a single bytes object.

        Layout strategy:

          1. Walk the tree depth-first to assign directory indices.
          2. Partition streams by mini-vs-regular (by size). Mini
             streams are concatenated into the root storage's
             "mini-stream"; regular streams each get their own chain
             of 512-byte sectors.
          3. Allocate sectors in this order: regular stream data,
             mini-stream data, mini-FAT, directory. Then compute how
             many FAT sectors are needed (each holds 128 entries) and
             reserve those at the end. Finally fill in the FAT
             (everything we allocated above is a known chain).
          4. Build the file header (DIFAT goes inline since we have
             well under 109 FAT sectors).
          5. Concatenate header + sector payloads (with 0-padding).
        """
        # 1. Assign directory indices (root is 0, then BFS).
        all_entries: List[_DirEntry] = []
        self._assign_dir_indices(self._root, all_entries)

        # 2. Partition streams.
        regular_streams: List[_DirEntry] = []
        mini_streams: List[_DirEntry] = []
        for e in all_entries:
            if e.obj_type == OBJ_STREAM:
                if e.stream_size >= MINI_STREAM_CUTOFF:
                    regular_streams.append(e)
                else:
                    if e.stream_size > 0:  # zero-byte streams take no sectors
                        mini_streams.append(e)

        # 3. Sector allocation. We use a single growing list of sector
        #    contents, and a parallel FAT array. Both grow together.
        sectors: List[bytes] = []
        fat: List[int] = []

        def alloc_chain(payload: bytes, chunk_size: int) -> int:
            """Append ``payload`` to ``sectors`` (chunked into
            ``chunk_size`` blocks, zero-padded). Returns the start
            sector index. Updates ``fat`` so the chain is properly
            linked, ending with FAT_ENDOFCHAIN."""
            if not payload:
                return FAT_ENDOFCHAIN
            assert chunk_size == SECTOR_SIZE  # mini-stream isn't allocated here
            n_chunks = (len(payload) + chunk_size - 1) // chunk_size
            start = len(sectors)
            for i in range(n_chunks):
                blob = payload[i * chunk_size : (i + 1) * chunk_size]
                if len(blob) < chunk_size:
                    blob = blob + b"\x00" * (chunk_size - len(blob))
                sectors.append(blob)
                # Provisional FAT entry: every sector in this chain
                # points at the next, except the last which gets
                # ENDOFCHAIN. We append placeholders; we'll overwrite
                # before the file is written out.
                if i < n_chunks - 1:
                    fat.append(start + i + 1)
                else:
                    fat.append(FAT_ENDOFCHAIN)
            return start

        # 3a. Regular streams.
        for e in regular_streams:
            e.start_sector = alloc_chain(e.data, SECTOR_SIZE)

        # 3b. Mini-stream content (concatenated, padded to mini-sector
        #     multiples). The mini-stream itself is a regular stream
        #     stored in the root entry's start_sector.
        mini_fat: List[int] = []
        mini_blob_parts: List[bytes] = []
        mini_cursor = 0  # in mini-sectors
        for e in mini_streams:
            n_mini = (e.stream_size + MINI_SECTOR_SIZE - 1) // MINI_SECTOR_SIZE
            e.start_sector = mini_cursor
            blob = e.data
            if len(blob) % MINI_SECTOR_SIZE:
                blob = blob + b"\x00" * (MINI_SECTOR_SIZE - len(blob) % MINI_SECTOR_SIZE)
            mini_blob_parts.append(blob)
            for i in range(n_mini):
                if i < n_mini - 1:
                    mini_fat.append(mini_cursor + i + 1)
                else:
                    mini_fat.append(FAT_ENDOFCHAIN)
            mini_cursor += n_mini

        mini_blob = b"".join(mini_blob_parts)
        mini_total_size = len(mini_blob)
        # Allocate the mini-stream as a regular sector chain. Its
        # start sector will live in the root's start_sector field.
        if mini_blob:
            mini_stream_start = alloc_chain(mini_blob, SECTOR_SIZE)
        else:
            mini_stream_start = FAT_ENDOFCHAIN

        # 3c. Mini-FAT. Each entry is u32; pad up to a sector multiple.
        if mini_fat:
            mini_fat_bytes = b"".join(struct.pack("<I", e) for e in mini_fat)
            # Pad the mini-FAT to a sector multiple with FREESECT entries.
            tail = SECTOR_SIZE - (len(mini_fat_bytes) % SECTOR_SIZE)
            if tail != SECTOR_SIZE:
                mini_fat_bytes += struct.pack("<I", FAT_FREESECT) * (tail // 4)
            mini_fat_start = alloc_chain(mini_fat_bytes, SECTOR_SIZE)
            n_mini_fat_sectors = len(mini_fat_bytes) // SECTOR_SIZE
        else:
            mini_fat_start = FAT_ENDOFCHAIN
            n_mini_fat_sectors = 0

        # Set root's start_sector to the mini-stream and stream_size
        # to the mini-stream byte length (per MS-CFB §2.6.4).
        self._root.start_sector = mini_stream_start
        self._root.stream_size = mini_total_size

        # 3d. Build directory entries; compute their sector indices.
        # First we need to know the BST structure (left/right/child
        # links), which depends on each entry's dir_index and its
        # siblings' dir_indices -- all of which are now assigned.
        for e in all_entries:
            if e.obj_type in (OBJ_STORAGE, OBJ_ROOT) and e.children:
                # Sort children by CFB rules and build a balanced BST.
                sorted_children = sorted(e.children, key=lambda c: _cfb_name_sort_key(c.name))
                root = _build_balanced_bst(sorted_children)
                e.child_root = root.dir_index if root else NOSTREAM
            else:
                e.child_root = NOSTREAM

        # Pad directory list out to a 4-entry multiple (one sector).
        n_pad_dir_entries = (-len(all_entries)) % DIR_ENTRIES_PER_SECTOR
        dir_blob = b"".join(self._pack_dir_entry(e) for e in all_entries)
        dir_blob += b"\x00" * (n_pad_dir_entries * DIR_ENTRY_SIZE)
        # Pad-entry slots get a special "unknown" representation:
        # all-zero name, type OBJ_UNKNOWN. Easiest to overwrite the
        # right number of entries with a known good template.
        if n_pad_dir_entries:
            empty = self._pack_empty_dir_entry()
            dir_blob = dir_blob[: -n_pad_dir_entries * DIR_ENTRY_SIZE] + empty * n_pad_dir_entries
        dir_start = alloc_chain(dir_blob, SECTOR_SIZE)

        # 3e. Reserve FAT sectors. Each FAT sector indexes 128 sectors
        #     of file content. Iteratively: every FAT sector we add
        #     also takes a slot in the FAT itself (marked FATSECT), so
        #     we may need to add another FAT sector. Repeat to fix
        #     point.
        n_fat = 0
        while True:
            total_after = len(fat) + n_fat  # current data + reserved-FAT slots
            need = (total_after + FAT_ENTRIES_PER_SECTOR - 1) // FAT_ENTRIES_PER_SECTOR
            if need <= n_fat:
                break
            n_fat = need

        # Allocate FAT sectors at the end of the file. Each one needs
        # a FAT entry pointing at itself with FAT_FATSECT.
        fat_sector_indices: List[int] = []
        for _ in range(n_fat):
            idx = len(fat)
            fat_sector_indices.append(idx)
            fat.append(FAT_FATSECT)
            sectors.append(b"")  # placeholder; real bytes filled in below

        # Now serialise the FAT into its reserved sectors. Pad final
        # FAT sector with FREESECT.
        fat_padding = (-len(fat)) % FAT_ENTRIES_PER_SECTOR
        for _ in range(fat_padding):
            fat.append(FAT_FREESECT)
        fat_blob = b"".join(struct.pack("<I", e) for e in fat)
        for i, sec_idx in enumerate(fat_sector_indices):
            sectors[sec_idx] = fat_blob[i * SECTOR_SIZE : (i + 1) * SECTOR_SIZE]

        # 4. File header.
        n_dir_sectors = len(dir_blob) // SECTOR_SIZE  # informational only in v3 (always 0 in header)
        header = self._pack_header(
            n_fat_sectors=n_fat,
            first_dir_sector=dir_start,
            first_mini_fat_sector=mini_fat_start,
            n_mini_fat_sectors=n_mini_fat_sectors,
            difat=fat_sector_indices,
        )

        # 5. Assemble. Sanity: every sector is exactly SECTOR_SIZE.
        for i, s in enumerate(sectors):
            if len(s) != SECTOR_SIZE:
                raise AssertionError(
                    f"sector {i} length {len(s)} != {SECTOR_SIZE}"
                )
        body = b"".join(sectors)
        return header + body

    # ----- Internal helpers --------------------------------------

    def _assign_dir_indices(self, node: _DirEntry, out: List[_DirEntry]) -> None:
        """Walk the tree depth-first (root, then each child's subtree)
        and assign sequential directory indices. Order doesn't matter
        for correctness but matters slightly for diff stability across
        runs."""
        node.dir_index = len(out)
        out.append(node)
        # Recurse on children sorted by CFB sort key so the directory
        # serialization is stable. Storage child order is determined
        # by the BST built later, not by physical position in the
        # directory array, so this is purely cosmetic.
        for child in sorted(node.children, key=lambda c: _cfb_name_sort_key(c.name)):
            self._assign_dir_indices(child, out)

    def _pack_dir_entry(self, e: _DirEntry) -> bytes:
        """Serialise a single 128-byte directory entry per MS-CFB §2.6.1."""
        name_utf16 = e.name.encode("utf-16-le")
        # Name length includes the trailing UTF-16 null (2 bytes), per spec.
        name_len = len(name_utf16) + 2
        if name_len > 64:
            raise ValueError(f"directory entry name too long: {e.name!r}")
        # Fixed 64-byte name field, zero-padded.
        name_field = name_utf16 + b"\x00\x00" + b"\x00" * (64 - name_len)
        # Stream size is u64 (low u32 then high u32).
        size = e.stream_size
        return struct.pack(
            "<64sHBB"        # 64-byte name + name length + obj type + color
            "III"            # left, right, child
            "16s"            # CLSID (zeros)
            "I"              # state flags (0)
            "QQ"             # creation time, modification time (both zero)
            "IQ",            # start sector + stream size (low u32 + high u32 = u64)
            name_field,
            name_len,
            e.obj_type,
            NODE_BLACK,
            e.left,
            e.right,
            e.child_root,
            b"\x00" * 16,
            0,
            0,
            0,
            e.start_sector if e.start_sector is not None else FAT_FREESECT,
            size,
        )

    def _pack_empty_dir_entry(self) -> bytes:
        """A 'no entry' directory slot: all zero except obj_type and
        the link fields, which are NOSTREAM."""
        return struct.pack(
            "<64sHBB"
            "III"
            "16s"
            "I"
            "QQ"
            "IQ",
            b"\x00" * 64,
            0,
            OBJ_UNKNOWN,
            NODE_BLACK,
            NOSTREAM,
            NOSTREAM,
            NOSTREAM,
            b"\x00" * 16,
            0,
            0,
            0,
            FAT_FREESECT,
            0,
        )

    def _pack_header(
        self,
        n_fat_sectors: int,
        first_dir_sector: int,
        first_mini_fat_sector: int,
        n_mini_fat_sectors: int,
        difat: List[int],
    ) -> bytes:
        """Build the 512-byte CFB header per MS-CFB §2.2."""
        if len(difat) > DIFAT_HEADER_SLOTS:
            # We never expect to hit this for a 2-3 MB PcbLib (109 FAT
            # sectors * 128 entries each = 13,952 sectors = 7 MB).
            raise NotImplementedError(
                f"{len(difat)} FAT sectors would require DIFAT extension "
                "(not implemented)"
            )

        # Pad DIFAT in the header to 109 entries with FREESECT.
        difat_padded = list(difat) + [FAT_FREESECT] * (DIFAT_HEADER_SLOTS - len(difat))
        difat_bytes = b"".join(struct.pack("<I", e) for e in difat_padded)

        return struct.pack(
            "<8s"            # signature
            "16s"            # CLSID (zeros, per AltiumSharp/OpenMcdf convention)
            "HH"             # minor version, major version
            "HHH"            # byte order, sector shift, mini-sector shift
            "6s"             # reserved (zeros)
            "I"              # number of directory sectors (0 for v3)
            "I"              # number of FAT sectors
            "I"              # first directory sector
            "I"              # transaction signature (0 unless writing transactions)
            "I"              # mini-stream cutoff (4096)
            "I"              # first mini-FAT sector
            "I"              # number of mini-FAT sectors
            "I"              # first DIFAT sector (ENDOFCHAIN since DIFAT fits in header)
            "I"              # number of DIFAT sectors
            "436s",          # 109 DIFAT entries (436 bytes)
            CFB_MAGIC,
            b"\x00" * 16,
            0x003E,          # minor version 62 (matches what Altium emits)
            0x0003,          # major version 3 (CFB v3)
            0xFFFE,          # byte order: little-endian
            9,               # sector shift: 1 << 9 = 512
            6,               # mini-sector shift: 1 << 6 = 64
            b"\x00" * 6,
            0,               # # directory sectors
            n_fat_sectors,
            first_dir_sector,
            0,               # transaction sig
            MINI_STREAM_CUTOFF,
            first_mini_fat_sector,
            n_mini_fat_sectors,
            FAT_ENDOFCHAIN,  # first DIFAT sector (none)
            0,               # # DIFAT sectors
            difat_bytes,
        )
