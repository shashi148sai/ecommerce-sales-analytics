"""
SalesPulse Analytics - Settings & System Configuration Page
Allows users to configure presentation currency (INR default vs GBP), reference exchange rates,
Indian localization preferences, and inspect Big Data & Cloud engine profiles.
"""

import streamlit as st
from config import settings
from src.dashboard.utils import get_active_currency_config


def render_page():
    st.title("⚙️ Application Settings & Preferences")
    st.caption("Manage currency presentation, reference exchange rates, Indian localization, and system runtime parameters.")
    
    symbol, code, rate = get_active_currency_config()
    
    tab1, tab2, tab3 = st.tabs(["💱 Currency & Localization", "⚡ Big Data & Spark Profile", "☁️ Cloud Storage (₹0 Safety)"])
    
    # --------------------------------------------------------------------------
    # Tab 1: Currency & Localization
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Presentation Currency & Exchange Rate")
        st.markdown(
            "SalesPulse Analytics defaults to **Indian Rupees (₹)** for presentation. "
            "Canonical British e-commerce datasets denominated in **GBP (£)** are converted dynamically "
            "using a transparently documented reference exchange rate."
        )
        
        with st.container(border=True):
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                curr_option = st.radio(
                    "Display Currency Presentation:",
                    options=["INR (₹) - Indian Rupees (Default)", "GBP (£) - British Pounds (Original Source)"],
                    index=0 if st.session_state.get("currency_mode", "INR (₹)").startswith("INR") else 1,
                    help="All dashboard KPI cards, charts, and table summaries adapt to this selection."
                )
                
                if curr_option.startswith("INR"):
                    st.session_state["currency_mode"] = "INR (₹)"
                    st.session_state["active_currency_symbol"] = "₹"
                else:
                    st.session_state["currency_mode"] = "GBP (£)"
                    st.session_state["active_currency_symbol"] = "£"
                    
            with col_c2:
                custom_rate = st.number_input(
                    "Reference Exchange Rate (1 GBP in ₹):",
                    min_value=1.0,
                    max_value=500.0,
                    value=float(st.session_state.get("inr_conversion_rate", settings.DEFAULT_GBP_TO_INR_RATE)),
                    step=0.5,
                    format="%.2f",
                    help="Documented reference rate used for currency conversion without requiring paid external FX APIs."
                )
                st.session_state["inr_conversion_rate"] = custom_rate
                
            st.divider()
            
            # Sourced Disclosure
            src_curr = st.session_state.get("dataset_source_currency", "GBP")
            st.info(
                f"**Currency Policy Disclosure:**\n\n"
                f"- **Active Presentation Currency:** `{st.session_state['currency_mode']}`\n"
                f"- **Dataset Source Currency:** `{src_curr}`\n"
                f"- **Configured Exchange Rate:** `1 GBP = ₹{custom_rate:.2f}` (Reference Date: {settings.REFERENCE_RATE_DATE})\n"
                f"- **Conversion Methodology:** When source is GBP and presentation is INR, prices and totals are scaled by ₹{custom_rate:.2f}. "
                f"If the dataset is already native INR, no conversion multiplier is applied. "
                f"This fixed reference rate preserves ₹0 out-of-pocket costs by avoiding paid live currency APIs."
            )
            
        st.divider()
        st.subheader("Indian Business Conventions")
        with st.container(border=True):
            i1, i2, i3 = st.columns(3)
            with i1:
                st.markdown("**Locale & Region:**")
                st.text(f"Locale: {settings.LOCALE}\nTimezone: {settings.TIMEZONE}")
            with i2:
                st.markdown("**Date Display Format:**")
                st.text("Format: DD-MM-YYYY\nWeek Start: Monday")
            with i3:
                st.markdown("**Fiscal Year Cycle:**")
                st.text("Cycle: 1 April – 31 March\nQuarters: Q1, Q2, Q3, Q4")
                
    # --------------------------------------------------------------------------
    # Tab 2: Big Data & Spark Profile
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Apache Spark Engine Profile")
        st.caption("Inspect PySpark master configuration, driver memory, and Catalyst query optimizer settings.")
        
        with st.container(border=True):
            p1, p2, p3 = st.columns(3)
            with p1:
                st.text_input("PySpark Master Node", value=settings.SPARK_MASTER, disabled=True)
            with p2:
                st.text_input("Driver Memory Allocation", value=settings.SPARK_DRIVER_MEMORY, disabled=True)
            with p3:
                st.text_input("Shuffle Partitions", value=settings.SPARK_SQL_SHUFFLE_PARTITIONS, disabled=True)
                
            st.info(
                "⚡ **Distributed Execution Architecture:**\n\n"
                "PySpark runs locally utilizing JVM worker threads (`local[2]`) with in-memory execution. "
                "Leveraging the Catalyst query optimizer and lazy DAG evaluation, "
                "the exact same transformation pipeline and Spark SQL models scale seamlessly to cloud clusters "
                "(such as Amazon EMR or Databricks) with zero code modifications."
            )
            
    # --------------------------------------------------------------------------
    # Tab 3: Cloud Storage & ₹0 Safety
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("Cloud Storage Architecture & ₹0 Safety Constraints")
        st.caption("SalesPulse is architected for Amazon S3 cloud replication while strictly enforcing offline ₹0 safety during local development.")
        
        with st.container(border=True):
            st.write(f"- **Active Storage Mode:** `{settings.STORAGE_MODE.upper()}` (Local Disk Persistence)")
            st.write(f"- **Target S3 Bucket Name:** `{settings.AWS_S3_BUCKET}`")
            st.write(f"- **AWS Region:** `{settings.AWS_REGION}`")
            st.write("- **Cloud Operations:** Disabled by default to guarantee ₹0 out-of-pocket expense.")
            st.write("- **Security:** AWS credentials are never committed to version control or requested in the UI.")
            
        st.divider()
        if st.button("🔄 Reset Application Session State"):
            st.session_state.clear()
            st.success("Session state cleared. Reloading application...")
            st.rerun()


if __name__ == "__main__":
    render_page()
