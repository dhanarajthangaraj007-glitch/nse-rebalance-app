"""
styling.py
----------
Custom CSS injection for a professional finance-dashboard look
(inspired by NSE / Tickertape), plus a lightweight dark/light theme
toggle that works independently of Streamlit's native theme system
(so it behaves consistently on Streamlit Cloud).
"""

import streamlit as st

# Recommendation -> color mapping used across cards, tables and badges.
RECO_COLORS = {
    "Strong Buy": "#16a34a",  # green-600
    "Buy": "#65a30d",         # lime-600
    "Watch": "#d97706",       # amber-600
    "Avoid": "#dc2626",       # red-600
}


def inject_css(dark: bool = False) -> None:
    """Inject the full custom stylesheet for the app.

    Parameters
    ----------
    dark : bool
        If True, apply the dark palette; otherwise light palette.
    """
    if dark:
        bg = "#0f172a"
        bg_secondary = "#1e293b"
        text = "#e2e8f0"
        text_muted = "#94a3b8"
        card_bg = "#1e293b"
        border = "#334155"
        accent = "#38bdf8"
    else:
        bg = "#f8fafc"
        bg_secondary = "#ffffff"
        text = "#0f172a"
        text_muted = "#475569"
        card_bg = "#ffffff"
        border = "#e2e8f0"
        accent = "#0ea5e9"

    st.markdown(
        f"""
        <style>
        /* ---- Global app background & text ---- */
        .stApp {{
            background-color: {bg};
            color: {text};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {bg_secondary};
            border-right: 1px solid {border};
        }}
        h1, h2, h3, h4, h5, h6, p, span, label, div {{
            color: {text};
        }}
        /* ---- Hide default Streamlit chrome for a cleaner product feel ---- */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* ---- KPI Summary cards ---- */
        .kpi-card {{
            background-color: {card_bg};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            text-align: left;
        }}
        .kpi-label {{
            font-size: 0.8rem;
            font-weight: 600;
            color: {text_muted};
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 6px;
        }}
        .kpi-value {{
            font-size: 1.9rem;
            font-weight: 700;
            color: {text};
            line-height: 1.1;
        }}
        .kpi-sub {{
            font-size: 0.78rem;
            color: {text_muted};
            margin-top: 4px;
        }}

        /* ---- Recommendation badges ---- */
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            color: white;
        }}

        /* ---- Section header ---- */
        .section-header {{
            font-size: 1.25rem;
            font-weight: 700;
            margin-top: 28px;
            margin-bottom: 6px;
            border-left: 4px solid {accent};
            padding-left: 10px;
        }}
        .section-sub {{
            color: {text_muted};
            font-size: 0.9rem;
            margin-bottom: 14px;
        }}

        /* ---- Upload dropzone tweak ---- */
        [data-testid="stFileUploaderDropzone"] {{
            background-color: {card_bg};
            border: 2px dashed {accent};
            border-radius: 14px;
        }}

        /* ---- Dataframe corners ---- */
        [data-testid="stDataFrame"] {{
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid {border};
        }}

        /* ---- Disclaimer box ---- */
        .disclaimer-box {{
            background-color: {"#3f2d0e" if dark else "#fffbeb"};
            border: 1px solid {"#7c5a10" if dark else "#fde68a"};
            color: {"#fde68a" if dark else "#92400e"};
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 0.85rem;
            margin-top: 20px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = "") -> str:
    """Return HTML for a single KPI summary card."""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """


def badge_html(recommendation: str) -> str:
    """Return an HTML color-coded badge for a recommendation label."""
    color = RECO_COLORS.get(recommendation, "#64748b")
    return f'<span class="badge" style="background-color:{color};">{recommendation}</span>'


def section_header(title: str, subtitle: str = "") -> None:
    """Render a styled section header with an optional subtitle."""
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="section-sub">{subtitle}</div>', unsafe_allow_html=True)
