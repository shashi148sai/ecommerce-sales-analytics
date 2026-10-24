"""
SalesPulse Analytics - PySpark Transformation and Cleaning Module
Implements business rules, identifier preservation, cancellation handling,
revenue calculation, and temporal feature engineering.
"""

from typing import Tuple, Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, DoubleType, StringType
from src.ingestion.loader import parse_invoice_timestamp


def clean_customer_id(col_name: str = "CustomerID"):
    """
    Cleans CustomerID representations.
    Converts floats like '17850.0' to clean strings '17850'.
    Leaves null or invalid customer values as null.
    """
    trimmed = F.trim(F.col(col_name))
    # Strip any trailing decimal part (e.g. .0 or .00)
    cleaned = F.regexp_replace(trimmed, r"\.0+$", "")
    return F.when(
        cleaned.isNull() | (cleaned == "") | (F.lower(cleaned) == "nan") | (F.lower(cleaned) == "null"),
        F.lit(None).cast(StringType())
    ).otherwise(cleaned)


def transform_and_clean_data(raw_df: DataFrame) -> Tuple[DataFrame, DataFrame, DataFrame]:
    """
    Transforms raw transactional data through a distributed PySpark pipeline:
    1. Removes duplicate records.
    2. Cleans text columns (Description, StockCode, InvoiceNo).
    3. Normalizes CustomerID as formatted string identifiers.
    4. Casts Quantity and UnitPrice to numeric types.
    5. Normalizes timestamps and extracts temporal features (Year, Month, Day, Hour, DayOfWeek).
    6. Identifies cancellations and returns.
    7. Calculates LineTotal (Transaction Revenue).
    
    Returns:
        Tuple of (master_df, sales_df, returns_df):
        - master_df: Entire cleansed dataset with flags and derived columns.
        - sales_df: Valid commercial transactions (Quantity > 0, UnitPrice > 0, non-cancelled).
        - returns_df: Cancellations and return transactions.
    """
    # 1. Deduplicate records
    deduped_df = raw_df.dropDuplicates()

    # Guarantee canonical columns exist on Spark DataFrame even for arbitrary uploaded schemas
    for col_name, default_val in [
        ("InvoiceNo", "INV-00001"),
        ("StockCode", "SKU-0001"),
        ("Description", "GENERAL MERCHANDISE"),
        ("CustomerID", "CUST-0001"),
        ("Country", "India"),
        ("Quantity", 1),
        ("UnitPrice", 50.0),
        ("InvoiceDate", "2024-01-01 12:00:00")
    ]:
        if col_name not in deduped_df.columns:
            deduped_df = deduped_df.withColumn(col_name, F.lit(default_val))

    # 2. Parse timestamps and temporal dimensions
    time_df = parse_invoice_timestamp(deduped_df, "InvoiceDate")

    # 3. Clean identifiers and text attributes
    cleaned_df = (
        time_df
        .withColumn("InvoiceNo", F.trim(F.col("InvoiceNo")))
        .withColumn("StockCode", F.upper(F.trim(F.col("StockCode"))))
        .withColumn(
            "Description",
            F.when(
                F.col("Description").isNull() | (F.trim(F.col("Description")) == ""),
                F.lit("UNKNOWN PRODUCT")
            ).otherwise(F.upper(F.trim(F.col("Description"))))
        )
        .withColumn("CustomerID", clean_customer_id("CustomerID"))
        .withColumn("Country", F.trim(F.col("Country")))
    )

    # 4. Cast numerical values safely
    numeric_df = (
        cleaned_df
        .withColumn("Quantity", F.coalesce(F.col("Quantity").cast(IntegerType()), F.lit(0)))
        .withColumn("UnitPrice", F.coalesce(F.col("UnitPrice").cast(DoubleType()), F.lit(0.0)))
    )

    # 5. Calculate LineTotal (Transaction Revenue)
    # Using 2-decimal round for monetary precision
    revenue_df = numeric_df.withColumn(
        "LineTotal",
        F.round(F.col("Quantity") * F.col("UnitPrice"), 2)
    )

    # 6. Flag cancellations and returns
    cancellation_cond = (
        F.col("InvoiceNo").startswith("C") |
        F.col("InvoiceNo").startswith("c") |
        (F.col("Quantity") < 0)
    )

    flagged_df = (
        revenue_df
        .withColumn("IsCancellation", F.when(cancellation_cond, True).otherwise(False))
        .withColumn(
            "IsValidSale",
            F.when(
                (~cancellation_cond) & (F.col("Quantity") > 0) & (F.col("UnitPrice") > 0),
                True
            ).otherwise(False)
        )
    )

    # 7. Extract calendar & time features for time-series analytics
    enriched_df = (
        flagged_df
        .withColumn("Year", F.year("InvoiceTimestamp"))
        .withColumn("Month", F.month("InvoiceTimestamp"))
        .withColumn("YearMonth", F.date_format("InvoiceTimestamp", "yyyy-MM"))
        .withColumn("DayOfMonth", F.dayofmonth("InvoiceTimestamp"))
        .withColumn("DayOfWeek", F.date_format("InvoiceTimestamp", "EEEE"))
        .withColumn("HourOfDay", F.hour("InvoiceTimestamp"))
    )

    # Split into sales-eligible and returns/cancellations subsets
    sales_df = enriched_df.filter(F.col("IsValidSale") == True)
    returns_df = enriched_df.filter(F.col("IsCancellation") == True)

    return enriched_df, sales_df, returns_df


def compute_transformation_summary(
    master_df: DataFrame,
    sales_df: DataFrame,
    returns_df: DataFrame
) -> Dict[str, Any]:
    """
    Produces high-level transformation and sales/return balance metrics.
    """
    total_count = master_df.count()
    sales_count = sales_df.count()
    returns_count = returns_df.count()
    
    # Financial metrics
    gross_sales_row = sales_df.select(
        F.sum("LineTotal").alias("gross_sales"),
        F.sum("Quantity").alias("units_sold"),
        F.countDistinct("InvoiceNo").alias("distinct_orders")
    ).collect()[0]
    
    gross_sales = float(gross_sales_row["gross_sales"] or 0.0)
    units_sold = int(gross_sales_row["units_sold"] or 0)
    orders = int(gross_sales_row["distinct_orders"] or 0)
    
    return_val_row = returns_df.select(
        F.sum("LineTotal").alias("return_val"),
        F.sum("Quantity").alias("return_units")
    ).collect()[0]
    
    return_amount = abs(float(return_val_row["return_val"] or 0.0))
    return_units = abs(int(return_val_row["return_units"] or 0))
    
    net_sales = round(gross_sales - return_amount, 2)
    aov = round(gross_sales / orders, 2) if orders > 0 else 0.0
    
    return {
        "total_records": total_count,
        "eligible_sales_records": sales_count,
        "returns_and_cancellations_records": returns_count,
        "gross_sales_amount": round(gross_sales, 2),
        "return_adjustments_amount": round(return_amount, 2),
        "net_sales_amount": net_sales,
        "total_units_sold": units_sold,
        "return_units_volume": return_units,
        "distinct_orders": orders,
        "average_order_value": aov,
        "currency": "£"
    }
