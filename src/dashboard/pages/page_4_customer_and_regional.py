"""
SalesPulse Analytics - Customer and Regional Analytics Page
Analyzes geographic revenue distributions, UK vs International markets,
and customer retention / repeat purchase metrics with currency localization.
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
    get_active_currency_config,
    apply_chart_theme,
    CHART_COLORS
)


def render_page():
    st.title("🌍 Customer and Regional Analytics")
    st.caption("Examine geographic revenue concentration and analyze customer loyalty and repeat purchasing patterns.")
    
    country_df = load_country_revenue()
    repeat_stats = load_repeat_customers()
    
    if country_df.empty:
        st.warning("⚠️ Regional analytics data is unavailable. Please process the dataset first.")
        return
        
    symbol, code, rate = get_active_currency_config()
    
    tab1, tab2 = st.tabs(["🗺️ Geographic Performance", "👥 Customer Loyalty & Retention"])
    
    with tab1:
        st.subheader("Regional Revenue Distribution")
        
        # Calculate UK vs International
        uk_row = country_df[country_df["Country"] == "United Kingdom"]
        intl_rows = country_df[country_df["Country"] != "United Kingdom"].copy()
        
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
            
        st.divider()
        col_chart, col_intl = st.columns([1.2, 0.8])
        
        with col_chart:
            top_countries = country_df.head(10).copy()
            top_countries["ScaledRevenue"] = top_countries["TotalRevenue"] * rate
            fig_country = px.bar(
                top_countries,
                x="ScaledRevenue",
                y="Country",
                orientation="h",
                text="ScaledRevenue",
                color="ScaledRevenue",
                color_continuous_scale="Blues",
                title=f"Top 10 Countries by Revenue ({symbol})",
                labels={"ScaledRevenue": f"Revenue ({symbol})", "Country": ""}
            )
            fig_country.update_traces(texttemplate=f"{symbol}%{{x:,.0f}}", textposition="inside")
            fig_country.update_layout(
                yaxis=dict(autorange="reversed", automargin=True, title=""),
                xaxis=dict(title=f"Revenue ({symbol})", tickprefix=symbol, automargin=True),
                coloraxis_showscale=False,
                margin=dict(l=20, r=30, t=60, b=40)
            )
            apply_chart_theme(fig_country)
            st.plotly_chart(fig_country, width="stretch")
            
        with col_intl:
            st.markdown(f"##### 🌐 Top International Markets ({symbol})")
            top_intl = intl_rows.head(8).copy()
            top_intl["ScaledRevenue"] = top_intl["TotalRevenue"] * rate
            top_intl["ScaledCountryAOV"] = top_intl["CountryAOV"] * rate
            st.dataframe(
                top_intl[["Country", "ScaledRevenue", "OrderCount", "ScaledCountryAOV"]].style.format({
                    "ScaledRevenue": f"{symbol}{{:,.2f}}",
                    "OrderCount": "{:,}",
                    "ScaledCountryAOV": f"{symbol}{{:,.2f}}"
                }),
                width="stretch"
            )
            
        st.divider()
        st.subheader("All Countries Summary Table")
        all_country_display = country_df.copy()
        all_country_display["ScaledRevenue"] = all_country_display["TotalRevenue"] * rate
        all_country_display["ScaledCountryAOV"] = all_country_display["CountryAOV"] * rate
        st.dataframe(
            all_country_display[["Country", "ScaledRevenue", "OrderCount", "CustomerCount", "UnitsSold", "ScaledCountryAOV"]].style.format({
                "ScaledRevenue": f"{symbol}{{:,.2f}}",
                "OrderCount": "{:,}",
                "CustomerCount": "{:,}",
                "UnitsSold": "{:,}",
                "ScaledCountryAOV": f"{symbol}{{:,.2f}}"
            }),
            width="stretch"
        )
        
    with tab2:
        st.subheader("Customer Loyalty & Lifetime Dynamics")
        
        if repeat_stats:
            lc1, lc2, lc3, lc4 = st.columns(4)
            with lc1:
                render_kpi_card("Registered Buyers", format_number(repeat_stats.get("total_registered_customers")))
            with lc2:
                render_kpi_card("Repeat Customers", format_number(repeat_stats.get("repeat_customers_count")), subtitle=f"{repeat_stats.get('repeat_customer_percent')}% of identified base")
            with lc3:
                render_kpi_card("Repeat Sales Share", f"{repeat_stats.get('repeat_revenue_share_percent', 0.0):.1f}%", subtitle="Dominant revenue stream")
            with lc4:
                render_kpi_card("Repeat Order Share", f"{repeat_stats.get('repeat_orders_share_percent', 0.0):.1f}%", subtitle="Of registered orders")
                
            st.divider()
            
            # Loyalty Distribution Donut
            r_cust = repeat_stats.get("repeat_customers_count", 0)
            s_cust = repeat_stats.get("single_order_customers_count", 0)
            
            donut_df = pd.DataFrame({
                "Segment": ["Repeat Customers (>= 2 Orders)", "Single-Order Buyers (1 Order)"],
                "Count": [r_cust, s_cust]
            })
            
            c_donut, c_desc = st.columns([1, 1])
            with c_donut:
                fig_loyalty = px.pie(
                    donut_df,
                    names="Segment",
                    values="Count",
                    hole=0.45,
                    color_discrete_sequence=[CHART_COLORS["primary"], CHART_COLORS["neutral_dark"]],
                    title="Identified Customer Base Composition"
                )
                fig_loyalty.update_traces(textinfo="percent+label")
                apply_chart_theme(fig_loyalty)
                st.plotly_chart(fig_loyalty, width="stretch")
                
            with c_desc:
                with st.container(border=True):
                    st.markdown("##### 💡 Retention Insights")
                    st.write(
                        "1. **High Repeat Dependency:** Repeat customers represent nearly **70%** of total registered revenue, "
                        "confirming high brand affinity and lifetime customer value (LTV).\n\n"
                        "2. **Guest Order Impact:** Transactions without Customer IDs represent unregistered / guest checkouts. "
                        "In academic rigor, guest purchases are never conflated with identifiable customer retention cohorts.\n\n"
                        "3. **Acquisition Target:** Turning even 10% of the single-order cohort into repeat buyers significantly "
                        "accelerates overall revenue throughput without increasing customer acquisition costs (CAC)."
                    )
        else:
            st.info("Repeat customer analysis statistics not available.")


if __name__ == "__main__":
    render_page()
