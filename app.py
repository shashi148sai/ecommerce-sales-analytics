"""
SalesPulse Analytics - Main Application Entrance
Big Data Analytics (BDA) & Cloud Computing (CC) Integrated Web Application
Powered by Apache Spark, PySpark, Spark SQL, Amazon S3, and Streamlit.
"""

import streamlit as st
from config import settings
from src.dashboard.utils import (
    load_pipeline_metadata,
    get_active_currency_config,
    inject_professional_styles,
    render_header_bar,
    render_footer
)
from src.dashboard.pages import (
    page_0_home as p0,
    page_upload_and_manage as p_upload,
    page_1_sales_overview as p1,
    page_2_product_analytics as p2,
    page_3_sales_trends as p3,
    page_4_customer_and_regional as p4,
    page_data_quality_and_reports as p_quality,
    page_settings as p_settings
)
import importlib
for _mod in [p0, p_upload, p1, p2, p3, p4, p_quality, p_settings]:
    importlib.reload(_mod)

# Page configuration
st.set_page_config(
    page_title="SalesPulse Analytics | Enterprise Big Data & Sales Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern SaaS styling
inject_professional_styles()

# ------------------------------------------------------------------------------
# Session State Initialization (Default Presentation Currency: INR)
# ------------------------------------------------------------------------------
meta = load_pipeline_metadata()
if meta and "shopping" in str(meta.get("dataset_file", "")).lower():
    st.session_state["dataset_source_currency"] = "USD"
    if "active_dataset_type" not in st.session_state:
        st.session_state["active_dataset_type"] = "shopping"

if "currency_mode" not in st.session_state:
    st.session_state["currency_mode"] = "INR (₹)"
    st.session_state["active_currency_symbol"] = "₹"
    
if "inr_conversion_rate" not in st.session_state:
    st.session_state["inr_conversion_rate"] = settings.DEFAULT_GBP_TO_INR_RATE
    
if "usd_conversion_rate" not in st.session_state:
    st.session_state["usd_conversion_rate"] = getattr(settings, "DEFAULT_USD_TO_INR_RATE", 84.00)
    
if "dataset_source_currency" not in st.session_state:
    st.session_state["dataset_source_currency"] = "USD" if meta and "shopping" in str(meta.get("dataset_file", "")).lower() else "GBP"
    
if "active_dataset_type" not in st.session_state:
    st.session_state["active_dataset_type"] = "shopping" if meta and "shopping" in str(meta.get("dataset_file", "")).lower() else ("canonical" if meta else "none")

# ------------------------------------------------------------------------------
# Sidebar Navigation & Environment Information
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ **SalesPulse** `Enterprise`")
    st.caption("Big Data & Cloud E-Commerce Analytics")
    
    # Active Dataset Status Badge
    dataset_type = st.session_state.get("active_dataset_type", "shopping" if meta and "shopping" in str(meta.get("dataset_file", "")).lower() else ("canonical" if meta else "none"))
    
    if dataset_type == "shopping" or (meta and "shopping" in str(meta.get("dataset_file", "")).lower()):
        st.success("🛍️ **Active:** Consumer Shopping Data (shopping.csv)")
    elif dataset_type == "sample":
        st.info("🧪 **Active:** Included Retail Sample")
    elif meta:
        st.success(f"● **Active:** {meta.get('dataset_file', 'OnlineRetail.csv')}")
    else:
        st.warning("○ **Active:** No Dataset Loaded")
        
    st.divider()
    
    # Navigation Pages (8 Sections matching requirements)
    pages = {
        "🏠 Home": p0.render_page,
        "📥 Upload & Manage Data": p_upload.render_page,
        "💼 Sales Overview": p1.render_page,
        "📦 Product Insights": p2.render_page,
        "👥 Customer Insights": p4.render_page,
        "📈 Sales Trends": p3.render_page,
        "🛡️ Data Quality & Reports": p_quality.render_page,
        "⚙️ Settings": p_settings.render_page,
    }
    
    page_keys = list(pages.keys())
    
    # Support programmatic navigation from buttons via session state
    if "nav_selection" not in st.session_state or st.session_state["nav_selection"] not in page_keys:
        st.session_state["nav_selection"] = page_keys[0]
        
    current_index = page_keys.index(st.session_state["nav_selection"])
    
    selected_page = st.radio(
        "Platform Navigation",
        page_keys,
        index=current_index,
        key="nav_radio",
        label_visibility="collapsed"
    )
    st.session_state["nav_selection"] = selected_page
    
    st.divider()
    
    # Quick Currency Switcher
    st.markdown("**💱 Currency Presentation:**")
    src_curr = str(st.session_state.get("dataset_source_currency", "USD" if dataset_type == "shopping" else "GBP")).upper()
    
    if src_curr == "USD":
        curr_options = ["INR (₹) - Indian Rupees", "USD ($) - US Dollars", "GBP (£) - British Pounds"]
    else:
        curr_options = ["INR (₹) - Indian Rupees", "GBP (£) - British Pounds", "USD ($) - US Dollars"]
        
    curr_idx = 0
    cur_mode = st.session_state.get("currency_mode", "INR (₹)")
    if cur_mode.startswith("USD"):
        curr_idx = 1 if src_curr == "USD" else 2
    elif cur_mode.startswith("GBP"):
        curr_idx = 2 if src_curr == "USD" else 1
        
    curr_radio = st.radio(
        "Active Display Currency:",
        options=curr_options,
        index=curr_idx,
        label_visibility="collapsed"
    )
    
    if curr_radio.startswith("INR"):
        st.session_state["currency_mode"] = "INR (₹)"
        st.session_state["active_currency_symbol"] = "₹"
    elif curr_radio.startswith("USD"):
        st.session_state["currency_mode"] = "USD ($)"
        st.session_state["active_currency_symbol"] = "$"
    else:
        st.session_state["currency_mode"] = "GBP (£)"
        st.session_state["active_currency_symbol"] = "£"
        
    symbol, code, rate = get_active_currency_config()
    if code == "INR" and src_curr == "USD":
        st.caption(f"Ref Rate: `1 USD = ₹{rate:.2f}`")
    elif code == "INR" and src_curr == "GBP":
        st.caption(f"Ref Rate: `1 GBP = ₹{rate:.2f}`")
    elif code == "INR" and src_curr == "INR":
        st.caption("Native INR Dataset `(1:1 direct)`")
        
    st.divider()
    st.caption(
        f"**Engine:** PySpark 3.5 (Catalyst)\n\n"
        f"**Storage:** {settings.STORAGE_MODE.upper()} (₹0 Local Safety)\n\n"
        f"SalesPulse Analytics © 2026"
    )

# ------------------------------------------------------------------------------
# Main Page Body: Global Header + Active View + Footer
# ------------------------------------------------------------------------------
render_header_bar()
pages[selected_page]()
render_footer()
