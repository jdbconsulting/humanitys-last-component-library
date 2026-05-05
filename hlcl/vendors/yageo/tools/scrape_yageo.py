#!/usr/bin/env python
"""
Pull the in-stock orderable-parts list for the three Yageo resistor
families we carry (RC = general-purpose thick film, AC = automotive
AEC-Q200 thick film, RT = precision thin film) from the public
Yageo Group product search backend, and write one CSV per family
to its sibling ``../<rc|ac|rt>/<rc|ac|rt>_parts.csv``.

Yageo's public product search site (https://yageogroup.com/products/...)
is a Next.js SPA that bails out to client-side rendering. It calls
two undocumented HTTP endpoints internally:

  - ``/search/query/bp-filter/<json>``    - facet listing + counts
  - ``/search/query/base-part/<json>``    - paginated product list,
                                             one entry per orderable
                                             MPN with a fully populated
                                             ``parameterValues`` array

Both accept the JSON body URL-encoded into the path (no headers,
no auth). They are the same endpoints the SPA itself calls; we
mirror its query shape:

    {
      "1":     1605,            // product category id (Resistors)
      "3":     [<series_ids>],  // parameterId 3 = "Series"
      "stock": true,            // restrict to currently-stocked parts
      "asc":   "", "desc": "",  // sort fields (left empty, server's
                                //   default sort by base-part id is
                                //   stable enough for our re-runs)
      "limit": <int>,           // page size, 1000 is comfortable
      "offset": <int>,          // pagination cursor
      "isNumeric": false
    }

The Yageo "Series" facet IDs (parameterId 3) for our three targets,
discovered by scraping the bp-filter response with no series filter:

    RC: 24261     (general-purpose thick film, "RC_L")
    AC: 373927    (automotive thick film, AEC-Q200)
    RT: 24279     (precision thin film)

In-stock counts at the time this scraper was first run (Nov 2025):

    RC: ~11.8k MPNs    AC: ~7.6k     RT: ~8.8k

This tool requires no API key and no headless browser. The endpoint
returns plain JSON; we walk it with stdlib ``urllib.request``.

Output schema (one row per stocked Yageo MPN, UTF-8 CSV with header):

    mpn,size_code,resistance_ohms,tolerance,tcr,power_w,
    voltage_v,temp_min_c,temp_max_c,length_mm,width_mm,height_mm

The columns are documented in detail in
``vendors/yageo/_yageo_common.py``'s module docstring; ``size_code``
is the 4-digit Yageo size prefix parsed off the MPN (``"0100"``,
``"0201"``, ``"0402"``, ...) and is the lookup key the family
build scripts use against
:data:`vendors.yageo._yageo_common.SIZE_TO_FOOTPRINT`.

Usage:

    python vendors/yageo/tools/scrape_yageo.py
    python vendors/yageo/tools/scrape_yageo.py --family rc
    python vendors/yageo/tools/scrape_yageo.py --limit 500
    python vendors/yageo/tools/scrape_yageo.py --output-dir /tmp/yageo

Re-runs are intended to be infrequent (matching Murata's
``fetch_gcm_pim.py`` workflow). The CSVs are checked in so the
build doesn't depend on network access.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.normpath(os.path.join(HERE, ".."))

DEFAULT_BASE_PART_ENDPOINT = "https://yageogroup.com/search/query/base-part/"
DEFAULT_BP_FILTER_ENDPOINT = "https://yageogroup.com/search/query/bp-filter/"

DEFAULT_LIMIT = 1000  # endpoint accepts >1000 fine; 1000 keeps each
                      # response under a few MB and well inside the
                      # default urllib socket timeout.

# (series_id, family_label, output_filename)
FAMILIES: tuple[tuple[int, str, str], ...] = (
    (24261,  "rc", "rc_parts.csv"),
    (373927, "ac", "ac_parts.csv"),
    (24279,  "rt", "rt_parts.csv"),
)

CSV_HEADERS = [
    "mpn", "size_code", "resistance_ohms", "tolerance", "tcr",
    "power_w", "voltage_v", "temp_min_c", "temp_max_c",
    "length_mm", "width_mm", "height_mm",
]

# Pull these PIM parameter names off each base-part record. Yageo
# duplicates some of the same values under different parameter names
# (e.g. raw "Resistance Tolerance" + "Compare ..." numerics);
# we always prefer the "Compare *" numeric fields where available
# because they're already SI-normalised, falling back to the
# human-formatted string fields where the comparator is missing.
PIM_FIELD_MAP = {
    "Resistance (Resistors)":              "resistance_ohms",
    "Resistance Tolerance":                "tolerance",
    "Temperature Coefficient (Resistors)": "tcr",
    "Compare Power":                       "power_w",
    "Compare Voltage DC":                  "voltage_v",
    "Compare Temperature Minimum":         "temp_min_c",
    "Compare Temperature Maximum":         "temp_max_c",
    "Compare Length":                      "length_mm_raw",  # in metres
    "Compare Thickness":                   "height_mm_raw",  # in metres
    "W":                                   "width_mm_str",   # "0.2mm +/-0.02mm"
}


# Yageo ships a 4-digit size-prefix as the first numeric block of
# every base-part MPN (RC0402..., AC0805..., RT0201...). The
# prefix-extractor below is intentionally permissive about the
# leading two letters so the same code path works for all three
# series; the family build scripts cross-check against the size
# they're actually configured for.
_MPN_SIZE_RE = re.compile(r"^[A-Za-z]{2}(\d{4})")

# "0.2mm +/-0.02mm" -> 0.2; tolerant of "0.2mm" alone.
_W_NOMINAL_RE = re.compile(r"^\s*([\d.]+)\s*mm")


def build_payload(series_id: int, *, limit: int, offset: int) -> dict:
    """Construct the JSON payload Yageo's base-part endpoint expects.
    Mirrors the body the SPA (yageogroup.com) sends; field names and
    order are matched exactly because the backend rejects unknown
    keys with HTTP 400."""
    return {
        "1":         1605,            # product category: Resistors
        "3":         [series_id],     # series filter
        "stock":     True,
        "asc":       "",
        "desc":      "",
        "limit":     limit,
        "offset":    offset,
        "isNumeric": False,
    }


def encode_query(payload: dict) -> str:
    """URL-encode the JSON body the way the SPA does -- as a URL
    PATH segment (not a query parameter), so the percent-encoding
    has to escape the JSON braces / colons too. ``urllib.parse.quote``
    with the default safe='/' over a single-line JSON dump matches
    the SPA's encoding byte-for-byte."""
    return urllib.parse.quote(json.dumps(payload, separators=(",", ":")))


