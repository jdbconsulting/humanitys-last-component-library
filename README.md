# The Be-Done-With-It-Passives Footprint Library

Are you tired of messing around with passive footprints? Want to get an Altium footprint library that does it correctly? This library is for you!

## Limitations

This library is limited to chip resistors and chip capacitors between 01005 (metric 0402) and 1210 (metric 3225). To calculate 3D model and landing pad dimensions certain dimensions are needed from the chip such as terminal width, height, and tolerances. So it isn't possible to make a truly generic footprint library. No highly optimized footprint library can really be generic.

## The Philosophy

IPC-SM-782 was one of the original standards documents to define Printed Circuit Board (PCB) land patterns for Surface Mount Devices (SMD). Originally published in 1996 it later got superseded by IPC-7351 in 2005. Later, IPC-7351 was revisioned again in 2007 and 2010. This library is based on the IPC-7351 2010 guidelines.

However, the guidelines do not fully define land pads. Rather, they specify three classes of PCB fabrication and assembly tolerances and corresponding solder fillets *given* component tolerances. These component tolerances must come from the designer.

So, what component tolerances do we use? The JEDEC standarizations body defines a list of standardized two-terminal chips.

....

### On the Question of 3D Tolerances

When mechanical engineers are taking a 3D model of a printed circuit board for enclosure or heatsink design, they'll often ask if the component dimensions are nominal or max. If they're designing a compression thermal pad they need to know the minimum and maximum component dimensions. Having 3D bodies that represent the maximum dimensions as provided by the manufacturer can be useful to ensure clearances to adjacent components are guaranteed, but this is not the only use case. Designing a thermal pad is an example where having maximum dimensions can lead to a lack of thermal contact. Therefore this library uses the nominal component dimensions in its 3D models.

## The Library

Different organizations make make different layer and artwork choices. So a component library cannot satisfy them all. This library adopts a rather minimal set of artwork:

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

The IPC calculated pad dimensions are used in all cases with the except of the CAPC0402*, CAPC0603*, and RES0402* footprints which were adjusted to provide a minimum of 0.1mm solder mask sliver between the pads.

All footprints are named per IPC-SM-782 which consists of the following format:

RESCxxyyXzzc
CAPCxxyyXzzc

- xx : component length in 1/10ths of a millimeter
- yy : component width in 1/10ths of a millimeter
- zz : component height in 1/10ths of a millimeter
- c  : IPC material condition (either L for Least, N for nominal, and M for most)

## Based on

While JEDEC defines standard chip package widths and heights, it does not define heights and terminals. While most chip resistors and capacitors have similar terminals and its likely their footprints would be interchangeable, the best yields are like obtained by using an IPC footprint that is based on the chips dimensions. But, the goal of a standard footprint library is to choose a representative landing pad with which most JEDEC compliant chips will be highly compatible. Therefore we need to choose a representative chip on which to design the footprint.

For the resistors we will use the Panasonic Precision Thick Film Chip Resistor, ERJ type:

![](panasonic_precision_thick_film_chip_resistors.png)

For the capacitors we will use the Samsung Electro-Mechanics Multi-Layer Chip Capacitor, CL type:

![](samsung_standard_mlcc_dimensions.png)


# TDK Capacitors

All Commercial Grade - General Purpose (up to 75VDC) with Production Status == Production
(downloaded 7/22/2023)



# Protel PCB Library Report

