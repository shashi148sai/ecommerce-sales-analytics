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
import src.dashboard.utils as dash_utils
importlib.reload(dash_utils)
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
# Navigation Configuration & Synchronized Session State
# ------------------------------------------------------------------------------
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

# Ensure navigation session state is initialized
if "nav_selection" not in st.session_state or st.session_state["nav_selection"] not in page_keys:
    st.session_state["nav_selection"] = page_keys[0]

def on_top_nav_change():
    if "top_pills_val" in st.session_state and st.session_state["top_pills_val"]:
        st.session_state["nav_selection"] = st.session_state["top_pills_val"]

def on_side_nav_change():
    if "side_radio_val" in st.session_state and st.session_state["side_radio_val"]:
        st.session_state["nav_selection"] = st.session_state["side_radio_val"]

# Keep both controls synchronized before widget rendering
st.session_state["top_pills_val"] = st.session_state["nav_selection"]
st.session_state["side_radio_val"] = st.session_state["nav_selection"]

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
        
    if st.button("🔄 Switch / Import Dataset", key="side_switch_ds", use_container_width=True):
        st.session_state["nav_selection"] = "📥 Upload & Manage Data"
        st.rerun()
        
    st.divider()
    
    # Navigation Pages
    st.markdown("**Navigation Pages:**")
    st.radio(
        "Platform Navigation",
        page_keys,
        key="side_radio_val",
        on_change=on_side_nav_change,
        label_visibility="collapsed"
    )
    
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
    st.caption("SalesPulse Analytics © 2026")

# ------------------------------------------------------------------------------
# Top Navigation Bar (Always Visible - Even When Sidebar is Collapsed)
# ------------------------------------------------------------------------------
top_bar_container = st.container()
with top_bar_container:
    tb_col1, tb_col2 = st.columns([1, 4.8], vertical_alignment="center")
    with tb_col1:
        st.markdown(
            "<div style='display:flex; align-items:center; gap:8px; padding-left: 2px;'>"
            "<span style='font-size:1.35rem;'>⚡</span>"
            "<span style='font-size:1.15rem; font-weight:800; color:#0F172A; letter-spacing:-0.02em;'>SalesPulse</span>"
            "</div>",
            unsafe_allow_html=True
        )
    with tb_col2:
        st.pills(
            "Main Navigation",
            options=page_keys,
            key="top_pills_val",
            on_change=on_top_nav_change,
            label_visibility="collapsed"
        )
    st.markdown("<hr style='margin: 0.4rem 0 1.25rem 0; border: none; border-top: 1px solid #E2E8F0;' />", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Main Page Body: Active View + Footer
# ------------------------------------------------------------------------------
active_page = st.session_state.get("nav_selection", page_keys[0])
if active_page in pages:
    pages[active_page]()
else:
    pages[page_keys[0]]()

render_footer()
