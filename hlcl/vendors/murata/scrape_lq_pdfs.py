#!/usr/bin/env python
"""
Refresh ``vendors/murata/lqm/lqm_parts.csv`` and
``vendors/murata/lqw/lqw_parts.csv`` from Murata's per-subseries
specification PDFs.

WHY THIS PATH (AND NOT THE PIM CSV API LIKE GCM/GRM)
------------------------------------------------------

The shared ``vendors/murata/fetch_gcm_pim.py`` driver hits Murata's
public PIM CSV endpoint at
``https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers``.
For ceramic capacitors that endpoint still returns a parametric CSV;
for inductors it currently 500s with the request body echoed back in
the response (Murata's own ``pim4-prd-products-sapi`` upstream is
locally closed -- confirmed by hitting the sibling
``products/search/part-number-suggestions`` endpoint and getting a
matching backend-failure JSON). The v2 endpoint at
``/public/api/pim/v2/...`` works but requires a registered API key
(see https://www.murata.com/en-global/support/api/v2), which we don't
ask the user to obtain.

What does work, completely unauthenticated, is the per-subseries
"reference specification" PDF Murata serves out of S3 at
``https://pim.murata.com/asset/pim4/inductor/<JELF_id>_PDF_INDUCTOR``.
Every subseries (e.g. LQM21PN_GE = JELF243B-0089, LQW18AN_00 =
JELF243A-0024) has one of these PDFs, each carrying the full ratings
table for every orderable MPN in that subseries (5-100 rows per
subseries; ~3000 orderable MPNs for LQM and ~2500 for LQW combined
across all subseries).

The mapping ``subseries -> JELF id`` lives in Murata's HTML lineup
pages, which ARE server-side rendered. So this scraper has two
phases:

    Phase 1: Crawl the lineup pages and extract a
             ``[(subseries, jelf_id), ...]`` list, filtering to
             LQM* / LQW*.

    Phase 2: For each (subseries, jelf_id), download the PDF, extract
             the part rows with pypdf, and write one CSV row per
             orderable MPN.

Output schemas (one row per orderable Murata MPN we carry):

    vendors/murata/lqm/lqm_parts.csv
    vendors/murata/lqw/lqw_parts.csv
        subseries,mpn,operating_temp_min_c,operating_temp_max_c,
        jelf_id,tokens

``tokens`` is the pipe-joined list of post-MPN whitespace tokens
exactly as they appear on the part's row in the spec PDF. Murata
prints LQM_ and LQW_ ratings tables in at least four flavours
(commercial vs AEC-Q200, with vs without separate L-change /
temperature-rise rated-current columns, with vs without an inline
DCR-tolerance band, etc.), so the per-family build scripts decode
the columns themselves -- they know which subseries to expect what
schema for. Doing the decode there rather than here keeps this
scraper resilient to Murata adding new column flavours.

Inductance value and tolerance are not stored in the CSV: both are
unambiguously encoded in the orderable MPN (Murata documents the
mapping in ``reference/murata_part_numbering.pdf``), and the build
scripts decode them straight from ``mpn`` rather than relying on
the PDF table values, which are sometimes printed with subtle
typographical inconsistencies (mixed full-width vs ASCII colons,
``±20`` vs ``±20%``, etc.) that are unsafe to depend on.

Usage:
    python hlcl/vendors/murata/scrape_lq_pdfs.py

Reruns are cheap thanks to a per-PDF disk cache under
``vendors/murata/.pdf_cache/``. Pass ``--refresh`` to bypass the
cache and re-download every PDF.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Iterable

import pypdf

HERE = os.path.dirname(os.path.abspath(__file__))
LQM_DIR = os.path.join(HERE, "lqm")
LQW_DIR = os.path.join(HERE, "lqw")
PDF_CACHE_DIR = os.path.join(HERE, ".pdf_cache")

LQM_CSV = os.path.join(LQM_DIR, "lqm_parts.csv")
LQW_CSV = os.path.join(LQW_DIR, "lqw_parts.csv")

# Lineup pages we crawl. Murata's inductor catalogue groups subseries
# by application (Power Inductors -> LQM/LQH; RF chip inductors ->
# LQW/LQP/LQG/LQB). Within each application bucket, "pi1"/"rf1" =
# commercial parts, "pi2"/"rf2"/"rf3" = automotive (AEC-Q200) variants.
# pi3 / pi4 are curated marketing lineups that link to the PIM SPA
# rather than per-subseries PDFs, so we skip them -- pi1 / pi2 already
# cover every subseries pi3 / pi4 highlight.
LINEUP_URLS = [
    "https://www.murata.com/en-us/products/inductor/power/overview/lineup/pi1",
    "https://www.murata.com/en-us/products/inductor/power/overview/lineup/pi2",
    "https://www.murata.com/en-us/products/inductor/chip/overview/lineup/rf1",
    "https://www.murata.com/en-us/products/inductor/chip/overview/lineup/rf2",
    "https://www.murata.com/en-us/products/inductor/chip/overview/lineup/rf3",
]

ASSET_URL_FMT = "https://pim.murata.com/asset/pim4/inductor/{jelf_id}_PDF_INDUCTOR"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36"
)

# One row per orderable MPN: leading whitespace, the MPN itself,
# whitespace, then a tail of whitespace-separated numeric / textual
# columns specific to the subseries. We capture (mpn, tail) and let
# the build script decode the tail.
_LQ_ROW_RE = re.compile(r"^\s*(LQ[MW][0-9A-Z]+)\s+(\S.*?)\s*$")
# Murata's "Operating temperature range" header line on page 1 of every
# subseries PDF; we lift the bounds from there so the per-family
# build script can emit a `Tr` column without re-reading the PDF.
_LQ_TR_RE = re.compile(
    r"Operating temperature range\s*(-?\d+)\s*°?C\s*to\s*\+?(-?\d+)\s*°?C",
    re.IGNORECASE,
)
# Skip the obvious non-data lines that happen to start with an LQM_ /
# LQW_ token (the introduction "applies to chip coil LQM21PN_GE
# series" line, and the spec-doc header that prints the masked
# subseries id). These don't have post-MPN numeric tails so the row
# regex would still extract garbage; cheaper to filter early.
_NON_DATA_HINTS = ("REFERENCE", "Spec No", "applies to", "Murata Standard")


# ---------------------------------------------------------------------------
# Phase 1: lineup-page crawl
# ---------------------------------------------------------------------------

def fetch_url(url: str, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def extract_subseries_jelf_pairs(html: str) -> list[tuple[str, str]]:
    """Return ``[(subseries_with_suffix, jelf_id), ...]`` for one lineup
    page. Each ``<tr>`` typically pairs one fully-qualified subseries
    identifier (e.g. ``LQM21PN_GE``) with one ``JELF...`` PDF link, but
    a few rows list multiple subseries that share a PDF (e.g.
    ``LQM2HPZ_GC`` and ``LQM2HPZ_GS`` both pointing at JELF243B-9112);
    we emit one tuple per subseries in those rows so the per-subseries
    enumeration downstream is a flat list.

    Subseries names without a ``_suffix`` (the bare LQM21PN /
    LQW04AN family-ancestor labels that appear as table-cell headers
    next to the suffixed rows) are dropped, so we don't emit duplicate
    rows for the same JELF under both the ancestor name and its
    qualified child."""
    out: list[tuple[str, str]] = []
    # Murata's lineup tables put one subseries+JELF per <tr>. Splitting
    # on the row tag and walking the chunks is robust enough.
    for chunk in re.split(r"<tr[^>]*>", html):
        pdfs = re.findall(r"JELF[0-9A-Z_-]+_PDF_INDUCTOR", chunk)
        if not pdfs:
            continue
        # Subseries id pattern: LQ + family letter + size digits +
        # type letters + a mandatory ``_suffix``. The leading ``\b``
        # is fine; the trailing ``\b`` works because ``[0-9A-Z]`` ends
        # on a word character regardless of the next char.
        subs = sorted(
            set(re.findall(r"\bLQ[A-Z][0-9]+[A-Z]+_[0-9A-Z]+\b", chunk))
        )
        for s in subs:
            for pdf in pdfs:
                jelf_id = pdf.removesuffix("_PDF_INDUCTOR")
                out.append((s, jelf_id))
    return out


def crawl_lineup_pages() -> dict[str, list[str]]:
    """Return ``{ subseries: [jelf_id, ...], ... }`` aggregated across
    every lineup page in :data:`LINEUP_URLS`. Some subseries appear in
    both pi1 and pi2 (commercial + AEC variants share the same
    subseries name with different ``_suffix``); we keep all pairs."""
    all_pairs: list[tuple[str, str]] = []
    for url in LINEUP_URLS:
        print(f"  [lineup] {url}", file=sys.stderr)
        html = fetch_url(url).decode("utf-8", errors="replace")
        pairs = extract_subseries_jelf_pairs(html)
        print(f"    -> {len(pairs)} (subseries, JELF) pairs", file=sys.stderr)
        all_pairs.extend(pairs)
    bucket: dict[str, list[str]] = {}
    for sub, jelf_id in all_pairs:
        bucket.setdefault(sub, []).append(jelf_id)
    # Dedup JELF ids per subseries, preserve insertion order.
    for sub, ids in bucket.items():
        seen = set()
        deduped: list[str] = []
        for j in ids:
            if j not in seen:
                deduped.append(j)
                seen.add(j)
        bucket[sub] = deduped
    return bucket


# ---------------------------------------------------------------------------
# Phase 2: per-PDF parts extraction
# ---------------------------------------------------------------------------

def cached_pdf(jelf_id: str, refresh: bool = False) -> bytes:
    """Return the PDF body, caching to ``.pdf_cache/<jelf_id>.pdf``."""
    os.makedirs(PDF_CACHE_DIR, exist_ok=True)
    path = os.path.join(PDF_CACHE_DIR, f"{jelf_id}.pdf")
    if not refresh and os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            return f.read()
    url = ASSET_URL_FMT.format(jelf_id=jelf_id)
    print(f"    [pdf] GET {url}", file=sys.stderr)
    body = fetch_url(url, timeout=60.0)
    with open(path, "wb") as f:
        f.write(body)
    # Be polite to Murata's CloudFront edge.
    time.sleep(0.25)
    return body


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Concatenate text across every page of ``pdf_bytes`` with newlines.
    The "reference specification" PDFs we read have a tabular layout
    that pypdf reproduces faithfully on text extraction, but the
    column boundaries are spaces of varying widths -- the per-family
    parser splits them downstream."""
    import io
    r = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    chunks = []
    for pg in r.pages:
        try:
            chunks.append(pg.extract_text() or "")
        except Exception:
            # Some Murata PDFs use unusual font encodings that pypdf
            # raises on. Skip the offending page rather than failing
            # the whole subseries.
            chunks.append("")
    return "\n".join(chunks)