| **Library File Name** | C:\projects\prestrike\ee\library\passives.PcbLib |
| --- | --- |
| **Library File Date/Time** | Saturday, May 27, 2023 11:34:18 PM |
| **Library File Size** | 2889728 |
| **Number of Components** | 102 |
| **Component List** | CAPC0402X02L, CAPC0402X02M, CAPC0402X02N, CAPC0603X03L, CAPC0603X03M, CAPC0603X03N, CAPC0603X05L, CAPC0603X05M, CAPC0603X05N, CAPC1005X02L, CAPC1005X02M, CAPC1005X02N, CAPC1005X03L, CAPC1005X03M, CAPC1005X03N, CAPC1005X05L, CAPC1005X05M, CAPC1005X05N, CAPC1005X06L, CAPC1005X06M, CAPC1005X06N, CAPC1005X07L, CAPC1005X07M, CAPC1005X07N, CAPC1608X05L, CAPC1608X05M, CAPC1608X05N, CAPC1608X07L, CAPC1608X07M, CAPC1608X07N, CAPC1608X08L, CAPC1608X08M, CAPC1608X08N, CAPC2012X07L, CAPC2012X07M, CAPC2012X07N, CAPC2012X08L, CAPC2012X08M, CAPC2012X08N, CAPC2012X09L, CAPC2012X09M, CAPC2012X09N, CAPC2012X11L, CAPC2012X11M, CAPC2012X11N, CAPC2012X12L, CAPC2012X12M, CAPC2012X12N, CAPC3216X09L, CAPC3216X09M, CAPC3216X09N, CAPC3216X12L, CAPC3216X12M, CAPC3216X12N, CAPC3216X16L, CAPC3216X16M, CAPC3216X16N, CAPC3225X09L, CAPC3225X09M, CAPC3225X09N, CAPC3225X13L, CAPC3225X13M, CAPC3225X13N, CAPC3225X14L, CAPC3225X14M, CAPC3225X14N, CAPC3225X16L, CAPC3225X16M, CAPC3225X16N, CAPC3225X18L, CAPC3225X18M, CAPC3225X18N, CAPC3225X20L, CAPC3225X20M, CAPC3225X20N, CAPC3225X25L, CAPC3225X25M, CAPC3225X25N, CAPC4532X16L, CAPC4532X16M, CAPC4532X16N, RESC0402X01L, RESC0402X01M, RESC0402X01N, RESC0603X02L, RESC0603X02M, RESC0603X02N, RESC1005X04L, RESC1005X04M, RESC1005X04N, RESC1608X04L, RESC1608X04M, RESC1608X04N, RESC2012X06L, RESC2012X06M, RESC2012X06N, RESC3216X06L, RESC3216X06M, RESC3216X06N, RESC3225X06L, RESC3225X06M, RESC3225X06N |

* * *

| ![](../QjzF557.wmf) |

| **Library Reference** |
## CAPC0402X02L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 0.40x0.20mm, IPC High Density |
| --- | --- |
| **Height** | 0.2mm |
| --- | --- |
| **Dimension** | 0.84mm x 0.34mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF568.wmf) |

| **Library Reference** |
## CAPC0402X02M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 0.40x0.20mm, IPC Low Density |
| --- | --- |
| **Height** | 0.2mm |
| --- | --- |
| **Dimension** | 1.24mm x 0.54mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF579.wmf) |

| **Library Reference** |
## CAPC0402X02N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 0.40x0.20mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.2mm |
| --- | --- |
| **Dimension** | 1.04mm x 0.44mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF589.wmf) |

| **Library Reference** |
## CAPC0603X03L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 0.60x0.30mm, IPC High Density |
| --- | --- |
| **Height** | 0.3mm |
| --- | --- |
| **Dimension** | 1.06mm x 0.44mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF58A.wmf) |

| **Library Reference** |
## CAPC0603X03M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 0.60x0.30mm, IPC Low Density |
| --- | --- |
| **Height** | 0.3mm |
| --- | --- |
| **Dimension** | 1.46mm x 0.64mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF59B.wmf) |

| **Library Reference** |
## CAPC0603X03N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 0.60x0.30mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.3mm |
| --- | --- |
| **Dimension** | 1.26mm x 0.54mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF5AC.wmf) |

| **Library Reference** |
## CAPC0603X05L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 0.60x0.30mm, IPC High Density |
| --- | --- |
| **Height** | 0.5mm |
| --- | --- |
| **Dimension** | 1.06mm x 0.44mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF5BC.wmf) |

| **Library Reference** |
## CAPC0603X05M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 0.60x0.30mm, IPC Low Density |
| --- | --- |
| **Height** | 0.5mm |
| --- | --- |
| **Dimension** | 1.46mm x 0.64mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF5BD.wmf) |

