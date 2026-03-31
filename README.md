# The Be-Done-With-It-Passives Footprint Library

Are you tired of messing around with passive footprints? Want to get an Altium footprint library that does it correctly? This library is for you!

![Coupon board screenshot](docs/coupon-board-screenshot.png)

## Limitations

This library is limited to chip resistors and chip capacitors between 01005 (metric 0402) and 1210 (metric 3225). To calculate 3D model and landing pad dimensions, certain dimensions are needed from the chip, such as terminal width, height, and tolerances. So it isn't possible to make a truly generic footprint library. No highly optimized footprint library can really be generic.

## The Philosophy

IPC-SM-782 was one of the original standards documents to define Printed Circuit Board (PCB) land patterns for Surface Mount Devices (SMD). Originally published in 1996, it was later superseded by IPC-7351 in 2005. IPC-7351 was then revised in 2007 and 2010. This library is based on the IPC-7351 2010 guidelines.

However, the guidelines do not fully define land pads. Rather, they specify three classes of PCB fabrication and assembly tolerances and corresponding solder fillets *given* component tolerances. These component tolerances must come from the designer.

So, what component tolerances do we use? The JEDEC standardization body defines a list of standardized two-terminal chips.

....

### On the Question of 3D Tolerances

When mechanical engineers are taking a 3D model of a printed circuit board for enclosure or heatsink design, they'll often ask if the component dimensions are nominal or max. If they're designing a compression thermal pad, they need to know the minimum and maximum component dimensions. Having 3D bodies that represent the maximum dimensions as provided by the manufacturer can be useful to ensure clearances to adjacent components are guaranteed, but this is not the only use case. Designing a thermal pad is an example where having maximum dimensions can lead to a lack of thermal contact. Therefore, this library uses the nominal component dimensions in its 3D models.

## The Library

Different organizations make different layer and artwork choices. So a component library cannot satisfy them all. This library adopts a rather minimal set of artwork:

1. Pads
    a. toe/side/heel per IPC-7351B (2010)
    b. Rules based paste mask expansion (i.e. defined globally at the PCBDoc level)
    c. Manual solder mask expansion set to 0.05mm (1.97mil) (per IPC-A-610 Class 2)
    d. Rounded rectangle shape with 25% corner radius on all corners (per IPC-7351A/B)
    e. length/width/height tolerance = +/- 0%
    f. terminal (band) length: RESC per Panasonic ERJ family, CAPC per Samsung CL family
2. Component Outline (Layer: Mechanical 15)
3. Component Centroid (Layer: Mechanical 15)
4. 3D Model (Layer: Mechanical 1)

The IPC calculated pad dimensions are used in all cases with the exception of the CAPC0402*, CAPC0603*, and RESC0402* footprints which were adjusted to provide a minimum of 0.1mm solder mask sliver between the pads.

All footprints are named per IPC-SM-782 which consists of the following format:

RESCxxyyXzzc
CAPCxxyyXzzc

- xx : component length in 1/10ths of a millimeter
- yy : component width in 1/10ths of a millimeter
- zz : component height in 1/10ths of a millimeter
- c  : IPC material condition (either L for least, N for nominal, or M for most)

## Based on

While JEDEC defines standard chip package lengths and widths, it does not define heights and terminals. While most chip resistors and capacitors have similar terminals and it's likely their footprints would be interchangeable, the best yields are likely obtained by using an IPC footprint that is based on the chips dimensions. But, the goal of a standard footprint library is to choose a representative landing pad with which most JEDEC compliant chips will be highly compatible. Therefore we need to choose a representative chip on which to design the footprint.

For the default resistors we will use the Panasonic Precision Thick Film Chip Resistor, ERJ type:

![](panasonic/panasonic_precision_thick_film_chip_resistors.png)

For the default capacitors we will use the TDK Multi-Layer Chip Capacitor, CGA type.


# Vendor Library Details

## TDK Capacitors

All Commercial Grade - General Purpose (up to 75VDC) with Production Status == Production
(downloaded 7/22/2023)

## Panasonic Resistors

TODO


