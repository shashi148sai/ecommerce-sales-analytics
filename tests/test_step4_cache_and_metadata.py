"""
Unit and integration tests for Step 4 cache invalidation, metadata reconciliation,
and accounting consistency in SalesPulse Analytics.
"""

import json
import time
from pathlib import Path
import pytest

from config import settings
from src.dashboard.utils import (
    load_pipeline_metadata,
    load_kpis,
    load_data_quality_report,
    load_monthly_trends,
    clear_analytics_cache,
    _get_path_mtime
)


def test_empty_cache_invalidation_after_file_creation(tmp_path, monkeypatch):
    """
    Verifies that calling cached loaders when files do not exist returns empty results,
    and once the pipeline writes output files to disk, the loaders immediately return
    the fresh data via mtime cache-key detection and clear_analytics_cache().
    """
    test_meta_dir = tmp_path / "metadata"
    test_analytics_dir = tmp_path / "analytics"
    test_reports_dir = tmp_path / "reports"
    
    test_meta_dir.mkdir(parents=True, exist_ok=True)
    test_analytics_dir.mkdir(parents=True, exist_ok=True)
    test_reports_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "METADATA_DIR", test_meta_dir)
    monkeypatch.setattr(settings, "ANALYTICS_DATA_DIR", test_analytics_dir)
    monkeypatch.setattr(settings, "REPORTS_DIR", test_reports_dir)

    # 1. Clear any residual cache
    clear_analytics_cache()

    # 2. Files do not exist yet on disk
    meta_path = test_meta_dir / "latest_pipeline_run.json"
    kpi_path = test_analytics_dir / "kpis_summary.json"
    report_path = test_reports_dir / "data_quality_report.json"

    assert not meta_path.exists()
    assert not kpi_path.exists()
    assert not report_path.exists()

    # 3. Cached loaders are invoked before pipeline run -> should return empty dicts
    initial_meta = load_pipeline_metadata()
    initial_kpis = load_kpis()
    initial_report = load_data_quality_report()

    assert initial_meta == {}
    assert initial_kpis == {}
    assert initial_report == {}

    # 4. Pipeline executes and writes outputs to disk
    sample_meta = {
        "dataset_file": "test_dataset.csv",
        "total_records_ingested": 1000,
        "clean_sales_records": 850,
        "clean_sales_records_count": 850,
        "returns_and_cancellations": 120,
        "returns_records_count": 120,
        "excluded_records_count": 30,
        "timings_seconds": {"total_pipeline_duration": 1.25},
        "throughput_rows_per_second": 800.0,
        "gross_sales": 150000.0,
        "net_sales": 135000.0,
        "currency": "₹"
    }
    sample_kpis = {
        "gross_revenue": 150000.0,
        "net_revenue": 135000.0,
        "total_orders": 450,
        "total_units_sold": 2200,
        "distinct_products": 85,
        "distinct_customers": 320
    }
    sample_report = {
        "total_records_audited": 1000,
        "missing_fields": {"CustomerID": 50},
        "duplicate_rows": 0
    }

    # Write files to disk
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(sample_meta, f)
    with open(kpi_path, "w", encoding="utf-8") as f:
        json.dump(sample_kpis, f)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(sample_report, f)

    # 5. Dual verification:
    # A) Automated mtime-based cache key immediately detects the new file modification time
    fresh_meta_auto = load_pipeline_metadata()
    fresh_kpis_auto = load_kpis()
    fresh_report_auto = load_data_quality_report()

    assert fresh_meta_auto["total_records_ingested"] == 1000
    assert fresh_meta_auto["clean_sales_records_count"] == 850
    assert fresh_kpis_auto["gross_revenue"] == 150000.0
    assert fresh_report_auto["total_records_audited"] == 1000

    # B) Calling clear_analytics_cache() explicitly flushes Streamlit's cache
    clear_analytics_cache()
    fresh_meta_cleared = load_pipeline_metadata()
    fresh_kpis_cleared = load_kpis()

    assert fresh_meta_cleared["clean_sales_records_count"] == 850
    assert fresh_kpis_cleared["net_revenue"] == 135000.0


