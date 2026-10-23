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
    st.markdown(
        "#### Modern Enterprise Sales Intelligence • Powered by Apache Spark & Cloud Architecture"
    )
    st.caption(
        "Process, analyze, and visualize high-volume e-commerce transaction data. "
        "Supports universal file formats, smart column auto-detection, and native Indian rupee (`₹`) localization."
    )
    
    symbol, code, rate = get_active_currency_config()
    meta = load_pipeline_metadata()
    kpis = load_kpis()
    
    # --------------------------------------------------------------------------
    # Primary Call to Action Buttons
    # --------------------------------------------------------------------------
    st.write("")
    cta_col1, cta_col2, cta_col3 = st.columns([1.2, 1.2, 1.4])
    
    with cta_col1:
        if st.button("🚀 Upload Your Dataset", type="primary", use_container_width=True):
            st.session_state["nav_selection"] = "📥 Upload & Manage Data"
            st.rerun()
            
    with cta_col2:
        if st.button("🧪 Explore Sample Dataset", type="secondary", use_container_width=True):
            with st.spinner("Initializing PySpark sample dataset pipeline..."):
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
            help="Download a clean CSV template with standard headers and valid sample transactions."
        )
        
    st.write("")
    
    # --------------------------------------------------------------------------
    # Active Dataset Overview / Live Metrics Snapshot
    # --------------------------------------------------------------------------
    dataset_type = st.session_state.get("active_dataset_type", "canonical" if meta else "none")
    
    if meta and kpis:
        with st.container(border=True):
            hdr_col, btn_col = st.columns([3, 1])
            with hdr_col:
                if dataset_type == "sample":
                    st.markdown("##### 🧪 Active Dataset: **UCI Online Retail (Validation Sample)**")
                else:
                    st.markdown(f"##### ✅ Active Dataset: **{meta.get('dataset_file', 'OnlineRetail.csv')}**")
                st.caption(
                    f"**{format_number(meta.get('total_records_ingested', 0))}** records processed • "
                    f"Throughput: **{meta.get('throughput_rows_per_second', 0):,.1f} rows/s** • "
                    f"Storage: **Local Lakehouse (Parquet)**"
                )
            with btn_col:
                if st.button("Open Dashboard ➔", type="primary", use_container_width=True):
                    st.session_state["nav_selection"] = "💼 Sales Overview"
                    st.rerun()
                    
            st.divider()
            
            # Quick 4-metric live teaser
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("NET SALES", format_currency(kpis.get("net_revenue"), compact=True))
            with m2:
                st.metric("TOTAL ORDERS", format_number(kpis.get("total_orders")))
            with m3:
                st.metric("UNITS SOLD", format_number(kpis.get("total_units_sold")))
            with m4:
                st.metric("CATALOG SKUs", format_number(kpis.get("distinct_products")))
    else:
        with st.container(border=True):
            st.markdown("##### ℹ️ Welcome! No Dataset Loaded")
            st.write(
                "Get started by uploading your own transactions or explore the platform using the built-in demo dataset:"
            )
            sc1, sc2 = st.columns(2)
            with sc1:
                if st.button("📁 Upload Custom Sales Data", type="primary", use_container_width=True):
                    st.session_state["nav_selection"] = "📥 Upload & Manage Data"
                    st.rerun()
            with sc2:
                if st.button("⚡ Quick-Load 540K-Row Sample Data", use_container_width=True):
                    st.session_state["active_dataset_type"] = "sample"
                    run_pipeline(input_file_path=settings.SAMPLE_RAW_FILE)
                    st.session_state["nav_selection"] = "💼 Sales Overview"
                    st.rerun()

    st.write("")
    
    # --------------------------------------------------------------------------
    # Three-Step Workflow Guide
    # --------------------------------------------------------------------------
    st.subheader("How SalesPulse Analytics Operates")
    
    step_c1, step_c2, step_c3 = st.columns(3)
    
    with step_c1:
        with st.container(border=True):
            st.markdown("#### 1️⃣ Ingest Any Format")
            st.caption(
                "Upload files in CSV, Excel, TSV, JSON, Parquet, or safe ZIP archives. "
                "You can also paste copied spreadsheet rows directly or use the interactive grid."
            )
            
    with step_c2:
        with st.container(border=True):
            st.markdown("#### 2️⃣ Validate & Map")
            st.caption(
                "Smart fuzzy alias detection maps your columns automatically. "
                "Audits missing fields, detects return invoices (`C*`), and prevents double-calculation."
            )
            
    with step_c3:
        with st.container(border=True):
            st.markdown("#### 3️⃣ Distributed Insights")
            st.caption(
                "Apache Spark executes high-speed aggregations in memory. "
                "Uncover revenue velocity, customer RFM tiers, regional distribution, and future demand."
            )
            
    st.write("")
    
    # --------------------------------------------------------------------------
    # Analytics Modules Grid with Direct Action Links
    # --------------------------------------------------------------------------
    st.subheader("Explore Analytics Modules")
    
    f1, f2, f3 = st.columns(3)
    with f1:
        with st.container(border=True):
            st.markdown("##### 💼 Sales Overview")
            st.caption("Commercial revenue reconciliation, return rates, and Indian FY quarter filters.")
            if st.button("View Sales Overview", key="nav_to_sales", use_container_width=True):
                st.session_state["nav_selection"] = "💼 Sales Overview"
                st.rerun()
    with f2:
        with st.container(border=True):
            st.markdown("##### 📦 Product Insights")
            st.caption("Bestselling merchandise ranked by revenue and unit volume with SKU search.")
            if st.button("View Product Insights", key="nav_to_products", use_container_width=True):
                st.session_state["nav_selection"] = "📦 Product Insights"
                st.rerun()
    with f3:
        with st.container(border=True):
            st.markdown("##### 👥 Customer Insights")
            st.caption("Buyer cohort retention, loyalty revenue share, and geographic distribution.")
            if st.button("View Customer Insights", key="nav_to_customers", use_container_width=True):
                st.session_state["nav_selection"] = "👥 Customer Insights"
                st.rerun()
                
    f4, f5, f6 = st.columns(3)
    with f4:
        with st.container(border=True):
            st.markdown("##### 📈 Sales Trends & Forecast")
            st.caption("MoM expansion rates, day-of-week cycles, and predictive demand forecasting.")
            if st.button("View Sales Trends", key="nav_to_trends", use_container_width=True):
                st.session_state["nav_selection"] = "📈 Sales Trends"
                st.rerun()
    with f5:
        with st.container(border=True):
            st.markdown("##### 🛡️ Data Quality & Reports")
            st.caption("Governance audits, schema validation scores, and partitioned Lakehouse tree.")
            if st.button("View Data Quality", key="nav_to_quality", use_container_width=True):
                st.session_state["nav_selection"] = "🛡️ Data Quality & Reports"
                st.rerun()
    with f6:
        with st.container(border=True):
            st.markdown("##### ⚙️ System Settings")
            st.caption(f"Presentation currency: **{code} ({symbol})**, reference rates, and Spark profile.")
            if st.button("View Settings", key="nav_to_settings", use_container_width=True):
                st.session_state["nav_selection"] = "⚙️ Settings"
                st.rerun()


if __name__ == "__main__":
    render_page()
