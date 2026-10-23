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

# ------------------------------------------------------------------------------
# Indian-First Currency & Localization Configuration
# ------------------------------------------------------------------------------
if "currency_mode" not in st.session_state:
    st.session_state["currency_mode"] = "GBP (£)"
if "inr_conversion_rate" not in st.session_state:
    st.session_state["inr_conversion_rate"] = settings.DEFAULT_GBP_TO_INR_RATE

st.sidebar.subheader("💱 Currency Presentation")
currency_selection = st.sidebar.radio(
    "Select Display Currency:",
    options=["GBP (£) - Original Dataset", "INR (₹) - Converted Reference"],
    index=0 if st.session_state["currency_mode"].startswith("GBP") else 1,
    help="Canonical dataset is in GBP (£). Choose INR (₹) to dynamically apply the documented reference exchange rate."
)

if currency_selection.startswith("GBP"):
    st.session_state["currency_mode"] = "GBP (£)"
    st.session_state["active_currency_symbol"] = "£"
else:
    st.session_state["currency_mode"] = "INR (₹)"
    st.session_state["active_currency_symbol"] = "₹"

with st.sidebar.expander("⚙️ Localization & FX Settings", expanded=False):
    st.caption("Documented Reference Exchange Rate:")
    custom_rate = st.number_input(
        "1 GBP to INR (₹)",
        min_value=1.0,
        max_value=500.0,
        value=float(st.session_state["inr_conversion_rate"]),
        step=0.5,
        format="%.2f"
    )
    st.session_state["inr_conversion_rate"] = custom_rate
    
    st.info(
        f"**Source Currency:** GBP (£)\n\n"
        f"**Target Currency:** INR (₹)\n\n"
        f"**Exchange Rate:** 1 GBP = ₹{custom_rate:.2f}\n\n"
        f"**Rate Date:** {settings.REFERENCE_RATE_DATE}\n\n"
        "*(Reference rate used for Indian presentation; historical transaction dates retain canonical £ values.)*"
    )
    st.caption(f"**Fiscal Year:** Indian FY (1 Apr – 31 Mar)\n\n**Locale:** `{settings.LOCALE}` | **TZ:** `{settings.TIMEZONE}`")

st.sidebar.divider()

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
st.sidebar.text(
    f"Engine: PySpark 3.5\n"
    f"Spark Master: {settings.SPARK_MASTER}\n"
    f"Active Currency: {st.session_state['currency_mode']}\n"
    f"Storage: {settings.STORAGE_MODE.upper()} (₹0 Offline)"
)

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
