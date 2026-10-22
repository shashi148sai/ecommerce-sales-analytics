"""
SalesPulse Analytics - Customer and Regional Analytics Page
Analyzes geographic revenue distributions, UK vs International markets,
and customer retention / repeat purchase metrics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard.utils import (
    load_country_revenue,
    load_repeat_customers,
    format_currency,
    format_number,
    format_percent,
    render_kpi_card,
    apply_chart_theme,
    CHART_COLORS
)


def render_page():
    st.title("🌍 Customer and Regional Analytics")
    st.markdown("Examine geographic revenue concentration and analyze customer loyalty and repeat purchasing patterns.")
    
    country_df = load_country_revenue()
    repeat_stats = load_repeat_customers()
    
    if country_df.empty:
        st.warning("⚠️ Regional analytics data is unavailable. Please process the dataset first.")
        return
        
    tab1, tab2 = st.tabs(["🗺️ Geographic Performance", "👥 Customer Loyalty & Retention"])
    
    with tab1:
        st.subheader("Regional Revenue Distribution")
        
        # Calculate UK vs International
        uk_row = country_df[country_df["Country"] == "United Kingdom"]
        intl_rows = country_df[country_df["Country"] != "United Kingdom"]
        
        total_rev = country_df["TotalRevenue"].sum()
        uk_rev = uk_row["TotalRevenue"].iloc[0] if not uk_row.empty else 0.0
        intl_rev = intl_rows["TotalRevenue"].sum()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            render_kpi_card("Total Global Revenue", format_currency(total_rev, compact=True), subtitle=f"Across {len(country_df)} countries")
        with c2:
            render_kpi_card("Domestic (UK) Revenue", format_currency(uk_rev, compact=True), subtitle=f"{format_percent((uk_rev/total_rev)*100)} of total")
        with c3:
            render_kpi_card("International Revenue", format_currency(intl_rev, compact=True), subtitle=f"{format_percent((intl_rev/total_rev)*100)} of total")
            
        col_chart, col_intl = st.columns([3, 2])
        
        with col_chart:
            # Choropleth or Bar of Top 10 Countries
            top_countries = country_df.head(10).copy()
            fig_country = px.bar(
                top_countries,
                x="TotalRevenue",
                y="Country",
                orientation="h",
                color="TotalRevenue",
                color_continuous_scale="Blues",
                title="Top 10 Countries by Revenue (£)",
                labels={"TotalRevenue": "Revenue (£)", "Country": "Country"}
            )
            fig_country.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
            apply_chart_theme(fig_country)
            st.plotly_chart(fig_country, use_container_width=True)
            
        with col_intl:
            st.markdown("**Top International Markets (Excl. UK)**")
            top_intl = intl_rows.head(8).copy()
            st.dataframe(
                top_intl[["Country", "TotalRevenue", "OrderCount", "CountryAOV"]].style.format({
                    "TotalRevenue": "£{:,.2f}",
                    "OrderCount": "{:,}",
                    "CountryAOV": "£{:.2f}"
                }),
                use_container_width=True
            )
            
        st.markdown("---")
        st.subheader("All Countries Summary Table")
        st.dataframe(
            country_df.style.format({
                "TotalRevenue": "£{:,.2f}",
                "OrderCount": "{:,}",
                "CustomerCount": "{:,}",
                "UnitsSold": "{:,}",
                "CountryAOV": "£{:.2f}"
            }),
            use_container_width=True
        )
        
    with tab2:
        st.subheader("Customer Retention and Guest Checkout Audit")
        
        if repeat_stats:
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                render_kpi_card("Registered Customers", format_number(repeat_stats.get("total_registered_customers")))
            with rc2:
                render_kpi_card("Repeat Customers", format_number(repeat_stats.get("repeat_customers_count")), subtitle=f"{repeat_stats.get('repeat_customer_rate_percent')}% of registered")
            with rc3:
                render_kpi_card("One-Time Buyers", format_number(repeat_stats.get("one_time_customers_count")), subtitle="Single invoice completed")
            with rc4:
                render_kpi_card("Repeat Revenue Share", f"{repeat_stats.get('repeat_revenue_share_percent', 0.0):.1f}%", subtitle="Of registered customer revenue")
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Pie Chart of Buyer Distribution
            col_p1, col_p2 = st.columns(2)
            
            with col_p1:
                pie_data = pd.DataFrame({
                    "Segment": ["Repeat Customers (>1 Order)", "One-Time Customers (1 Order)"],
                    "Count": [repeat_stats.get("repeat_customers_count", 0), repeat_stats.get("one_time_customers_count", 0)]
                })
                fig_pie = px.pie(
                    pie_data,
                    names="Segment",
                    values="Count",
                    color="Segment",
                    color_discrete_sequence=[CHART_COLORS["primary"], CHART_COLORS["accent"]],
                    title="Customer Frequency Breakdown"
                )
                apply_chart_theme(fig_pie)
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with col_p2:
                rev_pie = pd.DataFrame({
                    "RevenueSource": ["Repeat Customers", "One-Time Customers", "Guest Checkouts (Unregistered)"],
                    "Revenue": [
                        repeat_stats.get("repeat_customers_revenue", 0.0),
                        repeat_stats.get("one_time_customers_revenue", 0.0),
                        repeat_stats.get("guest_revenue", 0.0)
                    ]
                })
                fig_rev_pie = px.pie(
                    rev_pie,
                    names="RevenueSource",
                    values="Revenue",
                    color_discrete_sequence=[CHART_COLORS["primary"], CHART_COLORS["accent"], CHART_COLORS["slate"]],
                    title="Revenue Contribution by Checkout Type"
                )
                apply_chart_theme(fig_rev_pie)
                st.plotly_chart(fig_rev_pie, use_container_width=True)
        else:
            st.info("Repeat customer analysis data not available.")


if __name__ == "__main__":
    render_page()
