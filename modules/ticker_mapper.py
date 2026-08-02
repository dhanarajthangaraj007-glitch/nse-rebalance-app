"""
ticker_mapper.py
----------------
Maps a company name (as extracted from the PDF) to a Yahoo-Finance-style
NSE ticker (e.g. "RELIANCE.NS") using:

  1. An exact-match lookup against a bundled static CSV
     (data/nse_ticker_mapping.csv) covering common Nifty 500 constituents.
  2. A fuzzy-match fallback (difflib) for near-matches caused by OCR/PDF
     text quirks (extra punctuation, "Ltd" vs "Limited", etc).
  3. If nothing is found, the ticker is left blank so the user can fill
     it in manually in the review table before scoring.
"""

from __future__ import annotations

import difflib
import os
import re
from functools import lru_cache
from typing import Optional, Tuple

import pandas as pd

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nse_ticker_mapping.csv")


def _normalize(name: str) -> str:
    """Lowercase, strip common corporate suffixes/punctuation for matching."""
    n = name.lower()
    n = re.sub(r"[.,'’()\-/]", " ", n)
    n = re.sub(r"\b(limited|ltd|the|company|india|co)\b", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


@lru_cache(maxsize=1)
def load_mapping_table() -> pd.DataFrame:
    """Load and pre-normalize the static ticker mapping CSV (cached)."""
    df = pd.read_csv(_DATA_PATH)
    df["norm_name"] = df["company_name"].apply(_normalize)
    return df


def map_company_to_ticker(company_name: str, cutoff: float = 0.72) -> Tuple[Optional[str], float]:
    """Return (ticker, confidence) for a given company name.

    confidence is 1.0 for an exact normalized match, otherwise the
    difflib similarity ratio of the best fuzzy match (0-1). Returns
    (None, 0.0) if nothing clears the `cutoff` threshold.
    """
    table = load_mapping_table()
    norm_input = _normalize(company_name)

    # 1) Exact normalized match
    exact = table[table["norm_name"] == norm_input]
    if not exact.empty:
        return exact.iloc[0]["ticker"], 1.0

    # 2) Fuzzy match across all known normalized names
    choices = table["norm_name"].tolist()
    best = difflib.get_close_matches(norm_input, choices, n=1, cutoff=cutoff)
    if best:
        match_row = table[table["norm_name"] == best[0]].iloc[0]
        ratio = difflib.SequenceMatcher(None, norm_input, best[0]).ratio()
        return match_row["ticker"], round(ratio, 2)

    return None, 0.0


def bulk_map(company_names: list) -> pd.DataFrame:
    """Map a list of company names to tickers; returns a DataFrame with
    columns: company_name, ticker, match_confidence.
    """
    rows = []
    for name in company_names:
        ticker, conf = map_company_to_ticker(name)
        rows.append({"company_name": name, "ticker": ticker or "", "match_confidence": conf})
    return pd.DataFrame(rows)
