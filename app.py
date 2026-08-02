"""
app.py
------
NSE Rebalancing Intelligence Dashboard — Streamlit entry point.

Upload an NSE Indices periodic-review press release PDF, review the
auto-extracted inclusion/exclusion lists, then run a proprietary
multi-factor scoring engine (Quality / Momentum / Low-Volatility) on
every newly included stock to get a ranked, color-coded recommendation
table, suggested allocation, and downloadable scorecard.

Run locally:
    streamlit run app.py

See README.md for Streamlit Cloud deployment instructions.
"""

import io

import pandas as pd
import streamlit as st

from modules import market_data, pdf_parser, scoring, styling, ticker_mapper, utils
from modules.i18n import t
from modules.sample_data import get_sample_indices

# ---------------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="NSE Rebalancing Intelligence Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "lang": "en",
    "dark_mode": False,
    "parsed_indices": None,     # dict[str, IndexChanges] from parser/sample
    "inclusions_df": None,      # editable DataFrame of newly-included names
    "exclusions_df": None,      # display-only DataFrame of excluded names
    "raw_metrics_df": None,     # inclusions + fetched market data (pre-score)
    "last_source_id": None,     # de-dupe key so we don't re-parse every rerun
}
for key, val in _DEFAULTS.items():
    st.session_state.setdefault(key, val)


# ---------------------------------------------------------------------------
# Sidebar: language, theme, and scoring-weight controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙ Settings / அமைப்புகள்")

    lang_choice = st.selectbox(
        "Language / மொழி",
        options=["English", "தமிழ்"],
        index=0 if st.session_state.lang == "en" else 1,
    )
    st.session_state.lang = "en" if lang_choice == "English" else "ta"

    st.session_state.dark_mode = st.toggle(
        t("dark_mode"), value=st.session_state.dark_mode
    )

    st.divider()
    st.markdown(f"**{t('weights_title')}**")
    w_quality = st.slider(t("weight_quality"), 0, 100, 40, step=5)
    w_momentum = st.slider(t("weight_momentum"), 0, 100, 35, step=5)
    w_lowvol = st.slider(t("weight_lowvol"), 0, 100, 25, step=5)
    st.caption(t("weights_warning"))

    weights_raw = {"quality": w_quality, "momentum": w_momentum, "lowvol": w_lowvol}
    weights = scoring.normalize_weights(weights_raw)
    st.caption(
        f"→ Quality {weights['quality']*100:.0f}% · "
        f"Momentum {weights['momentum']*100:.0f}% · "
        f"Low-Vol {weights['lowvol']*100:.0f}%"
    )

# Apply theme CSS after we know the toggle state
styling.inject_css(dark=st.session_state.dark_mode)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title(f"📈 {t('app_title')}")
st.caption(t("app_subtitle"))
st.markdown(f'<div class="disclaimer-box">{t("disclaimer")}</div>', unsafe_allow_html=True)
st.write("")


# ---------------------------------------------------------------------------
# Upload zone (drag & drop) + sample data fallback
# ---------------------------------------------------------------------------
col_upload, col_sample = st.columns([3, 1])
with col_upload:
    uploaded_file = st.file_uploader(
        t("upload_label"), type=["pdf"], accept_multiple_files=False
    )
with col_sample:
    st.write("")
    st.write("")
    use_sample_clicked = st.button(f"🧪 {t('use_sample')}", use_container_width=True)


def _build_inclusions_exclusions(parsed: dict):
    """Flatten the parsed {index -> IndexChanges} dict into two tidy
    DataFrames: one for inclusions (with ticker mapping applied) and one
    for exclusions (informational only)."""
    inc_rows, exc_rows = [], []
    for index_name, changes in parsed.items():
        for name in changes.inclusions:
            inc_rows.append({"index_name": index_name, "company_name": name})
        for name in changes.exclusions:
            exc_rows.append({"index_name": index_name, "company_name": name})

    inc_df = pd.DataFrame(inc_rows, columns=["index_name", "company_name"])
    exc_df = pd.DataFrame(exc_rows, columns=["index_name", "company_name"])

    if not inc_df.empty:
        mapped = ticker_mapper.bulk_map(inc_df["company_name"].tolist())
        inc_df = inc_df.merge(mapped, on="company_name", how="left")
    else:
        inc_df["ticker"] = []
        inc_df["match_confidence"] = []

    return inc_df, exc_df


# ---------------------------------------------------------------------------
# Determine current "source" (uploaded file vs sample) and (re)parse only
# when the source actually changes, so slider/toggle reruns stay fast.
# ---------------------------------------------------------------------------
source_id = None
if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    source_id = f"upload:{uploaded_file.name}:{len(file_bytes)}"
elif use_sample_clicked:
    source_id = "sample"

