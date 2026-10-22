"""
SalesPulse Analytics - Data Validation and Quality Auditing Module
Performs schema conformance checks, null analysis, anomaly detection, and data quality metrics.
Generates structured JSON and CSV reports for cloud or local governance.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from config import settings


def validate_schema(
    df: DataFrame,
    required_columns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Validates that the given DataFrame contains all mandatory schema fields.
    
    Returns:
        Dictionary with validation status, present columns, and missing columns.
    """
    if required_columns is None:
        required_columns = settings.REQUIRED_COLUMNS
        
    actual_columns = df.columns
    missing_columns = [col for col in required_columns if col not in actual_columns]
    
    is_valid = len(missing_columns) == 0
    return {
        "is_valid": is_valid,
        "required_columns": required_columns,
        "actual_columns": actual_columns,
        "missing_columns": missing_columns,
        "column_count": len(actual_columns)
    }


def compute_data_quality_report(df: DataFrame) -> Dict[str, Any]:
    """
    Computes comprehensive data-quality statistics using distributed Spark transformations.
    
    Measures:
    - Total record counts
    - Missing value distribution across fields
    - Exact duplicate record count
    - Cancellations and negative/zero values
    - Identity coverage (registered vs guest checkouts)
    """
    total_records = df.count()
    if total_records == 0:
        return {
            "total_records": 0,
            "status": "EMPTY_DATASET",
            "missing_values": {},
            "duplicate_records": 0,
            "cancellation_count": 0,
            "negative_quantity_count": 0,
            "zero_or_negative_price_count": 0
        }
        
    # Check nulls or empty strings per column
    null_exprs = [
        F.count(
            F.when(
                F.col(c).isNull() | 
                (F.trim(F.col(c)) == "") | 
                (F.lower(F.trim(F.col(c))) == "nan") |
                (F.lower(F.trim(F.col(c))) == "null"),
                1
            )
        ).alias(c)
        for c in df.columns
    ]
    null_counts_row = df.select(null_exprs).collect()[0].asDict()
    
    missing_stats = {}
    for col_name, null_count in null_counts_row.items():
        missing_stats[col_name] = {
            "null_count": int(null_count),
            "null_percentage": round((null_count / total_records) * 100, 2)
        }
        
    # Measure duplicates
    distinct_count = df.dropDuplicates().count()
    duplicate_records = total_records - distinct_count
    
    # Cast Quantity and UnitPrice safely for inspection
    safe_qty = F.coalesce(F.col("Quantity").cast("int"), F.lit(0))
    safe_price = F.coalesce(F.col("UnitPrice").cast("double"), F.lit(0.0))
    
    # Anomaly and business rule counts
    cancellation_cond = (
        F.col("InvoiceNo").startswith("C") | 
        F.col("InvoiceNo").startswith("c") |
        (safe_qty < 0)
    )
    
    anomaly_row = df.select(
        F.count(F.when(cancellation_cond, 1)).alias("cancellations"),
        F.count(F.when(safe_qty < 0, 1)).alias("negative_quantity"),
        F.count(F.when(safe_qty == 0, 1)).alias("zero_quantity"),
        F.count(F.when(safe_price < 0, 1)).alias("negative_price"),
        F.count(F.when(safe_price == 0, 1)).alias("zero_price"),
        F.countDistinct("CustomerID").alias("distinct_customers"),
        F.countDistinct("StockCode").alias("distinct_products"),
        F.countDistinct("Country").alias("distinct_countries")
    ).collect()[0].asDict()
    
    # Clean records count (positive qty, positive price, not cancelled, non-null invoice)
    clean_condition = (
        (~cancellation_cond) &
        (safe_qty > 0) &
        (safe_price > 0) &
        F.col("InvoiceNo").isNotNull()
    )
    clean_records_count = df.filter(clean_condition).count()
    quality_score = round((clean_records_count / total_records) * 100, 2)
    
    report = {
        "total_records": total_records,
        "clean_records_count": clean_records_count,
        "data_quality_score_percent": quality_score,
        "duplicate_records": duplicate_records,
        "duplicate_percentage": round((duplicate_records / total_records) * 100, 2),
        "missing_values": missing_stats,
        "business_rule_violations": {
            "cancellation_count": int(anomaly_row["cancellations"]),
            "negative_quantity_count": int(anomaly_row["negative_quantity"]),
            "zero_quantity_count": int(anomaly_row["zero_quantity"]),
            "negative_price_count": int(anomaly_row["negative_price"]),
            "zero_price_count": int(anomaly_row["zero_price"]),
        },
        "cardinality": {
            "distinct_customers": int(anomaly_row["distinct_customers"]),
            "distinct_products": int(anomaly_row["distinct_products"]),
            "distinct_countries": int(anomaly_row["distinct_countries"])
        }
    }
    
    return report


def save_data_quality_report(
    report: Dict[str, Any],
    output_dir: Optional[Path] = None
) -> Path:
    """
    Saves the data quality audit report to disk as JSON.
    """
    target_dir = Path(output_dir or settings.REPORTS_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    report_file = target_dir / "data_quality_report.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    return report_file
