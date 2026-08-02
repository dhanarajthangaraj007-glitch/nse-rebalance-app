# 📈 NSE Rebalancing Intelligence Dashboard

A Streamlit web app that ingests an **NSE Indices periodic-review press
release PDF** (Nifty 50, Nifty 100, Nifty Next 50, Nifty Midcap 150,
Nifty 500, etc.), auto-extracts the stocks being **included/excluded**,
and runs a proprietary **Quality / Momentum / Low-Volatility** factor
scoring model on every newly included stock — producing a ranked,
color-coded recommendation dashboard with a suggested portfolio
allocation, in English or Tamil, in light or dark mode.

> ⚠ **Disclaimer:** This is a research/educational tool. The scoring
> model is a proprietary heuristic *inspired by* factor-investing
> principles used in Nifty methodology documents — it is **not** an
> official NSE product and is **not investment advice**.

---

## ✨ Features

- **Drag-and-drop PDF upload** with a bundled "sample data" mode so
  reviewers can try the full flow without a real press release.
- **Automatic extraction** of index name + inclusion/exclusion lists,
  using a layered text + table parsing strategy (pdfplumber), with an
  **editable review table** as a safety net for any PDF quirks.
- **Ticker auto-mapping**: company names are matched to Yahoo Finance
  NSE tickers (`RELIANCE.NS` style) via exact + fuzzy matching against
  a bundled 250+ company lookup table, with manual override.
- **Live market data** (`yfinance`): 6M/12M returns, annualized
  volatility, ROE, Debt/Equity, EPS growth.
- **Proprietary composite scoring**:
  - **Quality (40%)** — ROE (45%) + low Debt/Equity (30%) + EPS growth (25%)
  - **Momentum (35%)** — blended 6M/12M return, risk-adjusted by volatility
  - **Low Volatility (25%)** — inverse of annualized volatility
  - All sub-scores are cross-sectionally normalized (0–100) relative to
    the current batch of newly-included stocks, then combined with
    **user-adjustable weights** (sidebar sliders, auto-normalized to 100%).
- **Recommendation bands**: 🟢 Strong Buy (≥80) · 🟩 Buy (≥65) ·
  🟧 Watch (≥50) · 🔴 Avoid (<50).
- **Dashboard**: KPI summary cards, top-picks strip, filterable +
  sortable scorecard table with progress-bar visualizations, a
  suggested-allocation bar chart, per-stock plain-English score
  explanations, and CSV/Excel export.
- **Dark/Light mode** and **English/Tamil** UI toggle.
- Defensive engineering throughout: missing fundamentals are imputed
  with the peer-group median, failed ticker fetches don't crash the
  batch, and PDF extraction always ends in a human-editable table.

---

## 🗂 Project Structure

```
nse_rebalance_app/
├── app.py                        # Streamlit entry point / UI orchestration
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml               # Theme + upload-size defaults
├── data/
│   └── nse_ticker_mapping.csv    # Company name → Yahoo Finance ticker lookup
└── modules/
    ├── i18n.py                   # English/Tamil translation dictionary
    ├── styling.py                # Custom CSS, KPI cards, badges
    ├── pdf_parser.py             # PDF → {index: inclusions/exclusions}
    ├── ticker_mapper.py          # Company name → ticker (exact + fuzzy)
    ├── market_data.py            # yfinance price/fundamentals fetcher
    ├── scoring.py                # Factor scoring engine + explanations
    ├── sample_data.py            # Bundled demo dataset ("try sample")
    └── utils.py                  # CSV/Excel export helpers
```

---

## 🚀 Run Locally

```bash
# 1. Clone / copy the project, then from the project root:
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch
streamlit run app.py
```

The app opens at `http://localhost:8501`. Click **"Try bundled sample
data"** to see the full dashboard instantly, or upload a real NSE
rebalancing press release PDF.

---

## ☁️ Deploy on Streamlit Community Cloud (free)

1. Push this project to a **public (or private) GitHub repository**,
   keeping the folder structure above intact (the CSV in `data/` and
   the `modules/` package must be committed).
2. Go to **https://share.streamlit.io** → **"New app"**.
3. Select your repo, branch, and set **Main file path** to `app.py`.
4. Click **Deploy**. Streamlit Cloud will read `requirements.txt`
   automatically and install everything.
5. No secrets/API keys are required — `yfinance` calls Yahoo Finance's
   public endpoints directly.

**Tips for Streamlit Cloud:**
- If you hit Yahoo Finance rate-limiting under heavy simultaneous
  traffic, consider lowering `ttl` in `market_data.fetch_stock_metrics`'s
  `@st.cache_data` decorator or adding your own caching/proxy layer.
- `maxUploadSize` is set to 25MB in `.streamlit/config.toml`, which
  comfortably covers NSE press-release PDFs (typically <5MB).

## ☁️ Alternative: Deploy on Railway / Render

Both support Python web services directly from a repo:

- **Start command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- **Build command:** `pip install -r requirements.txt`
- Expose the port Streamlit binds to (Railway/Render auto-detect `$PORT`).

---

## 🧠 How the Scoring Model Works (Methodology Notes)

1. **Data collection** — for every newly-included stock's mapped ticker,
   fetch ~14 months of daily price history and the latest fundamentals
   snapshot via Yahoo Finance.
2. **Raw metric computation**:
   - `return_6m`, `return_12m`: trailing total price return.
   - `volatility_annualized`: std-dev of daily log returns × √252.
   - `roe`, `debt_to_equity`, `eps_growth`: pulled from Yahoo's
     fundamentals endpoint (`Ticker.get_info()`), which can vary in
     coverage stock-to-stock — missing values are imputed with the
     **peer-group median** so a single missing field doesn't unfairly
     zero out a stock's score.
3. **Cross-sectional normalization** — every raw metric is scaled to
   0–100 **relative to the other newly-included stocks in the same
   batch** (winsorized at the 5th/95th percentile to limit outlier
   distortion), similar in spirit to how factor indices rank their
   eligible universe rather than using fixed absolute thresholds.
4. **Composite score** = `Quality×wq + Momentum×wm + LowVol×wlv`,
   with `wq/wm/wlv` defaulting to 40/35/25 and adjustable in the sidebar
   (auto-normalized to sum to 100%).
5. **Recommendation band** and **suggested allocation** (proportional
   to composite score among Buy-rated-and-above names, normalized to
   100%) are derived directly from the composite score.

This is a **relative, batch-based** scoring system: scores describe how
a stock stacks up against its fellow new entrants in *this* rebalancing
event, not against the entire market.

---

## 🔧 Extending the App

- **More languages**: add another `"xx"` key to each entry in
  `modules/i18n.py`'s `TRANSLATIONS` dict.
- **More tickers**: append rows to `data/nse_ticker_mapping.csv`
  (`company_name,ticker`) — no code changes needed.
- **Historical comparison**: `market_data.py` already fetches ~14
  months of price history; you can extend `scoring.py` to snapshot and
  diff scores across multiple uploaded press releases over time using
  `st.session_state` or a small local SQLite/CSV log.
- **Adjustable recommendation thresholds**: currently fixed at
  80/65/50 in `scoring.RECO_THRESHOLDS` for stability of the "Strong
  Buy/Buy/Watch/Avoid" language — expose as sidebar sliders if you want
  full user control.

---

## 📜 License / Data Sources

- Price & fundamentals data: Yahoo Finance (via `yfinance`), for
  research/educational use.
- Ticker mapping: manually curated static list covering common Nifty
  500 constituents; may need periodic updates as index constituents
  and corporate actions change.
