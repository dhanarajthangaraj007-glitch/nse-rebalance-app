"""
app.py — NSE Rebalancing Intelligence Dashboard (SINGLE-FILE EDITION)
======================================================================
This is a self-contained, single-file version of the app: everything
(the UI, the PDF parser, the ticker lookup table, the scoring engine)
lives in this one file. It behaves identically to the modular version,
but is meant to be trivially easy to deploy from a phone — you only
ever need to upload TWO files to GitHub: this file and requirements.txt.

Run locally:
    streamlit run app.py

Deploy: see the "HOW TO DEPLOY" section at the very bottom of this file.
"""

import difflib
import io
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pdfplumber
import streamlit as st

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


# =============================================================================
# 0. PAGE CONFIG (must be the very first Streamlit call)
# =============================================================================
st.set_page_config(
    page_title="NSE Rebalancing Intelligence Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# 1. EMBEDDED DATA — company name -> Yahoo Finance NSE ticker lookup table
#    (Same data as data/nse_ticker_mapping.csv in the modular version, just
#    inlined here so there's no separate file to upload.)
# =============================================================================
_TICKER_CSV = """company_name,ticker
Reliance Industries Limited,RELIANCE.NS
Tata Consultancy Services Limited,TCS.NS
HDFC Bank Limited,HDFCBANK.NS
ICICI Bank Limited,ICICIBANK.NS
Infosys Limited,INFY.NS
Hindustan Unilever Limited,HINDUNILVR.NS
State Bank of India,SBIN.NS
Bharti Airtel Limited,BHARTIARTL.NS
ITC Limited,ITC.NS
Kotak Mahindra Bank Limited,KOTAKBANK.NS
Larsen & Toubro Limited,LT.NS
Axis Bank Limited,AXISBANK.NS
Bajaj Finance Limited,BAJFINANCE.NS
Asian Paints Limited,ASIANPAINT.NS
Maruti Suzuki India Limited,MARUTI.NS
HCL Technologies Limited,HCLTECH.NS
Sun Pharmaceutical Industries Limited,SUNPHARMA.NS
Titan Company Limited,TITAN.NS
UltraTech Cement Limited,ULTRACEMCO.NS
Wipro Limited,WIPRO.NS
Nestle India Limited,NESTLEIND.NS
Bajaj Finserv Limited,BAJAJFINSV.NS
Adani Enterprises Limited,ADANIENT.NS
Adani Ports and Special Economic Zone Limited,ADANIPORTS.NS
Power Grid Corporation of India Limited,POWERGRID.NS
NTPC Limited,NTPC.NS
Mahindra & Mahindra Limited,M&M.NS
JSW Steel Limited,JSWSTEEL.NS
Tata Motors Limited,TATAMOTORS.NS
Tata Steel Limited,TATASTEEL.NS
Coal India Limited,COALINDIA.NS
IndusInd Bank Limited,INDUSINDBK.NS
Grasim Industries Limited,GRASIM.NS
Hindalco Industries Limited,HINDALCO.NS
Dr. Reddy's Laboratories Limited,DRREDDY.NS
Cipla Limited,CIPLA.NS
Britannia Industries Limited,BRITANNIA.NS
Eicher Motors Limited,EICHERMOT.NS
Divi's Laboratories Limited,DIVISLAB.NS
Apollo Hospitals Enterprise Limited,APOLLOHOSP.NS
Bajaj Auto Limited,BAJAJ-AUTO.NS
SBI Life Insurance Company Limited,SBILIFE.NS
HDFC Life Insurance Company Limited,HDFCLIFE.NS
Tech Mahindra Limited,TECHM.NS
Shriram Finance Limited,SHRIRAMFIN.NS
Bharat Petroleum Corporation Limited,BPCL.NS
Oil and Natural Gas Corporation Limited,ONGC.NS
Tata Consumer Products Limited,TATACONSUM.NS
Trent Limited,TRENT.NS
Adani Green Energy Limited,ADANIGREEN.NS
LTIMindtree Limited,LTIM.NS
Zomato Limited,ETERNAL.NS
Jio Financial Services Limited,JIOFIN.NS
Varun Beverages Limited,VBL.NS
Vedanta Limited,VEDL.NS
Pidilite Industries Limited,PIDILITIND.NS
DLF Limited,DLF.NS
Godrej Consumer Products Limited,GODREJCP.NS
Ambuja Cements Limited,AMBUJACEM.NS
Havells India Limited,HAVELLS.NS
Dabur India Limited,DABUR.NS
Siemens Limited,SIEMENS.NS
InterGlobe Aviation Limited,INDIGO.NS
Bank of Baroda,BANKBARODA.NS
Punjab National Bank,PNB.NS
Canara Bank,CANBK.NS
Indian Oil Corporation Limited,IOC.NS
GAIL (India) Limited,GAIL.NS
Bharat Electronics Limited,BEL.NS
Hindustan Aeronautics Limited,HAL.NS
Zydus Lifesciences Limited,ZYDUSLIFE.NS
Lupin Limited,LUPIN.NS
Aurobindo Pharma Limited,AUROPHARMA.NS
Torrent Pharmaceuticals Limited,TORNTPHARM.NS
Mankind Pharma Limited,MANKIND.NS
Info Edge (India) Limited,NAUKRI.NS
Indus Towers Limited,INDUSTOWER.NS
Motherson Sumi Wiring India Limited,MSUMI.NS
Samvardhana Motherson International Limited,MOTHERSON.NS
Bosch Limited,BOSCHLTD.NS
United Spirits Limited,MCDOWELL-N.NS
Colgate Palmolive (India) Limited,COLPAL.NS
Marico Limited,MARICO.NS
Page Industries Limited,PAGEIND.NS
Berger Paints India Limited,BERGEPAINT.NS
Voltas Limited,VOLTAS.NS
Bharat Forge Limited,BHARATFORG.NS
Cummins India Limited,CUMMINSIND.NS
ABB India Limited,ABB.NS
CG Power and Industrial Solutions Limited,CGPOWER.NS
Polycab India Limited,POLYCAB.NS
Dixon Technologies (India) Limited,DIXON.NS
Persistent Systems Limited,PERSISTENT.NS
Coforge Limited,COFORGE.NS
Mphasis Limited,MPHASIS.NS
Oracle Financial Services Software Limited,OFSS.NS
L&T Technology Services Limited,LTTS.NS
Max Healthcare Institute Limited,MAXHEALTH.NS
Fortis Healthcare Limited,FORTIS.NS
Global Health Limited,MEDANTA.NS
Lloyds Metals and Energy Limited,LLOYDSME.NS
NMDC Limited,NMDC.NS
Steel Authority of India Limited,SAIL.NS
Jindal Steel & Power Limited,JINDALSTEL.NS
JSW Energy Limited,JSWENERGY.NS
Tata Power Company Limited,TATAPOWER.NS
Adani Power Limited,ADANIPOWER.NS
Adani Total Gas Limited,ATGL.NS
Adani Energy Solutions Limited,ADANIENSOL.NS
Torrent Power Limited,TORNTPOWER.NS
NHPC Limited,NHPC.NS
SJVN Limited,SJVN.NS
Power Finance Corporation Limited,PFC.NS
REC Limited,RECLTD.NS
Indian Railway Finance Corporation Limited,IRFC.NS
Rail Vikas Nigam Limited,RVNL.NS
Indian Railway Catering & Tourism Corporation Limited,IRCTC.NS
IRB Infrastructure Developers Limited,IRB.NS
GMR Airports Limited,GMRAIRPORT.NS
Adani Wilmar Limited,AWL.NS
Patanjali Foods Limited,PATANJALI.NS
United Breweries Limited,UBL.NS
Radico Khaitan Limited,RADICO.NS
Emami Limited,EMAMILTD.NS
Godrej Properties Limited,GODREJPROP.NS
Oberoi Realty Limited,OBEROIRLTY.NS
Macrotech Developers Limited,LODHA.NS
Prestige Estates Projects Limited,PRESTIGE.NS
Phoenix Mills Limited,PHOENIXLTD.NS
Sobha Limited,SOBHA.NS
Bandhan Bank Limited,BANDHANBNK.NS
Federal Bank Limited,FEDERALBNK.NS
IDFC First Bank Limited,IDFCFIRSTB.NS
AU Small Finance Bank Limited,AUBANK.NS
Yes Bank Limited,YESBANK.NS
RBL Bank Limited,RBLBANK.NS
Union Bank of India,UNIONBANK.NS
Indian Bank,INDIANB.NS
Bank of India,BANKINDIA.NS
Central Bank of India,CENTRALBK.NS
IDBI Bank Limited,IDBI.NS
Muthoot Finance Limited,MUTHOOTFIN.NS
Cholamandalam Investment and Finance Company Limited,CHOLAFIN.NS
L&T Finance Limited,LTF.NS
Bajaj Holdings & Investment Limited,BAJAJHLDNG.NS
Piramal Enterprises Limited,PEL.NS
PB Fintech Limited,POLICYBZR.NS
ICICI Lombard General Insurance Company Limited,ICICIGI.NS
ICICI Prudential Life Insurance Company Limited,ICICIPRULI.NS
Max Financial Services Limited,MFSL.NS
General Insurance Corporation of India,GICRE.NS
New India Assurance Company Limited,NIACL.NS
Life Insurance Corporation of India,LICI.NS
CDSL (Central Depository Services India Limited),CDSL.NS
Multi Commodity Exchange of India Limited,MCX.NS
BSE Limited,BSE.NS
Angel One Limited,ANGELONE.NS
360 One Wam Limited,360ONE.NS
Nippon Life India Asset Management Limited,NAM-INDIA.NS
HDFC Asset Management Company Limited,HDFCAMC.NS
UTI Asset Management Company Limited,UTIAMC.NS
Aditya Birla Sun Life AMC Limited,ABSLAMC.NS
Suzlon Energy Limited,SUZLON.NS
KPIT Technologies Limited,KPITTECH.NS
Tata Elxsi Limited,TATAELXSI.NS
Honeywell Automation India Limited,HONAUT.NS
Schaeffler India Limited,SCHAEFFLER.NS
SKF India Limited,SKFINDIA.NS
Timken India Limited,TIMKEN.NS
Escorts Kubota Limited,ESCORTS.NS
Ashok Leyland Limited,ASHOKLEY.NS
TVS Motor Company Limited,TVSMOTOR.NS
Hero MotoCorp Limited,HEROMOTOCO.NS
Balkrishna Industries Limited,BALKRISIND.NS
MRF Limited,MRF.NS
Apollo Tyres Limited,APOLLOTYRE.NS
CEAT Limited,CEATLTD.NS
JK Tyre & Industries Limited,JKTYRE.NS
Exide Industries Limited,EXIDEIND.NS
Amara Raja Energy & Mobility Limited,ARE&M.NS
Sona BLW Precision Forgings Limited,SONACOMS.NS
Craftsman Automation Limited,CRAFTSMAN.NS
Endurance Technologies Limited,ENDURANCE.NS
Sundram Fasteners Limited,SUNDRMFAST.NS
Supreme Industries Limited,SUPREMEIND.NS
Astral Limited,ASTRAL.NS
Finolex Industries Limited,FINPIPE.NS
Finolex Cables Limited,FINCABLES.NS
KEI Industries Limited,KEI.NS
Whirlpool of India Limited,WHIRLPOOL.NS
Blue Star Limited,BLUESTARCO.NS
Crompton Greaves Consumer Electricals Limited,CROMPTON.NS
Amber Enterprises India Limited,AMBER.NS
V-Guard Industries Limited,VGUARD.NS
Solar Industries India Limited,SOLARINDS.NS
Deepak Nitrite Limited,DEEPAKNTR.NS
PI Industries Limited,PIIND.NS
UPL Limited,UPL.NS
SRF Limited,SRF.NS
Aarti Industries Limited,AARTIIND.NS
Navin Fluorine International Limited,NAVINFLUOR.NS
Tata Chemicals Limited,TATACHEM.NS
Gujarat Narmada Valley Fertilizers & Chemicals Limited,GNFC.NS
Coromandel International Limited,COROMANDEL.NS
Chambal Fertilisers and Chemicals Limited,CHAMBLFERT.NS
Sumitomo Chemical India Limited,SUMICHEM.NS
Linde India Limited,LINDEINDIA.NS
Gland Pharma Limited,GLAND.NS
Alkem Laboratories Limited,ALKEM.NS
Ipca Laboratories Limited,IPCALAB.NS
Laurus Labs Limited,LAURUSLABS.NS
Biocon Limited,BIOCON.NS
Abbott India Limited,ABBOTINDIA.NS
Pfizer Limited,PFIZER.NS
Glaxosmithkline Pharmaceuticals Limited,GLAXO.NS
Sanofi India Limited,SANOFI.NS
Ajanta Pharma Limited,AJANTPHARM.NS
J.B. Chemicals & Pharmaceuticals Limited,JBCHEPHARM.NS
Natco Pharma Limited,NATCOPHARM.NS
Piramal Pharma Limited,PPLPHARMA.NS
Syngene International Limited,SYNGENE.NS
Metropolis Healthcare Limited,METROPOLIS.NS
Dr. Lal PathLabs Limited,LALPATHLAB.NS
Vijaya Diagnostic Centre Limited,VIJAYA.NS
Narayana Hrudayalaya Limited,NH.NS
KIMS (Krishna Institute of Medical Sciences) Limited,KIMS.NS
Cera Sanitaryware Limited,CERA.NS
Kajaria Ceramics Limited,KAJARIACER.NS
Century Plyboards (India) Limited,CENTURYPLY.NS
Greenpanel Industries Limited,GREENPANEL.NS
Action Construction Equipment Limited,ACE.NS
Thermax Limited,THERMAX.NS
KEC International Limited,KEC.NS
Kalpataru Projects International Limited,KPIL.NS
Larsen & Toubro Infotech Limited,LTI.NS
Zensar Technologies Limited,ZENSARTECH.NS
Sonata Software Limited,SONATSOFTW.NS
Cyient Limited,CYIENT.NS
Firstsource Solutions Limited,FSL.NS
Tata Communications Limited,TATACOMM.NS
Route Mobile Limited,ROUTE.NS
Affle (India) Limited,AFFLE.NS
Nazara Technologies Limited,NAZARA.NS
Delhivery Limited,DELHIVERY.NS
Nykaa (FSN E-Commerce Ventures Limited),NYKAA.NS
One97 Communications Limited,PAYTM.NS
Honasa Consumer Limited,HONASA.NS
Go Digit General Insurance Limited,GODIGIT.NS
Swiggy Limited,SWIGGY.NS
Hyundai Motor India Limited,HYUNDAI.NS
Waaree Energies Limited,WAAREEENER.NS
Premier Energies Limited,PREMIERENE.NS
NTPC Green Energy Limited,NTPCGREEN.NS
Bharat Dynamics Limited,BDL.NS
Mazagon Dock Shipbuilders Limited,MAZDOCK.NS
Cochin Shipyard Limited,COCHINSHIP.NS
Garden Reach Shipbuilders & Engineers Limited,GRSE.NS
Hindustan Copper Limited,HINDCOPPER.NS
National Aluminium Company Limited,NATIONALUM.NS
Hindustan Zinc Limited,HINDZINC.NS
Jubilant FoodWorks Limited,JUBLFOOD.NS
Devyani International Limited,DEVYANI.NS
Sapphire Foods India Limited,SAPPHIRE.NS
Westlife Foodworld Limited,WESTLIFE.NS
Avenue Supermarts Limited,DMART.NS
V-Mart Retail Limited,VMART.NS
Aditya Birla Fashion and Retail Limited,ABFRL.NS
Shoppers Stop Limited,SHOPERSTOP.NS
Metro Brands Limited,METROBRAND.NS
Bata India Limited,BATAINDIA.NS
Relaxo Footwears Limited,RELAXO.NS
Campus Activewear Limited,CAMPUS.NS
"""


# =============================================================================
# 2. i18n — English / Tamil translation dictionary
# =============================================================================
TRANSLATIONS = {
    "app_title": {"en": "NSE Rebalancing Intelligence Dashboard", "ta": "NSE மறுசீரமைப்பு நுண்ணறிவு டாஷ்போர்டு"},
    "app_subtitle": {
        "en": "Upload the NSE Indices periodic review press release and get an instant, factor-based scoring of every newly included stock.",
        "ta": "NSE குறியீடுகளின் காலாண்டு மறுஆய்வு செய்தி வெளியீட்டை பதிவேற்றி, புதிதாக சேர்க்கப்பட்ட ஒவ்வொரு பங்கிற்கும் உடனடி மதிப்பெண்ணைப் பெறுங்கள்.",
    },
    "upload_label": {"en": "Drag & drop the NSE rebalancing press release PDF here, or click to browse", "ta": "NSE மறுசீரமைப்பு செய்தி வெளியீடு PDF ஐ இங்கே இழுத்து விடவும் அல்லது கிளிக் செய்யவும்"},
    "processing": {"en": "Parsing PDF and detecting index sections...", "ta": "PDF ஐப் பகுப்பாய்வு செய்கிறது..."},
    "fetching_market_data": {"en": "Fetching live market data & computing factor scores...", "ta": "சந்தை தரவைப் பெற்று மதிப்பெண்களைக் கணக்கிடுகிறது..."},
    "no_file": {"en": "Upload a press release PDF to get started, or try the bundled sample.", "ta": "தொடங்க ஒரு PDF ஐ பதிவேற்றவும், அல்லது மாதிரி கோப்பை முயற்சிக்கவும்."},
    "detected_indices": {"en": "Detected Index Sections", "ta": "கண்டறியப்பட்ட குறியீடு பிரிவுகள்"},
    "review_extraction": {"en": "Review & Correct Extracted Stocks", "ta": "பிரித்தெடுக்கப்பட்ட பங்குகளை சரிபார்க்கவும்"},
    "review_help": {"en": "PDF extraction can occasionally miss a name. Please review the table below, fix any ticker/company name, then proceed to scoring.", "ta": "கீழே உள்ள அட்டவணையை சரிபார்த்து, தேவைப்பட்டால் திருத்தி, மதிப்பீட்டிற்குச் செல்லவும்."},
    "run_scoring": {"en": "Run Scoring Engine", "ta": "மதிப்பீட்டு இயந்திரத்தை இயக்கு"},
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
    "weights_warning": {"en": "Weights are auto-normalized to sum to 100%.", "ta": "எடைகள் தானாகவே 100% ஆக மாற்றப்படும்."},
    "allocation_title": {"en": "Suggested Portfolio Allocation", "ta": "பரிந்துரைக்கப்பட்ட ஒதுக்கீடு"},
    "allocation_help": {"en": "Allocation weight is proportional to the composite score among Buy-rated and above stocks. This is illustrative, not financial advice.", "ta": "இது விளக்கத்திற்காக மட்டுமே, நிதி ஆலோசனை அல்ல."},
    "explanation_title": {"en": "Why this score?", "ta": "இந்த மதிப்பெண் ஏன்?"},
    "dark_mode": {"en": "Dark Mode", "ta": "இருண்ட பயன்முறை"},
    "language": {"en": "Language", "ta": "மொழி"},
    "disclaimer": {
        "en": "⚠ This tool is for educational/research purposes only and does not constitute investment advice. Scores are derived from public market data and a proprietary heuristic model, not official NSE methodology.",
        "ta": "⚠ இந்த கருவி கல்வி/ஆராய்ச்சி நோக்கங்களுக்காக மட்டுமே, முதலீட்டு ஆலோசனை அல்ல.",
    },
    "use_sample": {"en": "Try bundled sample data instead", "ta": "மாதிரி தரவை முயற்சிக்கவும்"},
    "recommendation": {"en": "Recommendation", "ta": "பரிந்துரை"},
    "composite_score": {"en": "Composite Score", "ta": "கூட்டு மதிப்பெண்"},
    "quality_score": {"en": "Quality", "ta": "தரம்"},
    "momentum_score": {"en": "Momentum", "ta": "வேகம்"},
    "lowvol_score": {"en": "Low Volatility", "ta": "குறைந்த நிலையற்ற தன்மை"},
    "ticker_missing_warning": {"en": "Some companies could not be auto-mapped to a ticker. Please fill in the 'ticker' column manually below before scoring.", "ta": "சில நிறுவனங்களுக்கு டிக்கர் தானாக கிடைக்கவில்லை. கீழே கைமுறையாக நிரப்பவும்."},
}


def t(key: str) -> str:
    """Return the translated string for `key` in the active language."""
    lang = st.session_state.get("lang", "en")
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("en", key))