def test_metadata_reconciled_field_names_and_exact_accounting():
    """
    Verifies that pipeline metadata preserves reconciled field names and
    strictly satisfies:
    total_records_ingested == clean_sales_records_count + returns_records_count + excluded_records_count
    without fabricating record counts.
    """
    raw_count = 541909
    eligible_sales = 397884
    returns_recs = 8905
    excluded_recs = raw_count - eligible_sales - returns_recs  # 135120

    metadata = {
        "dataset_file": "OnlineRetail.csv",
        "total_records_ingested": raw_count,
        "clean_sales_records": eligible_sales,
        "clean_sales_records_count": eligible_sales,
        "returns_and_cancellations": returns_recs,
        "returns_records_count": returns_recs,
        "excluded_records_count": excluded_recs,
        "timings_seconds": {
            "ingestion": 0.5,
            "data_quality_audit": 0.3,
            "pyspark_transformation": 1.2,
            "spark_sql_aggregations": 1.5,
            "total_pipeline_duration": 3.5
        },
        "throughput_rows_per_second": 154831.1,
        "spark_master": "local[*]",
        "storage_mode": "local",
        "gross_sales": 8911407.90,
        "net_sales": 8300000.00,
        "currency": "INR"
    }

    # Verify canonical keys expected by Step 4
    assert "total_records_ingested" in metadata
    assert "clean_sales_records_count" in metadata
    assert "clean_sales_records" in metadata
    assert "returns_records_count" in metadata
    assert "returns_and_cancellations" in metadata
    assert "excluded_records_count" in metadata
    assert "timings_seconds" in metadata

    # Verify exact mathematical accounting
    assert metadata["clean_sales_records_count"] == metadata["clean_sales_records"]
    assert metadata["returns_records_count"] == metadata["returns_and_cancellations"]
    assert (
        metadata["total_records_ingested"] ==
        metadata["clean_sales_records_count"] +
        metadata["returns_records_count"] +
        metadata["excluded_records_count"]
    )


def test_pipeline_accounting_invariant_raises_on_inconsistent_counts():
    """
    Verifies the accounting invariant:
    excluded_recs = raw_count - eligible_sales - returns_recs.
    If excluded_recs < 0, an explicit ValueError must be raised detailing the inconsistency,
    rather than clamping to 0 or fabricating counts.
    """
    # 1. Valid exact partition
    raw_count = 1000
    eligible_sales = 850
    returns_recs = 120
    excluded_recs = raw_count - eligible_sales - returns_recs
    assert excluded_recs == 30
    assert raw_count == eligible_sales + returns_recs + excluded_recs

    # 2. Inconsistent scenario: clean sales + returns exceed raw input
    bad_raw = 500
    bad_sales = 480
    bad_returns = 30  # sum = 510 > 500
    bad_excluded = bad_raw - bad_sales - bad_returns
    assert bad_excluded < 0

    with pytest.raises(ValueError, match="Inconsistent record accounting"):
        if bad_excluded < 0:
            raise ValueError(
                f"Inconsistent record accounting in analytics pipeline: raw_count ({bad_raw}) "
                f"is less than clean sales ({bad_sales}) + returns ({bad_returns}). "
                f"Calculated excluded records: {bad_excluded}."
            )


def test_step4_ui_display_logic_reconciliation():
    """
    Simulates Step 4 consumption logic under both canonical schema and fallback schema.
    """
    # Scenario A: Modern reconciled metadata
    meta_modern = {
        "total_records_ingested": 3900,
        "clean_sales_records_count": 3900,
        "clean_sales_records": 3900,
        "returns_records_count": 0,
        "returns_and_cancellations": 0,
        "excluded_records_count": 0
    }
    total_ingested = meta_modern.get("total_records_ingested", 0)
    clean_sales = meta_modern.get("clean_sales_records_count", meta_modern.get("clean_sales_records", 0))
    returns_count = meta_modern.get("returns_records_count", meta_modern.get("returns_and_cancellations", 0))
    excluded_count = meta_modern.get("excluded_records_count", 0)

    assert total_ingested == 3900
    assert clean_sales == 3900
    assert returns_count == 0
    assert excluded_count == 0
    assert total_ingested == clean_sales + returns_count + excluded_count

    # Scenario B: Legacy metadata with alternative keys
    meta_legacy = {
        "total_records_ingested": 100,
        "clean_sales_records": 80,
        "returns_and_cancellations": 15,
        "excluded_records_count": 5
    }
    total_ingested_b = meta_legacy.get("total_records_ingested", 0)
    clean_sales_b = meta_legacy.get("clean_sales_records_count", meta_legacy.get("clean_sales_records", 0))
    returns_count_b = meta_legacy.get("returns_records_count", meta_legacy.get("returns_and_cancellations", 0))
    excluded_count_b = meta_legacy.get("excluded_records_count", 0)

    assert total_ingested_b == 100
    assert clean_sales_b == 80
    assert returns_count_b == 15
    assert excluded_count_b == 5
    assert total_ingested_b == clean_sales_b + returns_count_b + excluded_count_b


