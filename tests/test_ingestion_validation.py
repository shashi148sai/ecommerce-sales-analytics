"""
Unit tests for data ingestion, schema validation, and quality auditing.
"""

import pytest
from src.validation.validator import validate_schema, compute_data_quality_report
from src.ingestion.loader import parse_invoice_timestamp, get_download_instructions


def test_schema_validation_success(sample_raw_dataframe):
    """Verifies that a conformant DataFrame passes schema validation."""
    result = validate_schema(sample_raw_dataframe)
    assert result["is_valid"] is True
    assert len(result["missing_columns"]) == 0


def test_schema_validation_failure(spark_session):
    """Verifies that missing columns are flagged correctly."""
    df_missing = spark_session.createDataFrame([(1, "Item A")], ["id", "Description"])
    result = validate_schema(df_missing)
    assert result["is_valid"] is False
    assert "InvoiceNo" in result["missing_columns"]
    assert "Quantity" in result["missing_columns"]


def test_data_quality_report_metrics(sample_raw_dataframe):
    """Verifies calculation of null counts, duplicates, cancellations, and quality scores."""
    report = compute_data_quality_report(sample_raw_dataframe)
    
    # 8 rows originally, with 1 exact duplicate
    assert report["total_records"] == 8
    assert report["duplicate_records"] == 1
    
    # CustomerID null check
    assert report["missing_values"]["CustomerID"]["null_count"] == 1
    
    # Cancellation check (C536379 has C prefix and qty -1, 536380 has qty -3)
    violations = report["business_rule_violations"]
    assert violations["cancellation_count"] == 2
    assert violations["negative_quantity_count"] == 2
    assert violations["zero_price_count"] == 1


def test_empty_dataframe_quality_report(spark_session):
    """Verifies graceful handling of empty datasets without division by zero errors."""
    from pyspark.sql.types import StructType, StructField, StringType
    schema = StructType([StructField("InvoiceNo", StringType(), True)])
    empty_df = spark_session.createDataFrame([], schema)
    
    report = compute_data_quality_report(empty_df)
    assert report["total_records"] == 0
    assert report["status"] == "EMPTY_DATASET"


def test_parse_invoice_timestamp(sample_raw_dataframe):
    """Verifies timestamp parsing creates InvoiceTimestamp and InvoiceDateOnly columns."""
    df_parsed = parse_invoice_timestamp(sample_raw_dataframe, "InvoiceDate")
    assert "InvoiceTimestamp" in df_parsed.columns
    assert "InvoiceDateOnly" in df_parsed.columns
    
    row = df_parsed.first()
    assert str(row["InvoiceDateOnly"]) == "2010-12-01"


def test_download_instructions():
    """Verifies that dataset download instructions contain correct URL and details."""
    instructions = get_download_instructions()
    assert "archive.ics.uci.edu" in instructions
    assert "541,909" in instructions
