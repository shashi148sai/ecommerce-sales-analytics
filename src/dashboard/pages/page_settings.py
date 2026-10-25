"""
SalesPulse Analytics - Application Settings & Preferences
Clean, user-centric preferences for display currency, exchange rates, and quick dataset switching.
"""

import streamlit as st
import json
from config import settings
from src.dashboard.utils import get_active_currency_config, load_kpis, clear_analytics_cache
from src.processing.pipeline import run_pipeline


def render_page():
    st.title("⚙️ Application Settings & Preferences")
    st.caption("Customize display currency, adjust reference exchange rates, or switch sample datasets.")
    
    symbol, code, rate = get_active_currency_config()
    src_curr = st.session_state.get("dataset_source_currency", "USD")
    
    tab1, tab2 = st.tabs(["💱 Currency & Localization", "⚡ Data & Application Actions"])
    
    with tab1:
        st.subheader("Presentation Currency & Exchange Rate")
        st.caption("Select your preferred reporting currency. Figures across all dashboards update dynamically.")
        
        with st.container(border=True):
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                cur_mode_val = st.session_state.get("currency_mode", "INR (₹)")
                c_idx = 0
                if cur_mode_val.startswith("USD"):
                    c_idx = 1
                elif cur_mode_val.startswith("GBP"):
                    c_idx = 2
                    
                curr_option = st.radio(
                    "Display Currency Presentation:",
                    options=["INR (₹) - Indian Rupees (Default)", "USD ($) - US Dollars", "GBP (£) - British Pounds"],
                    index=c_idx,
                    help="All dashboard KPI cards, charts, and table summaries adapt to this selection."
                )
                
            with col_c2:
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    custom_usd = st.number_input(
                        "Reference Rate (1 USD in ₹):",
                        min_value=1.0,
                        max_value=200.0,
                        value=float(st.session_state.get("usd_conversion_rate", getattr(settings, "DEFAULT_USD_TO_INR_RATE", 84.00))),
                        step=0.5,
                        format="%.2f",
                        help="Exchange rate for USD-denominated transaction datasets."
                    )
                with col_r2:
                    custom_rate = st.number_input(
                        "Reference Rate (1 GBP in ₹):",
                        min_value=1.0,
                        max_value=500.0,
                        value=float(st.session_state.get("inr_conversion_rate", settings.DEFAULT_GBP_TO_INR_RATE)),
                        step=0.5,
                        format="%.2f",
                        help="Exchange rate for British pound datasets."
                    )
                    
            st.write("")
            col_apply, col_reset = st.columns([1.5, 3])
            with col_apply:
                if st.button("💾 Apply Currency Changes", type="primary", use_container_width=True):
                    if curr_option.startswith("INR"):
                        st.session_state["currency_mode"] = "INR (₹)"
                        st.session_state["active_currency_symbol"] = "₹"
                    elif curr_option.startswith("USD"):
                        st.session_state["currency_mode"] = "USD ($)"
                        st.session_state["active_currency_symbol"] = "$"
                    else:
                        st.session_state["currency_mode"] = "GBP (£)"
                        st.session_state["active_currency_symbol"] = "£"
                    st.session_state["usd_conversion_rate"] = custom_usd
                    st.session_state["inr_conversion_rate"] = custom_rate
                    st.success("✅ Currency settings applied successfully across all dashboard views!")
                    st.rerun()
            with col_reset:
                st.caption(f"Active: `{st.session_state.get('currency_mode', 'INR (₹)')}` • Source: `{src_curr}`")
                
        st.divider()
        st.subheader("Regional & Business Conventions")
        with st.container(border=True):
            i1, i2, i3 = st.columns(3)
            with i1:
                st.markdown("**Locale & Region**")
                st.write("English (India) • IST (UTC+05:30)")
            with i2:
                st.markdown("**Date Format**")
                st.write("DD-MM-YYYY (Standard Indian)")
            with i3:
                st.markdown("**Fiscal Year Cycle**")
                st.write("1 April – 31 March (Indian FY)")
                
    with tab2:
        st.subheader("Dataset Quick Actions")
        st.caption("Switch between sample datasets or clear application caches with a single click.")
        
        with st.container(border=True):
            st.markdown("##### 🧪 Fast Dataset Switcher")
            st.caption("Instantly load and analyze included business datasets:")
            
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                if st.button("🛍️ Load Shopping Trends Data (3,900 Rows)", use_container_width=True):
                    shop_file = getattr(settings, "SAMPLE_SHOPPING_FILE", settings.RAW_DATA_DIR / "shopping.csv")
                    if shop_file.exists():
                        with st.spinner("Processing Consumer Shopping dataset..."):
                            st.session_state["active_dataset_type"] = "shopping"
                            st.session_state["dataset_source_currency"] = "USD"
                            run_pipeline(input_file_path=shop_file)
                            clear_analytics_cache()
                            st.session_state["nav_selection"] = "💼 Sales Overview"
                            st.rerun()
                    else:
                        st.warning("Shopping dataset file not found at data/raw/shopping.csv.")
            with d_col2:
                if st.button("🛒 Load Retail Transactions Data (540K Rows)", use_container_width=True):
                    retail_file = settings.DEFAULT_RAW_FILE
                    if retail_file.exists():
                        with st.spinner("Processing Retail dataset..."):
                            st.session_state["active_dataset_type"] = "canonical"
                            st.session_state["dataset_source_currency"] = "GBP"
                            run_pipeline(input_file_path=retail_file)
                            clear_analytics_cache()
                            st.session_state["nav_selection"] = "💼 Sales Overview"
                            st.rerun()
                    else:
                        st.warning("OnlineRetail.csv not found at data/raw/.")
                        
        st.divider()
        st.subheader("System & Cache Maintenance")
        with st.container(border=True):
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                if st.button("🔄 Clear Cache & Reload", use_container_width=True):
                    clear_analytics_cache()
                    st.success("Cache cleared! Reloading...")
                    st.rerun()
            with m_col2:
                if st.button("🗑️ Reset Settings to Default", use_container_width=True):
                    st.session_state["currency_mode"] = "INR (₹)"
                    st.session_state["active_currency_symbol"] = "₹"
                    st.session_state["usd_conversion_rate"] = 84.00
                    st.session_state["inr_conversion_rate"] = settings.DEFAULT_GBP_TO_INR_RATE
                    st.success("Settings reset to defaults.")
                    st.rerun()
            with m_col3:
                kpis = load_kpis()
                st.download_button(
                    label="📥 Download Summary (JSON)",
                    data=json.dumps(kpis, indent=4),
                    file_name="salespulse_kpis_summary.json",
                    mime="application/json",
                    use_container_width=True
                )


if __name__ == "__main__":
    render_page()