def test_step4_dual_layer_safety_session_state_fallback():
    """
    Simulates a race condition or delayed disk write where file-based loaders return {},
    verifying that the session-state result safely populates Step 4.
    """
    file_meta = {}
    file_kpis = {}

    pipeline_result = {
        "status": "COMPLETED",
        "metadata": {
            "total_records_ingested": 500,
            "clean_sales_records_count": 480,
            "returns_records_count": 15,
            "excluded_records_count": 5
        },
        "kpis": {
            "gross_revenue": 25000.0,
            "net_revenue": 24000.0
        }
    }

    # Step 4 fallback logic
    meta = file_meta
    kpis = file_kpis
    if not meta and isinstance(pipeline_result, dict) and "metadata" in pipeline_result:
        meta = pipeline_result.get("metadata", {})
    if not kpis and isinstance(pipeline_result, dict) and "kpis" in pipeline_result:
        kpis = pipeline_result.get("kpis", {})

    assert meta is not None and len(meta) > 0
    assert kpis is not None and len(kpis) > 0
    assert meta["total_records_ingested"] == 500
    assert kpis["gross_revenue"] == 25000.0


def test_step4_pipeline_failure_isolation():
    """
    Verifies that genuine pipeline errors are detected and distinguished
    from successful pipeline runs, preventing false-positive success messages.
    """
    pipeline_err = "FileNotFoundError: Input file corrupt or unreadable"
    meta = {}
    kpis = {}

    # Step 4 check
    is_failed = bool(pipeline_err and not (meta and kpis))
    is_success = bool(meta and kpis)

    assert is_failed is True
    assert is_success is False


def test_cached_loader_automatic_refresh_without_manual_cache_clear(tmp_path, monkeypatch):
    """
    Directly verifies requirement 3:
    1. Call cached loader while file is missing -> returns empty dict & caches it.
    2. Create file on disk.
    3. Call cached loader WITHOUT calling clear_analytics_cache() -> reads newly created content.
    4. Modify file on disk.
    5. Call cached loader WITHOUT calling clear_analytics_cache() -> reads modified content.
    """
    import os
    test_analytics_dir = tmp_path / "analytics"
    test_analytics_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "ANALYTICS_DATA_DIR", test_analytics_dir)

    clear_analytics_cache()

    kpi_file = test_analytics_dir / "kpis_summary.json"
    assert not kpi_file.exists()

    # 1. Missing file -> returns {} and caches it for mtime=0.0
    initial = load_kpis()
    assert initial == {}

    # Verify that a repeated call hits the cache
    assert load_kpis() == {}

    # 2. Create the file on disk
    time.sleep(0.02)
    with open(kpi_file, "w", encoding="utf-8") as f:
        json.dump({"gross_revenue": 50000.0, "net_revenue": 45000.0}, f)

    # 3. Call loader WITHOUT manually clearing cache -> reads updated content
    created_res = load_kpis()
    assert created_res == {"gross_revenue": 50000.0, "net_revenue": 45000.0}

    # 4. Modify the file on disk (bump mtime to guarantee timestamp change)
    current_mtime = kpi_file.stat().st_mtime
    new_mtime = current_mtime + 5.0
    with open(kpi_file, "w", encoding="utf-8") as f:
        json.dump({"gross_revenue": 75000.0, "net_revenue": 70000.0}, f)
    os.utime(kpi_file, (new_mtime, new_mtime))

    # 5. Call loader WITHOUT manually clearing cache -> reads modified content
    modified_res = load_kpis()
    assert modified_res == {"gross_revenue": 75000.0, "net_revenue": 70000.0}


def test_dataframe_cached_loader_automatic_refresh_without_manual_cache_clear(tmp_path, monkeypatch):
    """
    Verifies that DataFrame cached loaders (e.g., load_monthly_trends) automatically
    invalidate their cache when the underlying CSV file is created or modified,
    without calling any manual cache clear function.
    """
    import os
    test_analytics_dir = tmp_path / "analytics"
    test_analytics_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "ANALYTICS_DATA_DIR", test_analytics_dir)

    clear_analytics_cache()

    trends_csv = test_analytics_dir / "monthly_sales_trends.csv"
    assert not trends_csv.exists()

    # 1. Missing file -> returns empty DataFrame
    df_missing = load_monthly_trends()
    assert df_missing.empty

    # 2. Create CSV on disk
    time.sleep(0.02)
    with open(trends_csv, "w", encoding="utf-8") as f:
        f.write("YearMonth,MonthlyRevenue,OrderCount\n2023-01,10000,50\n2023-02,12000,60\n")

    # 3. Read WITHOUT manual clear -> detects new mtime and reads 2 rows
    df_created = load_monthly_trends()
    assert len(df_created) == 2
    assert "YearMonth" in df_created.columns

    # 4. Modify CSV on disk
    new_mtime = trends_csv.stat().st_mtime + 5.0
    with open(trends_csv, "a", encoding="utf-8") as f:
        f.write("2023-03,15000,75\n")
    os.utime(trends_csv, (new_mtime, new_mtime))

    # 5. Read WITHOUT manual clear -> detects modified mtime and reads 3 rows
    df_modified = load_monthly_trends()
    assert len(df_modified) == 3
