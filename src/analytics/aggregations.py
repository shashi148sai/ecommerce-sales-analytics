"""
SalesPulse Analytics - Spark SQL Aggregations and Analytics Module
Executes distributed SQL queries to generate commercial KPIs, product rankings,
temporal trends, regional distributions, and customer repeat behavior.
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from config import settings


def register_spark_views(
    spark: SparkSession,
    master_df: DataFrame,
    sales_df: DataFrame,
    returns_df: DataFrame
) -> None:
    """
    Registers in-memory Spark SQL temporary views for SQL querying.
    """
    master_df.createOrReplaceTempView("v_master_transactions")
    sales_df.createOrReplaceTempView("v_valid_sales")
    returns_df.createOrReplaceTempView("v_cancellations_returns")


def get_overall_kpis(spark: SparkSession) -> Dict[str, Any]:
    """
    Calculates primary commercial KPIs using Spark SQL.
    Computes Gross Sales, Return Adjustments, Net Sales, Distinct Orders,
    Units Sold, Average Order Value, and active country/customer counts.
    """
    start_time = time.time()
    
    # 1. Gross sales and order metrics
    sales_query = """
        SELECT 
            COUNT(DISTINCT InvoiceNo) AS total_orders,
            COALESCE(SUM(LineTotal), 0.0) AS gross_revenue,
            COALESCE(SUM(Quantity), 0) AS total_units_sold,
            COUNT(DISTINCT StockCode) AS distinct_products_sold,
            COUNT(DISTINCT CustomerID) AS active_registered_customers,
            COUNT(DISTINCT Country) AS operating_countries
        FROM v_valid_sales
    """
    sales_res = spark.sql(sales_query).collect()[0]
    
    # 2. Cancellations and return adjustments
    returns_query = """
        SELECT 
            ABS(COALESCE(SUM(LineTotal), 0.0)) AS return_amount,
            ABS(COALESCE(SUM(Quantity), 0)) AS return_units,
            COUNT(DISTINCT InvoiceNo) AS return_orders
        FROM v_cancellations_returns
    """
    returns_res = spark.sql(returns_query).collect()[0]
    
    elapsed_sec = round(time.time() - start_time, 4)
    
    gross_revenue = float(sales_res["gross_revenue"] or 0.0)
    return_amount = float(returns_res["return_amount"] or 0.0)
    net_revenue = round(gross_revenue - return_amount, 2)
    total_orders = int(sales_res["total_orders"] or 0)
    units_sold = int(sales_res["total_units_sold"] or 0)
    return_units = int(returns_res["return_units"] or 0)
    
    aov = round(gross_revenue / total_orders, 2) if total_orders > 0 else 0.0
    return_rate_pct = round((return_amount / gross_revenue) * 100, 2) if gross_revenue > 0 else 0.0
    
    return {
        "currency": settings.DEFAULT_CURRENCY,
        "gross_revenue": round(gross_revenue, 2),
        "return_adjustments": round(return_amount, 2),
        "net_revenue": net_revenue,
        "total_orders": total_orders,
        "total_units_sold": units_sold,
        "return_units_volume": return_units,
        "return_orders_count": int(returns_res["return_orders"] or 0),
        "return_rate_percent": return_rate_pct,
        "average_order_value": aov,
        "distinct_products": int(sales_res["distinct_products_sold"] or 0),
        "active_registered_customers": int(sales_res["active_registered_customers"] or 0),
        "operating_countries": int(sales_res["operating_countries"] or 0),
        "execution_duration_sec": elapsed_sec
    }


def get_top_products_by_revenue(spark: SparkSession, limit: int = 10) -> DataFrame:
    """
    Retrieves the highest revenue-generating products using Spark SQL.
    """
    query = f"""
        SELECT 
            StockCode,
            FIRST(Description) AS Description,
            ROUND(SUM(LineTotal), 2) AS TotalRevenue,
            SUM(Quantity) AS UnitsSold,
            COUNT(DISTINCT InvoiceNo) AS OrderCount,
            ROUND(AVG(UnitPrice), 2) AS AvgUnitPrice
        FROM v_valid_sales
        GROUP BY StockCode
        ORDER BY TotalRevenue DESC
        LIMIT {limit}
    """
    return spark.sql(query)


def get_top_products_by_quantity(spark: SparkSession, limit: int = 10) -> DataFrame:
    """
    Retrieves the top products by volume of units sold.
    """
    query = f"""
        SELECT 
            StockCode,
            FIRST(Description) AS Description,
            SUM(Quantity) AS UnitsSold,
            ROUND(SUM(LineTotal), 2) AS TotalRevenue,
            COUNT(DISTINCT InvoiceNo) AS OrderCount
        FROM v_valid_sales
        GROUP BY StockCode
        ORDER BY UnitsSold DESC
        LIMIT {limit}
    """
    return spark.sql(query)


def get_monthly_sales_trends(spark: SparkSession) -> DataFrame:
    """
    Aggregates monthly sales volume, revenue, orders, and calculates Month-over-Month (MoM) growth.
    Uses Spark SQL Window functions for analytical ranking and lag calculations.
    """
    base_query = """
        SELECT 
            YearMonth,
            ROUND(SUM(LineTotal), 2) AS MonthlyRevenue,
            COUNT(DISTINCT InvoiceNo) AS MonthlyOrders,
            SUM(Quantity) AS MonthlyUnits,
            ROUND(SUM(LineTotal) / COUNT(DISTINCT InvoiceNo), 2) AS MonthlyAOV
        FROM v_valid_sales
        WHERE YearMonth IS NOT NULL
        GROUP BY YearMonth
        ORDER BY YearMonth ASC
    """
    monthly_df = spark.sql(base_query)
    
    # Calculate MoM growth via PySpark Window
    window_spec = Window.orderBy("YearMonth")
    lag_rev = F.lag("MonthlyRevenue", 1).over(window_spec)
    
    trend_df = (
        monthly_df
        .withColumn("PreviousMonthRevenue", lag_rev)
        .withColumn(
            "RevenueGrowthPercent",
            F.when(
                F.col("PreviousMonthRevenue").isNull() | (F.col("PreviousMonthRevenue") == 0),
                F.lit(0.0)
            ).otherwise(
                F.round(((F.col("MonthlyRevenue") - F.col("PreviousMonthRevenue")) / F.col("PreviousMonthRevenue")) * 100, 2)
            )
        )
    )
    return trend_df


def get_daily_sales_trends(spark: SparkSession) -> DataFrame:
    """
    Aggregates daily sales, orders, and average order value.
    """
    query = """
        SELECT 
            InvoiceDateOnly AS Date,
            ROUND(SUM(LineTotal), 2) AS DailyRevenue,
            COUNT(DISTINCT InvoiceNo) AS DailyOrders,
            SUM(Quantity) AS DailyUnits,
            ROUND(SUM(LineTotal) / COUNT(DISTINCT InvoiceNo), 2) AS DailyAOV
        FROM v_valid_sales
        WHERE InvoiceDateOnly IS NOT NULL
        GROUP BY InvoiceDateOnly
        ORDER BY InvoiceDateOnly ASC
    """
    return spark.sql(query)


def get_country_wise_revenue(spark: SparkSession) -> DataFrame:
    """
    Aggregates geographic commercial performance by country.
    """
    query = """
        SELECT 
            Country,
            ROUND(SUM(LineTotal), 2) AS TotalRevenue,
            COUNT(DISTINCT InvoiceNo) AS OrderCount,
            COUNT(DISTINCT CustomerID) AS CustomerCount,
            SUM(Quantity) AS UnitsSold,
            ROUND(SUM(LineTotal) / COUNT(DISTINCT InvoiceNo), 2) AS CountryAOV
        FROM v_valid_sales
        GROUP BY Country
        ORDER BY TotalRevenue DESC
    """
    return spark.sql(query)


def get_repeat_customer_analysis(spark: SparkSession) -> Dict[str, Any]:
    """
    Analyzes customer loyalty, segmenting one-time buyers vs repeat purchasers,
    and auditing guest checkout vs registered sales.
    """
    # 1. Registered customers purchase counts
    cust_query = """
        SELECT 
            CustomerID,
            COUNT(DISTINCT InvoiceNo) AS order_count,
            SUM(LineTotal) AS customer_revenue
        FROM v_valid_sales
        WHERE CustomerID IS NOT NULL
        GROUP BY CustomerID
    """
    cust_df = spark.sql(cust_query)
    cust_df.createOrReplaceTempView("v_customer_order_summary")
    
    seg_query = """
        SELECT 
            COUNT(DISTINCT CustomerID) AS total_registered,
            COUNT(DISTINCT CASE WHEN order_count > 1 THEN CustomerID END) AS repeat_customers,
            COUNT(DISTINCT CASE WHEN order_count = 1 THEN CustomerID END) AS one_time_customers,
            COALESCE(SUM(CASE WHEN order_count > 1 THEN customer_revenue ELSE 0 END), 0.0) AS repeat_revenue,
            COALESCE(SUM(CASE WHEN order_count = 1 THEN customer_revenue ELSE 0 END), 0.0) AS one_time_revenue
        FROM v_customer_order_summary
    """
    seg_res = spark.sql(seg_query).collect()[0]
    
    # 2. Guest (unregistered) checkout volume
    guest_query = """
        SELECT 
            COUNT(DISTINCT InvoiceNo) AS guest_orders,
            COALESCE(SUM(LineTotal), 0.0) AS guest_revenue
        FROM v_valid_sales
        WHERE CustomerID IS NULL
    """
    guest_res = spark.sql(guest_query).collect()[0]
    
    total_registered = int(seg_res["total_registered"] or 0)
    repeat_customers = int(seg_res["repeat_customers"] or 0)
    one_time_customers = int(seg_res["one_time_customers"] or 0)
    
    repeat_rev = float(seg_res["repeat_revenue"] or 0.0)
    one_time_rev = float(seg_res["one_time_revenue"] or 0.0)
    registered_rev = repeat_rev + one_time_rev
    
    guest_orders = int(guest_res["guest_orders"] or 0)
    guest_rev = float(guest_res["guest_revenue"] or 0.0)
    
    repeat_pct = round((repeat_customers / total_registered) * 100, 2) if total_registered > 0 else 0.0
    repeat_rev_pct = round((repeat_rev / registered_rev) * 100, 2) if registered_rev > 0 else 0.0
    
    return {
        "total_registered_customers": total_registered,
        "repeat_customers_count": repeat_customers,
        "one_time_customers_count": one_time_customers,
        "repeat_customer_rate_percent": repeat_pct,
        "repeat_customers_revenue": round(repeat_rev, 2),
        "one_time_customers_revenue": round(one_time_rev, 2),
        "repeat_revenue_share_percent": repeat_rev_pct,
        "guest_orders_count": guest_orders,
        "guest_revenue": round(guest_rev, 2),
        "currency": settings.DEFAULT_CURRENCY
    }


def get_temporal_patterns(spark: SparkSession) -> Dict[str, DataFrame]:
    """
    Aggregates revenue and transaction frequency across DayOfWeek and HourOfDay.
    """
    dow_query = """
        SELECT 
            DayOfWeek,
            ROUND(SUM(LineTotal), 2) AS Revenue,
            COUNT(DISTINCT InvoiceNo) AS Orders,
            SUM(Quantity) AS Units
        FROM v_valid_sales
        WHERE DayOfWeek IS NOT NULL
        GROUP BY DayOfWeek
    """
    dow_df = spark.sql(dow_query)
    
    hour_query = """
        SELECT 
            HourOfDay,
            ROUND(SUM(LineTotal), 2) AS Revenue,
            COUNT(DISTINCT InvoiceNo) AS Orders,
            SUM(Quantity) AS Units
        FROM v_valid_sales
        WHERE HourOfDay IS NOT NULL
        GROUP BY HourOfDay
        ORDER BY HourOfDay ASC
    """
    hour_df = spark.sql(hour_query)
    
    return {
        "day_of_week": dow_df,
        "hour_of_day": hour_df
    }


def save_analytics_tables_locally(
    analytics_tables: Dict[str, DataFrame],
    output_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """
    Persists aggregated analytics tables to Parquet and CSV in data/analytics.
    Utilizes Pandas/PyArrow export to eliminate dependency on Windows winutils.exe.
    """
    target_dir = Path(output_dir or settings.ANALYTICS_DATA_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    saved_files = {}
    
    for name, spark_df in analytics_tables.items():
        pdf = spark_df.toPandas()
        
        csv_path = target_dir / f"{name}.csv"
        parquet_path = target_dir / f"{name}.parquet"
        
        pdf.to_csv(csv_path, index=False)
        pdf.to_parquet(parquet_path, index=False)
        
        saved_files[name] = csv_path
        
    return saved_files
