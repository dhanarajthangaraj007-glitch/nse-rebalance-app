"""
scoring.py
----------
Proprietary factor-scoring engine for newly-included index stocks.

Methodology (inspired by, but NOT identical to, Nifty's official
multi-factor index construction principles — this is a heuristic
research tool, not an official replication):

  QUALITY SCORE (default weight 40%)
      - Return on Equity (higher is better)          .. 45% of Quality
      - Debt-to-Equity   (lower is better)            .. 30% of Quality
      - EPS growth       (higher & more stable is better) .. 25% of Quality

  MOMENTUM SCORE (default weight 35%)
      - Blend of 6M (40%) and 12M (60%) trailing total return,
        then RISK-ADJUSTED by dividing by annualized volatility
        (a Sharpe-style ratio), rewarding steady climbers over
        wildly spiking ones.

  LOW VOLATILITY SCORE (default weight 25%)
      - Inverse of annualized daily-return volatility.

All three raw components are converted to a 0-100 scale via
cross-sectional min-max normalization (winsorized at the 5th/95th
percentile to limit single-stock outlier distortion) *within the
current batch of newly-included stocks* — i.e. stocks are scored
relative to their rebalancing peer set, similar in spirit to how
factor indices rank their eligible universe.

COMPOSITE = Quality*w_q + Momentum*w_m + LowVol*w_lv, weights
user-adjustable in the sidebar (auto-normalized to sum to 100%).
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

DEFAULT_WEIGHTS = {"quality": 0.40, "momentum": 0.35, "lowvol": 0.25}

RECO_THRESHOLDS = [
    (80, "Strong Buy"),
    (65, "Buy"),
    (50, "Watch"),
    (0, "Avoid"),
]

# Emoji-prefixed labels used for the on-screen table so the recommendation
# is color/shape coded without depending on pandas Styler / theme support.
RECO_EMOJI = {
    "Strong Buy": "🟢 Strong Buy",
    "Buy": "🟩 Buy",
    "Watch": "🟧 Watch",
    "Avoid": "🔴 Avoid",
}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------
def _winsorize(series: pd.Series, lower_q: float = 0.05, upper_q: float = 0.95) -> pd.Series:
    if series.dropna().empty:
        return series
    lo, hi = series.quantile(lower_q), series.quantile(upper_q)
    return series.clip(lower=lo, upper=hi)


def normalize_0_100(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Cross-sectional min-max normalization to a 0-100 scale.

    Handles degenerate cases (all-equal values, single row, all-NaN)
    by returning a neutral 50 for every entry rather than raising or
    dividing by zero.
    """
    s = series.astype(float)
    if s.dropna().empty or s.nunique(dropna=True) <= 1:
        return pd.Series([50.0] * len(s), index=s.index)

    s_w = _winsorize(s)
    lo, hi = s_w.min(), s_w.max()
    if hi == lo:
        return pd.Series([50.0] * len(s), index=s.index)

    scaled = (s_w - lo) / (hi - lo) * 100.0
    if not higher_is_better:
        scaled = 100.0 - scaled
    return scaled.clip(0, 100)


def _impute_median(series: pd.Series) -> pd.Series:
    """Fill missing raw metrics with the cross-sectional median so a
    stock with one missing data point isn't unfairly zeroed-out; if the
    whole column is missing, fall back to 0."""
    median = series.median()
    if pd.isna(median):
        median = 0.0
    return series.fillna(median)


# ---------------------------------------------------------------------------
# Factor score computation
# ---------------------------------------------------------------------------
def compute_quality_score(df: pd.DataFrame) -> pd.Series:
    roe = _impute_median(df["roe"])
    dte = _impute_median(df["debt_to_equity"])
    eps_growth = _impute_median(df["eps_growth"])

    roe_n = normalize_0_100(roe, higher_is_better=True)
    dte_n = normalize_0_100(dte, higher_is_better=False)
    eps_n = normalize_0_100(eps_growth, higher_is_better=True)

    return (roe_n * 0.45 + dte_n * 0.30 + eps_n * 0.25).round(1)


def compute_momentum_score(df: pd.DataFrame) -> pd.Series:
    r6 = _impute_median(df["return_6m"])
    r12 = _impute_median(df["return_12m"])
    vol = _impute_median(df["volatility_annualized"]).replace(0, np.nan)
    vol = vol.fillna(vol.median() if not pd.isna(vol.median()) else 0.20)

    blended_return = r6 * 0.40 + r12 * 0.60
    # Risk-adjust: reward return earned per unit of volatility taken on.
    risk_adjusted = blended_return / vol.clip(lower=0.05)

    return normalize_0_100(risk_adjusted, higher_is_better=True).round(1)


