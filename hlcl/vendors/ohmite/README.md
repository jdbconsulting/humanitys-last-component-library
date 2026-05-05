# Ohmite Library Notes

Ohmite is a US-based resistor manufacturer; the lines in this repo
target their precision and current-sense families. This folder is a
per-family aggregator — every active Ohmite generator lives in its
own subfolder.

| Family                              | Folder        | Build target                 | Notes                                                                                                                                                                                                                                                            |
| ----------------------------------- | ------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **KDV** (current-sense, metal-film) | [`kdv/`](kdv) | `python build.py ohmite-kdv` | metal-film low-resistance chip resistor (current sense) family in 5 EIA sizes (0201–1206) with 197 standard orderable part numbers across two tolerances (0.5%, 1%) and 20 resistance values (50 mΩ – 820 mΩ). See [`kdv/README.md`](kdv/README.md) for details. |
