"""
Unit tests for Spark SQL aggregations, commercial KPIs, top products, trends, and repeat customers.
"""

import pytest
from config import settings
from src.processing.transformer import transform_and_clean_data
from src.analytics.aggregations import (
    register_spark_views,
    get_overall_kpis,
    get_top_products_by_revenue,
    get_top_products_by_quantity,
    get_monthly_sales_trends,
    get_daily_sales_trends,
    get_country_wise_revenue,
    get_repeat_customer_analysis,
    get_temporal_patterns,
    save_analytics_tables_locally
)


@pytest.fixture
def prepared_views(spark_session, sample_raw_dataframe):
    """Transforms raw sample and registers Spark SQL temporary views."""
    master_df, sales_df, returns_df = transform_and_clean_data(sample_raw_dataframe)
    register_spark_views(spark_session, master_df, sales_df, returns_df)
    return master_df, sales_df, returns_df


def test_overall_kpis(spark_session, prepared_views):
    """Verifies overall financial and operational KPIs from Spark SQL."""
    kpis = get_overall_kpis(spark_session)
    
    # Gross: 44.48, Returns: 31.25, Net: 13.23
    assert kpis["gross_revenue"] == 44.48
    assert kpis["return_adjustments"] == 31.25
    assert kpis["net_revenue"] == 13.23
    assert kpis["total_orders"] == 3
    assert kpis["total_units_sold"] == 16
    assert kpis["return_orders_count"] == 2
    assert kpis["average_order_value"] == round(44.48 / 3, 2)
    assert kpis["currency"] == settings.DEFAULT_CURRENCY


def test_top_products(spark_session, prepared_views):
    """Verifies top products by revenue and quantity ranking."""
    top_rev = get_top_products_by_revenue(spark_session, limit=5).collect()
    assert len(top_rev) > 0
    # First item should have the highest TotalRevenue
    assert top_rev[0]["TotalRevenue"] >= top_rev[-1]["TotalRevenue"]
    
    top_qty = get_top_products_by_quantity(spark_session, limit=5).collect()
    assert len(top_qty) > 0
    assert top_qty[0]["UnitsSold"] >= top_qty[-1]["UnitsSold"]


def test_monthly_trends_and_growth(spark_session, prepared_views):
    """Verifies monthly aggregation and MoM growth calculation."""
    monthly_df = get_monthly_sales_trends(spark_session)
    rows = monthly_df.collect()
    assert len(rows) >= 1
    first_month = rows[0]
    assert first_month["YearMonth"] == "2010-12"
    assert first_month["MonthlyRevenue"] == 44.48
    # With only 1 month in sample, previous is null/0, growth is 0.0
    assert first_month["RevenueGrowthPercent"] == 0.0


def test_country_wise_revenue(spark_session, prepared_views):
    """Verifies geographical aggregation."""
    country_df = get_country_wise_revenue(spark_session)
    rows = {r["Country"]: r["TotalRevenue"] for r in country_df.collect()}
    
    assert "United Kingdom" in rows
    assert "France" in rows
    # UK gross: 22.08 + 7.40 = 29.48, France gross: 15.00
    assert rows["United Kingdom"] == 29.48
    assert rows["France"] == 15.00


def test_repeat_customer_analysis(spark_session, prepared_views):
    """Verifies repeat customer identification and guest checkout audit."""
    repeat_stats = get_repeat_customer_analysis(spark_session)
    
    # Registered customers in sample:
    # 17850 has 1 invoice (536365)
    # 12583 has 1 invoice (536382)
    # Total registered: 2
    assert repeat_stats["total_registered_customers"] == 2
    assert repeat_stats["one_time_customers_count"] == 2
    assert repeat_stats["repeat_customers_count"] == 0
    
    # Guest checkout: 536366 has no CustomerID (revenue 7.40)
    assert repeat_stats["guest_orders_count"] == 1
    assert repeat_stats["guest_revenue"] == 7.40


def test_temporal_patterns(spark_session, prepared_views):
    """Verifies DayOfWeek and HourOfDay query outputs."""
    patterns = get_temporal_patterns(spark_session)
    dow = patterns["day_of_week"].collect()
    hod = patterns["hour_of_day"].collect()
    
    assert len(dow) > 0
    assert len(hod) > 0


def test_save_analytics_tables_locally(spark_session, prepared_views, tmp_path):
    """Verifies local export to both CSV and Parquet formats."""
    monthly_df = get_monthly_sales_trends(spark_session)
    tables = {"monthly_trends": monthly_df}
    
    saved = save_analytics_tables_locally(tables, output_dir=tmp_path)
    assert "monthly_trends" in saved
    assert (tmp_path / "monthly_trends.csv").exists()
    assert (tmp_path / "monthly_trends.parquet").exists()
