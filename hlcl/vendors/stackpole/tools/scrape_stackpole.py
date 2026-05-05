#!/usr/bin/env python
"""
Pull the in-stock orderable-parts list for the two Stackpole resistor
families we carry (RMCF = general-purpose thick film, RNCF = precision
thin film) from the public Stackpole Electronics product search
backend (``www.seielect.com``), and write one CSV per family to its
sibling ``../<rmcf|rncf>/<rmcf|rncf>_parts.csv``.

Stackpole's public product search site is a server-side jQuery page
that drives a DataTables-backed grid against a small set of
``/parametrics/*`` JSON endpoints. The two we use:

  - ``/parametrics/getcols``   - column metadata for one product type
                                  (parameter ids -> human labels).
  - ``/parametrics/partsearch`` - paginated DataTables-style payload
                                  with one row per orderable MPN; the
                                  request takes a JSON-stringified
                                  filter set and a DataTables
                                  ``start``/``length`` cursor.

Filter the search by ``imtypeid`` (product-type id) plus
``IMOnlyInStock=1`` for stocked-only results. Stackpole's
``imtypeid`` values for our two targets, discovered by the
``/uidata/specfinder/RMCF/0/2`` (and RNCF) endpoint:

    RMCF: 13     (general-purpose thick film, ``RMCF/RMCP`` series)
    RNCF: 161    (precision thin film, ``RNCF`` series)

In-stock counts at the time this scraper was first run (May 2026):

    RMCF: ~4.8k    RNCF: ~340

This tool requires no API key and no headless browser. The endpoint
returns plain JSON (with the column names as ``@oid<n>`` flat keys
plus a few ``@PartDesc`` / ``@StockPosition`` / ``@webDesc`` etc.
metadata fields). We resolve the ``@oid<n>`` -> column-name mapping
at runtime by calling ``/parametrics/getcols`` once per family, so
if Stackpole renumbers their parameter ids the scraper continues
to work without code changes.

Output schema (one row per stocked Stackpole MPN, UTF-8 CSV with
header):

    mpn,size,resistance_ohms,tolerance,tcr,power_w,
    voltage_v,overload_voltage_v,temp_min_c,temp_max_c,aecq200

The columns are documented in ``vendors/stackpole/_stackpole_common.py``
(module docstring); ``size`` is already the EIA case (``"01005"``,
``"0201"``, ``"0402"``, ...) and is the lookup key the family build
scripts use against
:data:`vendors.stackpole._stackpole_common.SIZE_TO_FOOTPRINT_THICK` /
:data:`SIZE_TO_FOOTPRINT_THIN`.

Usage:

    python vendors/stackpole/tools/scrape_stackpole.py
    python vendors/stackpole/tools/scrape_stackpole.py --family rmcf
    python vendors/stackpole/tools/scrape_stackpole.py --page-size 200
    python vendors/stackpole/tools/scrape_stackpole.py --output-dir /tmp/sei

Re-runs are intended to be infrequent (matching Yageo's
``scrape_yageo.py`` workflow). The CSVs are checked in so the
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

DEFAULT_PARTSEARCH_ENDPOINT = "https://www.seielect.com/parametrics/partsearch"
DEFAULT_GETCOLS_ENDPOINT = "https://www.seielect.com/parametrics/getcols"

# DataTables-style page size. The endpoint accepts large pages comfortably;
# 500 keeps each response under ~1.5 MB and well inside the default urllib
# socket timeout, while finishing each family in a handful of round-trips.
DEFAULT_PAGE_SIZE = 500

# (imtypeid, family_label, output_filename, technology_for_labels)
FAMILIES: tuple[tuple[int, str, str, str], ...] = (
    (13,  "rmcf", "rmcf_parts.csv", "Thick Film General Purpose"),
    (161, "rncf", "rncf_parts.csv", "Thin Film Precision"),
)

CSV_HEADERS = [
    "mpn", "size",
    "resistance_ohms", "tolerance", "tcr",
    "power_w", "voltage_v", "overload_voltage_v",
    "temp_min_c", "temp_max_c",
    "aecq200",
]

# Names of the parametric columns we pull off each row, keyed by the
# human-readable title returned by /parametrics/getcols. The actual
# @oid<n> integer changes if Stackpole renumbers their PIM parameters
# (it last shipped as: 11=Size, 47=Ohmic Value, 10=Tolerance, 3=TCR,
# 1=Power, 36=Max Working V, 37=Max Overload V, 57=Op Temp Range,
# 80=AECQ200). We resolve names -> oids at runtime so the scraper
# survives an upstream renumbering.
PARAM_TITLE_MAP: dict[str, str] = {
    "Size":                          "size",
    "Ohmic Value":                   "resistance_ohms",
    "Tolerance":                     "tolerance",
    "TCR":                           "tcr",
    "Power Rating (watts)":          "power_w",
    "Max Working Voltage":           "voltage_v",
    "Max Overload Voltage":          "overload_voltage_v",
    "Operating Temperature Range":   "temp_range",
    "AECQ200":                       "aecq200",
}

_TEMP_RANGE_RE = re.compile(r"\s*(-?\d+)\s*to\s*\+?(-?\d+)\s*", re.IGNORECASE)

# Stock-position values arrive as comma-grouped strings ("1,310,000");
# we don't store them in the CSV (the build scripts don't filter by
# absolute stock level), but we sanity-check in the run summary.
_THOUSANDS_RE = re.compile(r"[, ]")

_HEADERS = {
    # Mirror the request headers a logged-out browser sends. Without
    # a plausible UA + Referer the WAF in front of seielect.com
    # intermittently 503s with "The request is blocked." -- the
    # site tolerates well-formed scraping at low rates, so the rest
    # of the polite-scraping behaviour (page-size cap, sleep, retry)
    # is just defensive.
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept":  "application/json, text/javascript, */*; q=0.01",
    "Accept-Language":   "en-US,en;q=0.9",
    "Referer":           "https://www.seielect.com/index.html",
    "X-Requested-With":  "XMLHttpRequest",
    "Origin":            "https://www.seielect.com",
}


def _post_json(url: str, body: dict, *, timeout: float) -> dict:
    """POST a JSON body to ``url`` and return the decoded JSON
    response. Used for the ``/parametrics/getcols`` call which
    expects a real JSON request body."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={**_HEADERS, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _post_form(url: str, fields: dict, *, timeout: float) -> dict:
    """POST a form-urlencoded body (DataTables-style) and return
    the decoded JSON response. Used for ``/parametrics/partsearch``."""
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            **_HEADERS,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_oid_map(
    imtypeid: int,
    *,
    endpoint: str,
    timeout: float,
) -> dict[str, str]:
    """Resolve the ``@oid<n>`` JSON keys we care about to their
    canonical CSV column names.

    The returned dict maps ``"@oid<n>"`` -> CSV-column name (e.g.
    ``"size"``, ``"resistance_ohms"``). Only columns named in
    :data:`PARAM_TITLE_MAP` are included.
    """
    body = {
        "objectids":     [],
        "imtypeid":      [{"id": str(imtypeid)}],
        "imtechid":      [],
        "imcatid":       [],
        "imcommcode":    [],
        "IMOnlyInStock": "1",
    }
    resp = _post_json(endpoint, body, timeout=timeout)
    cols_json = (resp.get("apiResult") or {}).get("columns")
    if not cols_json:
        raise RuntimeError(
            f"getcols returned no columns for imtypeid={imtypeid}: {resp!r}"
        )
    cols = json.loads(cols_json)
    oid_map: dict[str, str] = {}
    for c in cols:
        title = c.get("title", "")
        oid = c.get("data", "")
        target = PARAM_TITLE_MAP.get(title)
        if target and oid.startswith("@oid"):
            oid_map[oid] = target
    return oid_map


