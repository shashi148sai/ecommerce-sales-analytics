"""
SalesPulse Analytics - Sales Trends Page
Visualizes temporal dynamics across monthly, daily, day-of-week, and hourly granularities,
including Month-over-Month (MoM) revenue growth rates.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.utils import (
    load_monthly_trends,
    load_daily_trends,
    load_temporal_patterns,
    format_currency,
    format_number,
    format_percent,
    apply_chart_theme,
    CHART_COLORS
)


def render_page():
    st.title("📅 Temporal Sales Trends & Growth")
    st.caption("Examine revenue cycles, order seasonality, and growth rates across macro (monthly) and micro (hourly) timelines.")
    
    monthly_df = load_monthly_trends()
    daily_df = load_daily_trends()
    temporal = load_temporal_patterns()
    
    if monthly_df.empty or daily_df.empty:
        st.warning("⚠️ Sales trend data is unavailable. Please run the processing pipeline first.")
        return
        
    tab1, tab2, tab3 = st.tabs(["📊 Monthly Progression & Growth", "📆 Daily Fluctuations", "⏰ Seasonality Patterns"])
    
    with tab1:
        st.subheader("Monthly Revenue & Growth Rates")
        
        # Monthly Growth Chart
        fig_mom = go.Figure()
        
        fig_mom.add_trace(go.Bar(
            x=monthly_df["YearMonth"],
            y=monthly_df["MonthlyRevenue"],
            name="Revenue (£)",
            marker_color=CHART_COLORS["primary"],
            hovertemplate="<b>%{x}</b><br>Revenue: £%{y:,.2f}<extra></extra>"
        ))
        
        fig_mom.add_trace(go.Scatter(
            x=monthly_df["YearMonth"],
            y=monthly_df["RevenueGrowthPercent"],
            name="MoM Growth (%)",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color=CHART_COLORS["danger"], width=2.5, dash="dot"),
            marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>MoM Growth: %{y:.2f}%<extra></extra>"
        ))
        
        fig_mom.update_layout(
            yaxis=dict(title="Revenue (£)", tickprefix="£", automargin=True, showgrid=True, gridcolor="#F1F5F9"),
            yaxis2=dict(title="MoM Growth Rate (%)", overlaying="y", side="right", ticksuffix="%", automargin=True, showgrid=False),
            xaxis=dict(title="", tickangle=-25, automargin=True),
            legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1.0),
            margin=dict(l=60, r=60, t=60, b=40)
        )
        apply_chart_theme(fig_mom, title="Monthly Revenue (£) & Month-over-Month Growth (%)")
        st.plotly_chart(fig_mom, width="stretch")
        
        # Table of monthly breakdown
        st.dataframe(
            monthly_df.style.format({
                "MonthlyRevenue": "£{:,.2f}",
                "MonthlyOrders": "{:,}",
                "MonthlyUnits": "{:,}",
                "MonthlyAOV": "£{:.2f}",
                "PreviousMonthRevenue": "£{:,.2f}",
                "RevenueGrowthPercent": "{:+.2f}%"
            }),
            width="stretch"
        )
        
    with tab2:
        st.subheader("Daily Sales Progression")
        daily_df["Date"] = pd.to_datetime(daily_df["Date"])
        
        # Date Filter
        min_date = daily_df["Date"].min().to_pydatetime()
        max_date = daily_df["Date"].max().to_pydatetime()
        
        with st.container(border=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
            with col_f2:
                end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
            
        filtered_daily = daily_df[
            (daily_df["Date"] >= pd.to_datetime(start_date)) &
            (daily_df["Date"] <= pd.to_datetime(end_date))
        ]
        
        fig_daily = px.line(
            filtered_daily,
            x="Date",
            y="DailyRevenue",
            title=f"Daily Revenue from {start_date} to {end_date}",
            labels={"DailyRevenue": "Daily Revenue (£)", "Date": "Date"}
        )
        fig_daily.update_traces(line_color=CHART_COLORS["secondary"], line_width=1.8)
        fig_daily.update_layout(
            yaxis=dict(tickprefix="£", automargin=True),
            xaxis=dict(automargin=True),
            margin=dict(l=50, r=30, t=60, b=40)
        )
        apply_chart_theme(fig_daily)
        st.plotly_chart(fig_daily, width="stretch")
        
    with tab3:
        st.subheader("Weekly & Hourly Cycles")
        dow_df = temporal.get("day_of_week", pd.DataFrame())
        hod_df = temporal.get("hour_of_day", pd.DataFrame())
        
        c_left, c_right = st.columns(2)
        
        with c_left:
            if not dow_df.empty:
                day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                dow_df["DayOrder"] = dow_df["DayOfWeek"].apply(lambda d: day_order.index(d) if d in day_order else 99)
                dow_df = dow_df.sort_values("DayOrder")
                
                fig_dow = px.bar(
                    dow_df,
                    x="DayOfWeek",
                    y="Revenue",
                    color="Revenue",
                    color_continuous_scale="Purples",
                    title="Revenue by Day of Week (£)",
                    labels={"Revenue": "Revenue (£)", "DayOfWeek": "Day"}
                )
                fig_dow.update_layout(
                    coloraxis_showscale=False,
                    yaxis=dict(tickprefix="£", automargin=True),
                    xaxis=dict(automargin=True),
                    margin=dict(l=50, r=30, t=60, b=40)
                )
                apply_chart_theme(fig_dow)
                st.plotly_chart(fig_dow, width="stretch")
                
        with c_right:
            if not hod_df.empty:
                fig_hod = px.line(
                    hod_df,
                    x="HourOfDay",
                    y="Revenue",
                    markers=True,
                    title="Revenue by Hour of Day (24-Hour Cycle)",
                    labels={"Revenue": "Revenue (£)", "HourOfDay": "Hour of Day"}
                )
                fig_hod.update_traces(line_color=CHART_COLORS["primary"], line_width=2.5)
                fig_hod.update_layout(
                    yaxis=dict(tickprefix="£", automargin=True),
                    xaxis=dict(automargin=True),
                    margin=dict(l=50, r=30, t=60, b=40)
                )
                apply_chart_theme(fig_hod)
                st.plotly_chart(fig_hod, width="stretch")


if __name__ == "__main__":
    render_page()
