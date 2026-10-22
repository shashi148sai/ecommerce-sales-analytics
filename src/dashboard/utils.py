"""
SalesPulse Analytics - Dashboard Utilities and Visual Styling
Provides currency formatting (£), KPI card styling, cached data loaders,
and consistent Plotly visualization palettes.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import settings


# ------------------------------------------------------------------------------
# Formatting Utilities
# ------------------------------------------------------------------------------
def format_currency(value: Optional[float], compact: bool = False) -> str:
    """Formats numeric values into GBP (£) standard currency format."""
    if value is None or pd.isna(value):
        return f"{settings.DEFAULT_CURRENCY}0.00"
    
    val = float(value)
    if compact:
        if abs(val) >= 1_000_000:
            return f"{settings.DEFAULT_CURRENCY}{val / 1_000_000:.2f}M"
        if abs(val) >= 1_000:
            return f"{settings.DEFAULT_CURRENCY}{val / 1_000:.1f}K"
            
    return f"{settings.DEFAULT_CURRENCY}{val:,.2f}"


def format_number(value: Optional[int]) -> str:
    """Formats integers with thousands separators."""
    if value is None or pd.isna(value):
        return "0"
    return f"{int(value):,}"


def format_percent(value: Optional[float]) -> str:
    """Formats floats as percentage strings."""
    if value is None or pd.isna(value):
        return "0.0%"
    return f"{float(value):.2f}%"


# ------------------------------------------------------------------------------
# UI KPI Card Component
# ------------------------------------------------------------------------------
def render_kpi_card(
    title: str,
    value: str,
    subtitle: Optional[str] = None,
    delta: Optional[str] = None,
    delta_positive: bool = True
):
    """
    Renders an accessible, responsive KPI card with modern typography and borders.
    """
    delta_color = "#10B981" if delta_positive else "#EF4444"
    delta_html = f"<span style='color: {delta_color}; font-size: 0.85rem; font-weight: 600;'>{delta}</span>" if delta else ""
    sub_html = f"<div style='color: #64748B; font-size: 0.8rem; margin-top: 4px;'>{subtitle}</div>" if subtitle else ""
    
    html = f"""
    <div style="
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    ">
        <div style="font-size: 0.85rem; font-weight: 500; color: #475569; text-transform: uppercase; letter-spacing: 0.05em;">
            {title}
        </div>
        <div style="display: flex; align-items: baseline; justify-content: space-between; margin-top: 8px;">
            <span style="font-size: 1.75rem; font-weight: 700; color: #0F172A;">{value}</span>
            {delta_html}
        </div>
        {sub_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# Cached Data Loaders
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_kpis() -> Dict[str, Any]:
    """Loads overall KPIs from JSON."""
    path = settings.ANALYTICS_DATA_DIR / "kpis_summary.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(show_spinner=False)
def load_monthly_trends() -> pd.DataFrame:
    """Loads monthly trends DataFrame."""
    path = settings.ANALYTICS_DATA_DIR / "monthly_sales_trends.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_daily_trends() -> pd.DataFrame:
    """Loads daily trends DataFrame."""
    path = settings.ANALYTICS_DATA_DIR / "daily_sales_trends.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_top_products_revenue() -> pd.DataFrame:
    """Loads top products by revenue DataFrame."""
    path = settings.ANALYTICS_DATA_DIR / "top_products_by_revenue.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_top_products_quantity() -> pd.DataFrame:
    """Loads top products by volume DataFrame."""
    path = settings.ANALYTICS_DATA_DIR / "top_products_by_quantity.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_country_revenue() -> pd.DataFrame:
    """Loads geographic sales performance DataFrame."""
    path = settings.ANALYTICS_DATA_DIR / "country_wise_revenue.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_repeat_customers() -> Dict[str, Any]:
    """Loads repeat customer statistics from JSON."""
    path = settings.ANALYTICS_DATA_DIR / "repeat_customer_summary.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(show_spinner=False)
def load_data_quality_report() -> Dict[str, Any]:
    """Loads data quality audit report from JSON."""
    path = settings.REPORTS_DIR / "data_quality_report.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(show_spinner=False)
def load_pipeline_metadata() -> Dict[str, Any]:
    """Loads the latest pipeline execution metadata."""
    path = settings.METADATA_DIR / "latest_pipeline_run.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(show_spinner=False)
def load_temporal_patterns() -> Dict[str, pd.DataFrame]:
    """Loads day of week and hourly distribution DataFrames."""
    dow_path = settings.ANALYTICS_DATA_DIR / "day_of_week_sales.csv"
    hod_path = settings.ANALYTICS_DATA_DIR / "hour_of_day_sales.csv"
    return {
        "day_of_week": pd.read_csv(dow_path) if dow_path.exists() else pd.DataFrame(),
        "hour_of_day": pd.read_csv(hod_path) if hod_path.exists() else pd.DataFrame()
    }


@st.cache_data(show_spinner=False)
def load_cleaned_sales_sample(limit: int = 10000) -> pd.DataFrame:
    """Loads a slice of cleaned sales for interactive filtering and RFM modeling."""
    path = settings.PROCESSED_DATA_DIR / "cleaned_sales.parquet"
    if path.exists():
        # Read parquet directly with pyarrow
        return pd.read_parquet(path)
    csv_path = settings.PROCESSED_DATA_DIR / "cleaned_sales.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()


# ------------------------------------------------------------------------------
# Chart Theming
# ------------------------------------------------------------------------------
CHART_COLORS = {
    "primary": "#2563EB",     # Modern Royal Blue
    "secondary": "#0D9488",   # Teal
    "accent": "#F59E0B",      # Amber
    "danger": "#EF4444",      # Crimson / Red
    "success": "#10B981",     # Emerald Green
    "purple": "#8B5CF6",      # Violet
    "slate": "#64748B"        # Slate grey
}


def apply_chart_theme(fig: go.Figure, title: str = "") -> go.Figure:
    """Applies a consistent corporate typography and layout theme to Plotly figures."""
    fig.update_layout(
        title={
            "text": title,
            "y": 0.95,
            "x": 0.0,
            "xanchor": "left",
            "yanchor": "top",
            "font": {"size": 16, "family": "Inter, -apple-system, sans-serif", "color": "#0F172A"}
        },
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title_text=""
        ),
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_size=13,
            font_family="Inter, sans-serif"
        )
    )
    return fig