| **Library Reference** |
## CAPC0603X05N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 0.60x0.30mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.5mm |
| --- | --- |
| **Dimension** | 1.26mm x 0.54mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF5CE.wmf) |

| **Library Reference** |
## CAPC1005X02L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC High Density |
| --- | --- |
| **Height** | 0.2mm |
| --- | --- |
| **Dimension** | 1.46mm x 0.64mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF5DE.wmf) |

| **Library Reference** |
## CAPC1005X02M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Low Density |
| --- | --- |
| **Height** | 0.2mm |
| --- | --- |
| **Dimension** | 1.86mm x 0.84mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF5EF.wmf) |

| **Library Reference** |
## CAPC1005X02N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.2mm |
| --- | --- |
| **Dimension** | 1.66mm x 0.74mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF5F0.wmf) |

| **Library Reference** |
## CAPC1005X03L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC High Density |
| --- | --- |
| **Height** | 0.3mm |
| --- | --- |
| **Dimension** | 1.46mm x 0.64mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF601.wmf) |

| **Library Reference** |
## CAPC1005X03M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Low Density |
| --- | --- |
| **Height** | 0.3mm |
| --- | --- |
| **Dimension** | 1.86mm x 0.84mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF611.wmf) |

| **Library Reference** |
## CAPC1005X03N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.3mm |
| --- | --- |
| **Dimension** | 1.66mm x 0.74mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF622.wmf) |

| **Library Reference** |
## CAPC1005X05L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC High Density |
| --- | --- |
| **Height** | 0.5mm |
| --- | --- |
| **Dimension** | 1.46mm x 0.64mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF633.wmf) |

| **Library Reference** |
## CAPC1005X05M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Low Density |
| --- | --- |
| **Height** | 0.5mm |
| --- | --- |
| **Dimension** | 1.86mm x 0.84mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF634.wmf) |

| **Library Reference** |
## CAPC1005X05N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.5mm |
| --- | --- |
| **Dimension** | 1.66mm x 0.74mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF644.wmf) |

| **Library Reference** |
## CAPC1005X06L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC High Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 1.46mm x 0.64mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF655.wmf) |

| **Library Reference** |
## CAPC1005X06M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Low Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 1.86mm x 0.84mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF665.wmf) |

| **Library Reference** |
## CAPC1005X06N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 1.66mm x 0.74mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF666.wmf) |

| **Library Reference** |
## CAPC1005X07L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC High Density |
| --- | --- |
| **Height** | 0.7mm |
| --- | --- |
| **Dimension** | 1.46mm x 0.64mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF677.wmf) |

| **Library Reference** |
## CAPC1005X07M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Low Density |
| --- | --- |
| **Height** | 0.7mm |
| --- | --- |
| **Dimension** | 1.86mm x 0.84mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF688.wmf) |

| **Library Reference** |
## CAPC1005X07N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.00x0.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.7mm |
| --- | --- |
| **Dimension** | 1.66mm x 0.74mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF689.wmf) |

| **Library Reference** |
## CAPC1608X05L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.60x0.80mm, IPC High Density |
| --- | --- |
| **Height** | 0.5mm |
| --- | --- |
| **Dimension** | 2.15mm x 1mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF699.wmf) |

| **Library Reference** |
## CAPC1608X05M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.60x0.80mm, IPC Low Density |
| --- | --- |
| **Height** | 0.5mm |
| --- | --- |
| **Dimension** | 2.95mm x 1.15mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF6AA.wmf) |

| **Library Reference** |
## CAPC1608X05N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.60x0.80mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.5mm |
| --- | --- |
| **Dimension** | 2.55mm x 1.05mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF6BB.wmf) |

| **Library Reference** |
## CAPC1608X07L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.60x0.80mm, IPC High Density |
| --- | --- |
| **Height** | 0.7mm |
| --- | --- |
| **Dimension** | 2.15mm x 1mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF6BC.wmf) |

