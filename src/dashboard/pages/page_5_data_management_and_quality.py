"""
SalesPulse Analytics - Data Management and Quality Auditing Page
Provides dataset upload, pipeline triggering, comprehensive data quality reporting,
and Amazon S3 cloud storage management.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from config import settings
from src.dashboard.utils import (
    load_data_quality_report,
    load_pipeline_metadata,
    format_number,
    format_percent,
    render_kpi_card,
    apply_chart_theme,
    CHART_COLORS
)
from src.processing.pipeline import run_pipeline
from src.storage.storage_manager import StorageManager


def render_page():
    st.title("🛡️ Data Management & Quality Auditing")
    st.caption("Execute data engineering pipelines, audit data health metrics, and manage local & Amazon S3 storage.")
    
    storage = StorageManager()
    quality_report = load_data_quality_report()
    metadata = load_pipeline_metadata()
    
    tab1, tab2, tab3 = st.tabs(["🚀 Pipeline Execution", "📋 Data Quality Audit", "☁️ Storage & Amazon S3"])
    
    # --------------------------------------------------------------------------
    # Tab 1: Pipeline Execution
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Run PySpark Analytics Pipeline")
        st.caption(
            "Execute the end-to-end Big Data pipeline: Ingestion ➔ Schema Conformance ➔ "
            "PySpark Transformations ➔ Spark SQL Aggregations ➔ Storage Replication."
        )
        
        with st.container(border=True):
            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                dataset_option = st.radio(
                    "Select Ingestion Source:",
                    ["Default Canonical Dataset (data/raw/OnlineRetail.csv)", "Lightweight Sample (sample_retail.csv)", "Upload New CSV/XLSX"],
                    index=0
                )
                
            with col_opt2:
                row_limit_opt = st.selectbox(
                    "Execution Scale / Row Limit:",
                    ["All Records (Full Execution)", "5,000 Rows", "25,000 Rows", "50,000 Rows"],
                    index=0
                )
                
            uploaded_file = None
            if dataset_option == "Upload New CSV/XLSX":
                uploaded_file = st.file_uploader("Upload Transaction File (.csv, .xlsx)", type=["csv", "xlsx"])
                
            run_btn = st.button("⚡ Execute Big Data Pipeline", type="primary")
            
        if run_btn:
            target_path = None
            if dataset_option == "Lightweight Sample (sample_retail.csv)":
                target_path = settings.SAMPLE_RAW_FILE
            elif dataset_option == "Upload New CSV/XLSX" and uploaded_file is not None:
                save_dest = settings.RAW_DATA_DIR / uploaded_file.name
                with open(save_dest, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                target_path = save_dest
            else:
                target_path = settings.DEFAULT_RAW_FILE
                
            limit_val = None
            if row_limit_opt == "5,000 Rows":
                limit_val = 5000
            elif row_limit_opt == "25,000 Rows":
                limit_val = 25000
            elif row_limit_opt == "50,000 Rows":
                limit_val = 50000
                
            with st.spinner("Executing PySpark distributed pipeline..."):
                try:
                    res = run_pipeline(input_file_path=target_path, limit_rows=limit_val)
                    st.success(f" Pipeline executed successfully! Processed {res['metadata']['total_records_ingested']:,} records in {res['metadata']['timings_seconds']['total_pipeline_duration']:.2f}s.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Pipeline execution failed: {str(e)}")
                    
        if metadata:
            st.divider()
            st.markdown("##### ⏱️ Latest Execution Run Profile")
            st.json(metadata)
            
    # --------------------------------------------------------------------------
    # Tab 2: Data Quality Audit
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Data Conformance & Quality Report")
        
        if quality_report:
            qc1, qc2, qc3, qc4 = st.columns(4)
            with qc1:
                render_kpi_card("Total Ingested", format_number(quality_report.get("total_records")))
            with qc2:
                render_kpi_card("Clean Sales Rows", format_number(quality_report.get("clean_records_count")))
            with qc3:
                score = quality_report.get("data_quality_score_percent", 0.0)
                render_kpi_card("Quality Conformance", f"{score}%", subtitle="Passed all business rules")
            with qc4:
                render_kpi_card("Duplicates Handled", format_number(quality_report.get("duplicate_records")), subtitle=f"{quality_report.get('duplicate_percentage')}% duplicates")
                
            st.divider()
            st.markdown("##### 📊 Missing Value Distribution")
            missing_data = []
            for col_name, stats in quality_report.get("missing_values", {}).items():
                missing_data.append({
                    "Column Name": col_name,
                    "Null Count": stats["null_count"],
                    "Null Percentage": f"{stats['null_percentage']}%"
                })
            st.dataframe(pd.DataFrame(missing_data), width="stretch")
            
            st.divider()
            col_viol, col_card = st.columns(2)
            with col_viol:
                with st.container(border=True):
                    st.markdown("##### ⚠️ Business Rule Audit")
                    violations = quality_report.get("business_rule_violations", {})
                    st.write(f"- **Cancellations & Returns (Invoice 'C*' or Qty < 0):** {format_number(violations.get('cancellation_count'))}")
                    st.write(f"- **Negative Quantity Transactions:** {format_number(violations.get('negative_quantity_count'))}")
                    st.write(f"- **Negative Unit Price Rows:** {format_number(violations.get('negative_price_count'))}")
                    st.write(f"- **Zero Unit Price Rows:** {format_number(violations.get('zero_price_count'))}")
            
            with col_card:
                with st.container(border=True):
                    st.markdown("##### 🏷️ Entity Cardinality")
                    cardinality = quality_report.get("cardinality", {})
                    st.write(f"- **Distinct Products (StockCodes):** {format_number(cardinality.get('distinct_products'))}")
                    st.write(f"- **Distinct Registered Customers:** {format_number(cardinality.get('distinct_customers'))}")
                    st.write(f"- **Distinct Operating Countries:** {format_number(cardinality.get('distinct_countries'))}")
        else:
            st.info("No data quality report generated yet. Run the pipeline in Tab 1.")
            
    # --------------------------------------------------------------------------
    # Tab 3: Storage & Amazon S3
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("Hybrid Storage Management (Local & Amazon S3)")
        st.caption(
            "SalesPulse organizes all transactional artifacts into a structured logical prefix hierarchy "
            "mirroring enterprise cloud data lake designs."
        )
        
        c_mode, c_bucket = st.columns(2)
        with c_mode:
            st.info(f"**Current Storage Mode:** `{storage.storage_mode.upper()}`")
        with c_bucket:
            st.info(f"**Target S3 Bucket:** `{storage.bucket_name}`")
            
        if st.button("🔍 Probe S3 Connectivity & Permissions"):
            status = storage.check_s3_status()
            if status["connected"] and status["bucket_exists"]:
                st.success(f" Connected: {status['message']}")
            else:
                st.warning(f"⚠️ S3 Status: {status['message']}")
                
        st.divider()
        st.markdown("##### 📁 Logical Prefix Storage Inspection")
        selected_cat = st.selectbox("Inspect Category Prefix:", list(StorageManager.CATEGORIES))
        
        files = storage.list_files(selected_cat)
        if files:
            file_df = pd.DataFrame(files)
            st.dataframe(file_df, width="stretch")
        else:
            st.write(f"No files currently listed under prefix `{selected_cat}/`.")
            
        st.divider()
        st.markdown("##### ☁️ Cloud Synchronization (₹0 Safety)")
        st.caption(
            "Replicates local processed Parquet tables, analytics summaries, and JSON reports to Amazon S3. "
            "Requires approved AWS credentials. Never commits credentials to Git."
        )
        if st.button("☁️ Synchronize Local Artifacts to S3"):
            with st.spinner("Connecting to Amazon S3..."):
                sync_res = storage.sync_local_to_s3()
                if sync_res.get("status") == "SUCCESS":
                    st.success(f" Successfully uploaded {sync_res['uploaded_count']} objects to s3://{storage.bucket_name}/.")
                else:
                    st.warning(f"⚠️ S3 Sync: {sync_res.get('message', 'Uploads incomplete. Check credentials.')}")


if __name__ == "__main__":
    render_page()