def fetch_page(
    imtypeid: int,
    *,
    start: int,
    length: int,
    endpoint: str,
    timeout: float,
    draw: int,
) -> dict:
    """Fetch one DataTables page of in-stock parts for one product
    type. The response shape is ``{draw, recordsTotal, recordsFiltered,
    data: [...]}``."""
    fields = {
        "objectids":     "[]",
        "imcatid":       "[]",
        "imtypeid":      json.dumps([{"id": str(imtypeid)}]),
        "imtechid":      "[]",
        "imcommcode":    "[]",
        "IMOnlyInStock": "1",
        "draw":          str(draw),
        "start":         str(start),
        "length":        str(length),
    }
    return _post_form(endpoint, fields, timeout=timeout)


def extract_record(
    row: dict,
    *,
    oid_map: dict[str, str],
) -> dict | None:
    """Convert one parametric-search JSON row into a flat dict keyed
    by :data:`CSV_HEADERS`. Returns ``None`` if the MPN field is
    missing (defensive -- the endpoint always populates ``@PartDesc``
    in practice)."""
    mpn = (row.get("@PartDesc") or "").strip()
    if not mpn:
        return None

    raw: dict[str, str] = {k: "" for k in CSV_HEADERS}
    raw["mpn"] = mpn

    for oid, target in oid_map.items():
        v = row.get(oid)
        if v is None:
            continue
        raw[target] = str(v).strip()

    # Operating-temperature range arrives as one cell ("-55 to +155");
    # split into the two columns the build scripts read.
    temp_range = raw.pop("temp_range", "")
    m = _TEMP_RANGE_RE.match(temp_range)
    if m:
        raw["temp_min_c"] = m.group(1)
        raw["temp_max_c"] = m.group(2)

    return raw