def parse_temp_range(text: str) -> tuple[int | None, int | None]:
    """Pull ``(tmin_c, tmax_c)`` out of the spec PDF header. Every
    LQM / LQW PDF carries one ``Operating temperature range -55°C to
    +125°C`` line near the top; the regex handles the ``+``/``-``
    sign on the upper bound and a few stray spaces."""
    m = _LQ_TR_RE.search(text)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def parse_part_row(line: str) -> tuple[str, list[str]] | None:
    """Decode one part-table line into ``(mpn, tail_tokens)`` or
    ``None`` for non-data lines. ``tail_tokens`` is the whitespace-
    split sequence of post-MPN columns exactly as they appear in the
    PDF (so e.g. ``"M ：±20%"`` becomes ``["M", "：±20%"]``); the
    per-family build script knows how to interpret the column
    sequence for each subseries flavour.

    Returns ``None`` for the spec-document header / introduction
    lines that happen to mention an LQM_ / LQW_ token but aren't part
    rows."""
    if not line.strip().startswith(("LQM", "LQW")):
        return None
    if any(hint in line for hint in _NON_DATA_HINTS):
        return None
    m = _LQ_ROW_RE.match(line)
    if not m:
        return None
    return m.group(1), m.group(2).split()


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "subseries", "mpn",
    "operating_temp_min_c", "operating_temp_max_c",
    "jelf_id",
    "tokens",
]