| **Library Reference** |
## CAPC1608X07M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.60x0.80mm, IPC Low Density |
| --- | --- |
| **Height** | 0.7mm |
| --- | --- |
| **Dimension** | 2.95mm x 1.15mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF6CC.wmf) |

| **Library Reference** |
## CAPC1608X07N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.60x0.80mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.7mm |
| --- | --- |
| **Dimension** | 2.55mm x 1.05mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF6DD.wmf) |

| **Library Reference** |
## CAPC1608X08L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.60x0.80mm, IPC High Density |
| --- | --- |
| **Height** | 0.8mm |
| --- | --- |
| **Dimension** | 2.15mm x 1mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF6ED.wmf) |

| **Library Reference** |
## CAPC1608X08M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.60x0.80mm, IPC Low Density |
| --- | --- |
| **Height** | 0.8mm |
| --- | --- |
| **Dimension** | 2.95mm x 1.15mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF6FE.wmf) |

| **Library Reference** |
## CAPC1608X08N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 1.60x0.80mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.8mm |
| --- | --- |
| **Dimension** | 2.55mm x 1.05mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF6FF.wmf) |

| **Library Reference** |
## CAPC2012X07L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC High Density |
| --- | --- |
| **Height** | 0.7mm |
| --- | --- |
| **Dimension** | 2.55mm x 1.4mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF710.wmf) |

| **Library Reference** |
## CAPC2012X07M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Low Density |
| --- | --- |
| **Height** | 0.7mm |
| --- | --- |
| **Dimension** | 3.35mm x 1.55mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF720.wmf) |

| **Library Reference** |
## CAPC2012X07N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.7mm |
| --- | --- |
| **Dimension** | 2.95mm x 1.45mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF731.wmf) |

| **Library Reference** |
## CAPC2012X08L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC High Density |
| --- | --- |
| **Height** | 0.8mm |
| --- | --- |
| **Dimension** | 2.55mm x 1.4mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF732.wmf) |

| **Library Reference** |
## CAPC2012X08M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Low Density |
| --- | --- |
| **Height** | 0.8mm |
| --- | --- |
| **Dimension** | 3.35mm x 1.55mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF743.wmf) |

| **Library Reference** |
## CAPC2012X08N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.8mm |
| --- | --- |
| **Dimension** | 2.95mm x 1.45mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF753.wmf) |

| **Library Reference** |
## CAPC2012X09L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC High Density |
| --- | --- |
| **Height** | 0.9mm |
| --- | --- |
| **Dimension** | 2.55mm x 1.4mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF764.wmf) |

| **Library Reference** |
## CAPC2012X09M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Low Density |
| --- | --- |
| **Height** | 0.9mm |
| --- | --- |
| **Dimension** | 3.35mm x 1.55mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF774.wmf) |

| **Library Reference** |
## CAPC2012X09N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.9mm |
| --- | --- |
| **Dimension** | 2.95mm x 1.45mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF775.wmf) |

| **Library Reference** |
## CAPC2012X11L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC High Density |
| --- | --- |
| **Height** | 1.1mm |
| --- | --- |
| **Dimension** | 2.55mm x 1.4mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF786.wmf) |

| **Library Reference** |
## CAPC2012X11M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Low Density |
| --- | --- |
| **Height** | 1.1mm |
| --- | --- |
| **Dimension** | 3.35mm x 1.55mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF797.wmf) |

| **Library Reference** |
## CAPC2012X11N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Medium Density |
| --- | --- |
| **Height** | 1.1mm |
| --- | --- |
| **Dimension** | 2.95mm x 1.45mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF798.wmf) |

| **Library Reference** |
## CAPC2012X12L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC High Density |
| --- | --- |
| **Height** | 1.2mm |
| --- | --- |
| **Dimension** | 2.55mm x 1.4mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF7A8.wmf) |

| **Library Reference** |
## CAPC2012X12M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Low Density |
| --- | --- |
| **Height** | 1.2mm |
| --- | --- |
| **Dimension** | 3.35mm x 1.55mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF7B9.wmf) |

