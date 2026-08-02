"""
i18n.py
--------
Lightweight bilingual (English / Tamil) text dictionary for the NSE
Rebalancing Intelligence Dashboard.

Usage:
    from modules.i18n import t
    st.title(t("app_title"))

The active language is read from st.session_state["lang"], which is set
by the language toggle in the sidebar (app.py). Defaults to English if
the key/language is missing so the app never crashes on a missing string.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Translation table. Keep keys short & semantic. Add new keys here whenever
# a new UI string is introduced anywhere in the app.
# ---------------------------------------------------------------------------
TRANSLATIONS = {
    "app_title": {
        "en": "NSE Rebalancing Intelligence Dashboard",
        "ta": "NSE மறுசீரமைப்பு நுண்ணறிவு டாஷ்போர்டு",
    },
    "app_subtitle": {
        "en": "Upload the NSE Indices periodic review press release and get an "
              "instant, factor-based scoring of every newly included stock.",
        "ta": "NSE குறியீடுகளின் காலாண்டு மறுஆய்வு செய்தி வெளியீட்டை பதிவேற்றி, "
              "புதிதாக சேர்க்கப்பட்ட ஒவ்வொரு பங்கிற்கும் உடனடி காரணி அடிப்படையிலான "
              "மதிப்பெண்ணைப் பெறுங்கள்.",
    },
    "upload_label": {
        "en": "Drag & drop the NSE rebalancing press release PDF here, or click to browse",
        "ta": "NSE மறுசீரமைப்பு செய்தி வெளியீடு PDF ஐ இங்கே இழுத்து விடவும் அல்லது "
              "உலாவ கிளிக் செய்யவும்",
    },
    "processing": {
        "en": "Parsing PDF and detecting index sections...",
        "ta": "PDF ஐப் பகுப்பாய்வு செய்து குறியீடு பிரிவுகளைக் கண்டறிகிறது...",
    },
    "fetching_market_data": {
        "en": "Fetching live market data & computing factor scores...",
        "ta": "நேரடி சந்தை தரவைப் பெற்று காரணி மதிப்பெண்களைக் கணக்கிடுகிறது...",
    },
    "no_file": {
        "en": "Upload a press release PDF to get started, or try the bundled sample.",
        "ta": "தொடங்குவதற்கு ஒரு செய்தி வெளியீடு PDF ஐ பதிவேற்றவும், அல்லது மாதிரி "
              "கோப்பை முயற்சிக்கவும்.",
    },
    "detected_indices": {
        "en": "Detected Index Sections",
        "ta": "கண்டறியப்பட்ட குறியீடு பிரிவுகள்",
    },
    "review_extraction": {
        "en": "Review & Correct Extracted Stocks",
        "ta": "பிரித்தெடுக்கப்பட்ட பங்குகளை சரிபார்த்து திருத்தவும்",
    },
    "review_help": {
        "en": "PDF extraction can occasionally miss or misread a name. Please "
              "review the table below, fix any ticker/company name, then "
              "proceed to scoring.",
        "ta": "PDF பிரித்தெடுத்தல் சில நேரங்களில் ஒரு பெயரை தவறவிடலாம் அல்லது "
              "தவறாகப் படிக்கலாம். கீழே உள்ள அட்டவணையை சரிபார்த்து, ஏதேனும் "
              "டிக்கர்/நிறுவனப் பெயரைச் சரிசெய்து, மதிப்பீட்டிற்குச் செல்லவும்.",
    },
    "run_scoring": {
        "en": "Run Scoring Engine",
        "ta": "மதிப்பீட்டு இயந்திரத்தை இயக்கு",
    },
    "summary_inclusions": {"en": "Total Inclusions", "ta": "மொத்த சேர்க்கைகள்"},
    "summary_exclusions": {"en": "Total Exclusions", "ta": "மொத்த நீக்கங்கள்"},
    "summary_strong_buy": {"en": "Strong Buy Ideas", "ta": "வலுவான வாங்கல் யோசனைகள்"},
    "summary_avg_score": {"en": "Avg. Composite Score", "ta": "சராசரி கூட்டு மதிப்பெண்"},
    "table_title": {"en": "Newly Included Stocks — Scorecard", "ta": "புதிதாக சேர்க்கப்பட்ட பங்குகள் — மதிப்பெண் அட்டவணை"},
    "excluded_title": {"en": "Stocks Being Excluded", "ta": "நீக்கப்படும் பங்குகள்"},
    "filter_index": {"en": "Filter by Index", "ta": "குறியீட்டால் வடிகட்டவும்"},
    "filter_reco": {"en": "Filter by Recommendation", "ta": "பரிந்துரையால் வடிகட்டவும்"},
    "sort_by": {"en": "Sort by", "ta": "வரிசைப்படுத்து"},
    "download_csv": {"en": "⬇ Download CSV", "ta": "⬇ CSV பதிவிறக்கவும்"},
    "download_xlsx": {"en": "⬇ Download Excel", "ta": "⬇ எக்செல் பதிவிறக்கவும்"},
    "weights_title": {"en": "Adjust Scoring Weights", "ta": "மதிப்பெண் எடைகளை சரிசெய்யவும்"},
    "weight_quality": {"en": "Quality Weight", "ta": "தரம் எடை"},
    "weight_momentum": {"en": "Momentum Weight", "ta": "வேக எடை"},
    "weight_lowvol": {"en": "Low Volatility Weight", "ta": "குறைந்த நிலையற்ற தன்மை எடை"},
    "weights_warning": {
        "en": "Weights are auto-normalized to sum to 100%.",
        "ta": "எடைகள் தானாகவே 100% ஆக இயல்பாக்கப்படுகின்றன.",
    },
    "allocation_title": {"en": "Suggested Portfolio Allocation", "ta": "பரிந்துரைக்கப்பட்ட போர்ட்ஃபோலியோ ஒதுக்கீடு"},
    "allocation_help": {
        "en": "Allocation weight is proportional to the composite score among "
              "Buy-rated and above stocks. This is illustrative, not financial advice.",
        "ta": "ஒதுக்கீடு எடை, வாங்கல்-மதிப்பீடு மற்றும் அதற்கு மேற்பட்ட பங்குகளிடையே "
              "கூட்டு மதிப்பெண்ணுக்கு விகிதாசாரமாக உள்ளது. இது விளக்கத்திற்காக மட்டுமே, "
              "நிதி ஆலோசனை அல்ல.",
    },
    "explanation_title": {"en": "Why this score?", "ta": "இந்த மதிப்பெண் ஏன்?"},
    "dark_mode": {"en": "Dark Mode", "ta": "இருண்ட பயன்முறை"},
    "language": {"en": "Language", "ta": "மொழி"},
    "disclaimer": {
        "en": "⚠ This tool is for educational/research purposes only and does not "
              "constitute investment advice. Scores are derived from public market "
              "data and a proprietary heuristic model, not official NSE methodology.",
        "ta": "⚠ இந்த கருவி கல்வி/ஆராய்ச்சி நோக்கங்களுக்காக மட்டுமே, முதலீட்டு "
              "ஆலோசனை அல்ல. மதிப்பெண்கள் பொது சந்தை தரவு மற்றும் ஒரு தனித்துவமான "
              "மாதிரியிலிருந்து பெறப்பட்டவை, அதிகாரப்பூர்வ NSE முறையியல் அல்ல.",
    },
    "use_sample": {"en": "Try bundled sample data instead", "ta": "மாதிரி தரவை முயற்சிக்கவும்"},
    "recommendation": {"en": "Recommendation", "ta": "பரிந்துரை"},
    "composite_score": {"en": "Composite Score", "ta": "கூட்டு மதிப்பெண்"},
    "quality_score": {"en": "Quality", "ta": "தரம்"},
    "momentum_score": {"en": "Momentum", "ta": "வேகம்"},
    "lowvol_score": {"en": "Low Volatility", "ta": "குறைந்த நிலையற்ற தன்மை"},
    "ticker_missing_warning": {
        "en": "Some companies could not be auto-mapped to a ticker. Please fill "
              "in the 'ticker' column manually below before scoring.",
        "ta": "சில நிறுவனங்களை டிக்கருடன் தானாக இணைக்க முடியவில்லை. மதிப்பீட்டிற்கு "
              "முன் கீழே 'ticker' நெடுவரிசையை கைமுறையாக நிரப்பவும்.",
    },
}


def t(key: str) -> str:
    """Return the translated string for `key` in the currently active language.

    Falls back to English, then to the raw key itself, so a missing
    translation never breaks the UI.
    """
    lang = st.session_state.get("lang", "en")
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("en", key))