def process_subseries(
    subseries: str, jelf_ids: Iterable[str], *, refresh: bool
) -> list[dict[str, str]]:
    """Return the list of normalised CSV rows for one subseries.
    Within the subseries we dedupe on ``mpn`` so a JELF id that
    appears more than once across the lineup pages doesn't double-
    count its parts."""
    rows_by_mpn: dict[str, dict[str, str]] = {}
    for jelf_id in jelf_ids:
        try:
            pdf_bytes = cached_pdf(jelf_id, refresh=refresh)
        except urllib.error.HTTPError as e:
            print(f"    [warn] HTTP {e.code} on {jelf_id}: {e.reason}", file=sys.stderr)
            continue
        text = extract_pdf_text(pdf_bytes)
        tmin, tmax = parse_temp_range(text)
        for line in text.splitlines():
            parsed = parse_part_row(line)
            if parsed is None:
                continue
            mpn, tail_tokens = parsed
            # Many spec PDFs print the same MPN twice (master table
            # plus an "alternate" row for the bulk-packaging suffix);
            # the second occurrence carries the same data so we keep
            # whichever we saw first.
            if mpn in rows_by_mpn:
                continue
            rows_by_mpn[mpn] = {
                "subseries": subseries,
                "mpn": mpn,
                "operating_temp_min_c": "" if tmin is None else str(tmin),
                "operating_temp_max_c": "" if tmax is None else str(tmax),
                "jelf_id": jelf_id,
                "tokens": "|".join(tail_tokens),
            }
    return list(rows_by_mpn.values())