def fetch_count(series_id: int, endpoint: str, *, timeout: float) -> int:
    """Return the in-stock count for a single series, used to size
    the pagination loop and as a sanity check after the walk
    finishes."""
    payload = {"1": 1605, "3": [series_id], "stock": True}
    url = endpoint + encode_query(payload)
    req = urllib.request.Request(
        url,
        headers={
            # Mirror the SPA's request headers so any future
            # Cloudflare / WAF tightening that fingerprints UA + Referer
            # doesn't lock us out unexpectedly.
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            ),
            "Accept":  "application/json, */*",
            "Referer": "https://yageogroup.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return int(data.get("counts", 0))


def fetch_page(
    series_id: int,
    *,
    limit: int,
    offset: int,
    endpoint: str,
    timeout: float,
) -> list:
    """Fetch one page of base-part records. Returns a list of dicts
    (length up to ``limit``), the same JSON shape Yageo's PIM emits."""
    url = endpoint + encode_query(build_payload(series_id, limit=limit, offset=offset))
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            ),
            "Accept":  "application/json, */*",
            "Referer": "https://yageogroup.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def extract_record(part: dict) -> dict | None:
    """Convert one Yageo base-part JSON record into a flat dict
    keyed by :data:`CSV_HEADERS`. Returns ``None`` if the MPN has no
    parseable size prefix (the family build scripts can't place it
    anyway, so dropping it here keeps the CSV tight)."""
    mpn = part.get("displayPn") or part.get("basePn") or ""
    if not mpn:
        return None
    m = _MPN_SIZE_RE.match(mpn)
    if not m:
        return None
    size_code = m.group(1)

    raw: dict[str, str] = {k: "" for k in CSV_HEADERS}
    raw["mpn"] = mpn
    raw["size_code"] = size_code

    for pv in part.get("parameterValues") or []:
        name = pv.get("parameterName")
        target = PIM_FIELD_MAP.get(name)
        if not target:
            continue
        # Use the raw `value` for numerics (already SI-normalised),
        # fall back to formattedValue for strings.
        v = pv.get("value")
        if v is None or v == "":
            v = pv.get("formattedValue", "")
        raw[target] = str(v)

    # Yageo's PIM emits "Compare Length" / "Compare Thickness" in metres
    # (e.g. 0.0004 for the 0.4 mm of an 01005 chip). Convert to mm
    # for the CSV.
    length_mm_raw = raw.pop("length_mm_raw", "")
    height_mm_raw = raw.pop("height_mm_raw", "")
    if length_mm_raw:
        try:
            raw["length_mm"] = f"{float(length_mm_raw) * 1000:g}"
        except ValueError:
            raw["length_mm"] = ""
    if height_mm_raw:
        try:
            raw["height_mm"] = f"{float(height_mm_raw) * 1000:g}"
        except ValueError:
            raw["height_mm"] = ""

    # Width comes in as "0.2mm +/-0.02mm" -- pull the leading nominal.
    width_str = raw.pop("width_mm_str", "")
    m = _W_NOMINAL_RE.match(width_str)
    raw["width_mm"] = m.group(1) if m else ""

    return raw


