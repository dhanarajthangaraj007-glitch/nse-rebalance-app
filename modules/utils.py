"""
utils.py
--------
Small stateless helper functions shared across the app: CSV/Excel export
buffers and a couple of formatting utilities.
"""

from __future__ import annotations

import io

import pandas as pd


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to UTF-8 CSV bytes for st.download_button."""
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Scorecard") -> bytes:
    """Serialize a DataFrame to an in-memory .xlsx file's bytes."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        # Auto-fit-ish column widths for readability
        worksheet = writer.sheets[sheet_name]
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[worksheet.cell(row=1, column=i + 1).column_letter].width = min(max_len, 40)
    buffer.seek(0)
    return buffer.read()


def format_pct(value, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value * 100:.{decimals}f}%"