def compute_lowvol_score(df: pd.DataFrame) -> pd.Series:
    vol = _impute_median(df["volatility_annualized"])
    return normalize_0_100(vol, higher_is_better=False).round(1)


def assign_recommendation(score: float) -> str:
    for threshold, label in RECO_THRESHOLDS:
        if score >= threshold:
            return label
    return "Avoid"


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return DEFAULT_WEIGHTS.copy()
    return {k: v / total for k, v in weights.items()}


def compute_scores(raw_df: pd.DataFrame, weights: Dict[str, float] = None) -> pd.DataFrame:
    """Main entry point. Takes a DataFrame with the raw metric columns
    (roe, debt_to_equity, eps_growth, return_6m, return_12m,
    volatility_annualized) and returns a copy with added score columns:
    quality_score, momentum_score, lowvol_score, composite_score,
    recommendation.
    """
    df = raw_df.copy()
    weights = normalize_weights(weights or DEFAULT_WEIGHTS)

    df["quality_score"] = compute_quality_score(df)
    df["momentum_score"] = compute_momentum_score(df)
    df["lowvol_score"] = compute_lowvol_score(df)

    df["composite_score"] = (
        df["quality_score"] * weights["quality"]
        + df["momentum_score"] * weights["momentum"]
        + df["lowvol_score"] * weights["lowvol"]
    ).round(1)

    df["recommendation"] = df["composite_score"].apply(assign_recommendation)
    return df


def suggest_allocation(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Suggest an illustrative portfolio allocation proportional to the
    composite score, restricted to Buy-rated-and-above stocks. Returns
    the input df with an added `suggested_allocation_pct` column
    (0 for Watch/Avoid names).
    """
    df = scored_df.copy()
    eligible_mask = df["recommendation"].isin(["Strong Buy", "Buy"])
    eligible_scores = df.loc[eligible_mask, "composite_score"]

    df["suggested_allocation_pct"] = 0.0
    if not eligible_scores.empty and eligible_scores.sum() > 0:
        weights = eligible_scores / eligible_scores.sum() * 100.0
        df.loc[eligible_mask, "suggested_allocation_pct"] = weights.round(1)

    return df


def generate_explanation(row: pd.Series) -> str:
    """Produce a short, human-readable rationale for a stock's scores,
    referencing its underlying raw metrics."""

    def pct(x):
        return "N/A" if pd.isna(x) else f"{x * 100:.1f}%"

    parts = []

    # Quality narrative
    roe_txt = pct(row.get("roe"))
    dte = row.get("debt_to_equity")
    dte_txt = "N/A" if pd.isna(dte) else f"{dte:.2f}x"
    parts.append(
        f"**Quality ({row['quality_score']:.0f}/100):** ROE of {roe_txt} and "
        f"debt-to-equity of {dte_txt} "
        + (
            "reflect a financially sound, low-leverage business."
            if row["quality_score"] >= 65
            else "are middling — leverage or profitability is not best-in-class."
            if row["quality_score"] >= 45
            else "suggest weaker profitability or higher leverage versus peers in this batch."
        )
    )

    # Momentum narrative
    r6_txt, r12_txt = pct(row.get("return_6m")), pct(row.get("return_12m"))
    parts.append(
        f"**Momentum ({row['momentum_score']:.0f}/100):** 6M return of {r6_txt} and "
        f"12M return of {r12_txt}, adjusted for volatility, "
        + (
            "shows strong, risk-efficient price trend."
            if row["momentum_score"] >= 65
            else "shows a moderate, unremarkable trend."
            if row["momentum_score"] >= 45
            else "shows weak or choppy price performance relative to peers."
        )
    )

    # Low-vol narrative
    vol = row.get("volatility_annualized")
    vol_txt = "N/A" if pd.isna(vol) else f"{vol * 100:.1f}%"
    parts.append(
        f"**Low Volatility ({row['lowvol_score']:.0f}/100):** Annualized volatility "
        f"of {vol_txt} is "
        + (
            "notably lower than peers, a stabilizing portfolio addition."
            if row["lowvol_score"] >= 65
            else "in line with peers."
            if row["lowvol_score"] >= 45
            else "higher than peers, adding portfolio risk."
        )
    )

    parts.append(
        f"**Overall:** Composite score of {row['composite_score']:.1f}/100 → "
        f"**{row['recommendation']}**."
    )

    return "\n\n".join(parts)
