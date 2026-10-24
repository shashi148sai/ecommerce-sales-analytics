"""
SalesPulse Analytics - Home Page
Modern, professional SaaS landing page with distinct visual separation,
live KPI snapshot, clear call-to-actions, and direct module navigation.
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
    # 1. Page Title & Value Proposition
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
    dataset_type = st.session_state.get(
        "active_dataset_type",
        "shopping" if meta and "shopping" in str(meta.get("dataset_file", "")).lower() else ("canonical" if meta else "none")
    )
    
    # --------------------------------------------------------------------------
    # SECTION 1: Active Dataset Status & Immediate Actions
    # --------------------------------------------------------------------------
    st.write("")
    with st.container(border=True):
        if meta and kpis:
            col_info, col_act1, col_act2, col_act3 = st.columns([2.5, 1.2, 1.1, 1.2], vertical_alignment="center")
            
            with col_info:
                if dataset_type == "shopping" or (meta and "shopping" in str(meta.get("dataset_file", "")).lower()):
                    st.markdown("##### 🛍️ Active Dataset: **Consumer Shopping Trends**")
                    st.caption(f"`shopping.csv` • **{format_number(meta.get('total_records_ingested', 0))}** transactions • Display: **{code} ({symbol})**")
                elif dataset_type in ("sample", "canonical"):
                    st.markdown("##### 🧪 Active Dataset: **UCI Online Retail 540K**")
                    st.caption(f"`OnlineRetail.csv` • **{format_number(meta.get('total_records_ingested', 0))}** transactions • Display: **{code} ({symbol})**")
                else:
                    st.markdown(f"##### 📁 Active Dataset: **{meta.get('dataset_file', 'Custom Dataset')}**")
                    st.caption(f"**{format_number(meta.get('total_records_ingested', 0))}** transactions analyzed • Display: **{code} ({symbol})**")
                    
            with col_act1:
                if st.button("📊 Open Sales Overview ➔", type="primary", use_container_width=True, help="Open executive commercial KPIs and quarterly reports"):
                    st.session_state["nav_selection"] = "💼 Sales Overview"
                    st.rerun()
                    
            with col_act2:
                if st.button("📥 Upload Data", type="secondary", use_container_width=True, help="Upload a new sales spreadsheet or paste rows"):
                    st.session_state["nav_selection"] = "📥 Upload & Manage Data"
                    st.rerun()
                    
            with col_act3:
                st.download_button(
                    label="📥 CSV Template",
                    data=get_csv_template(),
                    file_name="salespulse_template.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Download a clean CSV template with standard transaction headers"
                )
        else:
            st.markdown("##### ℹ️ Welcome! No Sales Dataset Active")
            st.write("Import your sales spreadsheet to begin analysis, or start immediately with our included sample datasets:")
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                if st.button("🚀 Upload Your Dataset", type="primary", use_container_width=True):
                    st.session_state["nav_selection"] = "📥 Upload & Manage Data"
                    st.rerun()
            with col_e2:
                if st.button("🛍️ Load Shopping Sample Data", type="secondary", use_container_width=True):
                    st.session_state["active_dataset_type"] = "shopping"
                    st.session_state["dataset_source_currency"] = "USD"
                    shop_path = getattr(settings, "SAMPLE_SHOPPING_FILE", settings.RAW_DATA_DIR / "shopping.csv")
                    run_pipeline(input_file_path=shop_path)
                    st.session_state["nav_selection"] = "💼 Sales Overview"
                    st.rerun()

    # --------------------------------------------------------------------------
    # SECTION 2: Live Executive Performance & Revenue Progression
    # --------------------------------------------------------------------------
    if meta and kpis:
        st.write("")
        with st.container(border=True):
            st.markdown("##### 📈 Executive Performance Snapshot")
            
            # 4 KPI metric cards
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("NET SALES", format_currency(kpis.get("net_revenue"), compact=True))
            with m2:
                st.metric("TOTAL ORDERS", format_number(kpis.get("total_orders")))
            with m3:
                st.metric("UNITS SOLD", format_number(kpis.get("total_units_sold")))
            with m4:
                st.metric("CATALOG SKUs", format_number(kpis.get("distinct_products")))
                
            # Revenue progression chart
            monthly_trends = load_monthly_trends()
            if not monthly_trends.empty:
                st.write("")
                scaled_rev = monthly_trends["MonthlyRevenue"] * rate
                fig_spark = px.area(
                    monthly_trends,
                    x="YearMonth",
                    y=scaled_rev,
                    title=f"Monthly Revenue Progression ({symbol})",
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

    # --------------------------------------------------------------------------
    # SECTION 3: Specialized Analytics Modules Directory
    # --------------------------------------------------------------------------
    st.write("")
    st.markdown("### 📑 Specialized Analytics Dashboards")
    st.caption("Jump directly to detailed business intelligence views:")
    
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    with row1_c1:
        with st.container(border=True):
            st.markdown("##### 💼 Commercial Sales")
            st.caption("Gross & net revenue reconciliation, returns, AOV, and Indian FY quarter breakdowns.")
            if st.button("Open Sales Overview ➔", key="btn_go_sales", use_container_width=True):
                st.session_state["nav_selection"] = "💼 Sales Overview"
                st.rerun()
                
    with row1_c2:
        with st.container(border=True):
            st.markdown("##### 📦 Products & SKUs")
            st.caption("Bestsellers ranked by revenue, unit volume, merchandise categories, and SKU lookup.")
            if st.button("Open Product Insights ➔", key="btn_go_products", use_container_width=True):
                st.session_state["nav_selection"] = "📦 Product Insights"
                st.rerun()
                
    with row1_c3:
        with st.container(border=True):
            st.markdown("##### 👥 Customers & Cohorts")
            st.caption("Repeat purchase rates, buyer retention cohorts, and geographic sales distribution.")
            if st.button("Open Customer Insights ➔", key="btn_go_customers", use_container_width=True):
                st.session_state["nav_selection"] = "👥 Customer Insights"
                st.rerun()
                
    row2_c1, row2_c2, row2_c3 = st.columns(3)
    with row2_c1:
        with st.container(border=True):
            st.markdown("##### 📈 Trends & Forecast")
            st.caption("Monthly growth rates, day-of-week shopping patterns, and Holt-Winters demand forecasting.")
            if st.button("Open Sales Trends ➔", key="btn_go_trends", use_container_width=True):
                st.session_state["nav_selection"] = "📈 Sales Trends"
                st.rerun()
                
    with row2_c2:
        with st.container(border=True):
            st.markdown("##### 🛡️ Data Quality & Audit")
            st.caption("Governance completeness audits, schema validation scoring, and cleaned CSV export.")
            if st.button("Open Quality Reports ➔", key="btn_go_quality", use_container_width=True):
                st.session_state["nav_selection"] = "🛡️ Data Quality & Reports"
                st.rerun()
                
    with row2_c3:
        with st.container(border=True):
            st.markdown("##### ⚙️ Settings & Currency")
            st.caption(f"Presentation currency: **{code} ({symbol})**, reference rates, and sample dataset reset.")
            if st.button("Open Settings ➔", key="btn_go_settings", use_container_width=True):
                st.session_state["nav_selection"] = "⚙️ Settings"
                st.rerun()

    # --------------------------------------------------------------------------
    # SECTION 4: Demonstration Datasets
    # --------------------------------------------------------------------------
    st.write("")
    with st.container(border=True):
        st.markdown("##### 🧪 Switch Demonstration Dataset")
        st.caption("Instantly swap the active business scenario between included benchmark datasets:")
        demo_col1, demo_col2 = st.columns(2)
        with demo_col1:
            if st.button("🛍️ Load Consumer Shopping Trends Data (3,900 Orders)", use_container_width=True):
                with st.spinner("Processing Consumer Shopping dataset..."):
                    shop_file = getattr(settings, "SAMPLE_SHOPPING_FILE", settings.RAW_DATA_DIR / "shopping.csv")
                    st.session_state["active_dataset_type"] = "shopping"
                    st.session_state["dataset_source_currency"] = "USD"
                    try:
                        run_pipeline(input_file_path=shop_file)
                        st.session_state["nav_selection"] = "💼 Sales Overview"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load dataset: {str(e)}")
        with demo_col2:
            if st.button("🛒 Load UCI Online Retail Data (541K Records)", use_container_width=True):
                with st.spinner("Processing UCI Online Retail dataset..."):
                    retail_file = settings.DEFAULT_RAW_FILE
                    st.session_state["active_dataset_type"] = "canonical"
                    st.session_state["dataset_source_currency"] = "GBP"
                    try:
                        run_pipeline(input_file_path=retail_file)
                        st.session_state["nav_selection"] = "💼 Sales Overview"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load dataset: {str(e)}")


if __name__ == "__main__":
    render_page()
