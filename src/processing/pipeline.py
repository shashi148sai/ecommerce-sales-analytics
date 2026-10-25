"""
SalesPulse Analytics - End-to-End Pipeline Orchestrator
Coordinates Ingestion, Schema Auditing, Distributed PySpark Cleaning,
Spark SQL Analytics Aggregations, Metadata Tracking, and Storage Persistence.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

from config import settings
from src.processing.spark_session import get_spark_session
from src.ingestion.loader import load_raw_data
from src.validation.validator import validate_schema, compute_data_quality_report, save_data_quality_report
from src.processing.transformer import transform_and_clean_data, compute_transformation_summary
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
from src.storage.storage_manager import StorageManager


def run_pipeline(
    input_file_path: Optional[Path] = None,
    limit_rows: Optional[int] = None,
    spark=None,
    column_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end Big Data & Cloud analytics pipeline.
    
    Args:
        input_file_path: Path to raw dataset CSV/XLSX (defaults to settings.DEFAULT_RAW_FILE).
        limit_rows: Optional row limit for fast development or memory-constrained testing.
        spark: Optional active SparkSession.
        column_mapping: Optional schema mapping dictionary for custom dataset compatibility.
        
    Returns:
        Comprehensive execution summary dictionary.
    """
    pipeline_start = time.time()
    file_path = Path(input_file_path or settings.DEFAULT_RAW_FILE)
    if not file_path.exists():
        # Fallback to sample if default raw not found
        if settings.SAMPLE_RAW_FILE.exists():
            file_path = settings.SAMPLE_RAW_FILE
        else:
            raise FileNotFoundError(f"No input dataset available at {file_path}")
            
    storage = StorageManager()
    if spark is None:
        spark = get_spark_session()
        
    # Step 1: Ingestion
    t0 = time.time()
    raw_df = load_raw_data(file_path, spark=spark, limit=limit_rows, column_mapping=column_mapping)
    raw_count = raw_df.count()
    ingest_time = round(time.time() - t0, 3)
    
    # Step 2: Schema Validation & Data Quality Report
    t1 = time.time()
    schema_status = validate_schema(raw_df)
    if not schema_status["is_valid"]:
        raise ValueError(f"Schema conformance failed. Missing columns: {schema_status['missing_columns']}")
        
    quality_report = compute_data_quality_report(raw_df)
    save_data_quality_report(quality_report, settings.REPORTS_DIR)
    audit_time = round(time.time() - t1, 3)
    
    # Step 3: PySpark Transformation and Cleaning
    t2 = time.time()
    master_df, sales_df, returns_df = transform_and_clean_data(raw_df)
    trans_summary = compute_transformation_summary(master_df, sales_df, returns_df)
    transform_time = round(time.time() - t2, 3)
    
    # Save cleaned sales dataset for dashboard and advanced modeling
    # Convert to Pandas / PyArrow for local persistence without native Hadoop DLL dependency
    sales_pdf = sales_df.toPandas()
    clean_sales_path = settings.PROCESSED_DATA_DIR / "cleaned_sales.parquet"
    clean_sales_csv = settings.PROCESSED_DATA_DIR / "cleaned_sales.csv"
    sales_pdf.to_parquet(clean_sales_path, index=False)
    sales_pdf.head(5000).to_csv(clean_sales_csv, index=False)
    
    # Step 4: Spark SQL Aggregations
    t3 = time.time()
    register_spark_views(spark, master_df, sales_df, returns_df)
    
    kpis = get_overall_kpis(spark)
    top_rev_df = get_top_products_by_revenue(spark, limit=20)
    top_qty_df = get_top_products_by_quantity(spark, limit=20)
    monthly_trends_df = get_monthly_sales_trends(spark)
    daily_trends_df = get_daily_sales_trends(spark)
    country_rev_df = get_country_wise_revenue(spark)
    repeat_stats = get_repeat_customer_analysis(spark)
    temporal_patterns = get_temporal_patterns(spark)
    
    # Persist summary tables in data/analytics
    analytics_tables = {
        "top_products_by_revenue": top_rev_df,
        "top_products_by_quantity": top_qty_df,
        "monthly_sales_trends": monthly_trends_df,
        "daily_sales_trends": daily_trends_df,
        "country_wise_revenue": country_rev_df,
        "day_of_week_sales": temporal_patterns["day_of_week"],
        "hour_of_day_sales": temporal_patterns["hour_of_day"]
    }
    save_analytics_tables_locally(analytics_tables, settings.ANALYTICS_DATA_DIR)
    
    # Save KPI and Repeat stats JSON
    with open(settings.ANALYTICS_DATA_DIR / "kpis_summary.json", "w", encoding="utf-8") as f:
        json.dump(kpis, f, indent=4)
        
    with open(settings.ANALYTICS_DATA_DIR / "repeat_customer_summary.json", "w", encoding="utf-8") as f:
        json.dump(repeat_stats, f, indent=4)
        
    analytics_time = round(time.time() - t3, 3)
    
    total_elapsed = round(time.time() - pipeline_start, 3)
    throughput = round(raw_count / total_elapsed, 1) if total_elapsed > 0 else 0.0
    
    # Step 5: Metadata tracking
    eligible_sales = trans_summary["eligible_sales_records"]
    returns_recs = trans_summary["returns_and_cancellations_records"]
    excluded_recs = raw_count - eligible_sales - returns_recs
    if excluded_recs < 0:
        raise ValueError(
            f"Inconsistent record accounting in analytics pipeline: raw_count ({raw_count}) "
            f"is less than clean sales ({eligible_sales}) + returns ({returns_recs}). "
            f"Calculated excluded records: {excluded_recs}."
        )

    run_metadata = {
        "dataset_file": str(file_path.name),
        "total_records_ingested": raw_count,
        "clean_sales_records": eligible_sales,
        "clean_sales_records_count": eligible_sales,
        "returns_and_cancellations": returns_recs,
        "returns_records_count": returns_recs,
        "excluded_records_count": excluded_recs,
        "timings_seconds": {
            "ingestion": ingest_time,
            "data_quality_audit": audit_time,
            "pyspark_transformation": transform_time,
            "spark_sql_aggregations": analytics_time,
            "total_pipeline_duration": total_elapsed
        },
        "throughput_rows_per_second": throughput,
        "spark_master": settings.SPARK_MASTER,
        "storage_mode": settings.STORAGE_MODE,
        "gross_sales": trans_summary["gross_sales_amount"],
        "net_sales": trans_summary["net_sales_amount"],
        "currency": settings.DEFAULT_CURRENCY
    }
    
    meta_path = settings.METADATA_DIR / "latest_pipeline_run.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(run_metadata, f, indent=4)
        
    # Optional S3 Replication
    if settings.STORAGE_MODE == "s3":
        storage.sync_local_to_s3()
        
    return {
        "status": "COMPLETED",
        "metadata": run_metadata,
        "kpis": kpis,
        "transformation_summary": trans_summary,
        "repeat_customer_analysis": repeat_stats
    }
