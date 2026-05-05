# TDK Library Notes

This folder is a per-family aggregator. Every active TDK generator
lives in its own subfolder.

| Family                    | Folder        | Build target                     | Notes                                                                                     |
| ------------------------- | ------------- | -------------------------------- | ----------------------------------------------------------------------------------------- |
| **CGA** (automotive MLCC) | [`cga/`](cga) | `python build.py tdk-capacitors` | TDK CGA automotive-grade MLCC; up to 75 VDC. Generator reads `cga/tdk_automotive_pn.csv`. |

Stale per-tool data still parked at this level:

- `tdk.csv`, `tdk.xls` — older inputs no longer consumed by any
  generator, retained for historical reference only. Safe to delete
  when the project no longer needs them.
- `History/` — historical DbLib snapshots; gitignored project-wide.

See [`cga/README.md`](cga/README.md) for per-family details.
