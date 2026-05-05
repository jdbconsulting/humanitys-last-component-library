#!/usr/bin/env python
"""
Fetch the full Murata GCM (automotive MLCC) orderable-parts list from
Murata's PIM backend and save it as vendors/murata/gcm/gcm_parts.csv.

This works around the 1,000-row cap on Murata's public PIM UI by calling
the underlying REST endpoint that the SPA uses for its "Download CSV"
button, with the `acquisitionNum` override bumped from the UI default of
1000 up to 10000 (enough headroom for every GCM MPN Murata ships today
- currently 5,781).

This requires no API key. The endpoint at
`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`
is the same one the SPA at https://pim.murata.com uses, and it's
unauthenticated. If Murata ever tightens access or changes the body
shape, the official long-term path is the Murata Product Information
Management API v2.2 (requires a free API key, see README.md).

Usage:
    python vendors/murata/fetch_gcm_pim.py
    python vendors/murata/fetch_gcm_pim.py --part-prefix GRM          # fetch GRM series instead
    python vendors/murata/fetch_gcm_pim.py --output vendors/murata/other.csv  # different output path

Output goes to vendors/murata/gcm/gcm_parts.csv by default (UTF-8
CSV, one row per orderable MPN, ~3 MB, ~5800 rows for GCM). Pass
``--output vendors/murata/grm/grm_parts.csv`` (with ``--part-prefix
GRM``) to refresh the GRM catalogue instead.

Expect the HTTP POST to take roughly 60 seconds for the full GCM set;
Murata's backend churns through the query synchronously.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers"
DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "gcm", "gcm_parts.csv"
)

# The SPA's "Download CSV" button hard-codes this to 1000, which is the
# UI cap the user hits. The backend itself honors higher values; we
# default to a margin above the current ~5800-part GCM universe and
# allow the caller to bump it via --acquisition-num for larger
# series (GRM exceeds 10000 today, hence the override flag).
DEFAULT_ACQUISITION_NUM = 10000


def build_request_body(part_prefix: str, acquisition_num: int) -> dict:
    """Match the JSON body shape the pim.murata.com SPA sends, observed
    by inspecting the minified bundle at
    /assets/entries/src_pages_pim_search.*.js. The fields below are the
    full set `postPartNumbers()` serialises; empty strings / empty lists
    are how the SPA encodes 'no filter'."""
    return {
        "productCategoryId": "ceramicCapacitorSMD",
        "partNum": part_prefix,
        "languageRegion": "en-us",
        "searchCondClass": 1,
        "series": "",
        "acquisitionNum": acquisition_num,
        "sortKey": "",
        "valSearchCondList": [],
        "rangeValSearchCondList": [],
        "dateRangeSearchCondList": [],
        "formFormat": "csv",
        "formOutputItemsList": [],
    }


def fetch(endpoint: str, body: dict, timeout: float) -> bytes:
    """POST the JSON body to endpoint, return the raw CSV bytes."""
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/csv, */*",
            # The SPA sends Origin/Referer on these XHRs; mirror them so
            # that anti-scraping middleware (if any) sees a legitimate
            # browser-originated request.
            "Origin": "https://pim.murata.com",
            "Referer": "https://pim.murata.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            ),
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--part-prefix",
        default="GCM",
        help="Murata part-number prefix to pull (default: GCM)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Destination CSV path (default: vendors/murata/gcm/gcm_parts.csv)",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help="Override the PIM endpoint URL (rarely needed)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="Request timeout in seconds (default: 600; Murata's backend "
             "can take several minutes for large series like GRM)",
    )
    parser.add_argument(
        "--acquisition-num",
        type=int,
        default=DEFAULT_ACQUISITION_NUM,
        help=(
            "Cap on the number of parts to return in one request. "
            f"Default: {DEFAULT_ACQUISITION_NUM}. The Murata PIM SPA "
            "ships with 1000; the backend honours higher values. The "
            "GCM series fits in 10000 but the GRM series exceeds it -- "
            "pass --acquisition-num 50000 (or higher) for GRM."
        ),
    )
    args = parser.parse_args()

    body = build_request_body(args.part_prefix, args.acquisition_num)
    print(
        f"Fetching up to {args.acquisition_num} {args.part_prefix}* parts from "
        f"{args.endpoint} (this typically takes 60-300s)...",
        file=sys.stderr,
    )
    t0 = time.time()
    try:
        csv_bytes = fetch(args.endpoint, body, args.timeout)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {e.reason}", file=sys.stderr)
        try:
            print(e.read().decode("utf-8", errors="replace")[:500], file=sys.stderr)
        except Exception:
            pass
        return 1
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        return 2
    elapsed = time.time() - t0

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(csv_bytes)

    # Cheap row count: number of newlines minus the header line. Good
    # enough as long as no cell contains a literal newline (spot-checked:
    # Murata's CSV escapes newlines inside quoted fields, so this is ok
    # for the current schema).
    row_count = csv_bytes.count(b"\n") - 1
    print(
        f"Wrote {args.output}: {len(csv_bytes):,} bytes, "
        f"{row_count:,} data rows, {elapsed:.1f}s.",
        file=sys.stderr,
    )

    if row_count >= args.acquisition_num:
        print(
            f"WARNING: row count ({row_count}) equals or exceeds the "
            f"acquisitionNum cap ({args.acquisition_num}). The returned "
            f"data may be truncated; pass --acquisition-num with a "
            f"larger value and re-run.",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