if source_id and source_id != st.session_state.last_source_id:
    st.session_state.last_source_id = source_id
    st.session_state.raw_metrics_df = None  # invalidate downstream scoring

    with st.spinner(t("processing")):
        if source_id == "sample":
            parsed = get_sample_indices()
        else:
            parsed = pdf_parser.parse_press_release(io.BytesIO(file_bytes))

    st.session_state.parsed_indices = parsed
    inc_df, exc_df = _build_inclusions_exclusions(parsed)
    st.session_state.inclusions_df = inc_df
    st.session_state.exclusions_df = exc_df

    if inc_df.empty:
        st.warning(
            "No inclusion entries could be detected automatically. You can "
            "still add rows manually in the table below."
        )

if st.session_state.parsed_indices is None:
    st.info(t("no_file"))
    st.stop()


# ---------------------------------------------------------------------------
# Detected index sections summary
# ---------------------------------------------------------------------------
styling.section_header(t("detected_indices"))
summary_rows = [
    {
        "Index": idx_name,
        "Inclusions": len(changes.inclusions),
        "Exclusions": len(changes.exclusions),
    }
    for idx_name, changes in st.session_state.parsed_indices.items()
]
st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Review & correct extracted inclusions (editable table)
# ---------------------------------------------------------------------------
styling.section_header(t("review_extraction"), t("review_help"))

inc_df = st.session_state.inclusions_df.copy()
if not inc_df.empty and (
    inc_df["ticker"].isna().any() or (inc_df["ticker"].astype(str).str.strip() == "").any()
):
    st.warning(t("ticker_missing_warning"))

edited_inclusions = st.data_editor(
    inc_df[["index_name", "company_name", "ticker", "match_confidence"]]
    if not inc_df.empty
    else pd.DataFrame(columns=["index_name", "company_name", "ticker", "match_confidence"]),
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="inclusions_editor",
    column_config={
        "index_name": st.column_config.TextColumn("Index"),
        "company_name": st.column_config.TextColumn("Company Name", width="large"),
        "ticker": st.column_config.TextColumn("Ticker (Yahoo Finance, e.g. RELIANCE.NS)"),
        "match_confidence": st.column_config.NumberColumn(
            "Match Confidence", format="%.2f", disabled=True
        ),
    },
)
st.session_state.inclusions_df = edited_inclusions

# Exclusions — informational, lightly editable in case of extraction errors
styling.section_header(t("excluded_title"))
exc_df = st.session_state.exclusions_df
st.dataframe(
    exc_df if not exc_df.empty else pd.DataFrame(columns=["index_name", "company_name"]),
    hide_index=True,
    use_container_width=True,
)


# ---------------------------------------------------------------------------
# Run scoring engine
# ---------------------------------------------------------------------------
run_clicked = st.button(f"🚀 {t('run_scoring')}", type="primary", use_container_width=False)

if run_clicked:
    valid_df = edited_inclusions[
        edited_inclusions["ticker"].astype(str).str.strip() != ""
    ].reset_index(drop=True)

    if valid_df.empty:
        st.error(
            "No valid tickers to score. Please fill in the 'ticker' column "
            "for at least one company above."
        )
    else:
        with st.spinner(t("fetching_market_data")):
            metrics_df = market_data.fetch_batch(valid_df["ticker"].tolist())
            merged = valid_df.merge(metrics_df, on="ticker", how="left")
        st.session_state.raw_metrics_df = merged

        failed = merged[merged["data_ok"] != True]  # noqa: E712
        if not failed.empty:
            st.warning(
                f"Market data could not be fetched for {len(failed)} "
                f"ticker(s): {', '.join(failed['ticker'].astype(str).tolist())}. "
                "These will use peer-median estimates in scoring."
            )


