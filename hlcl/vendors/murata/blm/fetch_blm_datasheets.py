#!/usr/bin/env python
"""
Refresh vendors/murata/blm/blm_dimensions.csv from Murata's
productdetail pages.

vendors/murata/blm/blm_dimensions.csv carries per-base-MPN body
dimensions (Length, Width, Thickness in mm) for every BLM-series chip
ferrite bead in vendors/murata/blm/blm_parts.csv. ``base_mpn =
MPN[:10]`` is the key, since Murata's tolerance / temperature-grade /
packaging suffix bytes don't change physical dimensions.

vendors/murata/blm/murata-ferrite.py reads the resulting CSV at build
time to pick the right IPC-7351B nominal-height code per part (e.g.
BLM18KG101 = 0.6 mm tall -> INDC1608X60, BLM18KG331 = 0.8 mm tall ->
INDC1608X80; same subseries, different footprint).

WHY THIS ISN'T A SELF-CONTAINED CLI SCRAPE
-------------------------------------------

Murata serves productdetail (https://www.murata.com/products/productdetail?partno=...)
as a React SPA -- the spec table is filled in by client-side JavaScript
after page load, not in the initial HTML. A direct ``urllib.request``
hits the SPA shell and returns ~5 KB of bootstrap with no spec data.

Murata's per-subseries Specifications PDFs (``ENFA####.pdf`` URLs
linked from each productdetail page) live on a CloudFront distribution
that returns HTTP 500 to non-browser User-Agents -- confirmed against
``urllib``, ``curl``, and Cursor's WebFetch tool.

Murata's PIM CSV API (https://pimapi.murata.com/...; see
../fetch_gcm_pim.py for an example call) doesn't expose a chip-ferrite-bead
product category as of this writing -- every plausible
``productCategoryId`` (chipFerriteBead, ferriteBead, EMIFIL, etc.)
returns an empty body. Ferrites can be filtered under
``productCategoryId="inductor"`` but the schema there is wired for
inductors (Inductance, Q, etc.) and BLM parts come back with empty
dimension columns.

So the working extraction path is the productdetail page's
JS-rendered spec table, accessed through a tool that can render the
page (Cursor's WebFetch, Playwright, Selenium, etc.). The repo policy
is pure-stdlib Python with no native-binary dependencies, so a
headless-browser CLI tool is out of scope.

REFRESH PROCEDURE
-----------------

When you add a new BLM MPN to ``blm_parts.csv``, refresh
``blm_dimensions.csv`` by handing this prompt to a Cursor agent (or
any agent with a JS-rendering web-fetch tool):

    Read vendors/murata/blm/blm_parts.csv. For every unique 10-char
    base MPN (BLM<size:2><subseries:2><value:3>), pick a representative
    full MPN and fetch
    https://www.murata.com/products/productdetail?partno={MPN} . The
    response includes a markdown spec table with rows like
    ``|Length|1.6mm|`` / ``|Width|0.8mm|`` / ``|Thickness|0.8mm|``.
    Extract those nominal values and write
    vendors/murata/blm/blm_dimensions.csv with this exact schema:

        base_mpn,sample_mpn,length_mm,width_mm,thickness_mm,source_url

    sorted by base_mpn. Also save a per-subseries reference dump to
    vendors/murata/blm/reference/<subseries>.md so a human reviewer can
    audit the extraction.

This script itself prints the same instructions and exits non-zero,
so a forgotten datasheet refresh will be loud but the build can
continue from cached data.

Until/unless Murata exposes a stable headless-friendly endpoint or
adds chip-ferrite-bead to the public PIM CSV API, this is the cleanest
approach.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS_CSV = os.path.join(HERE, "blm_parts.csv")
DIMENSIONS_CSV = os.path.join(HERE, "blm_dimensions.csv")
REFERENCE_DIR = os.path.join(HERE, "reference")


def main():
    if not os.path.exists(PARTS_CSV):
        print(f"error: {PARTS_CSV} not found", file=sys.stderr)
        return 1

    print(__doc__.strip().split("REFRESH PROCEDURE\n-----------------\n")[1], file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
