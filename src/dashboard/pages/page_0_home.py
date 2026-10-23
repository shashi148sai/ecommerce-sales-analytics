"""
SalesPulse Analytics - Home Page
Welcoming, beginner-friendly landing page with prominent CTAs,
guided 3-step workflow, template downloads, and clear dataset status indicators.
"""

import streamlit as st
import pandas as pd
from config import settings
from src.dashboard.utils import (
    load_kpis,
    load_pipeline_metadata,
    get_csv_template,
    format_number,
    format_currency,
    get_active_currency_config
)
from src.processing.pipeline import run_pipeline


def render_page():
    # --------------------------------------------------------------------------
    # Hero Section
    # --------------------------------------------------------------------------
    st.title("⚡ SalesPulse Analytics")
    st.subheader("*Turn your e-commerce sales data into meaningful business insights.*")
    
    st.markdown(
        "Welcome to **SalesPulse Analytics**, an enterprise-grade Big Data & Cloud business analytics platform. "
        "Seamlessly import transactional sales data in any format—CSV, Excel, TSV, JSON, Parquet, or manual entry—"
        "to calculate revenue KPIs, uncover product movers, analyze customer retention, forecast demand, and audit data health."
    )
    
    symbol, code, rate = get_active_currency_config()
    meta = load_pipeline_metadata()
    kpis = load_kpis()
    
    # --------------------------------------------------------------------------
    # Prominent Primary Actions (CTA Buttons)
    # --------------------------------------------------------------------------
    st.write("")
    cta_col1, cta_col2, cta_col3 = st.columns([1.2, 1.2, 1.6])
    
    with cta_col1:
        if st.button("🚀 Upload Your Dataset", type="primary", use_container_width=True):
            st.session_state["nav_selection"] = "📥 Upload & Manage Data"
            st.rerun()
            
    with cta_col2:
        if st.button("🧪 Explore Sample Data", type="secondary", use_container_width=True):
            with st.spinner("Loading included sample e-commerce dataset..."):
                if settings.SAMPLE_RAW_FILE.exists():
                    st.session_state["active_dataset_type"] = "sample"
                    st.session_state["dataset_source_currency"] = "GBP"
                    try:
                        run_pipeline(input_file_path=settings.SAMPLE_RAW_FILE)
                        st.session_state["nav_selection"] = "💼 Sales Overview"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load sample dataset: {str(e)}")
                else:
                    st.warning("Sample dataset file not found at default location.")
                    
    with cta_col3:
        st.download_button(
            label="📥 Download CSV Sales Template",
            data=get_csv_template(),
            file_name="salespulse_template.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download a clean CSV template with standard column headers and example rows."
        )
        
    st.divider()
    
    # --------------------------------------------------------------------------
    # Active Dataset Status Card
    # --------------------------------------------------------------------------
    dataset_type = st.session_state.get("active_dataset_type", "canonical" if meta else "none")
    
    if meta and kpis:
        with st.container(border=True):
            status_col1, status_col2 = st.columns([2.5, 1])
            with status_col1:
                if dataset_type == "sample":
                    st.info(
                        "🧪 **Active Dataset: Included Sample Data (Validation Sample)**\n\n"
                        "*Note: You are currently viewing sample validation data for demonstration purposes.*"
                    )
                else:
                    st.success(
                        f"✅ **Active Dataset:** `{meta.get('dataset_file', 'OnlineRetail.csv')}` — "
                        f"**{format_number(meta.get('total_records_ingested', 0))}** total records ingested | "
                        f"Throughput: **{meta.get('throughput_rows_per_second', 0):,.1f} rows/s**"
                    )
            with status_col2:
                if st.button("View Dashboard ➔", use_container_width=True):
                    st.session_state["nav_selection"] = "💼 Sales Overview"
                    st.rerun()
    else:
        with st.container(border=True):
            st.markdown("#### ℹ️ No Dataset Loaded Yet")
            st.write(
                "To get started, choose one of the options above:\n"
                "- Click **Upload Your Dataset** to upload your own CSV, Excel, JSON, or Parquet file.\n"
                "- Click **Explore Sample Data** to immediately experience the dashboard with pre-packaged data.\n"
                "- Click **Download CSV Sales Template** to see the recommended layout for your data."
            )
            
    st.write("")
    
    # --------------------------------------------------------------------------
    # Three Simple Steps Section
    # --------------------------------------------------------------------------
    st.subheader("How SalesPulse Analytics Works")
    
    step_c1, step_c2, step_c3 = st.columns(3)
    
    with step_c1:
        with st.container(border=True):
            st.markdown("### 1️⃣ Upload or Enter")
            st.markdown(
                "**Flexible Data Ingestion**\n\n"
                "Upload a CSV, XLSX, TSV, JSON, or Parquet file, paste copied table rows directly from Excel, "
                "or enter transactions manually using the built-in data editor."
            )
            
    with step_c2:
        with st.container(border=True):
            st.markdown("### 2️⃣ Validate & Map")
            st.markdown(
                "**Smart Schema Conformance**\n\n"
                "Automatic column detection recognizes your custom field names (e.g. `order_id`, `price`). "
                "Review missing values, duplicate lines, and confirm mappings before processing."
            )
            
    with step_c3:
        with st.container(border=True):
            st.markdown("### 3️⃣ Analyze & Export")
            st.markdown(
                "**Distributed Big Data Analytics**\n\n"
                "PySpark and Spark SQL calculate revenue, order velocity, customer loyalty, and demand forecasts. "
                "Explore interactive Plotly charts and export cleaned data & audit reports."
            )
            
    st.divider()
    
    # --------------------------------------------------------------------------
    # Platform Capabilities Feature Grid
    # --------------------------------------------------------------------------
    st.subheader("Explore Available Analytics Modules")
    
    f1, f2, f3 = st.columns(3)
    with f1:
        with st.container(border=True):
            st.markdown("##### 💼 Sales Overview")
            st.caption("Gross sales, refunds, net revenue, distinct orders, AOV, and Indian FY quarter filters.")
    with f2:
        with st.container(border=True):
            st.markdown("##### 📦 Product Insights")
            st.caption("Bestselling catalog items ranked by revenue & unit volume with interactive SKU search.")
    with f3:
        with st.container(border=True):
            st.markdown("##### 👥 Customer Insights")
            st.caption("Repeat buyer cohort analysis, loyalty revenue share, and geographic market distribution.")
            
    f4, f5, f6 = st.columns(3)
    with f4:
        with st.container(border=True):
            st.markdown("##### 📈 Sales Trends")
            st.caption("Temporal progression, Month-over-Month (MoM) growth rates, daily volume, and hourly cycles.")
    with f5:
        with st.container(border=True):
            st.markdown("##### 🛡️ Data Quality & Reports")
            st.caption("Audit reports, missing value analysis, duplicate detection, and Amazon S3 management.")
    with f6:
        with st.container(border=True):
            st.markdown("##### ⚙️ Settings & Localization")
            st.caption(f"Default currency: **{code} ({symbol})**, reference exchange rates, and financial year preferences.")


if __name__ == "__main__":
    render_page()