# ---------------------------------------------------------------------------
# Dashboard (only rendered once we have raw market metrics to score)
# ---------------------------------------------------------------------------
if st.session_state.raw_metrics_df is not None and not st.session_state.raw_metrics_df.empty:
    scored = scoring.compute_scores(st.session_state.raw_metrics_df, weights)
    scored = scoring.suggest_allocation(scored)
    scored["recommendation_display"] = scored["recommendation"].map(scoring.RECO_EMOJI)

    # --- KPI summary cards ---------------------------------------------
    n_incl = len(scored)
    n_excl = len(st.session_state.exclusions_df)
    n_strong_buy = int((scored["recommendation"] == "Strong Buy").sum())
    avg_score = scored["composite_score"].mean()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(styling.kpi_card(t("summary_inclusions"), str(n_incl)), unsafe_allow_html=True)
    with k2:
        st.markdown(styling.kpi_card(t("summary_exclusions"), str(n_excl)), unsafe_allow_html=True)
    with k3:
        st.markdown(styling.kpi_card(t("summary_strong_buy"), str(n_strong_buy)), unsafe_allow_html=True)
    with k4:
        st.markdown(
            styling.kpi_card(t("summary_avg_score"), f"{avg_score:.1f}/100"),
            unsafe_allow_html=True,
        )

    # --- Top picks strip --------------------------------------------------
    top_picks = scored.sort_values("composite_score", ascending=False).head(3)
    if not top_picks.empty:
        st.write("")
        cols = st.columns(len(top_picks))
        for col, (_, row) in zip(cols, top_picks.iterrows()):
            with col:
                st.markdown(
                    styling.kpi_card(
                        row["company_name"][:28],
                        f"{row['composite_score']:.1f}",
                        styling.badge_html(row["recommendation"]),
                    ),
                    unsafe_allow_html=True,
                )

    # --- Filterable / sortable scorecard table -----------------------------
    styling.section_header(t("table_title"))

    f1, f2, f3 = st.columns(3)
    with f1:
        index_filter = st.multiselect(
            t("filter_index"), sorted(scored["index_name"].dropna().unique().tolist())
        )
    with f2:
        reco_filter = st.multiselect(
            t("filter_reco"), ["Strong Buy", "Buy", "Watch", "Avoid"]
        )
    with f3:
        sort_col = st.selectbox(
            t("sort_by"),
            options=["composite_score", "quality_score", "momentum_score", "lowvol_score", "company_name"],
            index=0,
        )

    filtered = scored.copy()
    if index_filter:
        filtered = filtered[filtered["index_name"].isin(index_filter)]
    if reco_filter:
        filtered = filtered[filtered["recommendation"].isin(reco_filter)]
    ascending = sort_col == "company_name"
    filtered = filtered.sort_values(sort_col, ascending=ascending)

    display_cols = [
        "index_name", "company_name", "ticker", "recommendation_display",
        "quality_score", "momentum_score", "lowvol_score", "composite_score",
        "suggested_allocation_pct",
    ]
    st.dataframe(
        filtered[display_cols],
        hide_index=True,
        use_container_width=True,
        column_config={
            "index_name": st.column_config.TextColumn("Index"),
            "company_name": st.column_config.TextColumn("Company"),
            "ticker": st.column_config.TextColumn("Ticker"),
            "recommendation_display": st.column_config.TextColumn(t("recommendation")),
            "quality_score": st.column_config.ProgressColumn(
                t("quality_score"), min_value=0, max_value=100, format="%.0f"
            ),
            "momentum_score": st.column_config.ProgressColumn(
                t("momentum_score"), min_value=0, max_value=100, format="%.0f"
            ),
            "lowvol_score": st.column_config.ProgressColumn(
                t("lowvol_score"), min_value=0, max_value=100, format="%.0f"
            ),
            "composite_score": st.column_config.ProgressColumn(
                t("composite_score"), min_value=0, max_value=100, format="%.1f"
            ),
            "suggested_allocation_pct": st.column_config.ProgressColumn(
                "Suggested Alloc %", min_value=0, max_value=100, format="%.1f%%"
            ),
        },
    )

    # --- Download buttons ---------------------------------------------------
    export_df = filtered[display_cols].rename(columns={"recommendation_display": "recommendation"})
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            t("download_csv"),
            data=utils.to_csv_bytes(export_df),
            file_name="nse_rebalance_scorecard.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            t("download_xlsx"),
            data=utils.to_excel_bytes(export_df),
            file_name="nse_rebalance_scorecard.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # --- Suggested portfolio allocation chart -------------------------------
    styling.section_header(t("allocation_title"), t("allocation_help"))
    alloc_df = (
        scored[scored["suggested_allocation_pct"] > 0]
        .sort_values("suggested_allocation_pct", ascending=False)
        [["company_name", "suggested_allocation_pct"]]
        .set_index("company_name")
    )
    if not alloc_df.empty:
        st.bar_chart(alloc_df, use_container_width=True)
    else:
        st.info("No stocks currently qualify for an allocation (Buy-rated or above).")

    # --- Per-stock explanations ---------------------------------------------
    styling.section_header(t("explanation_title"))
    for _, row in filtered.iterrows():
        with st.expander(
            f"{row['recommendation_display']} — "
            f"{row['company_name']} ({row['ticker']}) — {row['composite_score']:.1f}/100"
        ):
            st.markdown(scoring.generate_explanation(row))

else:
    st.info(
        f"👆 Click **{t('run_scoring')}** above once you've reviewed the "
        "extracted stock list to generate the full dashboard."
    )
