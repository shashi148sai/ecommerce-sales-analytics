"""
SalesPulse Analytics - Home Page
Welcoming, beginner-friendly landing page with prominent CTAs,
guided 3-step workflow, template downloads, and clear dataset status indicators.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from config import settings
from src.dashboard.utils import (
    load_kpis,
    load_pipeline_metadata,
    load_monthly_trends,
    apply_chart_theme,
    get_csv_template,
    format_number,
    format_currency,
    get_active_currency_config
)
from src.processing.pipeline import run_pipeline


def render_page():
    # --------------------------------------------------------------------------
    # 1. Hero Section & Value Proposition
    # --------------------------------------------------------------------------
    st.title("⚡ SalesPulse Analytics")
    st.markdown("#### *Turn your e-commerce sales data into meaningful business insights.*")
    st.caption(
        "Modern enterprise analytics platform for processing, analyzing, and visualizing e-commerce transactions. "
        "Supports flexible file formats, automatic schema detection, and native Indian Rupee (`₹`) localization."
    )
    
    symbol, code, rate = get_active_currency_config()
    meta = load_pipeline_metadata()
    kpis = load_kpis()
    
    # --------------------------------------------------------------------------
    # 2. Three-Step Workflow Guide (Upload, Analyze, Explore)
    # --------------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("##### 🚀 Simple 3-Step Analytics Workflow")
        w1, w2, w3 = st.columns(3)
        with w1:
            st.markdown("**1. 📥 Upload**")
            st.caption("Upload CSV, Excel, TSV, JSON, Parquet, or paste copied transaction rows.")
        with w2:
            st.markdown("**2. ⚡ Analyze**")
            st.caption("Auto-detect column names, reconcile schema, and execute Spark SQL aggregations.")
        with w3:
            st.markdown("**3. 📊 Explore**")
            st.caption("Explore executive sales KPIs, bestseller rankings, customer cohorts, and demand forecasts.")
            
    # --------------------------------------------------------------------------
    # 3. Primary Call-to-Action Buttons
    # --------------------------------------------------------------------------
    cta_col1, cta_col2, cta_col3, cta_col4 = st.columns([1.3, 1.4, 1.4, 1.3])
    
    with cta_col1:
        if st.button("🚀 Upload Your Dataset", type="primary", use_container_width=True):
            st.session_state["nav_selection"] = "📥 Upload & Manage Data"
            st.rerun()
            
    with cta_col2:
        if st.button("🛍️ Explore Shopping Data", type="secondary", use_container_width=True, help="Load Consumer Shopping Trends dataset (3,900 consumer purchase logs)"):
            with st.spinner("Loading Consumer Shopping dataset..."):
                shop_file = getattr(settings, "SAMPLE_SHOPPING_FILE", settings.RAW_DATA_DIR / "shopping.csv")
                if shop_file.exists():
                    st.session_state["active_dataset_type"] = "shopping"
                    st.session_state["dataset_source_currency"] = "USD"
                    try:
                        run_pipeline(input_file_path=shop_file)
                        st.session_state["nav_selection"] = "💼 Sales Overview"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load shopping dataset: {str(e)}")
                else:
                    st.warning("Shopping dataset file not found at data/raw/shopping.csv.")
                    
    with cta_col3:
        if st.button("🛒 Explore Retail 540K", type="secondary", use_container_width=True, help="Load UCI Online Retail dataset (541,909 transactions)"):
            with st.spinner("Loading UCI Online Retail dataset..."):
                retail_file = settings.DEFAULT_RAW_FILE
                if retail_file.exists():
                    st.session_state["active_dataset_type"] = "canonical"
                    st.session_state["dataset_source_currency"] = "GBP"
                    try:
                        run_pipeline(input_file_path=retail_file)
                        st.session_state["nav_selection"] = "💼 Sales Overview"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load retail dataset: {str(e)}")
                else:
                    st.warning("OnlineRetail.csv not found at data/raw/.")
                    
    with cta_col4:
        st.download_button(
            label="📥 Download CSV Template",
            data=get_csv_template(),
            file_name="salespulse_template.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download a clean CSV template with standard headers and sample transactions."
        )
        
    st.write("")
    
    # --------------------------------------------------------------------------
    # 4. Active Dataset Overview / Live Metrics Snapshot
    # --------------------------------------------------------------------------
    dataset_type = st.session_state.get("active_dataset_type", "shopping" if meta and "shopping" in str(meta.get("dataset_file", "")).lower() else ("canonical" if meta else "none"))
    
    if meta and kpis:
        with st.container(border=True):
            hdr_col, btn_col = st.columns([3, 1])
            with hdr_col:
                if dataset_type == "shopping" or (meta and "shopping" in str(meta.get("dataset_file", "")).lower()):
                    st.markdown("##### 🛍️ Active Dataset: **Consumer Shopping Trends (shopping.csv)** *(Sample Data)*")
                elif dataset_type == "sample" or dataset_type == "canonical":
                    st.markdown("##### 🧪 Active Dataset: **UCI Online Retail (OnlineRetail.csv)** *(Sample Data)*")
                else:
                    st.markdown(f"##### 📁 Active Dataset: **{meta.get('dataset_file', 'User Uploaded Data')}** *(User Data)*")
                st.caption(
                    f"**{format_number(meta.get('total_records_ingested', 0))}** transactions analyzed • "
                    f"Reporting Currency: **{code} ({symbol})**"
                )
            with btn_col:
                if st.button("Open Full Dashboard ➔", type="primary", use_container_width=True):
                    st.session_state["nav_selection"] = "💼 Sales Overview"
                    st.rerun()
                    
            st.divider()
            
            # Interactive 4-metric live teaser
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("NET SALES", format_currency(kpis.get("net_revenue"), compact=True))
            with m2:
                st.metric("TOTAL ORDERS", format_number(kpis.get("total_orders")))
            with m3:
                st.metric("UNITS SOLD", format_number(kpis.get("total_units_sold")))
            with m4:
                st.metric("CATALOG SKUs", format_number(kpis.get("distinct_products")))
                
            # Interactive sparkline overview
            monthly_trends = load_monthly_trends()
            if not monthly_trends.empty:
                st.write("")
                scaled_rev = monthly_trends["MonthlyRevenue"] * rate
                fig_spark = px.area(
                    monthly_trends,
                    x="YearMonth",
                    y=scaled_rev,
                    title=f"📈 Overall Revenue Progression ({symbol})",
                    labels={"y": f"Revenue ({symbol})", "YearMonth": "Month"}
                )
                fig_spark.update_traces(line_color="#2563EB", fillcolor="rgba(37,99,235,0.08)")
                fig_spark.update_layout(
                    height=220,
                    margin=dict(l=30, r=20, t=35, b=25),
                    xaxis=dict(showgrid=False, title=""),
                    yaxis=dict(showgrid=True, gridcolor="#F1F5F9", tickprefix=symbol)
                )
                apply_chart_theme(fig_spark)
                st.plotly_chart(fig_spark, use_container_width=True)
    else:
        with st.container(border=True):
            st.markdown("##### ℹ️ Welcome! No Dataset Loaded")
            st.write(
                "No transaction dataset is currently loaded. Get started in seconds by uploading your sales data or exploring with our included sample datasets:"
            )
            sc1, sc2 = st.columns(2)
            with sc1:
                if st.button("📁 Upload Your Dataset", type="primary", use_container_width=True):
                    st.session_state["nav_selection"] = "📥 Upload & Manage Data"
                    st.rerun()
            with sc2:
                if st.button("🛍️ Explore Shopping Trends Data", use_container_width=True):
                    st.session_state["active_dataset_type"] = "shopping"
                    st.session_state["dataset_source_currency"] = "USD"
                    run_pipeline(input_file_path=getattr(settings, "SAMPLE_SHOPPING_FILE", settings.RAW_DATA_DIR / "shopping.csv"))
                    st.session_state["nav_selection"] = "💼 Sales Overview"
                    st.rerun()

    st.write("")
    
    # --------------------------------------------------------------------------
    # 5. Interactive Analytics Modules Directory
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
            st.caption("Governance audits, schema validation scores, and clean data downloads.")
            if st.button("View Data Quality", key="nav_to_quality", use_container_width=True):
                st.session_state["nav_selection"] = "🛡️ Data Quality & Reports"
                st.rerun()
    with f6:
        with st.container(border=True):
            st.markdown("##### ⚙️ System Settings")
            st.caption(f"Presentation currency: **{code} ({symbol})**, reference rates, and preferences.")
            if st.button("View Settings", key="nav_to_settings", use_container_width=True):
                st.session_state["nav_selection"] = "⚙️ Settings"
                st.rerun()


if __name__ == "__main__":
    render_page()
