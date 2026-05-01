"""
DDL-001 drawing-standards constants. Direct port of
``house/HouseLibGenerator/DdlConventions.cs``. If you change one of
these, also update ``docs/standards/DDL-001.tex`` and re-run the full
build so all consumers see the same numbers.
"""

# §11.2 Pads:
#   shape:   rounded rectangle, 25% corner radius
#   sm exp:  manual 0.05 mm per pad
#   pm exp:  inherit board rule (no per-pad override)
#   sliver:  >= 0.1 mm between adjacent mask apertures, otherwise
#            bridge with a single Top Solder region instead of
#            shrinking the copper.
PAD_CORNER_RADIUS_PERCENT = 25
SOLDER_MASK_EXPANSION_MM  = 0.05
MIN_SOLDER_MASK_SLIVER_MM = 0.1

# §11.4 Component outline + centroid (Mechanical 15):
#   line width 0.1 mm, closed rectangle = nominal L x W. Centroid is a
#   crosshair clipped to the component outline with each arm capped at
#   MAX_CROSSHAIR_HALF_ARM_MM so the total cross length is never longer
#   than 2 * MAX_CROSSHAIR_HALF_ARM_MM = 1 mm.
OUTLINE_LINE_WIDTH_MM     = 0.1
MAX_CROSSHAIR_HALF_ARM_MM = 0.5

# §11.3 3D body (Mechanical 1): nominal L x W x H, Z=0. Chip
# components sit on the board so there's no standoff.
COMPONENT_BODY_STANDOFF_MM = 0.0