| **Library Reference** |
## CAPC2012X12N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 2.00x1.20mm, IPC Medium Density |
| --- | --- |
| **Height** | 1.2mm |
| --- | --- |
| **Dimension** | 2.95mm x 1.45mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF7CA.wmf) |

| **Library Reference** |
## CAPC3216X09L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x1.60mm, IPC High Density |
| --- | --- |
| **Height** | 0.9mm |
| --- | --- |
| **Dimension** | 3.75mm x 1.8mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF7DA.wmf) |

| **Library Reference** |
## CAPC3216X09M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x1.60mm, IPC Low Density |
| --- | --- |
| **Height** | 0.9mm |
| --- | --- |
| **Dimension** | 4.55mm x 1.95mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF7DB.wmf) |

| **Library Reference** |
## CAPC3216X09N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x1.60mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.9mm |
| --- | --- |
| **Dimension** | 4.15mm x 1.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF7EC.wmf) |

| **Library Reference** |
## CAPC3216X12L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x1.60mm, IPC High Density |
| --- | --- |
| **Height** | 1.2mm |
| --- | --- |
| **Dimension** | 3.75mm x 1.8mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF7FC.wmf) |

| **Library Reference** |
## CAPC3216X12M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x1.60mm, IPC Low Density |
| --- | --- |
| **Height** | 1.2mm |
| --- | --- |
| **Dimension** | 4.55mm x 1.95mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF7FD.wmf) |

| **Library Reference** |
## CAPC3216X12N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x1.60mm, IPC Medium Density |
| --- | --- |
| **Height** | 1.2mm |
| --- | --- |
| **Dimension** | 4.15mm x 1.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF80E.wmf) |

| **Library Reference** |
## CAPC3216X16L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x1.60mm, IPC High Density |
| --- | --- |
| **Height** | 1.6mm |
| --- | --- |
| **Dimension** | 3.75mm x 1.8mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF81F.wmf) |

| **Library Reference** |
## CAPC3216X16M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x1.60mm, IPC Low Density |
| --- | --- |
| **Height** | 1.6mm |
| --- | --- |
| **Dimension** | 4.55mm x 1.95mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF82F.wmf) |

| **Library Reference** |
## CAPC3216X16N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x1.60mm, IPC Medium Density |
| --- | --- |
| **Height** | 1.6mm |
| --- | --- |
| **Dimension** | 4.15mm x 1.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF830.wmf) |

| **Library Reference** |
## CAPC3225X09L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC High Density |
| --- | --- |
| **Height** | 0.9mm |
| --- | --- |
| **Dimension** | 3.75mm x 2.7mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF841.wmf) |

| **Library Reference** |
## CAPC3225X09M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Low Density |
| --- | --- |
| **Height** | 0.9mm |
| --- | --- |
| **Dimension** | 4.55mm x 2.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF852.wmf) |

| **Library Reference** |
## CAPC3225X09N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.9mm |
| --- | --- |
| **Dimension** | 4.15mm x 2.75mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF862.wmf) |

| **Library Reference** |
## CAPC3225X13L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC High Density |
| --- | --- |
| **Height** | 1.3mm |
| --- | --- |
| **Dimension** | 3.75mm x 2.7mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF863.wmf) |

| **Library Reference** |
## CAPC3225X13M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Low Density |
| --- | --- |
| **Height** | 1.3mm |
| --- | --- |
| **Dimension** | 4.55mm x 2.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF874.wmf) |

| **Library Reference** |
## CAPC3225X13N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 1.3mm |
| --- | --- |
| **Dimension** | 4.253mm x 2.853mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF884.wmf) |

| **Library Reference** |
## CAPC3225X14L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC High Density |
| --- | --- |
| **Height** | 1.4mm |
| --- | --- |
| **Dimension** | 3.75mm x 2.7mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF895.wmf) |

| **Library Reference** |
## CAPC3225X14M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Low Density |
| --- | --- |
| **Height** | 1.4mm |
| --- | --- |
| **Dimension** | 4.55mm x 2.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF896.wmf) |

