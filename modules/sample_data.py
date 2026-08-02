"""
sample_data.py
--------------
A small, illustrative "rebalancing result" used when the user clicks
"Try bundled sample data" instead of uploading a PDF. This lets a
reviewer see the full dashboard flow immediately.

The company names intentionally include:
  - Exact matches to data/nse_ticker_mapping.csv (to demo confidence=1.0)
  - One loosely-formatted name (to demo the fuzzy matcher)
  - One unmapped/fictional name (to demo the manual-review safety net)

This is illustrative sample data only, not a real NSE announcement.
"""

from modules.pdf_parser import IndexChanges


def get_sample_indices():
    return {
        "Nifty 50": IndexChanges(
            inclusions=["Jio Financial Services Limited", "Adani Power Limited"],
            exclusions=["Divi's Laboratories Limited", "Bharat Petroleum Corporation Limited"],
        ),
        "Nifty Next 50": IndexChanges(
            inclusions=["Waaree Energies Limited", "Premier Energies Limited", "TATA ELXSI LTD."],
            exclusions=["Jio Financial Services Limited"],
        ),
        "Nifty Midcap 150": IndexChanges(
            inclusions=["Sona BLW Precision Forgings Limited", "Sample Innovations Ltd"],
            exclusions=["Craftsman Automation Limited"],
        ),
    }
