"""
Unit tests for Indian-First Localization, Currency Conversion,
Fiscal Year & Quarter calculations, and Schema Mapping.
"""

import pytest
import pandas as pd
from datetime import datetime

from config import settings
from src.dashboard.utils import (
    format_indian_number,
    format_compact_indian,
    format_compact_standard,
    format_currency,
    format_number,
    format_date_indian,
    get_indian_financial_year,
    get_indian_fy_quarter,
    get_active_currency_config
)
from src.validation.validator import detect_schema_mapping


# ------------------------------------------------------------------------------
# 1. Indian Number Grouping Tests
# ------------------------------------------------------------------------------
def test_format_indian_number():
    """Verifies Indian numbering grouping (1,00,000 / 10,00,000 / 1,00,00,000)."""
    assert format_indian_number(0) == "0"
    assert format_indian_number(None) == "0"
    assert format_indian_number(999) == "999"
    assert format_indian_number(1000) == "1,000"
    assert format_indian_number(10000) == "10,000"
    assert format_indian_number(100000) == "1,00,000"       # 1 Lakh
    assert format_indian_number(1000000) == "10,00,000"     # 10 Lakh
    assert format_indian_number(10000000) == "1,00,00,000"  # 1 Crore
    assert format_indian_number(541909) == "5,41,909"       # Dataset row count in Indian notation
    
    # Decimals
    assert format_indian_number(123456.78, decimals=2) == "1,23,456.78"
    assert format_indian_number(-9876543.21, decimals=2) == "-98,76,543.21"


# ------------------------------------------------------------------------------
# 2. Compact Notation (Lakh & Crore vs Western M & K)
# ------------------------------------------------------------------------------
def test_format_compact_indian():
    """Verifies Indian compact commercial notations (Cr, L, K)."""
    assert format_compact_indian(10_640_000, currency_symbol="₹") == "₹1.06 Cr"
    assert format_compact_indian(1_500_000, currency_symbol="₹") == "₹15.00 L"
    assert format_compact_indian(150_000, currency_symbol="₹") == "₹1.50 L"
    assert format_compact_indian(45_200, currency_symbol="₹") == "₹45.2 K"
    assert format_compact_indian(500, currency_symbol="₹") == "₹500.00"
    assert format_compact_indian(-10_000_000, currency_symbol="₹") == "-₹1.00 Cr"


def test_format_compact_standard():
    """Verifies standard Western compact notation (M, K)."""
    assert format_compact_standard(10_640_000, currency_symbol="£") == "£10.64M"
    assert format_compact_standard(45_200, currency_symbol="£") == "£45.2K"
    assert format_compact_standard(150, currency_symbol="£") == "£150.00"


# ------------------------------------------------------------------------------
# 3. Currency Conversion & Formatting
# ------------------------------------------------------------------------------
def test_currency_conversion_math():
    """Tests conversion from canonical GBP to INR at specified exchange rates."""
    reference_rate = 106.50
    gbp_val = 100.0
    expected_inr = gbp_val * reference_rate
    
    # Test with explicit overrides
    formatted_inr = format_currency(
        gbp_val,
        override_symbol="₹",
        override_rate=reference_rate,
        use_indian_format=True
    )
    assert formatted_inr == "₹10,650.00"
    
    # Test compact INR
    formatted_inr_compact = format_currency(
        100_000,
        compact=True,
        override_symbol="₹",
        override_rate=reference_rate,
        use_indian_format=True
    )
    # 100,000 * 106.50 = 10,650,000 = 1.065 Cr -> 1.07 Cr or 1.06 Cr
    assert "Cr" in formatted_inr_compact
    assert "₹" in formatted_inr_compact


# ------------------------------------------------------------------------------
# 4. Indian Financial Year (FY: 1 April – 31 March) & Quarters
# ------------------------------------------------------------------------------
def test_indian_financial_year():
    """Verifies Indian fiscal year calculations."""
    # Canonical dataset spans 01/12/2010 to 09/12/2011
    assert get_indian_financial_year("2010-12-01") == "FY 2010-11"
    assert get_indian_financial_year("2011-01-15") == "FY 2010-11"
    assert get_indian_financial_year("2011-03-31") == "FY 2010-11"
    assert get_indian_financial_year("2011-04-01") == "FY 2011-12"
    assert get_indian_financial_year("2011-09-01") == "FY 2011-12"
    assert get_indian_financial_year("2011-12-09") == "FY 2011-12"
    assert get_indian_financial_year(None) == "N/A"


def test_indian_fy_quarter():
    """Verifies Indian financial quarters (Q1: Apr-Jun, Q2: Jul-Sep, Q3: Oct-Dec, Q4: Jan-Mar)."""
    assert get_indian_fy_quarter("2011-04-15") == "Q1 (Apr-Jun)"
    assert get_indian_fy_quarter("2011-06-30") == "Q1 (Apr-Jun)"
    assert get_indian_fy_quarter("2011-07-01") == "Q2 (Jul-Sep)"
    assert get_indian_fy_quarter("2011-09-30") == "Q2 (Jul-Sep)"
    assert get_indian_fy_quarter("2010-12-01") == "Q3 (Oct-Dec)"
    assert get_indian_fy_quarter("2011-01-10") == "Q4 (Jan-Mar)"
    assert get_indian_fy_quarter("2011-03-31") == "Q4 (Jan-Mar)"
    assert get_indian_fy_quarter(None) == "N/A"


def test_format_date_indian():
    """Verifies standard DD-MM-YYYY date formatting."""
    assert format_date_indian("2011-12-09 12:50:00") == "09-12-2011"
    assert format_date_indian(datetime(2010, 12, 1, 8, 26)) == "01-12-2010"
    assert format_date_indian(None) == "-"


# ------------------------------------------------------------------------------
# 5. Schema Mapping & Detection Tests
# ------------------------------------------------------------------------------
def test_detect_schema_mapping_canonical():
    """Verifies schema detection on canonical UCI dataset headers."""
    canonical_cols = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
    mapping, missing = detect_schema_mapping(canonical_cols)
    assert len(missing) == 0
    assert mapping["InvoiceNo"] == "InvoiceNo"
    assert mapping["StockCode"] == "StockCode"
    assert mapping["Quantity"] == "Quantity"
    assert mapping["UnitPrice"] == "UnitPrice"


def test_detect_schema_mapping_aliases():
    """Verifies intelligent alias resolution (e.g. order_id, sku, item_price, user_id)."""
    custom_cols = ["order_id", "sku", "product_description", "qty", "order_date", "item_price", "user_id", "shipping_country"]
    mapping, missing = detect_schema_mapping(custom_cols)
    assert len(missing) == 0
    assert mapping["order_id"] == "InvoiceNo"
    assert mapping["sku"] == "StockCode"
    assert mapping["product_description"] == "Description"
    assert mapping["qty"] == "Quantity"
    assert mapping["order_date"] == "InvoiceDate"
    assert mapping["item_price"] == "UnitPrice"
    assert mapping["user_id"] == "CustomerID"
    assert mapping["shipping_country"] == "Country"


def test_detect_schema_mapping_missing_required():
    """Verifies missing fields are detected properly when incompatible headers are supplied."""
    incomplete_cols = ["order_id", "sku", "price"]
    mapping, missing = detect_schema_mapping(incomplete_cols)
    assert "Quantity" in missing
    assert "InvoiceDate" in missing
    assert "Description" in missing
    assert "Country" in missing
