# Samsung Library Notes

This folder is a per-family aggregator. Every active Samsung
generator lives in its own subfolder.

| Family                        | Folder      | Build target                         | Notes                                                                                                            |
| ----------------------------- | ----------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| **CL** (general-purpose MLCC) | [`cl/`](cl) | `python build.py samsung-capacitors` | the only Samsung family currently carried; includes the input MPN list, decoder script, and reference datasheets |

Untracked per-tool reference data (downloaded, not source) lives at:

- `Automotive/`, `General/` — Samsung MLCC S-parameter / Touchstone
  libraries downloaded from Samsung's design tool. Both folders are
  `.gitignore`d (see the project root `.gitignore`); re-fetch with
  the vendor scripts rather than committing.
- `History/` — historical DbLib snapshots; gitignored project-wide.

See [`cl/README.md`](cl/README.md) for the per-family details.
