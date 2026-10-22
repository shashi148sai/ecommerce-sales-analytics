"""
SalesPulse Analytics - Main Application Entrance
Big Data Analytics (BDA) & Cloud Computing (CC) Integrated Web Application
Powered by Apache Spark, PySpark, Spark SQL, Amazon S3, and Streamlit.
"""

import streamlit as st
from config import settings
from src.dashboard.utils import load_kpis, load_pipeline_metadata, format_currency, format_number
from src.dashboard.pages import (
    page_1_sales_overview as p1,
    page_2_product_analytics as p2,
    page_3_sales_trends as p3,
    page_4_customer_and_regional as p4,
    page_5_data_management_and_quality as p5,
    page_6_forecasting_and_segmentation as p6,
    page_7_system_performance as p7
)

# Page configuration
st.set_page_config(
    page_title="SalesPulse Analytics | BDA & Cloud Computing",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global styling injection for clean corporate aesthetics
st.markdown("""
<style>
    /* Metric styling */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }
    /* Clean sidebar headers */
    .sidebar-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 2px;
    }
    .sidebar-subtitle {
        font-size: 0.8rem;
        color: #64748B;
        margin-bottom: 16px;
    }
    .badge-status {
        background-color: #ECFDF5;
        color: #065F46;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Sidebar Navigation & Environment Information
# ------------------------------------------------------------------------------
st.sidebar.markdown("<div class='sidebar-header'>⚡ SalesPulse Analytics</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='sidebar-subtitle'>B.Tech BDA & Cloud Computing Project</div>", unsafe_allow_html=True)

# Project Status Badges
storage_badge_text = "Local Storage (₹0 Cost)" if settings.STORAGE_MODE == "local" else f"Amazon S3 ({settings.AWS_S3_BUCKET})"
st.sidebar.markdown(f"<div class='badge-status'>● {storage_badge_text}</div>", unsafe_allow_html=True)

pages = {
    "💼 Sales Overview": p1.render_page,
    "📦 Product Analytics": p2.render_page,
    "📈 Sales Trends": p3.render_page,
    "🌍 Customer and Regional": p4.render_page,
    "🛡️ Data Management & Quality": p5.render_page,
    "🔮 Forecasting & Segmentation": p6.render_page,
    "⚡ System Performance": p7.render_page,
}

selected_page = st.sidebar.radio("Navigation", list(pages.keys()), index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("**System Profile:**")
st.sidebar.text(f"Engine: PySpark 3.5\nSpark Master: {settings.SPARK_MASTER}\nCurrency: {settings.DEFAULT_CURRENCY} (GBP)")

meta = load_pipeline_metadata()
if meta:
    st.sidebar.markdown(f"**Dataset:** `{meta.get('dataset_file')}`\n- Ingested: **{meta.get('total_records_ingested', 0):,}**\n- Throughput: **{meta.get('throughput_rows_per_second', 0):,.1f} rows/s**")

st.sidebar.markdown("---")
st.sidebar.caption("SalesPulse Analytics © 2026\nAcademic Project for BDA & Cloud Computing")

# Render active page
pages[selected_page]()