def write_csv(path: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["subseries"], r["mpn"]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--refresh", action="store_true",
        help="ignore the local PDF cache and re-download every spec PDF",
    )
    args = p.parse_args()

    print("Phase 1: crawling Murata inductor lineup pages...", file=sys.stderr)
    bucket = crawl_lineup_pages()
    lqm_subs = sorted(s for s in bucket if s.startswith("LQM"))
    lqw_subs = sorted(s for s in bucket if s.startswith("LQW"))
    print(
        f"  found {len(lqm_subs)} LQM subseries, "
        f"{len(lqw_subs)} LQW subseries "
        f"({len(bucket)} total LQ-prefixed including LQH/LQP/LQG/LQB).",
        file=sys.stderr,
    )

    print("Phase 2: downloading + parsing per-subseries spec PDFs...", file=sys.stderr)
    lqm_rows: list[dict[str, str]] = []
    for s in lqm_subs:
        n_before = len(lqm_rows)
        lqm_rows.extend(process_subseries(s, bucket[s], refresh=args.refresh))
        print(f"  {s:20s} +{len(lqm_rows) - n_before} parts", file=sys.stderr)
    write_csv(LQM_CSV, CSV_FIELDS, lqm_rows)

    lqw_rows: list[dict[str, str]] = []
    for s in lqw_subs:
        n_before = len(lqw_rows)
        lqw_rows.extend(process_subseries(s, bucket[s], refresh=args.refresh))
        print(f"  {s:20s} +{len(lqw_rows) - n_before} parts", file=sys.stderr)
    write_csv(LQW_CSV, CSV_FIELDS, lqw_rows)

    print(file=sys.stderr)
    print(f"Wrote {LQM_CSV}: {len(lqm_rows)} rows", file=sys.stderr)
    print(f"Wrote {LQW_CSV}: {len(lqw_rows)} rows", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
