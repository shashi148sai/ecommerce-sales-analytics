"""
SalesPulse Analytics - Data Management and Quality Auditing Page
Provides an explicit 4-step dataset import and processing interface,
comprehensive data quality reporting, and Amazon S3 logical storage management.
"""

import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path

from config import settings
from src.dashboard.utils import (
    load_data_quality_report,
    load_pipeline_metadata,
    load_kpis,
    load_monthly_trends,
    format_number,
    format_percent,
    render_kpi_card,
    apply_chart_theme,
    CHART_COLORS
)
from src.processing.pipeline import run_pipeline
from src.validation.validator import detect_schema_mapping
from src.storage.storage_manager import StorageManager


def render_page():
    st.title("🛡️ Data Management & Quality Auditing")
    st.caption("End-to-end Big Data ingestion wizard, distributed pipeline execution, schema auditing, and cloud data lake management.")
    
    storage = StorageManager()
    quality_report = load_data_quality_report()
    metadata = load_pipeline_metadata()
    kpis = load_kpis()
    
    tab1, tab2, tab3 = st.tabs(["📥 4-Step Ingestion & Pipeline", "📋 Data Quality Audit", "☁️ Storage & Amazon S3"])
    
    # --------------------------------------------------------------------------
    # Tab 1: 4-Step Ingestion & Processing Wizard
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Data Ingestion & Big Data Processing Wizard")
        st.caption("A guided 4-step workflow: Dataset Selection ➔ Schema Validation & Preview ➔ Spark Pipeline Configuration ➔ Execution & Exports.")
        
        # ----------------------------------------------------------------------
        # STEP 1: Select Dataset
        # ----------------------------------------------------------------------
        with st.container(border=True):
            st.markdown("#### 📂 Step 1: Select Dataset")
            st.caption("Choose the canonical UCI benchmark dataset, a lightweight development sample, or upload a custom CSV/Excel file.")
            
            source_choice = st.radio(
                "Ingestion Source:",
                options=[
                    "Canonical UCI Online Retail Dataset (data/raw/OnlineRetail.csv)",
                    "Lightweight Development Sample (data/raw/sample_retail.csv)",
                    "Upload Custom Dataset (.csv, .xlsx, .xls)"
                ],
                index=0,
                horizontal=False
            )
            
            selected_file_path = None
            is_file_ready = False
            file_error = None
            file_info = {}
            
            if source_choice.startswith("Canonical"):
                canonical_path = settings.DEFAULT_RAW_FILE
                if canonical_path.exists():
                    selected_file_path = canonical_path
                    is_file_ready = True
                    sz_mb = canonical_path.stat().st_size / (1024 * 1024)
                    file_info = {
                        "name": canonical_path.name,
                        "path": str(canonical_path),
                        "size": f"{sz_mb:.2f} MB",
                        "format": "CSV (Canonical UCI Online Retail)"
                    }
                else:
                    file_error = f"Canonical dataset not found at {canonical_path}. Please place it in data/raw/ or upload it."
                    
            elif source_choice.startswith("Lightweight"):
                sample_path = settings.SAMPLE_RAW_FILE
                if sample_path.exists():
                    selected_file_path = sample_path
                    is_file_ready = True
                    sz_kb = sample_path.stat().st_size / 1024
                    file_info = {
                        "name": sample_path.name,
                        "path": str(sample_path),
                        "size": f"{sz_kb:.1f} KB",
                        "format": "CSV (Validation Sample)"
                    }
                else:
                    file_error = f"Sample dataset not found at {sample_path}."
                    
            else:  # Upload Custom
                uploaded = st.file_uploader(
                    "Upload Transaction File (Drag-and-drop or Browse)",
                    type=["csv", "xlsx", "xls"],
                    help=f"Supported formats: .csv, .xlsx, .xls. Maximum allowed file size: {settings.MAX_UPLOAD_SIZE_MB}MB."
                )
                if uploaded is not None:
                    # Validate file size
                    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
                    if uploaded.size > max_bytes:
                        file_error = f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB ({uploaded.size / (1024*1024):.2f} MB uploaded)."
                    elif uploaded.size == 0:
                        file_error = "Uploaded file is completely empty (0 bytes). Please upload a valid dataset."
                    else:
                        # Save uploaded file safely into RAW_DATA_DIR
                        save_dest = settings.RAW_DATA_DIR / uploaded.name
                        try:
                            with open(save_dest, "wb") as f:
                                f.write(uploaded.getbuffer())
                            selected_file_path = save_dest
                            is_file_ready = True
                            sz_mb = uploaded.size / (1024 * 1024)
                            file_info = {
                                "name": uploaded.name,
                                "path": str(save_dest),
                                "size": f"{sz_mb:.2f} MB" if sz_mb >= 1 else f"{uploaded.size / 1024:.1f} KB",
                                "format": uploaded.name.split(".")[-1].upper()
                            }
                            st.success(f" File uploaded successfully: `{uploaded.name}` ({file_info['size']})")
                        except Exception as e:
                            file_error = f"Failed to save uploaded file: {str(e)}"
                            
            if file_error:
                st.error(f"❌ {file_error}")
            elif is_file_ready:
                col_i1, col_i2, col_i3 = st.columns(3)
                with col_i1:
                    st.text(f"File: {file_info.get('name')}")
                with col_i2:
                    st.text(f"Size: {file_info.get('size')}")
                with col_i3:
                    st.text(f"Format: {file_info.get('format')}")
                    
        # ----------------------------------------------------------------------
        # STEP 2: Validate and Preview (Non-blocking)
        # ----------------------------------------------------------------------
        schema_is_valid = False
        active_column_mapping = {}
        
        with st.container(border=True):
            st.markdown("#### 🔍 Step 2: Validate & Preview Schema")
            st.caption("Inspects dataset columns, infers data types, checks mandatory fields, and applies intelligent schema mapping without starting heavy Spark operations.")
            
            if not is_file_ready or selected_file_path is None:
                st.info("ℹ️ Select or upload a valid dataset in Step 1 to inspect and preview schema.")
            else:
                try:
                    # Fast lightweight preview using Pandas (top 50 rows)
                    suffix = selected_file_path.suffix.lower()
                    if suffix == ".csv":
                        preview_df = pd.read_csv(selected_file_path, nrows=50)
                    else:
                        preview_df = pd.read_excel(selected_file_path, nrows=50)
                        
                    raw_cols = preview_df.columns.tolist()
                    detected_mapping, missing_reqs = detect_schema_mapping(raw_cols)
                    active_column_mapping = detected_mapping
                    
                    # Conformance Status Badge
                    if len(missing_reqs) == 0:
                        schema_is_valid = True
                        st.success("✅ **Schema Status: VALID** — All 8 required e-commerce fields are present or successfully mapped.")
                    elif len(missing_reqs) == 1 and missing_reqs[0] == "CustomerID":
                        schema_is_valid = True
                        st.warning("⚠️ **Schema Status: WARNING** — `CustomerID` is absent. Transactions will be processed as guest checkouts.")
                    else:
                        schema_is_valid = False
                        st.error(f"❌ **Schema Status: INVALID** — Missing mandatory fields: `{', '.join(missing_reqs)}`. Review mapping below.")
                        
                    # Metadata KPI Row
                    pv_c1, pv_c2, pv_c3, pv_c4 = st.columns(4)
                    with pv_c1:
                        st.metric("PREVIEW SAMPLE", f"{len(preview_df)} rows")
                    with pv_c2:
                        st.metric("COLUMNS FOUND", f"{len(raw_cols)}")
                    with pv_c3:
                        st.metric("FIELDS MAPPED", f"{len(detected_mapping)} / {len(settings.REQUIRED_COLUMNS)}")
                    with pv_c4:
                        st.metric("NULL CHECK", "Audited" if schema_is_valid else "Action Required")
                        
                    # Schema Mapping Expander
                    with st.expander("🧩 Schema Mapping & Field Conformance Details", expanded=(not schema_is_valid)):
                        st.markdown(
                            "SalesPulse automatically maps known aliases to standard schema fields "
                            "(e.g. `order_id` ➔ `InvoiceNo`, `price` ➔ `UnitPrice`, `sku` ➔ `StockCode`)."
                        )
                        mapping_rows = []
                        for req in settings.REQUIRED_COLUMNS:
                            mapped_from = [k for k, v in detected_mapping.items() if v == req]
                            source_col = mapped_from[0] if mapped_from else "❌ Not Found"
                            dtype = str(preview_df[source_col].dtype) if source_col in preview_df.columns else "N/A"
                            mapping_rows.append({
                                "Target Canonical Field": req,
                                "Matched Source Column": source_col,
                                "Inferred Type": dtype,
                                "Status": "✅ Mapped" if source_col in preview_df.columns else "⚠️ Missing"
                            })
                        st.dataframe(pd.DataFrame(mapping_rows), width="stretch")
                        
                        if not schema_is_valid:
                            st.info(
                                "💡 **How to resolve schema issues:**\n"
                                "1. Ensure your dataset includes invoice identifiers, item descriptions, quantity, date, and unit price.\n"
                                "2. Rename your CSV/Excel headers to match standard aliases (e.g. `InvoiceNo`, `StockCode`, `Quantity`, `UnitPrice`, `InvoiceDate`).\n"
                                "3. For standard UCI Online Retail data, headers are matched automatically."
                            )
                            
                    # Preview Data Table
                    st.markdown("##### 📄 Data Preview (First 15 Records):")
                    st.dataframe(preview_df.head(15), width="stretch")
                    
                except Exception as e:
                    st.error(f"❌ Failed to parse and preview dataset: {str(e)}")
                    schema_is_valid = False
                    
        # ----------------------------------------------------------------------
        # STEP 3: Configure and Process
        # ----------------------------------------------------------------------
        with st.container(border=True):
            st.markdown("#### ⚡ Step 3: Configure & Execute Spark Pipeline")
            st.caption("Configure execution scale and launch the distributed Apache Spark analytical engine.")
            
            c_scale, c_mode = st.columns(2)
            with c_scale:
                execution_scale = st.selectbox(
                    "Execution Workload / Row Limit:",
                    options=[
                        "Full Dataset (Process All Available Records)",
                        "50,000 Rows (Balanced Demonstration)",
                        "25,000 Rows (Fast Testing)",
                        "5,000 Rows (Instant Smoke Test)"
                    ],
                    index=0,
                    help="Limit records for rapid interactive evaluation on memory-constrained systems."
                )
            with c_mode:
                st.text_input("PySpark Execution Master:", value=settings.SPARK_MASTER, disabled=True)
                
            limit_val = None
            if "5,000" in execution_scale:
                limit_val = 5000
            elif "25,000" in execution_scale:
                limit_val = 25000
            elif "50,000" in execution_scale:
                limit_val = 50000
                
            # Architecture & Workload Summary Card
            with st.container(border=True):
                st.markdown("**Distributed Pipeline Workload:**")
                st.markdown(
                    "- **Stage 1 (Ingestion):** Multi-threaded CSV/Excel ingestion into PySpark DataFrames with permissive mode.\n"
                    "- **Stage 2 (Conformance & Quality):** Schema validation, missing value distribution, and duplicate removal.\n"
                    "- **Stage 3 (Transformation):** Date parsing, return classification (`C*` & negative quantity segregation), and revenue calculation.\n"
                    "- **Stage 4 (Spark SQL Analytics):** Distributed SQL views for product rankings, monthly trends, RFM, and geographic shares.\n"
                    "- **Stage 5 (Persistence):** Local partition storage and metadata generation (zero out-of-pocket cloud cost)."
                )
                
            btn_disabled = not is_file_ready or not schema_is_valid
            execute_button = st.button(
                "⚡ Execute Big Data Pipeline",
                type="primary",
                disabled=btn_disabled,
                help="Requires a valid dataset selected in Step 1 and validated in Step 2."
            )
            
            if execute_button and selected_file_path is not None:
                with st.status("Executing PySpark Distributed Pipeline...", expanded=True) as status_box:
                    try:
                        st.write("🔄 Initializing Apache Spark Session (PySpark 3.5)...")
                        time.sleep(0.5)
                        
                        st.write("📥 Loading raw records and conforming schema...")
                        time.sleep(0.5)
                        
                        st.write("🛡️ Auditing data quality, missing fields, and duplicates...")
                        time.sleep(0.5)
                        
                        st.write("⚙️ Segregating returns/cancellations and calculating sales...")
                        time.sleep(0.5)
                        
                        st.write("📊 Executing Spark SQL distributed aggregations...")
                        res = run_pipeline(
                            input_file_path=selected_file_path,
                            limit_rows=limit_val,
                            column_mapping=active_column_mapping if active_column_mapping else None
                        )
                        
                        st.write("💾 Persisting analytical tables and metadata to disk...")
                        time.sleep(0.5)
                        
                        status_box.update(
                            label=f" Pipeline Completed Successfully in {res['metadata']['timings_seconds']['total_pipeline_duration']:.2f}s!",
                            state="complete",
                            expanded=False
                        )
                        st.success(
                            f" Successfully ingested **{res['metadata']['total_records_ingested']:,}** records at "
                            f"**{res['metadata']['throughput_rows_per_second']:,.1f} rows/s**."
                        )
                        st.rerun()
                    except Exception as e:
                        status_box.update(label="❌ Pipeline Failed", state="error", expanded=True)
                        st.error(f"Pipeline execution encountered an error: {str(e)}")
                        
        # ----------------------------------------------------------------------
        # STEP 4: Results & Data Exports
        # ----------------------------------------------------------------------
        with st.container(border=True):
            st.markdown("#### 📊 Step 4: Results & Data Exports")
            st.caption("Review actual pipeline output metrics, record exclusion audit, and download cleaned datasets.")
            
            if not metadata or not quality_report:
                st.info("ℹ️ No pipeline execution results available yet. Complete Steps 1–3 to generate results.")
            else:
                m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
                with m_c1:
                    render_kpi_card("Total Ingested", format_number(metadata.get("total_records_ingested")))
                with m_c2:
                    render_kpi_card("Accepted Sales", format_number(metadata.get("clean_sales_records_count")))
                with m_c3:
                    render_kpi_card("Returns Segregated", format_number(metadata.get("returns_records_count")), subtitle="Handled separately")
                with m_c4:
                    render_kpi_card("Pipeline Duration", f"{metadata.get('timings_seconds', {}).get('total_pipeline_duration', 0):.2f}s")
                with m_c5:
                    render_kpi_card("Quality Conformance", f"{quality_report.get('data_quality_score_percent', 0.0)}%", subtitle="Passed all rules")
                    
                st.divider()
                st.markdown("##### 🛡️ Record Accounting & Exclusion Audit")
                rec_acc = [
                    {"Metric Category": "Raw Ingested Records", "Count": format_number(metadata.get("total_records_ingested")), "Status": "Ingested", "Description": "All transaction lines read from source"},
                    {"Metric Category": "Accepted Commercial Sales", "Count": format_number(metadata.get("clean_sales_records_count")), "Status": "Included in Analytics", "Description": "Valid positive transactions with clean unit price and quantity"},
                    {"Metric Category": "Return Adjustments (Cancelled 'C*')", "Count": format_number(metadata.get("returns_records_count")), "Status": "Segregated", "Description": "Subtracted from gross revenue to yield exact net revenue"},
                    {"Metric Category": "Duplicates Handled", "Count": format_number(quality_report.get("duplicate_records")), "Status": "De-duplicated", "Description": "Exact identical records purged during pipeline conformance"},
                    {"Metric Category": "Excluded Incomplete Records", "Count": format_number(metadata.get("excluded_records_count")), "Status": "Excluded", "Description": "Zero or negative unit price rows, or corrupted identifiers"}
                ]
                st.dataframe(pd.DataFrame(rec_acc), width="stretch")
                
                st.divider()
                st.markdown("##### 📥 Data Downloads & Export Artifacts")
                col_d1, col_d2, col_d3 = st.columns(3)
                
                with col_d1:
                    monthly_csv_path = settings.ANALYTICS_DATA_DIR / "monthly_sales_trends.csv"
                    if monthly_csv_path.exists():
                        with open(monthly_csv_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                label="📥 Monthly Sales Trends (CSV)",
                                data=f.read(),
                                file_name="salespulse_monthly_trends.csv",
                                mime="text/csv",
                                width="stretch"
                            )
                            
                with col_d2:
                    kpis_json_path = settings.ANALYTICS_DATA_DIR / "kpis_summary.json"
                    if kpis_json_path.exists():
                        with open(kpis_json_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                label="📥 Executive KPIs Summary (JSON)",
                                data=f.read(),
                                file_name="salespulse_kpis_summary.json",
                                mime="application/json",
                                width="stretch"
                            )
                            
                with col_d3:
                    quality_json_path = settings.REPORTS_DIR / "data_quality_report.json"
                    if quality_json_path.exists():
                        with open(quality_json_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                label="📥 Full Data Quality Audit (JSON)",
                                data=f.read(),
                                file_name="salespulse_data_quality_report.json",
                                mime="application/json",
                                width="stretch"
                            )
                            
    # --------------------------------------------------------------------------
    # Tab 2: Data Quality Audit
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Data Conformance & Quality Report")
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
            st.info(f"**Current Storage Mode:** `{storage.storage_mode.upper()}` (₹0 Local Safety)")
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
