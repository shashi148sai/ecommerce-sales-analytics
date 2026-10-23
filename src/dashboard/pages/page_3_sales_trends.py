"""
SalesPulse Analytics - Sales Trends Page
Visualizes temporal dynamics across monthly, daily, day-of-week, and hourly granularities,
including Month-over-Month (MoM) revenue growth rates and Indian Financial Year (FY) quarters.
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
    format_date_indian,
    get_active_currency_config,
    get_indian_financial_year,
    get_indian_fy_quarter,
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
        
    symbol, code, rate = get_active_currency_config()
    
    tab1, tab2, tab3 = st.tabs(["📊 Monthly Progression & Growth", "📆 Daily Fluctuations", "⏰ Seasonality Patterns"])
    
    # --------------------------------------------------------------------------
    # Tab 1: Monthly Progression & Growth
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Monthly Revenue & Growth Rates")
        
        # Indian Financial Year Filter
        monthly_df["Date"] = pd.to_datetime(monthly_df["YearMonth"] + "-01")
        monthly_df["Indian_FY"] = monthly_df["Date"].apply(get_indian_financial_year)
        monthly_df["Indian_Quarter"] = monthly_df["Date"].apply(get_indian_fy_quarter)
        available_fys = ["All Financial Years"] + sorted(list(monthly_df["Indian_FY"].unique()))
        
        with st.container(border=True):
            col_fy1, col_fy2 = st.columns(2)
            with col_fy1:
                selected_fy = st.selectbox("📅 Indian Financial Year (1 Apr – 31 Mar):", available_fys, index=0)
            with col_fy2:
                fy_df = monthly_df if selected_fy == "All Financial Years" else monthly_df[monthly_df["Indian_FY"] == selected_fy]
                avail_qtrs = ["All Quarters"] + sorted(list(fy_df["Indian_Quarter"].unique()))
                selected_qtr = st.selectbox("📆 Financial Quarter:", avail_qtrs, index=0)
                
        disp_monthly = fy_df if selected_qtr == "All Quarters" else fy_df[fy_df["Indian_Quarter"] == selected_qtr]
        
        # Scale by active currency rate
        scaled_disp = disp_monthly.copy()
        scaled_disp["ScaledMonthlyRevenue"] = scaled_disp["MonthlyRevenue"] * rate
        scaled_disp["ScaledPreviousRevenue"] = scaled_disp["PreviousMonthRevenue"] * rate
        scaled_disp["ScaledMonthlyAOV"] = scaled_disp["MonthlyAOV"] * rate
        
        # Monthly Growth Chart
        fig_mom = go.Figure()
        
        fig_mom.add_trace(go.Bar(
            x=scaled_disp["YearMonth"],
            y=scaled_disp["ScaledMonthlyRevenue"],
            name=f"Revenue ({symbol})",
            marker_color=CHART_COLORS["primary"],
            hovertemplate=f"<b>%{{x}}</b><br>Revenue: {symbol}%{{y:,.2f}}<extra></extra>"
        ))
        
        fig_mom.add_trace(go.Scatter(
            x=scaled_disp["YearMonth"],
            y=scaled_disp["RevenueGrowthPercent"],
            name="MoM Growth (%)",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color=CHART_COLORS["danger"], width=2.5, dash="dot"),
            marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>MoM Growth: %{y:.2f}%<extra></extra>"
        ))
        
        fig_mom.update_layout(
            yaxis=dict(title=f"Revenue ({symbol})", tickprefix=symbol, automargin=True, showgrid=True, gridcolor="#F1F5F9"),
            yaxis2=dict(title="MoM Growth Rate (%)", overlaying="y", side="right", ticksuffix="%", automargin=True, showgrid=False),
            xaxis=dict(title="", tickangle=-25, automargin=True),
            legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1.0),
            margin=dict(l=60, r=60, t=60, b=40)
        )
        apply_chart_theme(fig_mom, title=f"Monthly Revenue ({symbol}) & Month-over-Month Growth (%)")
        st.plotly_chart(fig_mom, width="stretch")
        
        # Table of monthly breakdown
        table_df = scaled_disp[[
            "YearMonth", "Indian_FY", "Indian_Quarter", "ScaledMonthlyRevenue", 
            "MonthlyOrders", "MonthlyUnits", "ScaledMonthlyAOV", 
            "ScaledPreviousRevenue", "RevenueGrowthPercent"
        ]].copy()
        
        st.dataframe(
            table_df.style.format({
                "ScaledMonthlyRevenue": f"{symbol}{{:,.2f}}",
                "MonthlyOrders": "{:,}",
                "MonthlyUnits": "{:,}",
                "ScaledMonthlyAOV": f"{symbol}{{:,.2f}}",
                "ScaledPreviousRevenue": f"{symbol}{{:,.2f}}",
                "RevenueGrowthPercent": "{:+.2f}%"
            }),
            width="stretch"
        )
        
    # --------------------------------------------------------------------------
    # Tab 2: Daily Fluctuations
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Daily Sales Progression")
        daily_df["ParsedDate"] = pd.to_datetime(daily_df["Date"])
        daily_df["ScaledDailyRevenue"] = daily_df["DailyRevenue"] * rate
        
        min_date = daily_df["ParsedDate"].min().to_pydatetime()
        max_date = daily_df["ParsedDate"].max().to_pydatetime()
        
        with st.container(border=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                start_date = st.date_input("Start Date (DD-MM-YYYY)", min_date, min_value=min_date, max_value=max_date)
            with col_f2:
                end_date = st.date_input("End Date (DD-MM-YYYY)", max_date, min_value=min_date, max_value=max_date)
            
        filtered_daily = daily_df[
            (daily_df["ParsedDate"] >= pd.to_datetime(start_date)) &
            (daily_df["ParsedDate"] <= pd.to_datetime(end_date))
        ].copy()
        
        filtered_daily["DisplayDate"] = filtered_daily["ParsedDate"].apply(format_date_indian)
        
        fig_daily = px.line(
            filtered_daily,
            x="ParsedDate",
            y="ScaledDailyRevenue",
            title=f"Daily Revenue ({symbol}) from {format_date_indian(start_date)} to {format_date_indian(end_date)}",
            labels={"ScaledDailyRevenue": f"Daily Revenue ({symbol})", "ParsedDate": "Date"}
        )
        fig_daily.update_traces(line_color=CHART_COLORS["secondary"], line_width=1.8)
        fig_daily.update_layout(
            yaxis=dict(tickprefix=symbol, automargin=True),
            xaxis=dict(automargin=True),
            margin=dict(l=50, r=30, t=60, b=40)
        )
        apply_chart_theme(fig_daily)
        st.plotly_chart(fig_daily, width="stretch")
        
    # --------------------------------------------------------------------------
    # Tab 3: Seasonality Patterns
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("Weekly & Hourly Cycles")
        dow_df = temporal.get("day_of_week", pd.DataFrame()).copy()
        hod_df = temporal.get("hour_of_day", pd.DataFrame()).copy()
        
        c_left, c_right = st.columns(2)
        
        with c_left:
            if not dow_df.empty:
                dow_df["ScaledRevenue"] = dow_df["Revenue"] * rate
                day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                dow_df["DayOrder"] = dow_df["DayOfWeek"].apply(lambda d: day_order.index(d) if d in day_order else 99)
                dow_df = dow_df.sort_values("DayOrder")
                
                fig_dow = px.bar(
                    dow_df,
                    x="DayOfWeek",
                    y="ScaledRevenue",
                    color="ScaledRevenue",
                    color_continuous_scale="Purples",
                    title=f"Revenue by Day of Week ({symbol})",
                    labels={"ScaledRevenue": f"Revenue ({symbol})", "DayOfWeek": "Day of Week"}
                )
                fig_dow.update_layout(
                    coloraxis_showscale=False,
                    yaxis=dict(tickprefix=symbol, automargin=True),
                    xaxis=dict(automargin=True),
                    margin=dict(l=50, r=30, t=60, b=40)
                )
                apply_chart_theme(fig_dow)
                st.plotly_chart(fig_dow, width="stretch")
                
        with c_right:
            if not hod_df.empty:
                hod_df["ScaledRevenue"] = hod_df["Revenue"] * rate
                fig_hod = px.line(
                    hod_df,
                    x="HourOfDay",
                    y="ScaledRevenue",
                    markers=True,
                    title=f"Revenue by Hour of Day ({symbol}) — 24-Hour Cycle",
                    labels={"ScaledRevenue": f"Revenue ({symbol})", "HourOfDay": "Hour of Day"}
                )
                fig_hod.update_traces(line_color=CHART_COLORS["primary"], line_width=2.5)
                fig_hod.update_layout(
                    yaxis=dict(tickprefix=symbol, automargin=True),
                    xaxis=dict(automargin=True),
                    margin=dict(l=50, r=30, t=60, b=40)
                )
                apply_chart_theme(fig_hod)
                st.plotly_chart(fig_hod, width="stretch")


if __name__ == "__main__":
    render_page()