def scrape_family(
    imtypeid: int,
    *,
    label: str,
    page_size: int,
    partsearch_endpoint: str,
    getcols_endpoint: str,
    timeout: float,
    sleep_between_pages: float,
) -> list[dict]:
    """Walk every DataTables page of one product type until exhausted.
    Returns the full flattened record list. Sleeps between pages so
    we don't hammer the public endpoint."""
    oid_map = fetch_oid_map(
        imtypeid, endpoint=getcols_endpoint, timeout=timeout,
    )
    print(
        f"[{label}] resolved {len(oid_map)} parameter columns: "
        f"{', '.join(sorted(oid_map.values()))}",
        file=sys.stderr,
    )

    out: list[dict] = []
    start = 0
    page_idx = 0
    expected = 0
    while True:
        page_idx += 1
        t0 = time.time()
        page = fetch_page(
            imtypeid,
            start=start,
            length=page_size,
            endpoint=partsearch_endpoint,
            timeout=timeout,
            draw=page_idx,
        )
        elapsed = time.time() - t0
        rows = page.get("data") or []
        n = len(rows)
        if page_idx == 1:
            try:
                expected = int(page.get("recordsTotal") or 0)
            except (TypeError, ValueError):
                expected = 0
            print(
                f"[{label}] expected {expected:,} in-stock parts "
                f"(imtypeid={imtypeid}, page_size={page_size})",
                file=sys.stderr,
            )
        print(
            f"[{label}] page {page_idx}: start={start:6d} got {n:5d} parts "
            f"in {elapsed:5.1f}s",
            file=sys.stderr,
        )
        for r in rows:
            rec = extract_record(r, oid_map=oid_map)
            if rec is not None:
                out.append(rec)
        if n < page_size:
            break
        start += page_size
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
        # changed mid-scrape or that we're hitting a parameterless
        # edge case.
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

    De-dupes on ``mpn`` so a part that appears on the boundary of
    two pages (rare, but possible if Stackpole re-paginates between
    requests) only lands once. Sort order matches Stackpole's default
    backend ordering, which we preserve by appending in scrape order.
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
             "Default: scrape both (rmcf, rncf).",
    )
    ap.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Parent directory for the per-family CSVs; each family "
             "writes to <output-dir>/<family>/<family>_parts.csv. "
             "Defaults to vendors/stackpole/ next to this tool.",
    )
    ap.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"DataTables page length; default {DEFAULT_PAGE_SIZE}.",
    )
    ap.add_argument(
        "--partsearch-endpoint",
        default=DEFAULT_PARTSEARCH_ENDPOINT,
        help="Override the partsearch endpoint URL (rarely needed).",
    )
    ap.add_argument(
        "--getcols-endpoint",
        default=DEFAULT_GETCOLS_ENDPOINT,
        help="Override the getcols (column metadata) endpoint URL.",
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
        default=0.5,
        help="Seconds to sleep between paginated requests; keeps the "
             "scrape gentle on the public endpoint (default 0.5).",
    )
    args = ap.parse_args()

    selected = (
        FAMILIES if not args.family
        else tuple(f for f in FAMILIES if f[1] in args.family)
    )

    overall_t0 = time.time()
    rc = 0
    for imtypeid, label, filename, _tech in selected:
        try:
            rows = scrape_family(
                imtypeid,
                label=label,
                page_size=args.page_size,
                partsearch_endpoint=args.partsearch_endpoint,
                getcols_endpoint=args.getcols_endpoint,
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