| **Library Reference** |
## CAPC3225X14N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 1.4mm |
| --- | --- |
| **Dimension** | 4.15mm x 2.75mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF8A7.wmf) |

| **Library Reference** |
## CAPC3225X16L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC High Density |
| --- | --- |
| **Height** | 1.6mm |
| --- | --- |
| **Dimension** | 3.75mm x 2.7mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF8B7.wmf) |

| **Library Reference** |
## CAPC3225X16M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Low Density |
| --- | --- |
| **Height** | 1.6mm |
| --- | --- |
| **Dimension** | 4.55mm x 2.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF8D8.wmf) |

| **Library Reference** |
## CAPC3225X16N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 1.6mm |
| --- | --- |
| **Dimension** | 4.15mm x 2.75mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF8D9.wmf) |

| **Library Reference** |
## CAPC3225X18L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC High Density |
| --- | --- |
| **Height** | 1.8mm |
| --- | --- |
| **Dimension** | 3.75mm x 2.7mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF8E9.wmf) |

| **Library Reference** |
## CAPC3225X18M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Low Density |
| --- | --- |
| **Height** | 1.8mm |
| --- | --- |
| **Dimension** | 4.55mm x 2.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF8FA.wmf) |

| **Library Reference** |
## CAPC3225X18N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 1.8mm |
| --- | --- |
| **Dimension** | 4.15mm x 2.75mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF90A.wmf) |

| **Library Reference** |
## CAPC3225X20L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC High Density |
| --- | --- |
| **Height** | 2mm |
| --- | --- |
| **Dimension** | 3.75mm x 2.7mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF90B.wmf) |

| **Library Reference** |
## CAPC3225X20M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Low Density |
| --- | --- |
| **Height** | 2mm |
| --- | --- |
| **Dimension** | 4.55mm x 2.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF91C.wmf) |

| **Library Reference** |
## CAPC3225X20N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 2mm |
| --- | --- |
| **Dimension** | 4.15mm x 2.75mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF92D.wmf) |

| **Library Reference** |
## CAPC3225X25L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC High Density |
| --- | --- |
| **Height** | 2.5mm |
| --- | --- |
| **Dimension** | 3.75mm x 2.7mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF93D.wmf) |

| **Library Reference** |
## CAPC3225X25M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Low Density |
| --- | --- |
| **Height** | 2.5mm |
| --- | --- |
| **Dimension** | 4.55mm x 2.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF93E.wmf) |

| **Library Reference** |
## CAPC3225X25N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 3.20x2.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 2.5mm |
| --- | --- |
| **Dimension** | 4.15mm x 2.75mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF94F.wmf) |

| **Library Reference** |
## CAPC4532X16L
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 4.50x3.20mm, IPC High Density |
| --- | --- |
| **Height** | 1.6mm |
| --- | --- |
| **Dimension** | 5.05mm x 3.4mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF960.wmf) |

| **Library Reference** |
## CAPC4532X16M
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 4.50x3.20mm, IPC Low Density |
| --- | --- |
| **Height** | 1.6mm |
| --- | --- |
| **Dimension** | 5.85mm x 3.55mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF970.wmf) |

| **Library Reference** |
## CAPC4532X16N
 |
| --- | --- |
| **Description** | Chip Capacitor, 2-Leads, Body 4.50x3.20mm, IPC Medium Density |
| --- | --- |
| **Height** | 1.6mm |
| --- | --- |
| **Dimension** | 5.45mm x 3.45mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF981.wmf) |

| **Library Reference** |
## RESC0402X01L
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 0.40x0.20mm, IPC High Density |
| --- | --- |
| **Height** | 0.13mm |
| --- | --- |
| **Dimension** | 0.751mm x 0.25mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF982.wmf) |

| **Library Reference** |
## RESC0402X01M
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 0.40x0.20mm, IPC Low Density |
| --- | --- |
| **Height** | 0.13mm |
| --- | --- |
| **Dimension** | 1.151mm x 0.45mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF992.wmf) |