def scrape_family(
    series_id: int,
    *,
    label: str,
    limit: int,
    endpoint: str,
    bp_filter_endpoint: str,
    timeout: float,
    sleep_between_pages: float,
) -> list[dict]:
    """Walk every page of one series until exhausted. Returns the
    full flattened record list. Sleeps between pages so we don't
    hammer the public endpoint."""
    expected = fetch_count(series_id, bp_filter_endpoint, timeout=timeout)
    print(
        f"[{label}] expected {expected:,} in-stock parts "
        f"(series_id={series_id}, limit={limit})",
        file=sys.stderr,
    )

    out: list[dict] = []
    offset = 0
    page_idx = 0
    while True:
        page_idx += 1
        t0 = time.time()
        page = fetch_page(
            series_id,
            limit=limit,
            offset=offset,
            endpoint=endpoint,
            timeout=timeout,
        )
        elapsed = time.time() - t0
        n = len(page)
        print(
            f"[{label}] page {page_idx}: offset={offset:6d} got {n:5d} parts "
            f"in {elapsed:5.1f}s",
            file=sys.stderr,
        )
        for p in page:
            rec = extract_record(p)
            if rec is not None:
                out.append(rec)
        if n < limit:
            # Backend exhausted -- last partial page (or single page
            # smaller than `limit`) marks the end of the catalogue.
            break
        offset += limit
        if sleep_between_pages > 0:
            time.sleep(sleep_between_pages)

    print(
        f"[{label}] done: scraped {len(out):,} parts "
        f"(expected {expected:,})",
        file=sys.stderr,
    )
    if expected and abs(len(out) - expected) > expected * 0.01:
        # >1% drift between the count probe and the walked total
        # is unusual enough to warn about; could mean the catalogue
        # changed mid-scrape (a part went out of stock) or that
        # we're hitting a parameterless edge case.
        print(
            f"[{label}] WARNING: scraped {len(out)} parts vs expected "
            f"{expected} (drift > 1%)",
            file=sys.stderr,
        )
    return out


def write_csv(rows: Iterable[dict], path: str) -> int:
    """Write ``rows`` (each a dict keyed by :data:`CSV_HEADERS`) to a
    UTF-8 CSV file at ``path``, using the LF line terminator that
    every other generated file in this repo uses. Returns the row
    count actually written.

    De-dupes on ``mpn`` so a part that appears on the boundary of two
    pages (rare, but possible if Yageo re-paginates between requests)
    only lands once. Sort order matches Yageo's default backend
    ordering by base-part id, which we preserve by appending
    in scrape order.
    """
    seen_mpns: set[str] = set()
    n = 0
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(
            f, fieldnames=CSV_HEADERS, extrasaction="ignore", lineterminator="\n",
        )
        w.writeheader()
        for r in rows:
            mpn = r.get("mpn")
            if not mpn or mpn in seen_mpns:
                continue
            seen_mpns.add(mpn)
            w.writerow(r)
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--family",
        action="append",
        choices=[f[1] for f in FAMILIES],
        help="Restrict the scrape to one family (repeatable). "
             "Default: scrape all three (rc, ac, rt).",
    )
    ap.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Parent directory for the per-family CSVs; each family "
             "writes to <output-dir>/<family>/<family>_parts.csv. "
             "Defaults to vendors/yageo/ next to this tool.",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Page size; default {DEFAULT_LIMIT}.",
    )
    ap.add_argument(
        "--endpoint",
        default=DEFAULT_BASE_PART_ENDPOINT,
        help="Override the base-part endpoint URL (rarely needed).",
    )
    ap.add_argument(
        "--bp-filter-endpoint",
        default=DEFAULT_BP_FILTER_ENDPOINT,
        help="Override the bp-filter (count probe) endpoint URL.",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-request timeout in seconds (default 120).",
    )
    ap.add_argument(
        "--sleep",
        type=float,
        default=0.25,
        help="Seconds to sleep between paginated requests; keeps the "
             "scrape gentle on the public endpoint (default 0.25).",
    )
    args = ap.parse_args()

    selected = (
        FAMILIES if not args.family
        else tuple(f for f in FAMILIES if f[1] in args.family)
    )

    overall_t0 = time.time()
    rc = 0
    for series_id, label, filename in selected:
        try:
            rows = scrape_family(
                series_id,
                label=label,
                limit=args.limit,
                endpoint=args.endpoint,
                bp_filter_endpoint=args.bp_filter_endpoint,
                timeout=args.timeout,
                sleep_between_pages=args.sleep,
            )
        except urllib.error.HTTPError as e:
            print(f"[{label}] HTTP {e.code} {e.reason}", file=sys.stderr)
            try:
                print(e.read().decode("utf-8", errors="replace")[:500], file=sys.stderr)
            except Exception:
                pass
            rc = 1
            continue
        except urllib.error.URLError as e:
            print(f"[{label}] connection error: {e.reason}", file=sys.stderr)
            rc = 2
            continue

        out_path = os.path.join(args.output_dir, label, filename)
        n = write_csv(rows, out_path)
        print(
            f"[{label}] wrote {out_path}: {n:,} unique MPNs",
            file=sys.stderr,
        )

    print(
        f"All done in {time.time() - overall_t0:.1f}s.",
        file=sys.stderr,
    )
    return rc


if __name__ == "__main__":
    sys.exit(main())