# =============================================================================
# 3. STYLING — custom CSS, KPI cards, badges
# =============================================================================
RECO_COLORS = {"Strong Buy": "#16a34a", "Buy": "#65a30d", "Watch": "#d97706", "Avoid": "#dc2626"}
RECO_EMOJI = {"Strong Buy": "🟢 Strong Buy", "Buy": "🟩 Buy", "Watch": "🟧 Watch", "Avoid": "🔴 Avoid"}


def inject_css(dark: bool = False) -> None:
    if dark:
        bg, bg2, text, muted, card, border, accent = "#0f172a", "#1e293b", "#e2e8f0", "#94a3b8", "#1e293b", "#334155", "#38bdf8"
    else:
        bg, bg2, text, muted, card, border, accent = "#f8fafc", "#ffffff", "#0f172a", "#475569", "#ffffff", "#e2e8f0", "#0ea5e9"

    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {bg}; color: {text}; }}
        section[data-testid="stSidebar"] {{ background-color: {bg2}; border-right: 1px solid {border}; }}
        h1, h2, h3, h4, h5, h6, p, span, label, div {{ color: {text}; }}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        .kpi-card {{ background-color: {card}; border: 1px solid {border}; border-radius: 14px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: left; }}
        .kpi-label {{ font-size: 0.8rem; font-weight: 600; color: {muted}; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; }}
        .kpi-value {{ font-size: 1.9rem; font-weight: 700; color: {text}; line-height: 1.1; }}
        .kpi-sub {{ font-size: 0.78rem; color: {muted}; margin-top: 4px; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; color: white; }}
        .section-header {{ font-size: 1.25rem; font-weight: 700; margin-top: 28px; margin-bottom: 6px; border-left: 4px solid {accent}; padding-left: 10px; }}
        .section-sub {{ color: {muted}; font-size: 0.9rem; margin-bottom: 14px; }}
        [data-testid="stFileUploaderDropzone"] {{ background-color: {card}; border: 2px dashed {accent}; border-radius: 14px; }}
        [data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; border: 1px solid {border}; }}
        .disclaimer-box {{ background-color: {"#3f2d0e" if dark else "#fffbeb"}; border: 1px solid {"#7c5a10" if dark else "#fde68a"}; color: {"#fde68a" if dark else "#92400e"}; border-radius: 10px; padding: 12px 16px; font-size: 0.85rem; margin-top: 20px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = "") -> str:
    return f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>'


def badge_html(recommendation: str) -> str:
    color = RECO_COLORS.get(recommendation, "#64748b")
    return f'<span class="badge" style="background-color:{color};">{recommendation}</span>'


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="section-sub">{subtitle}</div>', unsafe_allow_html=True)


# =============================================================================
# 4. PDF PARSER — extract index name + inclusion/exclusion company lists
# =============================================================================
KNOWN_INDICES = [
    "NIFTY NEXT 50", "NIFTY MIDCAP 150", "NIFTY MIDCAP 50", "NIFTY SMALLCAP 250",
    "NIFTY SMALLCAP 50", "NIFTY MICROCAP 250", "NIFTY LARGEMIDCAP 250",
    "NIFTY MIDSMALLCAP 400", "NIFTY100", "NIFTY 100", "NIFTY 200", "NIFTY 500",
    "NIFTY TOTAL MARKET", "NIFTY 50",
]
_INDEX_PATTERN = re.compile(r"\b(" + "|".join(re.escape(n) for n in KNOWN_INDICES) + r")\b", re.IGNORECASE)
_INCLUSION_KEYWORDS = re.compile(r"\b(inclusion|included|addition|entrant)s?\b", re.IGNORECASE)
_EXCLUSION_KEYWORDS = re.compile(r"\b(exclusion|excluded|removal|deletion)s?\b", re.IGNORECASE)
_COMPANY_LINE = re.compile(r"^\s*(?:\(?\d{1,3}[\).:-]?\s*)?([A-Z][A-Za-z0-9&.,'’()\-/ ]{2,80})\s*$")
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
    inclusions: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)