| **Library Reference** |
## RESC0402X01N
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 0.40x0.20mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.13mm |
| --- | --- |
| **Dimension** | 0.951mm x 0.35mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF9A3.wmf) |

| **Library Reference** |
## RESC0603X02L
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 0.60x0.30mm, IPC High Density |
| --- | --- |
| **Height** | 0.23mm |
| --- | --- |
| **Dimension** | 0.95mm x 0.4mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF9B4.wmf) |

| **Library Reference** |
## RESC0603X02M
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 0.60x0.30mm, IPC Low Density |
| --- | --- |
| **Height** | 0.23mm |
| --- | --- |
| **Dimension** | 1.35mm x 0.55mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF9B5.wmf) |

| **Library Reference** |
## RESC0603X02N
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 0.60x0.30mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.23mm |
| --- | --- |
| **Dimension** | 1.15mm x 0.45mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF9C5.wmf) |

| **Library Reference** |
## RESC1005X04L
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 1.00x0.50mm, IPC High Density |
| --- | --- |
| **Height** | 0.35mm |
| --- | --- |
| **Dimension** | 1.35mm x 0.6mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF9D6.wmf) |

| **Library Reference** |
## RESC1005X04M
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 1.00x0.50mm, IPC Low Density |
| --- | --- |
| **Height** | 0.35mm |
| --- | --- |
| **Dimension** | 1.75mm x 0.75mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF9E7.wmf) |

| **Library Reference** |
## RESC1005X04N
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 1.00x0.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.35mm |
| --- | --- |
| **Dimension** | 1.55mm x 0.65mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzF9F7.wmf) |

| **Library Reference** |
## RESC1608X04L
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 1.60x0.80mm, IPC High Density |
| --- | --- |
| **Height** | 0.45mm |
| --- | --- |
| **Dimension** | 2.05mm x 1mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA08.wmf) |

| **Library Reference** |
## RESC1608X04M
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 1.60x0.80mm, IPC Low Density |
| --- | --- |
| **Height** | 0.45mm |
| --- | --- |
| **Dimension** | 2.85mm x 1.05mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA18.wmf) |

| **Library Reference** |
## RESC1608X04N
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 1.60x0.80mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.45mm |
| --- | --- |
| **Dimension** | 2.45mm x 1mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA29.wmf) |

| **Library Reference** |
## RESC2012X06L
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 2.00x1.20mm, IPC High Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 2.45mm x 1.3mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA2A.wmf) |

| **Library Reference** |
## RESC2012X06M
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 2.00x1.20mm, IPC Low Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 3.25mm x 1.45mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA3B.wmf) |

| **Library Reference** |
## RESC2012X06N
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 2.00x1.20mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 2.85mm x 1.35mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA4B.wmf) |

| **Library Reference** |
## RESC3216X06L
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 3.20x1.60mm, IPC High Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 3.65mm x 1.8mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA5C.wmf) |

| **Library Reference** |
## RESC3216X06M
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 3.20x1.60mm, IPC Low Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 4.45mm x 1.85mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA5D.wmf) |

| **Library Reference** |
## RESC3216X06N
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 3.20x1.60mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 4.153mm x 1.853mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA6E.wmf) |

| **Library Reference** |
## RESC3225X06L
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 3.20x2.50mm, IPC High Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 3.65mm x 2.7mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA7E.wmf) |

| **Library Reference** |
## RESC3225X06M
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 3.20x2.50mm, IPC Low Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 4.45mm x 2.75mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |

* * *

| ![](../QjzFA8F.wmf) |

| **Library Reference** |
## RESC3225X06N
 |
| --- | --- |
| **Description** | Chip Resistor, 2-Leads, Body 3.20x2.50mm, IPC Medium Density |
| --- | --- |
| **Height** | 0.6mm |
| --- | --- |
| **Dimension** | 4.05mm x 2.7mm |
| --- | --- |
| **Number of Pads** | 2 |
| --- | --- |
| **Number of Primitives** | 9 |
| --- | --- |

 |
| --- | --- |