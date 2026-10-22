"""
Unit tests for PySpark data cleaning, business rules, cancellations, and revenue calculations.
"""

import pytest
from src.processing.transformer import transform_and_clean_data, compute_transformation_summary


def test_customer_id_cleaning(sample_raw_dataframe):
    """Verifies that floats like '17850.0' become '17850' as a string, and nulls remain null."""
    master_df, _, _ = transform_and_clean_data(sample_raw_dataframe)
    
    rows = master_df.filter(master_df.InvoiceNo == "536365").collect()
    for row in rows:
        assert row["CustomerID"] == "17850"
        
    guest_row = master_df.filter(master_df.InvoiceNo == "536366").first()
    assert guest_row["CustomerID"] is None


def test_duplicate_removal(sample_raw_dataframe):
    """Verifies that exact duplicates are eliminated."""
    master_df, _, _ = transform_and_clean_data(sample_raw_dataframe)
    # 8 raw rows - 1 duplicate = 7 distinct rows
    assert master_df.count() == 7


def test_revenue_and_cancellation_logic(sample_raw_dataframe):
    """Verifies LineTotal calculation and separation into sales vs returns."""
    master_df, sales_df, returns_df = transform_and_clean_data(sample_raw_dataframe)
    
    # Check LineTotal on 536365 item: qty 6, price 2.55 -> 15.30
    item = sales_df.filter((sales_df.InvoiceNo == "536365") & (sales_df.StockCode == "85123A")).first()
    assert item is not None
    assert round(item["LineTotal"], 2) == 15.30
    assert item["IsValidSale"] is True
    assert item["IsCancellation"] is False
    
    # Check returns dataframe: should contain C536379 and 536380 (negative qty)
    return_invoices = [r["InvoiceNo"] for r in returns_df.collect()]
    assert "C536379" in return_invoices
    assert "536380" in return_invoices
    
    # Zero price item (536381) should NOT be in sales_df
    zero_price_sales = sales_df.filter(sales_df.InvoiceNo == "536381").count()
    assert zero_price_sales == 0


def test_transformation_summary_metrics(sample_raw_dataframe):
    """Verifies financial metrics: gross sales, return adjustment, net sales, and AOV."""
    master_df, sales_df, returns_df = transform_and_clean_data(sample_raw_dataframe)
    summary = compute_transformation_summary(master_df, sales_df, returns_df)
    
    # Valid sales in sample:
    # 536365: (6 * 2.55 = 15.30) + (2 * 3.39 = 6.78) = 22.08
    # 536366: (4 * 1.85 = 7.40)
    # 536382: (4 * 3.75 = 15.00)
    # Total Gross: 22.08 + 7.40 + 15.00 = 44.48
    assert summary["gross_sales_amount"] == 44.48
    assert summary["distinct_orders"] == 3
    assert summary["average_order_value"] == round(44.48 / 3, 2)
    assert summary["total_units_sold"] == 16  # 6 + 2 + 4 + 4
    
    # Returns in sample:
    # C536379: -1 * 27.50 = -27.50
    # 536380: -3 * 1.25 = -3.75
    # Total Returns: 31.25
    assert summary["return_adjustments_amount"] == 31.25
    assert summary["net_sales_amount"] == round(44.48 - 31.25, 2)
