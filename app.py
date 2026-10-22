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

# ------------------------------------------------------------------------------
# Sidebar Navigation & Environment Information
# ------------------------------------------------------------------------------
st.sidebar.title("⚡ SalesPulse Analytics")
st.sidebar.caption("B.Tech Capstone Project: Big Data Analytics & Cloud Computing")

# Storage Mode Indicator
storage_badge_text = "Local Storage (₹0 Cost)" if settings.STORAGE_MODE == "local" else f"Amazon S3 ({settings.AWS_S3_BUCKET})"
st.sidebar.success(f"● Storage: {storage_badge_text}")

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

st.sidebar.divider()
st.sidebar.markdown("**System Profile:**")
st.sidebar.text(f"Engine: PySpark 3.5\nSpark Master: {settings.SPARK_MASTER}\nCurrency: {settings.DEFAULT_CURRENCY} (GBP)")

meta = load_pipeline_metadata()
if meta:
    st.sidebar.markdown(
        f"**Dataset:** `{meta.get('dataset_file')}`\n"
        f"- Ingested: **{meta.get('total_records_ingested', 0):,}**\n"
        f"- Throughput: **{meta.get('throughput_rows_per_second', 0):,.1f} rows/s**"
    )

st.sidebar.divider()
st.sidebar.caption("SalesPulse Analytics © 2026\nAcademic Project for BDA & Cloud Computing")

# Render active page
pages[selected_page]()
