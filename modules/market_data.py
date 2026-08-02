"""
market_data.py
--------------
Pulls the raw inputs needed for factor scoring from Yahoo Finance via
`yfinance`:

  - 6-month & 12-month total price return
  - Annualized daily-return volatility (for both the momentum
    risk-adjustment and the standalone Low-Volatility factor)
  - Fundamentals: Return on Equity, Debt-to-Equity, EPS growth proxy

All network calls are wrapped in try/except so a single bad ticker
(delisted, mis-mapped, rate-limited) never crashes the whole batch —
it simply falls back to NaN, which the scoring module handles via
cross-sectional median imputation.

Streamlit's `st.cache_data` is used to avoid refetching the same
ticker repeatedly within a session (NSE press releases can list the
same stock across multiple index sections).
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - handled gracefully in the UI
    yf = None

try:
    import streamlit as st
    _cache_data = st.cache_data
except ImportError:  # pragma: no cover - allows unit-testing without Streamlit
    def _cache_data(func=None, **kwargs):
        return func if func else (lambda f: f)


TRADING_DAYS_6M = 126
TRADING_DAYS_12M = 252


@_cache_data(ttl=60 * 60, show_spinner=False)
def fetch_stock_metrics(ticker: str) -> Dict:
    """Fetch price + fundamental raw metrics for a single ticker.

    Returns a dict of raw (un-normalized) metrics. Missing values are
    represented as np.nan so downstream scoring can impute sensibly.
    """
    metrics = {
        "ticker": ticker,
        "return_6m": np.nan,
        "return_12m": np.nan,
        "volatility_annualized": np.nan,
        "roe": np.nan,
        "debt_to_equity": np.nan,
        "eps_growth": np.nan,
        "current_price": np.nan,
        "data_ok": False,
        "error": None,
    }

    if not ticker or yf is None:
        metrics["error"] = "yfinance not available or ticker missing"
        return metrics

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="14mo", interval="1d", auto_adjust=True)

        if hist is None or hist.empty or "Close" not in hist:
            metrics["error"] = "No price history returned"
            return metrics

        closes = hist["Close"].dropna()
        if len(closes) < 30:
            metrics["error"] = "Insufficient price history"
            return metrics

        last_price = closes.iloc[-1]
        metrics["current_price"] = float(last_price)

        # --- Momentum inputs: 6M / 12M trailing total return ---
        if len(closes) > TRADING_DAYS_6M:
            metrics["return_6m"] = float(last_price / closes.iloc[-TRADING_DAYS_6M] - 1.0)
        if len(closes) > TRADING_DAYS_12M:
            metrics["return_12m"] = float(last_price / closes.iloc[-TRADING_DAYS_12M] - 1.0)
        elif len(closes) > 30:
            # Not quite 12 months of history (recent IPO/listing) — use
            # whatever history is available as a partial proxy.
            metrics["return_12m"] = float(last_price / closes.iloc[0] - 1.0)

        # --- Volatility: annualized std-dev of daily log returns ---
        daily_returns = np.log(closes / closes.shift(1)).dropna()
        if len(daily_returns) > 20:
            metrics["volatility_annualized"] = float(daily_returns.std() * np.sqrt(252))

        # --- Fundamentals (best-effort; Yahoo coverage varies by stock) ---
        info = {}
        try:
            info = tk.get_info()
        except Exception:
            try:
                info = tk.info  # older yfinance fallback
            except Exception:
                info = {}

        roe = info.get("returnOnEquity")
        metrics["roe"] = float(roe) if roe is not None else np.nan

        dte = info.get("debtToEquity")
        # Yahoo reports debtToEquity as a percentage-like ratio (e.g. 45.3 == 0.453x)
        metrics["debt_to_equity"] = float(dte) / 100.0 if dte is not None else np.nan

        eps_growth = info.get("earningsGrowth")
        if eps_growth is None:
            eps_growth = info.get("earningsQuarterlyGrowth")
        metrics["eps_growth"] = float(eps_growth) if eps_growth is not None else np.nan

        metrics["data_ok"] = True

    except Exception as exc:  # noqa: BLE001 - deliberately broad, network is flaky
        metrics["error"] = str(exc)

    return metrics


def fetch_batch(tickers: list) -> pd.DataFrame:
    """Fetch metrics for a list of tickers and return as a DataFrame,
    one row per ticker, preserving input order."""
    records = [fetch_stock_metrics(t) for t in tickers]
    return pd.DataFrame(records)
