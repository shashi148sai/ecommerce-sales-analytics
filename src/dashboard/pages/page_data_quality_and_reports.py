"""
SalesPulse Analytics - Data Quality & Reports Page
Provides comprehensive data health auditing, null distributions,
anomaly and business rule violation tracking, data export downloads,
and Amazon S3 logical prefix data lake inspection.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path

from config import settings
from src.dashboard.utils import (
    load_data_quality_report,
    load_pipeline_metadata,
    load_kpis,
    format_number,
    format_currency,
    format_percent,
    render_kpi_card,
    get_active_currency_config,
    apply_chart_theme,
    CHART_COLORS
)
from src.storage.storage_manager import StorageManager


def render_page():
    st.title("🛡️ Data Quality, Governance & Reports")
    st.caption("Comprehensive data health auditing, record exclusion breakdown, downloadable reports, and cloud data lake management.")
    
    storage = StorageManager()
    quality_report = load_data_quality_report()
    metadata = load_pipeline_metadata()
    kpis = load_kpis()
    symbol, code, rate = get_active_currency_config()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Data Quality Audit", "📥 Reports & Exports", "☁️ Storage & S3 Lake", "⏱️ Engine Telemetry"])
    
    # --------------------------------------------------------------------------
    # Tab 1: Data Quality Audit
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Data Conformance & Quality Health Audit")
        st.caption("Detailed statistical evaluation of data integrity, null distributions, and business rule conformance.")
        
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
            st.markdown("##### 📊 Missing Value Distribution Across Attributes")
            missing_data = []
            for col_name, stats in quality_report.get("missing_values", {}).items():
                missing_data.append({
                    "Attribute / Column": col_name,
                    "Missing Count": format_number(stats.get("null_count")),
                    "Missing Percentage": f"{stats.get('null_percentage')}%",
                    "Impact": "Guest checkout" if col_name == "CustomerID" else ("No country segmentation" if col_name == "Country" else "Essential for analytics")
                })
            st.dataframe(pd.DataFrame(missing_data), use_container_width=True)
            
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
            st.info("ℹ️ No data quality report generated yet. Import and process a dataset in **Upload & Manage Data**.")
            
    # --------------------------------------------------------------------------
    # Tab 2: Reports & Exports
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Downloadable Analytics Summaries & Reports")
        st.caption("Export processed sales data, analytical summaries, and JSON audit files for external reporting or spreadsheets.")
        
        c_exp1, c_exp2 = st.columns(2)
        
        with c_exp1:
            with st.container(border=True):
                st.markdown("##### 📊 Commercial Summary Reports")
                monthly_csv_path = settings.ANALYTICS_DATA_DIR / "monthly_sales_trends.csv"
                if monthly_csv_path.exists():
                    with open(monthly_csv_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="📥 Monthly Sales Trends (CSV)",
                            data=f.read(),
                            file_name="salespulse_monthly_trends.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                top_prod_path = settings.ANALYTICS_DATA_DIR / "top_products_revenue.csv"
                if top_prod_path.exists():
                    with open(top_prod_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="📥 Top Products by Revenue (CSV)",
                            data=f.read(),
                            file_name="salespulse_top_products.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
        with c_exp2:
            with st.container(border=True):
                st.markdown("##### 🛡️ Governance & Audit JSON Exports")
                kpis_json_path = settings.ANALYTICS_DATA_DIR / "kpis_summary.json"
                if kpis_json_path.exists():
                    with open(kpis_json_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="📥 Executive KPIs Summary (JSON)",
                            data=f.read(),
                            file_name="salespulse_kpis_summary.json",
                            mime="application/json",
                            use_container_width=True
                        )
                quality_json_path = settings.REPORTS_DIR / "data_quality_report.json"
                if quality_json_path.exists():
                    with open(quality_json_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="📥 Full Data Quality Audit (JSON)",
                            data=f.read(),
                            file_name="salespulse_data_quality_report.json",
                            mime="application/json",
                            use_container_width=True
                        )
                        
    # --------------------------------------------------------------------------
    # Tab 3: Storage & S3 Lake
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("Hybrid Storage Management (Local & Amazon S3)")
        st.caption("SalesPulse organizes data into an enterprise logical prefix hierarchy mirroring AWS cloud data lakes.")
        
        c_mode, c_bucket = st.columns(2)
        with c_mode:
            st.info(f"**Current Storage Mode:** `{storage.storage_mode.upper()}` (₹0 Local Safety)")
        with c_bucket:
            st.info(f"**Target S3 Bucket:** `{storage.bucket_name}`")
            
        if st.button("🔍 Probe S3 Connectivity & Permissions (Mock/Safe)"):
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
            st.dataframe(file_df, use_container_width=True)
        else:
            st.write(f"No files currently listed under prefix `{selected_cat}/`.")
            
        st.divider()
        st.markdown("##### ☁️ Cloud Synchronization (₹0 Safety)")
        st.caption("Replicates local processed Parquet tables and reports to Amazon S3 when live cloud operations are authorized.")
        if st.button("☁️ Synchronize Local Artifacts to S3"):
            with st.spinner("Connecting to Amazon S3..."):
                sync_res = storage.sync_local_to_s3()
                if sync_res.get("status") == "SUCCESS":
                    st.success(f" Successfully uploaded {sync_res['uploaded_count']} objects to s3://{storage.bucket_name}/.")
                else:
                    st.warning(f"⚠️ S3 Sync: {sync_res.get('message', 'Uploads incomplete. Check credentials.')}")
                    
    # --------------------------------------------------------------------------
    # Tab 4: Engine Telemetry
    # --------------------------------------------------------------------------
    with tab4:
        st.subheader("PySpark Pipeline Telemetry & Latency")
        if metadata:
            timings = metadata.get("timings_seconds", {})
            total_duration = timings.get("total_pipeline_duration", 0.0)
            throughput = metadata.get("throughput_rows_per_second", 0.0)
            rows = metadata.get("total_records_ingested", 0)
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                render_kpi_card("Total Ingested", format_number(rows), subtitle=metadata.get("dataset_file"))
            with c2:
                render_kpi_card("Pipeline Duration", f"{total_duration:.2f}s", subtitle="End-to-end execution")
            with c3:
                render_kpi_card("Throughput", f"{throughput:,.1f}", subtitle="Rows per second")
            with c4:
                render_kpi_card("Spark Master", metadata.get("spark_master", "local[2]"), subtitle="Local CPU Cores Allocated")
                
            st.divider()
            stage_data = [
                {"Stage": "1. Data Ingestion & Schema Binding", "Seconds": timings.get("ingestion", 0.0)},
                {"Stage": "2. Data Quality Audit & Rules Check", "Seconds": timings.get("data_quality_audit", 0.0)},
                {"Stage": "3. PySpark Transformations & Cleaning", "Seconds": timings.get("pyspark_transformation", 0.0)},
                {"Stage": "4. Spark SQL Aggregations & Storage", "Seconds": timings.get("spark_sql_aggregations", 0.0)}
            ]
            st.dataframe(pd.DataFrame(stage_data), use_container_width=True)
        else:
            st.info("No pipeline execution telemetry available yet.")


if __name__ == "__main__":
    render_page()