def _is_noise(line: str) -> bool:
    if not line or len(line.strip()) < 3:
        return True
    return any(p.search(line) for p in _NOISE_PATTERNS)


def clean_company_name(raw: str) -> str:
    name = raw.strip()
    name = re.sub(r"^\s*(?:\(?\d{1,3}[\).:-]?\s*)+", "", name)
    name = re.sub(r"^[•\-–\*]\s*", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"\bLtd\.?$", "Limited", name, flags=re.IGNORECASE)
    return name.strip(" .,")


def extract_text_and_tables(pdf_bytes) -> Dict:
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
    return {"pages_text": pages_text, "pages_tables": pages_tables, "full_text": "\n".join(pages_text)}


def _normalize_index_name(raw: str) -> str:
    name = re.sub(r"\s+", " ", raw.strip().upper())
    if name == "NIFTY100":
        name = "NIFTY 100"
    return name.title()


def _split_into_index_blocks(full_text: str) -> Dict[str, str]:
    matches = list(_INDEX_PATTERN.finditer(full_text))
    blocks: Dict[str, str] = {}
    for i, m in enumerate(matches):
        index_name = _normalize_index_name(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        chunk = full_text[start:end]
        blocks[index_name] = blocks.get(index_name, "") + "\n" + chunk
    return blocks


def _lines_to_company_names(segment: str) -> List[str]:
    names = []
    for line in segment.splitlines():
        line = line.strip()
        if not line or _is_noise(line):
            continue
        if _INCLUSION_KEYWORDS.fullmatch(line.strip(":： ")) or _EXCLUSION_KEYWORDS.fullmatch(line.strip(":： ")):
            continue
        m = _COMPANY_LINE.match(line)
        if m:
            candidate = clean_company_name(m.group(1))
            if len(candidate) >= 3 and candidate.upper() not in {"INCLUSION", "EXCLUSION"}:
                names.append(candidate)
    return names


def _extract_names_from_block(block_text: str) -> IndexChanges:
    inc_match = _INCLUSION_KEYWORDS.search(block_text)
    exc_match = _EXCLUSION_KEYWORDS.search(block_text)
    changes = IndexChanges()
    if not inc_match and not exc_match:
        return changes

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

    changes.inclusions = list(dict.fromkeys(changes.inclusions))
    changes.exclusions = list(dict.fromkeys(changes.exclusions))
    return changes


def _extract_from_tables(pages_tables: List[List]) -> Dict[str, IndexChanges]:
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
    extracted = extract_text_and_tables(pdf_bytes)
    blocks = _split_into_index_blocks(extracted["full_text"])
    results: Dict[str, IndexChanges] = {}
    for index_name, block_text in blocks.items():
        changes = _extract_names_from_block(block_text)
        if changes.inclusions or changes.exclusions:
            results[index_name] = changes

    table_results = _extract_from_tables(extracted["pages_tables"])
    for key, changes in table_results.items():
        if key not in results:
            results[key] = changes
        else:
            results[key].inclusions = list(dict.fromkeys(results[key].inclusions + changes.inclusions))
            results[key].exclusions = list(dict.fromkeys(results[key].exclusions + changes.exclusions))
    return results


# =============================================================================
# 5. TICKER MAPPER — company name -> Yahoo Finance ticker (exact + fuzzy)
# =============================================================================
def _normalize_name(name: str) -> str:
    n = name.lower()
    n = re.sub(r"[.,'’()\-/]", " ", n)
    n = re.sub(r"\b(limited|ltd|the|company|india|co)\b", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


@lru_cache(maxsize=1)
def load_mapping_table() -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(_TICKER_CSV))
    df["norm_name"] = df["company_name"].apply(_normalize_name)
    return df


def map_company_to_ticker(company_name: str, cutoff: float = 0.72) -> Tuple[Optional[str], float]:
    table = load_mapping_table()
    norm_input = _normalize_name(company_name)

    exact = table[table["norm_name"] == norm_input]
    if not exact.empty:
        return exact.iloc[0]["ticker"], 1.0

    choices = table["norm_name"].tolist()
    best = difflib.get_close_matches(norm_input, choices, n=1, cutoff=cutoff)
    if best:
        match_row = table[table["norm_name"] == best[0]].iloc[0]
        ratio = difflib.SequenceMatcher(None, norm_input, best[0]).ratio()
        return match_row["ticker"], round(ratio, 2)

    return None, 0.0


def bulk_map(company_names: list) -> pd.DataFrame:
    rows = []
    for name in company_names:
        ticker, conf = map_company_to_ticker(name)
        rows.append({"company_name": name, "ticker": ticker or "", "match_confidence": conf})
    return pd.DataFrame(rows)


# =============================================================================
# 6. MARKET DATA — yfinance price history + fundamentals
# =============================================================================
TRADING_DAYS_6M = 126
TRADING_DAYS_12M = 252


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_stock_metrics(ticker: str) -> Dict:
    metrics = {
        "ticker": ticker, "return_6m": np.nan, "return_12m": np.nan,
        "volatility_annualized": np.nan, "roe": np.nan, "debt_to_equity": np.nan,
        "eps_growth": np.nan, "current_price": np.nan, "data_ok": False, "error": None,
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

        if len(closes) > TRADING_DAYS_6M:
            metrics["return_6m"] = float(last_price / closes.iloc[-TRADING_DAYS_6M] - 1.0)
        if len(closes) > TRADING_DAYS_12M:
            metrics["return_12m"] = float(last_price / closes.iloc[-TRADING_DAYS_12M] - 1.0)
        elif len(closes) > 30:
            metrics["return_12m"] = float(last_price / closes.iloc[0] - 1.0)

        daily_returns = np.log(closes / closes.shift(1)).dropna()
        if len(daily_returns) > 20:
            metrics["volatility_annualized"] = float(daily_returns.std() * np.sqrt(252))

        info = {}
        try:
            info = tk.get_info()
        except Exception:
            try:
                info = tk.info
            except Exception:
                info = {}

        roe = info.get("returnOnEquity")
        metrics["roe"] = float(roe) if roe is not None else np.nan
        dte = info.get("debtToEquity")
        metrics["debt_to_equity"] = float(dte) / 100.0 if dte is not None else np.nan
        eps_growth = info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth")
        metrics["eps_growth"] = float(eps_growth) if eps_growth is not None else np.nan
        metrics["data_ok"] = True

    except Exception as exc:  # noqa: BLE001
        metrics["error"] = str(exc)

    return metrics


def fetch_batch(tickers: list) -> pd.DataFrame:
    records = [fetch_stock_metrics(t) for t in tickers]
    return pd.DataFrame(records)


# =============================================================================
# 7. SCORING ENGINE — Quality / Momentum / Low-Volatility factor model
# =============================================================================
DEFAULT_WEIGHTS = {"quality": 0.40, "momentum": 0.35, "lowvol": 0.25}
RECO_THRESHOLDS = [(80, "Strong Buy"), (65, "Buy"), (50, "Watch"), (0, "Avoid")]


def _winsorize(series: pd.Series, lower_q: float = 0.05, upper_q: float = 0.95) -> pd.Series:
    if series.dropna().empty:
        return series
    lo, hi = series.quantile(lower_q), series.quantile(upper_q)
    return series.clip(lower=lo, upper=hi)


def normalize_0_100(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
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
    median = series.median()
    if pd.isna(median):
        median = 0.0
    return series.fillna(median)


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
    df = scored_df.copy()
    eligible_mask = df["recommendation"].isin(["Strong Buy", "Buy"])
    eligible_scores = df.loc[eligible_mask, "composite_score"]
    df["suggested_allocation_pct"] = 0.0
    if not eligible_scores.empty and eligible_scores.sum() > 0:
        alloc = eligible_scores / eligible_scores.sum() * 100.0
        df.loc[eligible_mask, "suggested_allocation_pct"] = alloc.round(1)
    return df


def generate_explanation(row: pd.Series) -> str:
    def pct(x):
        return "N/A" if pd.isna(x) else f"{x * 100:.1f}%"

    parts = []
    roe_txt = pct(row.get("roe"))
    dte = row.get("debt_to_equity")
    dte_txt = "N/A" if pd.isna(dte) else f"{dte:.2f}x"
    parts.append(
        f"**Quality ({row['quality_score']:.0f}/100):** ROE of {roe_txt} and debt-to-equity of {dte_txt} "
        + ("reflect a financially sound, low-leverage business." if row["quality_score"] >= 65
           else "are middling — leverage or profitability is not best-in-class." if row["quality_score"] >= 45
           else "suggest weaker profitability or higher leverage versus peers in this batch.")
    )
    r6_txt, r12_txt = pct(row.get("return_6m")), pct(row.get("return_12m"))
    parts.append(
        f"**Momentum ({row['momentum_score']:.0f}/100):** 6M return of {r6_txt} and 12M return of {r12_txt}, adjusted for volatility, "
        + ("shows strong, risk-efficient price trend." if row["momentum_score"] >= 65
           else "shows a moderate, unremarkable trend." if row["momentum_score"] >= 45
           else "shows weak or choppy price performance relative to peers.")
    )
    vol = row.get("volatility_annualized")
    vol_txt = "N/A" if pd.isna(vol) else f"{vol * 100:.1f}%"
    parts.append(
        f"**Low Volatility ({row['lowvol_score']:.0f}/100):** Annualized volatility of {vol_txt} is "
        + ("notably lower than peers, a stabilizing portfolio addition." if row["lowvol_score"] >= 65
           else "in line with peers." if row["lowvol_score"] >= 45
           else "higher than peers, adding portfolio risk.")
    )
    parts.append(f"**Overall:** Composite score of {row['composite_score']:.1f}/100 → **{row['recommendation']}**.")
    return "\n\n".join(parts)


RECO_EMOJI = {"Strong Buy": "🟢 Strong Buy", "Buy": "🟩 Buy", "Watch": "🟧 Watch", "Avoid": "🔴 Avoid"}


# =============================================================================
# 8. EXPORT HELPERS — CSV / Excel
# =============================================================================
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Scorecard") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[worksheet.cell(row=1, column=i + 1).column_letter].width = min(max_len, 40)
    buffer.seek(0)
    return buffer.read()


# =============================================================================
# 9. SAMPLE DATA — bundled demo dataset ("Try sample" button)
# =============================================================================
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


# =============================================================================
# 10. SESSION STATE DEFAULTS
# =============================================================================
_DEFAULTS = {
    "lang": "en",
    "dark_mode": False,
    "parsed_indices": None,
    "inclusions_df": None,
    "exclusions_df": None,
    "raw_metrics_df": None,
    "last_source_id": None,
}
for _k, _v in _DEFAULTS.items():
    st.session_state.setdefault(_k, _v)


def _empty_inclusions_df():
    return pd.DataFrame(columns=["index_name", "company_name", "ticker", "match_confidence"])


def _empty_exclusions_df():
    return pd.DataFrame(columns=["index_name", "company_name"])


# =============================================================================
# 11. SIDEBAR — language, theme, scoring weights
# =============================================================================
with st.sidebar:
    st.markdown("### ⚙ Settings / அமைப்புகள்")

    lang_choice = st.selectbox(
        "Language / மொழி", options=["English", "தமிழ்"],
        index=0 if st.session_state.lang == "en" else 1,
    )
    st.session_state.lang = "en" if lang_choice == "English" else "ta"
    st.session_state.dark_mode = st.toggle(t("dark_mode"), value=st.session_state.dark_mode)

    st.divider()
    st.markdown(f"**{t('weights_title')}**")
    w_quality = st.slider(t("weight_quality"), 0, 100, 40, step=5)
    w_momentum = st.slider(t("weight_momentum"), 0, 100, 35, step=5)
    w_lowvol = st.slider(t("weight_lowvol"), 0, 100, 25, step=5)
    st.caption(t("weights_warning"))

    weights = normalize_weights({"quality": w_quality, "momentum": w_momentum, "lowvol": w_lowvol})
    st.caption(
        f"→ Quality {weights['quality']*100:.0f}% · Momentum {weights['momentum']*100:.0f}% · "
        f"Low-Vol {weights['lowvol']*100:.0f}%"
    )

inject_css(dark=st.session_state.dark_mode)


# =============================================================================
# 12. HEADER
# =============================================================================
st.title(f"📈 {t('app_title')}")
st.caption(t("app_subtitle"))
st.markdown(f'<div class="disclaimer-box">{t("disclaimer")}</div>', unsafe_allow_html=True)
st.write("")


# =============================================================================
# 13. UPLOAD ZONE + SAMPLE DATA BUTTON
# =============================================================================
col_upload, col_sample = st.columns([3, 1])
with col_upload:
    uploaded_file = st.file_uploader(t("upload_label"), type=["pdf"], accept_multiple_files=False)
with col_sample:
    st.write("")
    st.write("")
    use_sample_clicked = st.button(f"🧪 {t('use_sample')}", use_container_width=True)


def _build_inclusions_exclusions(parsed: dict):
    """Flatten {index -> IndexChanges} into (inclusions_df, exclusions_df).

    Tickers are attached POSITIONALLY (never via a key-based merge) —
    the same company can legitimately appear more than once across
    different indices, and merging on a non-unique "company_name" key
    would multiply rows combinatorially.
    """
    inc_rows, exc_rows = [], []
    for index_name, changes in parsed.items():
        for name in changes.inclusions:
            inc_rows.append({"index_name": index_name, "company_name": name})
        for name in changes.exclusions:
            exc_rows.append({"index_name": index_name, "company_name": name})

    inc_df = pd.DataFrame(inc_rows, columns=["index_name", "company_name"])
    exc_df = pd.DataFrame(exc_rows, columns=["index_name", "company_name"])

    if not inc_df.empty:
        mapped = bulk_map(inc_df["company_name"].tolist())
        inc_df = inc_df.reset_index(drop=True)
        inc_df["ticker"] = mapped["ticker"].values
        inc_df["match_confidence"] = mapped["match_confidence"].values
    else:
        inc_df["ticker"] = pd.Series(dtype="object")
        inc_df["match_confidence"] = pd.Series(dtype="float")

    return inc_df, exc_df


# =============================================================================
# 14. PARSE ONLY WHEN THE SOURCE ACTUALLY CHANGES
# =============================================================================
source_id = None
if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    source_id = f"upload:{uploaded_file.name}:{len(file_bytes)}"
elif use_sample_clicked:
    source_id = "sample"

if source_id and source_id != st.session_state.last_source_id:
    st.session_state.last_source_id = source_id
    st.session_state.raw_metrics_df = None

    with st.spinner(t("processing")):
        if source_id == "sample":
            parsed = get_sample_indices()
        else:
            parsed = parse_press_release(io.BytesIO(file_bytes))

    st.session_state.parsed_indices = parsed

    try:
        inc_df, exc_df = _build_inclusions_exclusions(parsed)
    except Exception as exc:  # noqa: BLE001 - never let a parsing hiccup crash the app
        st.error(
            f"Something went wrong while mapping extracted names to tickers "
            f"({exc}). You can still add rows manually in the table below."
        )
        inc_df, exc_df = _empty_inclusions_df(), _empty_exclusions_df()

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


# =============================================================================
# 15. DETECTED INDEX SECTIONS SUMMARY (+ sanity warning for runaway extraction)
# =============================================================================
section_header(t("detected_indices"))
summary_rows = [
    {"Index": idx_name, "Inclusions": len(changes.inclusions), "Exclusions": len(changes.exclusions)}
    for idx_name, changes in st.session_state.parsed_indices.items()
]
st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)

_SUSPICIOUS_COUNT_THRESHOLD = 20
suspicious = [
    row["Index"] for row in summary_rows
    if row["Inclusions"] > _SUSPICIOUS_COUNT_THRESHOLD or row["Exclusions"] > _SUSPICIOUS_COUNT_THRESHOLD
]
if suspicious:
    st.warning(
        "⚠ Unusually large counts detected for: **" + ", ".join(suspicious) + "**. "
        "This usually means the parser picked up a full constituent list or "
        "unrelated text rather than just the actual changes — please "
        "carefully check (and delete any wrong rows from) the editable "
        "table below before running the scoring engine."
    )


# =============================================================================
# 16. REVIEW & CORRECT EXTRACTED INCLUSIONS (editable table)
# =============================================================================
section_header(t("review_extraction"), t("review_help"))

inc_df = st.session_state.get("inclusions_df")
if inc_df is None:
    inc_df = _empty_inclusions_df()
inc_df = inc_df.copy()

if not inc_df.empty and (
    inc_df["ticker"].isna().any() or (inc_df["ticker"].astype(str).str.strip() == "").any()
):
    st.warning(t("ticker_missing_warning"))

edited_inclusions = st.data_editor(
    inc_df[["index_name", "company_name", "ticker", "match_confidence"]] if not inc_df.empty else _empty_inclusions_df(),
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="inclusions_editor",
    column_config={
        "index_name": st.column_config.TextColumn("Index"),
        "company_name": st.column_config.TextColumn("Company Name", width="large"),
        "ticker": st.column_config.TextColumn("Ticker (Yahoo Finance, e.g. RELIANCE.NS)"),
        "match_confidence": st.column_config.NumberColumn("Match Confidence", format="%.2f", disabled=True),
    },
)
st.session_state.inclusions_df = edited_inclusions

section_header(t("excluded_title"))
exc_df = st.session_state.get("exclusions_df")
if exc_df is None:
    exc_df = _empty_exclusions_df()
st.dataframe(
    exc_df if not exc_df.empty else _empty_exclusions_df(),
    hide_index=True, use_container_width=True,
)


# =============================================================================
# 17. RUN SCORING ENGINE
# =============================================================================
run_clicked = st.button(f"🚀 {t('run_scoring')}", type="primary")

if run_clicked:
    valid_df = edited_inclusions[edited_inclusions["ticker"].astype(str).str.strip() != ""].reset_index(drop=True)
    if valid_df.empty:
        st.error("No valid tickers to score. Please fill in the 'ticker' column for at least one company above.")
    else:
        with st.spinner(t("fetching_market_data")):
            metrics_df = fetch_batch(valid_df["ticker"].tolist())
            merged = valid_df.merge(metrics_df, on="ticker", how="left")
        st.session_state.raw_metrics_df = merged

        failed = merged[merged["data_ok"] != True]  # noqa: E712
        if not failed.empty:
            st.warning(
                f"Market data could not be fetched for {len(failed)} ticker(s): "
                f"{', '.join(failed['ticker'].astype(str).tolist())}. "
                "These will use peer-median estimates in scoring."
            )


# =============================================================================
# 18. DASHBOARD
# =============================================================================
if st.session_state.raw_metrics_df is not None and not st.session_state.raw_metrics_df.empty:
    scored = compute_scores(st.session_state.raw_metrics_df, weights)
    scored = suggest_allocation(scored)
    scored["recommendation_display"] = scored["recommendation"].map(RECO_EMOJI)

    n_incl = len(scored)
    n_excl = len(st.session_state.exclusions_df) if st.session_state.exclusions_df is not None else 0
    n_strong_buy = int((scored["recommendation"] == "Strong Buy").sum())
    avg_score = scored["composite_score"].mean()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(kpi_card(t("summary_inclusions"), str(n_incl)), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi_card(t("summary_exclusions"), str(n_excl)), unsafe_allow_html=True)
    with k3:
        st.markdown(kpi_card(t("summary_strong_buy"), str(n_strong_buy)), unsafe_allow_html=True)
    with k4:
        st.markdown(kpi_card(t("summary_avg_score"), f"{avg_score:.1f}/100"), unsafe_allow_html=True)

    top_picks = scored.sort_values("composite_score", ascending=False).head(3)
    if not top_picks.empty:
        st.write("")
        cols = st.columns(len(top_picks))
        for col, (_, row) in zip(cols, top_picks.iterrows()):
            with col:
                st.markdown(
                    kpi_card(row["company_name"][:28], f"{row['composite_score']:.1f}", badge_html(row["recommendation"])),
                    unsafe_allow_html=True,
                )

    section_header(t("table_title"))
    f1, f2, f3 = st.columns(3)
    with f1:
        index_filter = st.multiselect(t("filter_index"), sorted(scored["index_name"].dropna().unique().tolist()))
    with f2:
        reco_filter = st.multiselect(t("filter_reco"), ["Strong Buy", "Buy", "Watch", "Avoid"])
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
    filtered = filtered.sort_values(sort_col, ascending=(sort_col == "company_name"))

    display_cols = [
        "index_name", "company_name", "ticker", "recommendation_display",
        "quality_score", "momentum_score", "lowvol_score", "composite_score",
        "suggested_allocation_pct",
    ]
    st.dataframe(
        filtered[display_cols], hide_index=True, use_container_width=True,
        column_config={
            "index_name": st.column_config.TextColumn("Index"),
            "company_name": st.column_config.TextColumn("Company"),
            "ticker": st.column_config.TextColumn("Ticker"),
            "recommendation_display": st.column_config.TextColumn(t("recommendation")),
            "quality_score": st.column_config.ProgressColumn(t("quality_score"), min_value=0, max_value=100, format="%.0f"),
            "momentum_score": st.column_config.ProgressColumn(t("momentum_score"), min_value=0, max_value=100, format="%.0f"),
            "lowvol_score": st.column_config.ProgressColumn(t("lowvol_score"), min_value=0, max_value=100, format="%.0f"),
            "composite_score": st.column_config.ProgressColumn(t("composite_score"), min_value=0, max_value=100, format="%.1f"),
            "suggested_allocation_pct": st.column_config.ProgressColumn("Suggested Alloc %", min_value=0, max_value=100, format="%.1f%%"),
        },
    )

    export_df = filtered[display_cols].rename(columns={"recommendation_display": "recommendation"})
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(t("download_csv"), data=to_csv_bytes(export_df), file_name="nse_rebalance_scorecard.csv",
                            mime="text/csv", use_container_width=True)
    with dl2:
        st.download_button(t("download_xlsx"), data=to_excel_bytes(export_df), file_name="nse_rebalance_scorecard.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    section_header(t("allocation_title"), t("allocation_help"))
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

    section_header(t("explanation_title"))
    for _, row in filtered.iterrows():
        with st.expander(
            f"{row['recommendation_display']} — {row['company_name']} ({row['ticker']}) — {row['composite_score']:.1f}/100"
        ):
            st.markdown(generate_explanation(row))

else:
    st.info(f"👆 Click **{t('run_scoring')}** above once you've reviewed the extracted stock list to generate the full dashboard.")


# =============================================================================
# HOW TO DEPLOY (read this, don't run it)
# =============================================================================
# 1. Local run:      streamlit run app.py
# 2. Streamlit Cloud: push this file + requirements.txt to a GitHub repo,
#    then at https://share.streamlit.io -> New app -> pick the repo ->
#    Main file path: app.py -> Deploy. No other files/folders required.
