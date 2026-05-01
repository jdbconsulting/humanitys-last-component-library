# Panasonic Library Notes

## Panasonic Resistors

Panasonic groups [chip resistor series](https://industrial.panasonic.com/ww/products/resistors/chip-resistors) by application (high temperature, high precision, current sensing, high power, anti-sulfurated, general purpose, networks/arrays). The table below lists every chip-resistor family called out in their "Types of chip resistors" selector (April 2026), using the same family keys (wildcards `*` denote size/grade suffixes in part numbers).

For Panasonic's full fixed-resistor portfolio overview, see [`reference/panasonic_fixed_resistors.pdf`](reference/panasonic_fixed_resistors.pdf). Per-family datasheets are linked where available.

Reference image (Panasonic ERJ thick-film chip resistor family):

![](reference/panasonic_precision_thick_film_chip_resistors.png)

| Family (Panasonic) | Brief description | In Library |
| --- | --- | --- |
| **ERJH** | High-temperature / high-voltage thin-film chip resistors | |
| **[ERA\*P](reference/panasonic_era-p.pdf)** | Thin-film high-voltage 1206 line (500 V limiting voltage), otherwise matches ERA\*V/K | Yes - 1206 only (`ERA-8PEB`) |
| **[ERA\*V / ERA\*K](reference/panasonic_era-v.pdf)** | Thin-film high precision / high stability (V = standard range, K = high-resistance extension) | Yes - 0402 / 0603 / 0805 only; for 1206 see ERA\*P |
| **[ERA\*A](reference/panasonic_era-a.pdf)** | Thick-film high-precision chip resistors (A series) | Yes - 0201 only (`ERA-1AEB`); 0402-1206 sizes are superseded by ERA\*V/K |
| **ERJPB** | Thick-film super high precision | No - redundant with ERA\*V / ERA\*K at the sizes we carry |
| **ERJPC** | Thick-film super high precision (newer ERJPC line) | |
| **ERJ\*B / ERJBW / ERJLW** | Current sensing: wide-terminal low-resistance thick-film types | |
| **ERJA / ERJB** | Current sensing: metal-plate (shunt) types | |
| **ERJD** | Current sensing: anti-surge metal-plate / specialized surge-rated types | |
| **ERJMB / ERJMS** | Current sensing: metal-plate for high current / anti-pulse applications | |
| **ERJP** | Small size / high power thick-film chip resistors | |
| **ERJT** | Small size / high power thick-film chip resistors (precision grades) | |
| **ERJS / ERJU** | Anti-sulfurated thick-film chip resistors | |
| **ERJU-R** | Anti-sulfurated wide-terminal types | |
| **ERJUP** | Anti-sulfurated thick-film precision | |
| **ERJC1** | Anti-sulfurated large-format / high-power special cases | |
| **[ERJ](reference/panasonic_erj.pdf)** | General-purpose thick-film chip resistors | Yes |
| **EXB** (8, 15 element) | Resistor network (isolated / bussed) | |
| **EXB** (2, 4, 8 element) | Resistor array | |
| **EXBU** (2, 4, 8 element) | Anti-sulfurated resistor arrays | |
