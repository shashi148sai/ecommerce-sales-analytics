"""
SalesPulse Analytics - Dashboard Utilities and Visual Styling
Indian-First Localization (en-IN, Asia/Kolkata, DD-MM-YYYY, Lakh/Crore notation)
Provides dual currency support (GBP original vs INR converted reference rate),
Streamlit native bordered KPI cards, cached data loaders, and Plotly palettes.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import settings


# ------------------------------------------------------------------------------
# Indian-First Number & Currency Formatting
# ------------------------------------------------------------------------------
def format_indian_number(val: Optional[Union[int, float]], decimals: int = 0) -> str:
    """
    Formats integers or floats using the Indian numbering system grouping:
    e.g. 1,00,00,000 (Crore), 10,00,000 (10 Lakh), 1,00,000 (1 Lakh).
    """
    if val is None or pd.isna(val):
        return "0"
    
    is_neg = val < 0
    val = abs(val)
    
    if decimals > 0:
        int_part = int(val)
        dec_part = f"{val - int_part:.{decimals}f}"[1:]  # includes the '.'
    else:
        int_part = int(round(val))
        dec_part = ""
        
    s = str(int_part)
    if len(s) <= 3:
        formatted_int = s
    else:
        last3 = s[-3:]
        rem = s[:-3]
        groups = []
        while len(rem) > 2:
            groups.append(rem[-2:])
            rem = rem[:-2]
        if rem:
            groups.append(rem)
        formatted_int = ",".join(reversed(groups)) + "," + last3
        
    return f"-{formatted_int}{dec_part}" if is_neg else f"{formatted_int}{dec_part}"


def format_compact_standard(val: Optional[Union[int, float]], currency_symbol: str = "") -> str:
    """
    Formats numbers into standard Western compact notation:
    - >= 1,000,000 -> X.XX M (Million)
    - >= 1,000     -> X.X K (Thousand)
    - else         -> formatted with 2 decimals if currency, or exact
    """
    if val is None or pd.isna(val):
        return f"{currency_symbol}0.00" if currency_symbol else "0"
        
    prefix = f"{currency_symbol}" if currency_symbol else ""
    is_neg = val < 0
    val_abs = abs(val)
    sign = "-" if is_neg else ""
    
    if val_abs >= 1_000_000:
        return f"{sign}{prefix}{val_abs / 1_000_000:.2f}M"
    elif val_abs >= 1_000:
        return f"{sign}{prefix}{val_abs / 1_000:.1f}K"
    else:
        return f"{sign}{prefix}{val_abs:,.2f}" if currency_symbol else f"{sign}{val_abs:,}"


def format_compact_indian(val: Optional[Union[int, float]], currency_symbol: str = "") -> str:
    """
    Formats numbers into compact Indian commercial notation:
    - >= 1,00,00,000 -> X.XX Cr (Crore)
    - >= 1,00,000    -> X.XX L (Lakh)
    - >= 1,000       -> X.X K (Thousand)
    - else           -> formatted with Indian commas
    """
    if val is None or pd.isna(val):
        return f"{currency_symbol}0" if currency_symbol else "0"
        
    prefix = f"{currency_symbol}" if currency_symbol else ""
    is_neg = val < 0
    val_abs = abs(val)
    sign = "-" if is_neg else ""
    
    if val_abs >= 10_000_000:  # 1 Crore
        return f"{sign}{prefix}{val_abs / 10_000_000:.2f} Cr"
    elif val_abs >= 100_000:    # 1 Lakh
        return f"{sign}{prefix}{val_abs / 100_000:.2f} L"
    elif val_abs >= 1_000:
        return f"{sign}{prefix}{val_abs / 1_000:.1f} K"
    else:
        return f"{sign}{prefix}{val_abs:,.2f}" if currency_symbol else f"{sign}{val_abs:,}"


def get_active_currency_config() -> Tuple[str, str, float]:
    """
    Retrieves the user's active presentation currency mode, symbol, and multiplier from session_state.
    Defaults to INR (₹) - Indian Rupees as required by project guidelines.
    Dynamically accounts for dataset source currency (e.g. GBP vs INR) so that native INR datasets
    are never erroneously multiplied by conversion rates.
    """
    mode = st.session_state.get("currency_mode", "INR (₹)")
    source_curr = str(st.session_state.get("dataset_source_currency", "GBP")).upper()
    inr_rate = float(st.session_state.get("inr_conversion_rate", settings.DEFAULT_GBP_TO_INR_RATE))
    
    if mode.startswith("INR") or mode == "INR":
        symbol = "₹"
        code = "INR"
        # If source is GBP, apply reference exchange rate; if already INR, multiplier is 1.0
        rate = inr_rate if source_curr == "GBP" else 1.0
    else:
        symbol = "£"
        code = "GBP"
        # If source is INR and user wants GBP, divide; if already GBP, multiplier is 1.0
        rate = (1.0 / inr_rate) if source_curr == "INR" else 1.0
        
    return symbol, code, rate


def format_currency(
    value: Optional[float],
    compact: bool = False,
    override_symbol: Optional[str] = None,
    override_rate: Optional[float] = None,
    use_indian_format: Optional[bool] = None
) -> str:
    """
    Formats currency amounts with appropriate localization.
    Defaults to INR (₹) and Indian number grouping (Lakh/Crore) unless overridden.
    Never outputs the euro symbol (€).
    """
    if value is None or pd.isna(value):
        symbol = override_symbol or st.session_state.get("active_currency_symbol", settings.DEFAULT_CURRENCY)
        return f"{symbol}0.00"
        
    symbol, code, rate = get_active_currency_config()
    if override_symbol is not None:
        symbol = override_symbol
    if override_rate is not None:
        rate = override_rate
        
    converted_val = float(value) * rate
    if override_symbol is not None and override_symbol != "₹":
        is_indian = use_indian_format if use_indian_format is not None else False
    else:
        is_indian = use_indian_format if use_indian_format is not None else (code == "INR" or symbol == "₹")
    
    if compact:
        if is_indian:
            return format_compact_indian(converted_val, currency_symbol=symbol)
        else:
            return format_compact_standard(converted_val, currency_symbol=symbol)
            
    if is_indian:
        return f"{symbol}{format_indian_number(converted_val, decimals=2)}"
    return f"{symbol}{converted_val:,.2f}"


def check_available_analyses(df_or_cols: Union[pd.DataFrame, List[str], Dict[str, Any], set]) -> Dict[str, Any]:
    """
    Evaluates which analytical modules are supported by the active dataset schema.
    Uses intelligent schema mapping to recognize alias variations.
    
    Returns:
        Dictionary mapping capability keys to booleans with human-readable rationale.
    """
    if isinstance(df_or_cols, pd.DataFrame):
        cols = list(df_or_cols.columns)
    elif isinstance(df_or_cols, dict):
        cols = list(df_or_cols.keys())
    elif isinstance(df_or_cols, (list, tuple, set)):
        cols = list(df_or_cols)
    else:
        cols = []
        
    from src.validation.validator import detect_schema_mapping
    mapping, _ = detect_schema_mapping([str(c) for c in cols])
    mapped_targets = set(mapping.values())
    
    # Direct presence check (in case standard names already exist)
    direct_set = {str(c).strip() for c in cols}
    mapped_targets.update(direct_set)
    
    # Revenue analysis: needs (Quantity and UnitPrice) OR SalesAmount
    has_qty = "Quantity" in mapped_targets
    has_price = "UnitPrice" in mapped_targets
    has_sales = "SalesAmount" in mapped_targets
    revenue_available = (has_qty and has_price) or has_sales
    
    # Time-series: needs Date / InvoiceDate
    has_date = "InvoiceDate" in mapped_targets
    
    # Product analysis: needs Description or StockCode
    has_product = "Description" in mapped_targets or "StockCode" in mapped_targets
    
    # Customer analysis: needs CustomerID
    has_customer = "CustomerID" in mapped_targets
    
    # Regional analysis: needs Country
    has_region = "Country" in mapped_targets
    
    explanations = {}
    if not revenue_available:
        explanations["revenue"] = "Requires either (Quantity + Unit Price) or a pre-calculated Total Sales Amount."
    if not has_date:
        explanations["time_series"] = "Requires an Order Date or Transaction Date column to analyze temporal trends and seasonality."
    if not has_product:
        explanations["product"] = "Requires a Product Code/SKU or Item Description to rank bestselling catalog items."
    if not has_customer:
        explanations["customer"] = "Requires Customer IDs to calculate customer retention, repeat orders, and RFM loyalty tiers."
    if not has_region:
        explanations["regional"] = "Requires a Country or Geographic Region field to map regional sales distribution."
        
    return {
        "revenue_analysis": revenue_available,
        "time_series_analysis": has_date,
        "product_analysis": has_product,
        "customer_analysis": has_customer,
        "regional_analysis": has_region,
        "explanations": explanations
    }


def get_csv_template() -> str:
    """Returns a ready-to-use CSV template string with realistic e-commerce sample data."""
    return (
        "InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country\n"
        "536365,85123A,WHITE HANGING HEART T-LIGHT HOLDER,6,01-12-2010 08:26,2.55,17850,United Kingdom\n"
        "536365,71053,WHITE METAL LANTERN,6,01-12-2010 08:26,3.39,17850,United Kingdom\n"
        "536365,84406B,CREAM CUPID HEARTS COAT HANGER,8,01-12-2010 08:26,2.75,17850,United Kingdom\n"
        "536366,22633,HAND WARMER UNION JACK,6,01-12-2010 08:28,1.85,17850,United Kingdom\n"
        "536367,84879,ASSORTED COLOUR BIRD ORNAMENT,32,01-12-2010 08:34,1.69,13047,United Kingdom\n"
        "C536379,D,Discount,-1,01-12-2010 09:41,27.50,14527,United Kingdom\n"
    )


def format_number(
    value: Optional[int],
    compact: bool = False,
    use_indian_format: Optional[bool] = None
) -> str:
    """Formats numeric counts using standard or Indian numbering system."""
    if value is None or pd.isna(value):
        return "0"
        
    _, code, _ = get_active_currency_config()
    is_indian = use_indian_format if use_indian_format is not None else (code == "INR")
    
    if compact:
        if is_indian:
            return format_compact_indian(value)
        return format_compact_standard(value)
        
    if is_indian:
        return format_indian_number(value, decimals=0)
    return f"{int(round(value)):,}"


def format_percent(value: Optional[float]) -> str:
    """Formats floats as percentage strings."""
    if value is None or pd.isna(value):
        return "0.0%"
    return f"{float(value):.2f}%"


def format_date_indian(dt: Any) -> str:
    """Formats a datetime/date object into Indian standard DD-MM-YYYY format."""
    if dt is None or pd.isna(dt):
        return "-"
    try:
        ts = pd.to_datetime(dt)
        return ts.strftime("%d-%m-%Y")
    except Exception:
        return str(dt)


# ------------------------------------------------------------------------------
# Indian Financial Year (FY) Helpers (1 April - 31 March)
# ------------------------------------------------------------------------------
def get_indian_financial_year(dt: Any) -> str:
    """
    Calculates the Indian Financial Year for a given date.
    April to March cycle: e.g. Dec 2010 -> FY 2010-11, Jan 2011 -> FY 2010-11.
    """
    try:
        ts = pd.to_datetime(dt)
        if pd.isna(ts):
            return "N/A"
        year = ts.year
        month = ts.month
        if month >= 4:
            return f"FY {year}-{str(year + 1)[-2:]}"
        else:
            return f"FY {year - 1}-{str(year)[-2:]}"
    except Exception:
        return "N/A"


def get_indian_fy_quarter(dt: Any) -> str:
    """
    Calculates the Indian FY Quarter:
    - Q1: April to June
    - Q2: July to September
    - Q3: October to December
    - Q4: January to March
    """
    try:
        ts = pd.to_datetime(dt)
        if pd.isna(ts):
            return "N/A"
        m = ts.month
        if m in (4, 5, 6):
            return "Q1 (Apr-Jun)"
        elif m in (7, 8, 9):
            return "Q2 (Jul-Sep)"
        elif m in (10, 11, 12):
            return "Q3 (Oct-Dec)"
        else:
            return "Q4 (Jan-Mar)"
    except Exception:
        return "N/A"


# ------------------------------------------------------------------------------
# UI KPI Card Component (Streamlit Native Bordered Containers)
# ------------------------------------------------------------------------------
def render_kpi_card(
    title: str,
    value: str,
    subtitle: Optional[str] = None,
    delta: Optional[str] = None,
    delta_positive: bool = True
):
    """
    Renders an accessible, responsive KPI card using Streamlit's native bordered container
    and metric component, guaranteeing zero HTML leakage and consistent column alignment.
    """
    with st.container(border=True):
        st.metric(
            label=title.upper(),
            value=value,
            delta=delta if delta else None,
            delta_color="normal" if delta_positive else "inverse"
        )
        if subtitle:
            st.caption(subtitle)


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
        df = pd.read_csv(path)
        if "Date" in df.columns:
            df["DateObj"] = pd.to_datetime(df["Date"])
            df["DisplayDate"] = df["DateObj"].dt.strftime("%d-%m-%Y")
            df["FinancialYear"] = df["DateObj"].apply(get_indian_financial_year)
            df["FYQuarter"] = df["DateObj"].apply(get_indian_fy_quarter)
        return df
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
        return pd.read_parquet(path)
    csv_path = settings.PROCESSED_DATA_DIR / "cleaned_sales.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()


# ------------------------------------------------------------------------------
# Chart Theming
# ------------------------------------------------------------------------------
CHART_COLORS = {
    "primary": "#1E3A8A",     # Deep Navy / Royal Blue
    "secondary": "#0D9488",   # Teal
    "accent": "#D97706",      # Warm Amber / Saffron
    "danger": "#DC2626",      # Crimson / Red
    "success": "#059669",     # Emerald Green
    "purple": "#7C3AED",      # Royal Violet
    "slate": "#64748B"        # Slate grey
}


def apply_chart_theme(fig: go.Figure, title: str = "") -> go.Figure:
    """Applies a consistent corporate typography and responsive layout theme to Plotly figures."""
    fig.update_layout(
        title={
            "text": title,
            "y": 0.98,
            "x": 0.0,
            "xanchor": "left",
            "yanchor": "top",
            "font": {"size": 15, "family": "Inter, -apple-system, sans-serif", "color": "#0F172A"}
        },
        template="plotly_white",
        margin=dict(l=50, r=40, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="right",
            x=1.0,
            title_text=""
        ),
        xaxis=dict(automargin=True),
        yaxis=dict(automargin=True),
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_size=13,
            font_family="Inter, sans-serif"
        )
    )
    return fig
