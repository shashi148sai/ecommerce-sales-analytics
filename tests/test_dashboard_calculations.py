"""
Unit tests for dashboard formatting, KPI calculation logic, and chart utilities.
"""

import pytest
import pandas as pd
import plotly.graph_objects as go
from config import settings
from src.dashboard.utils import (
    format_currency,
    format_number,
    format_percent,
    apply_chart_theme,
    load_kpis,
    load_monthly_trends,
    load_top_products_revenue
)


def test_format_currency():
    """Verifies that currency adheres strictly to INR (₹) by default and supports GBP (£) mode."""
    # Default presentation mode is INR (₹) with reference rate conversion for canonical GBP
    assert format_currency(0) == "₹0.00"
    assert format_currency(None) == "₹0.00"
    
    # Explicit INR direct mode (1:1 native INR)
    assert format_currency(1234.56, override_symbol="₹", override_rate=1.0) == "₹1,234.56"
    assert format_currency(10_640_000, compact=True, override_symbol="₹", override_rate=1.0) == "₹1.06 Cr"
    
    # GBP mode with explicit overrides
    assert format_currency(1234.56, override_symbol="£", override_rate=1.0) == "£1,234.56"
    assert format_currency(10_640_000, compact=True, override_symbol="£", override_rate=1.0) == "£10.64M"
    assert format_currency(45_200, compact=True, override_symbol="£", override_rate=1.0) == "£45.2K"
    assert format_currency(150, compact=True, override_symbol="£", override_rate=1.0) == "£150.00"


def test_format_number():
    """Verifies thousands separation and Indian grouping formatting."""
    # Under Indian default, uses Indian numbering (5,41,909)
    assert format_number(541909, use_indian_format=True) == "5,41,909"
    # In standard mode, uses standard comma (541,909)
    assert format_number(541909, use_indian_format=False) == "541,909"
    assert format_number(0) == "0"
    assert format_number(None) == "0"


def test_format_percent():
    """Verifies percentage formatting."""
    assert format_percent(8.40) == "8.40%"
    assert format_percent(0) == "0.00%"
    assert format_percent(None) == "0.0%"


def test_apply_chart_theme():
    """Verifies application of corporate typography and layout theme."""
    fig = go.Figure(go.Scatter(x=[1, 2], y=[3, 4]))
    fig_themed = apply_chart_theme(fig, title="Test Chart")
    
    assert fig_themed.layout.title.text == "Test Chart"
    assert fig_themed.layout.template.layout.margin is not None


def test_data_loaders_integration():
    """Verifies that data loaders retrieve the persisted outputs correctly."""
    kpis = load_kpis()
    assert isinstance(kpis, dict)
    if kpis:
        assert "gross_revenue" in kpis
        assert "net_revenue" in kpis
        assert kpis["currency"] in ["£", "₹", settings.DEFAULT_CURRENCY]
        
    monthly = load_monthly_trends()
    assert isinstance(monthly, pd.DataFrame)
    if not monthly.empty:
        assert "YearMonth" in monthly.columns
        assert "MonthlyRevenue" in monthly.columns
        
    top_rev = load_top_products_revenue()
    assert isinstance(top_rev, pd.DataFrame)
    if not top_rev.empty:
        assert "StockCode" in top_rev.columns
        assert "TotalRevenue" in top_rev.columns
