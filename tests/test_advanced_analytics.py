"""
Unit tests for Sales Forecasting, RFM Customer Segmentation, and Benchmarking.
"""

import pytest
import pandas as pd
import numpy as np
from src.analytics.advanced import perform_sales_forecasting, compute_rfm_segmentation
from src.analytics.benchmark import generate_synthetic_benchmark_dataset


def test_sales_forecasting():
    """Verifies time-series forecasting, hold-out error calculation, and future projections."""
    # Create 30 days of synthetic daily sales with an upward trend and weekly cycle
    dates = pd.date_range(start="2011-01-01", periods=30, freq="D")
    base_rev = 1000 + np.arange(30) * 15 + (np.arange(30) % 7) * 50
    daily_df = pd.DataFrame({"Date": dates, "DailyRevenue": base_rev})
    
    result = perform_sales_forecasting(daily_df, forecast_days=7, test_ratio=0.2)
    
    # Check evaluation metrics
    metrics = result["evaluation_metrics"]
    assert "MAE" in metrics
    assert "RMSE" in metrics
    assert "MAPE_percent" in metrics
    assert metrics["holdout_test_days"] == 6
    assert metrics["MAE"] >= 0.0
    
    # Check forecast output length
    assert len(result["forecast"]) == 7
    assert "ForecastedRevenue" in result["forecast"][0]
    assert "LowerBound" in result["forecast"][0]
    assert "UpperBound" in result["forecast"][0]


def test_rfm_segmentation():
    """Verifies RFM feature calculation and clustering."""
    data = {
        "CustomerID": ["101", "101", "102", "103", "103", "103", "104"],
        "InvoiceNo": ["INV1", "INV2", "INV3", "INV4", "INV5", "INV6", "INV7"],
        "InvoiceTimestamp": [
            "2011-12-01 10:00:00",
            "2011-12-05 11:00:00",
            "2011-10-15 12:00:00",
            "2011-12-08 14:00:00",
            "2011-12-08 15:00:00",
            "2011-12-09 09:00:00",
            "2011-05-01 08:00:00"
        ],
        "LineTotal": [150.0, 200.0, 45.0, 300.0, 500.0, 250.0, 20.0]
    }
    df = pd.DataFrame(data)
    
    rfm, summary = compute_rfm_segmentation(df, n_clusters=2)
    
    assert len(rfm) == 4  # 4 distinct customers
    assert "Recency" in rfm.columns
    assert "Frequency" in rfm.columns
    assert "Monetary" in rfm.columns
    assert "Segment" in rfm.columns
    
    # Customer 103 should have highest frequency (3) and highest monetary (1050)
    c103 = rfm[rfm["CustomerID"] == "103"].iloc[0]
    assert c103["Frequency"] == 3
    assert c103["Monetary"] == 1050.0
    
    # Customer 104 should have highest recency (oldest purchase)
    c104 = rfm[rfm["CustomerID"] == "104"].iloc[0]
    assert c104["Recency"] > c103["Recency"]
    
    assert not summary.empty
    assert "CustomerCount" in summary.columns


def test_benchmark_synthetic_data_generation(spark_session, sample_raw_dataframe):
    """Verifies synthetic scaling dataset generation with distinct prefixes."""
    target_count = 20
    bench_df = generate_synthetic_benchmark_dataset(
        spark_session, sample_raw_dataframe, target_row_count=target_count
    )
    
    assert bench_df.count() == target_count
    # Check that invoices are prefixed as synthetic
    first_invoice = bench_df.first()["InvoiceNo"]
    assert first_invoice.startswith("SYN-")
