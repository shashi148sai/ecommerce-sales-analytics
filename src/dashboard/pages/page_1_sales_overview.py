"""
SalesPulse Analytics - Sales Overview Page
Displays top-level commercial KPIs, revenue progression, top product revenue shares,
Indian Financial Year (FY) filtering, and commercial summaries.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.utils import (
    load_kpis,
    load_monthly_trends,
    load_top_products_revenue,
    load_repeat_customers,
    format_currency,
    format_number,
    format_percent,
    render_kpi_card,
    apply_chart_theme,
    get_active_currency_config,
    get_indian_financial_year,
    get_indian_fy_quarter,
    CHART_COLORS
)


def render_page():
    st.title("💼 Commercial Sales Overview")
    st.caption("High-level executive overview of e-commerce revenue, transaction volume, and operational metrics.")
    
    kpis = load_kpis()
    monthly_df = load_monthly_trends()
    top_rev_df = load_top_products_revenue()
    repeat_stats = load_repeat_customers()
    
    if not kpis:
        st.warning("⚠️ No analytics results found. Please run the pipeline from the **Data Management and Quality** page.")
        return
        
    symbol, code, rate = get_active_currency_config()
    
    # --------------------------------------------------------------------------
    # Timeline & Indian Financial Year (FY) Filter
    # --------------------------------------------------------------------------
    if not monthly_df.empty:
        monthly_df["Date"] = pd.to_datetime(monthly_df["YearMonth"] + "-01")
        monthly_df["Indian_FY"] = monthly_df["Date"].apply(get_indian_financial_year)
        monthly_df["Indian_Quarter"] = monthly_df["Date"].apply(get_indian_fy_quarter)
        available_fys = ["All Financial Years"] + sorted(list(monthly_df["Indian_FY"].unique()))
    else:
        available_fys = ["All Financial Years"]
        
    with st.container(border=True):
        f_col1, f_col2, f_col3 = st.columns([1, 1, 1.5])
        with f_col1:
            selected_fy = st.selectbox("📅 Indian Financial Year (1 Apr – 31 Mar):", available_fys, index=0)
        with f_col2:
            fy_filtered = monthly_df if selected_fy == "All Financial Years" else monthly_df[monthly_df["Indian_FY"] == selected_fy]
            avail_qtrs = ["All Quarters"] + sorted(list(fy_filtered["Indian_Quarter"].unique())) if not fy_filtered.empty else ["All Quarters"]
            selected_qtr = st.selectbox("📆 Financial Quarter:", avail_qtrs, index=0)
        with f_col3:
            st.caption(f"**Presentation Currency:** `{code} ({symbol})` | **Multiplier:** `{rate:.2f}x`")
            if code == "INR":
                st.caption(f"*(Converted dynamically from canonical GBP at reference rate 1 GBP = ₹{rate:.2f})*")
            else:
                st.caption("*(Canonical dataset currency: British Pounds £)*")
                
    filtered_monthly = fy_filtered if selected_qtr == "All Quarters" else fy_filtered[fy_filtered["Indian_Quarter"] == selected_qtr]

    # --------------------------------------------------------------------------
    # Executive KPI Cards (Row 1) - Streamlit Native Bordered Containers
    # --------------------------------------------------------------------------
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        render_kpi_card(
            title="Gross Revenue",
            value=format_currency(kpis.get("gross_revenue"), compact=True),
            subtitle=f"Exact: {format_currency(kpis.get('gross_revenue'))}"
        )
    with c2:
        render_kpi_card(
            title="Return Adjustments",
            value=format_currency(kpis.get("return_adjustments"), compact=True),
            subtitle=f"{format_percent(kpis.get('return_rate_percent'))} of gross sales",
            delta=f"-{format_percent(kpis.get('return_rate_percent'))}",
            delta_positive=False
        )
    with c3:
        render_kpi_card(
            title="Net Revenue",
            value=format_currency(kpis.get("net_revenue"), compact=True),
            subtitle="Gross minus refunds/returns"
        )
    with c4:
        render_kpi_card(
            title="Distinct Orders",
            value=format_number(kpis.get("total_orders")),
            subtitle=f"Units: {format_number(kpis.get('total_units_sold'))}"
        )
    with c5:
        render_kpi_card(
            title="Avg Order Value",
            value=format_currency(kpis.get("average_order_value")),
            subtitle="Gross sales / total orders"
        )
        
    st.divider()
    
    # --------------------------------------------------------------------------
    # Main Trend Chart & Top Products
    # --------------------------------------------------------------------------
    col_left, col_right = st.columns([1.1, 0.9])
    
    with col_left:
        st.subheader("📈 Monthly Revenue Progression")
        if not filtered_monthly.empty:
            fig_trend = go.Figure()
            
            scaled_revenue = filtered_monthly["MonthlyRevenue"] * rate
            
            # Revenue Bar
            fig_trend.add_trace(go.Bar(
                x=filtered_monthly["YearMonth"],
                y=scaled_revenue,
                name=f"Revenue ({symbol})",
                marker_color=CHART_COLORS["primary"],
                hovertemplate=f"<b>%{{x}}</b><br>Revenue: {symbol}%{{y:,.2f}}<extra></extra>"
            ))
            
            # Order Count Line
            fig_trend.add_trace(go.Scatter(
                x=filtered_monthly["YearMonth"],
                y=filtered_monthly["MonthlyOrders"],
                name="Order Count",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color=CHART_COLORS["accent"], width=3),
                marker=dict(size=6),
                hovertemplate="<b>%{x}</b><br>Orders: %{y:,}<extra></extra>"
            ))
            
            fig_trend.update_layout(
                yaxis=dict(title=f"Revenue ({symbol})", tickprefix=symbol, automargin=True, showgrid=True, gridcolor="#F1F5F9"),
                yaxis2=dict(title="Order Count", overlaying="y", side="right", automargin=True, showgrid=False),
                xaxis=dict(title="", tickangle=-30, automargin=True),
                legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1.0),
                margin=dict(l=60, r=60, t=60, b=45)
            )
            apply_chart_theme(fig_trend)
            st.plotly_chart(fig_trend, width="stretch")
        else:
            st.info("No monthly trend data matches the selected financial year/quarter filter.")
            
    with col_right:
        st.subheader("🏆 Top 5 Revenue Products")
        if not top_rev_df.empty:
            top5 = top_rev_df.head(5).copy()
            top5["ScaledRevenue"] = top5["TotalRevenue"] * rate
            # Truncate description cleanly for legible axes
            top5["ShortDesc"] = top5["Description"].apply(
                lambda x: str(x)[:24] + "..." if len(str(x)) > 26 else str(x)
            )
            
            fig_top = px.bar(
                top5,
                x="ScaledRevenue",
                y="ShortDesc",
                orientation="h",
                text="ScaledRevenue",
                color="ScaledRevenue",
                color_continuous_scale="Blues",
                labels={"ScaledRevenue": f"Revenue ({symbol})", "ShortDesc": ""},
                hover_data={"Description": True, "UnitsSold": True, "ScaledRevenue": ":,.2f"}
            )
            fig_top.update_traces(
                texttemplate=f"{symbol}%{{x:,.0f}}",
                textposition="inside"
            )
            fig_top.update_layout(
                yaxis=dict(autorange="reversed", automargin=True, title=""),
                xaxis=dict(title=f"Revenue ({symbol})", tickprefix=symbol, automargin=True),
                coloraxis_showscale=False,
                margin=dict(l=10, r=30, t=60, b=45)
            )
            apply_chart_theme(fig_top)
            st.plotly_chart(fig_top, width="stretch")
        else:
            st.info("Top products data not available.")
            
    # --------------------------------------------------------------------------
    # Operational Comparison Highlights
    # --------------------------------------------------------------------------
    st.divider()
    st.subheader("⚖️ Operational Distribution and Comparisons")
    
    sc1, sc2, sc3 = st.columns(3)
    
    with sc1:
        with st.container(border=True):
            st.markdown("##### 📦 Catalog & Reach")
            st.write(f"- **Distinct Products Sold:** {format_number(kpis.get('distinct_products'))}")
            st.write(f"- **Operating Countries:** {format_number(kpis.get('operating_countries'))}")
            st.write(f"- **Total Return Orders:** {format_number(kpis.get('return_orders_count'))}")
            st.write(f"- **Return Units Volume:** {format_number(kpis.get('return_units_volume'))}")
        
    with sc2:
        with st.container(border=True):
            st.markdown("##### 👥 Customer Checkout Mix")
            registered_count = repeat_stats.get("total_registered_customers", 0)
            guest_rev = repeat_stats.get("guest_revenue", 0.0)
            repeat_rev_share = repeat_stats.get("repeat_revenue_share_percent", 0.0)
            
            st.write(f"- **Active Registered Buyers:** {format_number(registered_count)}")
            st.write(f"- **Repeat Customer Revenue Share:** {repeat_rev_share:.1f}%")
            st.write(f"- **Guest (Unregistered) Orders:** {format_number(repeat_stats.get('guest_orders_count', 0))}")
            st.write(f"- **Guest Checkout Revenue:** {format_currency(guest_rev)}")
        
    with sc3:
        with st.container(border=True):
            st.markdown("##### 🛡️ Governance & Policy")
            st.write(f"- **Active Currency:** {code} ({symbol})")
            st.write("- **Canonical Base:** British Pounds (£) - UCI Online Retail")
            st.write("- **Cost Profile:** ₹0 Out-of-Pocket Local Execution")
            st.write("- **Profit Claim:** *None (COGS absent in dataset)*")
            
            # Download KPI summary CSV
            kpi_df = pd.DataFrame([kpis])
            csv_bytes = kpi_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Executive KPI Summary (CSV)",
                data=csv_bytes,
                file_name="salespulse_executive_kpis.csv",
                mime="text/csv",
                width="stretch"
            )


if __name__ == "__main__":
    render_page()
