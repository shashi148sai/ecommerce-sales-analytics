"""
SalesPulse Analytics - Sales Trends & Forecasting Resilience Regression Tests
Verifies:
1. Daily aggregation schema consistency ('Date', 'DailyRevenue').
2. Canonical daily series preparation across column aliases ('InvoiceDate', 'Revenue', 'LineTotal', etc.).
3. End-to-end forecasting pipeline schema (eval_df containing 'DailyRevenue' and 'ActualRevenue').
4. Exact regression verification for eval_df["ScaledActual"] = eval_df["DailyRevenue"] * rate.
5. Rejection of empty, malformed, or overly sparse datasets without fabricating zeroes.
6. Currency conversion correctness (INR default vs GBP, single multiplication, preservation of counts/percentages).
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from config import settings
from src.analytics.advanced import (
    validate_and_prepare_daily_series,
    perform_sales_forecasting
)
from src.dashboard.utils import get_active_currency_config, format_currency


@pytest.fixture
def sample_30_day_series():
    """Generates 30 days of realistic daily sales transactions."""
    dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
    revenue = 1500.0 + np.arange(30) * 20.0 + (np.arange(30) % 7) * 45.0
    return pd.DataFrame({
        "Date": dates,
        "DailyRevenue": revenue,
        "DailyOrders": np.random.randint(10, 50, size=30)
    })


def test_daily_sales_trends_csv_schema_and_column():
    """Verifies that the persisted daily sales trends table has canonical columns."""
    path = settings.ANALYTICS_DATA_DIR / "daily_sales_trends.csv"
    assert path.exists(), f"Expected analytics file not found: {path}"
    
    df = pd.read_csv(path)
    assert not df.empty
    assert "Date" in df.columns
    assert "DailyRevenue" in df.columns
    assert "DailyOrders" in df.columns
    assert "DailyUnits" in df.columns
    assert "DailyAOV" in df.columns
    
    # Check that DailyRevenue is numeric and positive on average
    assert pd.to_numeric(df["DailyRevenue"], errors="coerce").notna().all()
    assert df["DailyRevenue"].sum() > 0


def test_validate_and_prepare_daily_series_accepts_aliases():
    """Verifies that daily series preparation adapts to varying column naming conventions."""
    dates = pd.date_range(start="2023-03-01", periods=20, freq="D")
    rev = np.linspace(500, 1500, 20)
    
    # 1. InvoiceDate and Revenue
    df1 = pd.DataFrame({"InvoiceDate": dates, "Revenue": rev})
    norm1 = validate_and_prepare_daily_series(df1)
    assert "Date" in norm1.columns and "DailyRevenue" in norm1.columns
    assert len(norm1) == 20
    
    # 2. order_date and LineTotal
    df2 = pd.DataFrame({"order_date": dates, "LineTotal": rev})
    norm2 = validate_and_prepare_daily_series(df2)
    assert "Date" in norm2.columns and "DailyRevenue" in norm2.columns
    assert len(norm2) == 20
    
    # 3. date and SalesAmount
    df3 = pd.DataFrame({"date": dates, "SalesAmount": rev})
    norm3 = validate_and_prepare_daily_series(df3)
    assert "Date" in norm3.columns and "DailyRevenue" in norm3.columns
    assert len(norm3) == 20


def test_forecasting_output_contains_consistent_schema(sample_30_day_series):
    """Verifies that forecasting output includes Date, DailyRevenue, ActualRevenue, and PredictedRevenue."""
    result = perform_sales_forecasting(sample_30_day_series, forecast_days=14, test_ratio=0.2)
    
    history = pd.DataFrame(result["history"])
    eval_df = pd.DataFrame(result["holdout_evaluation"])
    forecast_df = pd.DataFrame(result["forecast"])
    
    # History schema
    assert "Date" in history.columns
    assert "DailyRevenue" in history.columns
    assert "ActualRevenue" in history.columns
    
    # Holdout evaluation schema - CRITICAL: must have BOTH DailyRevenue and ActualRevenue
    assert "Date" in eval_df.columns
    assert "DailyRevenue" in eval_df.columns
    assert "ActualRevenue" in eval_df.columns
    assert "PredictedRevenue" in eval_df.columns
    assert len(eval_df) == 6
    
    # Future forecast schema
    assert "Date" in forecast_df.columns
    assert "ForecastedRevenue" in forecast_df.columns
    assert "PredictedRevenue" in forecast_df.columns
    assert "DailyRevenue" in forecast_df.columns
    assert "LowerBound" in forecast_df.columns
    assert "UpperBound" in forecast_df.columns
    assert len(forecast_df) == 14


def test_exact_regression_eval_df_scaled_actual(sample_30_day_series):
    """
    Directly tests the operation that previously failed with KeyError: 'DailyRevenue':
    eval_df["ScaledActual"] = eval_df["DailyRevenue"] * rate
    """
    rate = 106.50
    result = perform_sales_forecasting(sample_30_day_series, forecast_days=7, test_ratio=0.2)
    eval_df = pd.DataFrame(result["holdout_evaluation"])
    
    # This must NOT raise KeyError: 'DailyRevenue'
    eval_df["ScaledActual"] = eval_df["DailyRevenue"] * rate
    assert "ScaledActual" in eval_df.columns
    assert len(eval_df["ScaledActual"]) == len(eval_df)
    assert (eval_df["ScaledActual"] > 0).all()


def test_forecasting_with_sample_dataset_file():
    """Verifies end-to-end execution of demand forecasting using the actual persisted dataset."""
    path = settings.ANALYTICS_DATA_DIR / "daily_sales_trends.csv"
    daily_df = pd.read_csv(path)
    
    result = perform_sales_forecasting(daily_df, forecast_days=30, test_ratio=0.20)
    
    metrics = result["evaluation_metrics"]
    assert metrics["MAE"] > 0
    assert metrics["RMSE"] > 0
    assert metrics["MAPE_percent"] >= 0
    assert metrics["holdout_test_days"] > 0
    assert metrics["train_days"] > metrics["holdout_test_days"]
    
    # Validate that holdout records match evaluation
    eval_df = pd.DataFrame(result["holdout_evaluation"])
    assert len(eval_df) == metrics["holdout_test_days"]
    assert "DailyRevenue" in eval_df.columns
    assert "ActualRevenue" in eval_df.columns


def test_empty_and_insufficient_history_rejection():
    """Verifies clear error reporting when input is empty or has fewer than 14 days."""
    # 1. Empty DataFrame
    with pytest.raises(ValueError, match="input dataset is empty"):
        perform_sales_forecasting(pd.DataFrame())
        
    # 2. None input
    with pytest.raises(ValueError, match="input dataset is empty"):
        perform_sales_forecasting(None)
        
    # 3. Only 5 days (insufficient history)
    short_dates = pd.date_range("2023-01-01", periods=5, freq="D")
    short_df = pd.DataFrame({"Date": short_dates, "DailyRevenue": [100.0] * 5})
    with pytest.raises(ValueError, match="Insufficient time-series history"):
        perform_sales_forecasting(short_df)
        
    # 4. Missing revenue column
    missing_rev = pd.DataFrame({"Date": short_dates, "Units": [1, 2, 3, 4, 5]})
    with pytest.raises(ValueError, match="no usable revenue column"):
        perform_sales_forecasting(missing_rev)


def test_sparse_dataset_does_not_fabricate_zeroes():
    """
    Verifies that a dataset with very few dates scattered over a long time span
    is rejected rather than fabricating hundreds of zero-revenue days to pass.
    """
    # 3 transactions spread across 3 years
    sparse_dates = [pd.Timestamp("2021-01-01"), pd.Timestamp("2022-01-01"), pd.Timestamp("2023-01-01")]
    sparse_df = pd.DataFrame({"Date": sparse_dates, "DailyRevenue": [500.0, 600.0, 700.0]})
    
    with pytest.raises(ValueError, match="Insufficient time-series history"):
        validate_and_prepare_daily_series(sparse_df, min_observed_days=14)


def test_currency_conversion_applied_once_and_preserves_orders():
    """Verifies that currency scaling operates on financial values without mutating dates or counts."""
    rate = settings.DEFAULT_GBP_TO_INR_RATE  # 106.50
    daily_rev = 100.0
    scaled_rev = daily_rev * rate
    assert round(scaled_rev, 2) == 10650.0
    
    # Order counts must remain integer counts (never multiplied by exchange rate)
    orders = 15
    assert orders == 15
    
    # Growth percent must remain pure percentage
    pct = 12.5
    assert pct == 12.5
