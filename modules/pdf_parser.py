"""
pdf_parser.py
-------------
Extracts index names and Inclusion / Exclusion stock lists from an
NSE Indices periodic-review press release PDF.

NSE press releases are not machine-generated in a single fixed layout —
the wording and table structure has changed slightly across years — so
this parser uses a layered strategy and is deliberately defensive:

  1. Extract raw text AND raw tables (pdfplumber) page by page.
  2. Locate "index blocks" by scanning for known index names
     (e.g. "NIFTY 50", "NIFTY NEXT 50", "NIFTY MIDCAP 150" ...).
  3. Within each block, locate "Inclusion" and "Exclusion" sub-sections
     using both table headers and free-text regex fallback.
  4. Clean company names (strip numbering, bullet characters, trailing
     "Ltd."/"Limited" noise) and de-duplicate.

Because real-world PDFs can still trip up any parser, the calling app
(app.py) always shows the extracted rows in an editable table so the
user can correct anything before scoring — this module aims for a high
recall, best-effort extraction rather than perfection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

import pdfplumber


# ---------------------------------------------------------------------------
# Known NSE index names we actively look for. Longer/more specific names are
# listed first so regex alternation matches "NIFTY NEXT 50" before "NIFTY 50"
# when both could otherwise partially match.
# ---------------------------------------------------------------------------
KNOWN_INDICES = [
    "NIFTY NEXT 50",
    "NIFTY MIDCAP 150",
    "NIFTY MIDCAP 50",
    "NIFTY SMALLCAP 250",
    "NIFTY SMALLCAP 50",
    "NIFTY MICROCAP 250",
    "NIFTY LARGEMIDCAP 250",
    "NIFTY MIDSMALLCAP 400",
    "NIFTY100",
    "NIFTY 100",
    "NIFTY 200",
    "NIFTY 500",
    "NIFTY TOTAL MARKET",
    "NIFTY 50",
]

_INDEX_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in KNOWN_INDICES) + r")\b",
    re.IGNORECASE,
)

# Words that signal the start of an inclusion / exclusion sub-section.
_INCLUSION_KEYWORDS = re.compile(r"\b(inclusion|included|addition|entrant)s?\b", re.IGNORECASE)
_EXCLUSION_KEYWORDS = re.compile(r"\b(exclusion|excluded|removal|deletion)s?\b", re.IGNORECASE)

# A line that is almost certainly a company name: starts with an optional
# serial number / bullet, then letters, and is not a pure heading/footer.
_COMPANY_LINE = re.compile(
    r"^\s*(?:\(?\d{1,3}[\).:-]?\s*)?([A-Z][A-Za-z0-9&.,'’()\-/ ]{2,80})\s*$"
)

# Lines to ignore even if they superficially look like a company name.
_NOISE_PATTERNS = [
    re.compile(r"^\s*(sr\.?\s*no\.?|s\.?\s*no\.?|company\s*name|security\s*name)\s*$", re.IGNORECASE),
    re.compile(r"^\s*page\s+\d+", re.IGNORECASE),
    re.compile(r"^\s*nse\s*indices", re.IGNORECASE),
    re.compile(r"^\s*press\s*release", re.IGNORECASE),
    re.compile(r"^\s*w\.?e\.?f\.?", re.IGNORECASE),
    re.compile(r"^\s*effective\s+from", re.IGNORECASE),
    re.compile(r"^\s*note\s*:", re.IGNORECASE),
    re.compile(r"^\s*for\s+further\s+information", re.IGNORECASE),
    re.compile(r"^\s*about\s+nse", re.IGNORECASE),
]


@dataclass
class IndexChanges:
    """Container for the inclusion/exclusion lists of a single index."""
    inclusions: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)


def _is_noise(line: str) -> bool:
    if not line or len(line.strip()) < 3:
        return True
    return any(p.search(line) for p in _NOISE_PATTERNS)


def clean_company_name(raw: str) -> str:
    """Normalize a raw extracted company-name string."""
    name = raw.strip()
    # Strip leading serial numbers / bullets like "12.", "(3)", "-"
    name = re.sub(r"^\s*(?:\(?\d{1,3}[\).:-]?\s*)+", "", name)
    name = re.sub(r"^[•\-–\*]\s*", "", name)
    # Collapse internal whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Normalise common suffixes for consistent downstream matching
    name = re.sub(r"\bLtd\.?$", "Limited", name, flags=re.IGNORECASE)
    return name.strip(" .,")


def extract_text_and_tables(pdf_bytes) -> Dict:
    """Open a PDF (bytes-like/file-like) and return per-page text + tables.

    Returns
    -------
    dict with keys:
        "pages_text": List[str]   - full text per page, in order
        "pages_tables": List[List[List[List[str]]]] - raw tables per page
        "full_text": str          - all page text concatenated
    """
    pages_text: List[str] = []
    pages_tables: List[List] = []

    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            pages_tables.append(tables)

    return {
        "pages_text": pages_text,
        "pages_tables": pages_tables,
        "full_text": "\n".join(pages_text),
    }


def _split_into_index_blocks(full_text: str) -> Dict[str, str]:
    """Split the full document text into chunks, one per detected index name.

    Each block runs from one index-name match to the next (or end of doc),
    so it captures the inclusion/exclusion text that follows that heading.
    """
    matches = list(_INDEX_PATTERN.finditer(full_text))
    blocks: Dict[str, str] = {}

    for i, m in enumerate(matches):
        index_name = _normalize_index_name(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        chunk = full_text[start:end]
        # Merge if the same index name appears in multiple non-contiguous
        # spots (e.g. mentioned in an intro paragraph, then again as a
        # table heading) — concatenate text rather than overwrite.
        blocks[index_name] = blocks.get(index_name, "") + "\n" + chunk

    return blocks


def _normalize_index_name(raw: str) -> str:
    name = re.sub(r"\s+", " ", raw.strip().upper())
    if name == "NIFTY100":
        name = "NIFTY 100"
    return name.title().replace("Nifty", "Nifty").replace("nifty", "Nifty")


def _extract_names_from_block(block_text: str) -> IndexChanges:
    """Given the raw text belonging to one index, split into inclusion vs
    exclusion company-name lists using keyword-anchored sectioning."""

    inc_match = _INCLUSION_KEYWORDS.search(block_text)
    exc_match = _EXCLUSION_KEYWORDS.search(block_text)

    changes = IndexChanges()

    if not inc_match and not exc_match:
        return changes

    # Determine ordering of the two sections so we can slice correctly,
    # since NSE releases sometimes list Exclusion before Inclusion.
    anchors = sorted(
        [(m.start(), "inclusion") for m in [inc_match] if m] +
        [(m.start(), "exclusion") for m in [exc_match] if m]
    )
    anchors.append((len(block_text), "end"))

    for idx in range(len(anchors) - 1):
        start_pos, label = anchors[idx]
        end_pos, _ = anchors[idx + 1]
        segment = block_text[start_pos:end_pos]
        names = _lines_to_company_names(segment)
        if label == "inclusion":
            changes.inclusions.extend(names)
        elif label == "exclusion":
            changes.exclusions.extend(names)

    # De-duplicate while preserving order
    changes.inclusions = list(dict.fromkeys(changes.inclusions))
    changes.exclusions = list(dict.fromkeys(changes.exclusions))
    return changes


def _lines_to_company_names(segment: str) -> List[str]:
    names = []
    for line in segment.splitlines():
        line = line.strip()
        if not line or _is_noise(line):
            continue
        # Skip the keyword line itself (e.g. "Inclusion:" with nothing else)
        if _INCLUSION_KEYWORDS.fullmatch(line.strip(":： ")) or _EXCLUSION_KEYWORDS.fullmatch(line.strip(":： ")):
            continue
        m = _COMPANY_LINE.match(line)
        if m:
            candidate = clean_company_name(m.group(1))
            # Filter out short all-caps section labels that slipped through
            if len(candidate) >= 3 and not candidate.upper() in {"INCLUSION", "EXCLUSION"}:
                names.append(candidate)
    return names


def _extract_from_tables(pages_tables: List[List]) -> Dict[str, IndexChanges]:
    """Secondary strategy: scan extracted tables for columns headed with
    Inclusion/Exclusion-like text, which NSE releases often use.
    Returns a dict keyed by a generic index name placeholder when the
    specific index cannot be determined from the table alone; the caller
    merges this with the text-based results.
    """
    results: Dict[str, IndexChanges] = {}
    for tables in pages_tables:
        for table in tables:
            if not table or len(table) < 2:
                continue
            header = [(cell or "").strip() for cell in table[0]]
            inc_col, exc_col = None, None
            for i, h in enumerate(header):
                if _INCLUSION_KEYWORDS.search(h):
                    inc_col = i
                if _EXCLUSION_KEYWORDS.search(h):
                    exc_col = i
            if inc_col is None and exc_col is None:
                continue

            key = "Unassigned Index"
            changes = results.setdefault(key, IndexChanges())
            for row in table[1:]:
                if inc_col is not None and inc_col < len(row) and row[inc_col]:
                    name = clean_company_name(row[inc_col])
                    if len(name) >= 3:
                        changes.inclusions.append(name)
                if exc_col is not None and exc_col < len(row) and row[exc_col]:
                    name = clean_company_name(row[exc_col])
                    if len(name) >= 3:
                        changes.exclusions.append(name)
    return results


def parse_press_release(pdf_bytes) -> Dict[str, IndexChanges]:
    """Main entry point: parse an NSE press release PDF and return a dict
    mapping index name -> IndexChanges(inclusions, exclusions).
    """
    extracted = extract_text_and_tables(pdf_bytes)
    blocks = _split_into_index_blocks(extracted["full_text"])

    results: Dict[str, IndexChanges] = {}
    for index_name, block_text in blocks.items():
        changes = _extract_names_from_block(block_text)
        if changes.inclusions or changes.exclusions:
            results[index_name] = changes

    # Merge in anything the table-based strategy found that text parsing
    # missed, attaching it under "Unassigned Index" for manual review.
    table_results = _extract_from_tables(extracted["pages_tables"])
    for key, changes in table_results.items():
        if key not in results:
            results[key] = changes
        else:
            results[key].inclusions = list(
                dict.fromkeys(results[key].inclusions + changes.inclusions)
            )
            results[key].exclusions = list(
                dict.fromkeys(results[key].exclusions + changes.exclusions)
            )

    return results
