"""
SalesPulse Analytics - Sales Trends Page
Visualizes temporal dynamics across monthly, daily, day-of-week, and hourly granularities,
including Month-over-Month (MoM) revenue growth rates, Indian Financial Year (FY) quarters,
and predictive demand forecasting with hold-out validation.
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
    render_kpi_card,
    apply_chart_theme,
    CHART_COLORS
)
from src.analytics.advanced import perform_sales_forecasting


def render_page():
    st.title("📅 Temporal Sales Trends & Forecasting")
    st.caption("Examine revenue cycles, order seasonality, growth rates across macro/micro timelines, and predictive forecasts.")
    
    monthly_df = load_monthly_trends()
    daily_df = load_daily_trends()
    temporal = load_temporal_patterns()
    symbol, code, rate = get_active_currency_config()
    
    # --------------------------------------------------------------------------
    # Empty State Handling
    # --------------------------------------------------------------------------
    if monthly_df.empty and daily_df.empty:
        with st.container(border=True):
            st.markdown("### ℹ️ Temporal Trends Unavailable")
            st.markdown(
                "Sales trends require a usable transaction date or timestamp column. "
                "No temporal summary is currently generated for the active session."
            )
            if st.button("🚀 Upload or Select Dataset", type="primary"):
                st.session_state["nav_selection"] = "📥 Upload & Manage Data"
                st.rerun()
        return
        
    # Standardize canonical schema on daily_df if present
    if not daily_df.empty:
        if "Date" not in daily_df.columns:
            for alt in ["InvoiceDate", "InvoiceDateOnly", "order_date", "date", "OrderDate", "transaction_date"]:
                if alt in daily_df.columns:
                    daily_df["Date"] = daily_df[alt]
                    break
        if "DailyRevenue" not in daily_df.columns:
            for alt in ["Revenue", "TotalRevenue", "LineTotal", "SalesAmount", "Sales", "NetRevenue", "Amount"]:
                if alt in daily_df.columns:
                    daily_df["DailyRevenue"] = daily_df[alt]
                    break
        
    # Sample Data Banner Disclosure
    if st.session_state.get("active_dataset_type") == "sample":
        st.info("🧪 **Sample Dataset Active:** Showing temporal trends and seasonal patterns for the sample dataset.")
        
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Monthly Progression & Growth", "📆 Daily Fluctuations", "⏰ Seasonality Patterns", "🔮 Demand Forecasting"])
    
    # --------------------------------------------------------------------------
    # Tab 1: Monthly Progression & Growth
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Monthly Revenue & Growth Rates")
        st.caption("Displays month-over-month (MoM) financial expansion and Indian Financial Year quarter comparisons.")
        
        # Indian Financial Year Filter
        if "YearMonth" in monthly_df.columns:
            monthly_df["Date"] = pd.to_datetime(monthly_df["YearMonth"] + "-01")
            monthly_df["Indian_FY"] = monthly_df["Date"].apply(get_indian_financial_year)
            monthly_df["Indian_Quarter"] = monthly_df["Date"].apply(get_indian_fy_quarter)
            available_fys = ["All Financial Years"] + sorted(list(monthly_df["Indian_FY"].unique()))
        else:
            available_fys = ["All Financial Years"]
            
        with st.container(border=True):
            col_fy1, col_fy2 = st.columns(2)
            with col_fy1:
                selected_fy = st.selectbox("📅 Indian Financial Year (1 Apr – 31 Mar):", available_fys, index=0)
            with col_fy2:
                fy_df = monthly_df if selected_fy == "All Financial Years" else monthly_df[monthly_df["Indian_FY"] == selected_fy]
                avail_qtrs = ["All Quarters"] + sorted(list(fy_df["Indian_Quarter"].unique())) if not fy_df.empty else ["All Quarters"]
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
        st.plotly_chart(fig_mom, use_container_width=True)
        
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
            use_container_width=True
        )
        
    # --------------------------------------------------------------------------
    # Tab 2: Daily Fluctuations
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Daily Sales Progression")
        st.caption("Visualizes day-by-day sales swings with interactive Indian date range selection.")
        
        if daily_df.empty or "Date" not in daily_df.columns or "DailyRevenue" not in daily_df.columns:
            st.warning("⚠️ Daily sales timeline is missing required 'Date' or 'DailyRevenue' fields.")
        else:
            clean_daily = daily_df.copy()
            clean_daily["ParsedDate"] = pd.to_datetime(clean_daily["Date"], errors="coerce")
            clean_daily["CleanRevenue"] = pd.to_numeric(clean_daily["DailyRevenue"], errors="coerce")
            clean_daily = clean_daily.dropna(subset=["ParsedDate", "CleanRevenue"])
            
            if clean_daily.empty:
                st.warning("⚠️ No valid transaction dates or revenue amounts found for daily breakdown.")
            else:
                clean_daily["ScaledDailyRevenue"] = clean_daily["CleanRevenue"] * rate
                min_date = clean_daily["ParsedDate"].min().to_pydatetime()
                max_date = clean_daily["ParsedDate"].max().to_pydatetime()
                
                with st.container(border=True):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        start_date = st.date_input("Start Date (DD-MM-YYYY)", min_date, min_value=min_date, max_value=max_date)
                    with col_f2:
                        end_date = st.date_input("End Date (DD-MM-YYYY)", max_date, min_value=min_date, max_value=max_date)
                    
                filtered_daily = clean_daily[
                    (clean_daily["ParsedDate"] >= pd.to_datetime(start_date)) &
                    (clean_daily["ParsedDate"] <= pd.to_datetime(end_date))
                ].copy()
                
                filtered_daily["DisplayDate"] = filtered_daily["ParsedDate"].apply(format_date_indian)
                
                # Interactive range summary cards
                if not filtered_daily.empty:
                    range_rev = float(filtered_daily["ScaledDailyRevenue"].sum())
                    range_days = len(filtered_daily)
                    range_avg = range_rev / range_days if range_days > 0 else 0.0
                    peak_idx = filtered_daily["ScaledDailyRevenue"].idxmax()
                    peak_row = filtered_daily.loc[peak_idx]
                    
                    rk1, rk2, rk3, rk4 = st.columns(4)
                    with rk1:
                        st.metric("Period Revenue", format_currency(range_rev, override_rate=1.0, compact=True))
                    with rk2:
                        st.metric("Daily Average", format_currency(range_avg, override_rate=1.0))
                    with rk3:
                        st.metric("Peak Day Sales", format_currency(float(peak_row['ScaledDailyRevenue']), override_rate=1.0, compact=True), delta=format_date_indian(peak_row['ParsedDate']))
                    with rk4:
                        st.metric("Observed Days", f"{range_days} Days")
                        
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
                st.plotly_chart(fig_daily, use_container_width=True)

    # --------------------------------------------------------------------------
    # Tab 3: Seasonality Patterns
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("Weekly & Hourly Cycles")
        st.caption("Reveals purchasing behavior across days of the week and 24-hour diurnal timelines.")
        
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
                st.plotly_chart(fig_dow, use_container_width=True)
                
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
                st.plotly_chart(fig_hod, use_container_width=True)

    # --------------------------------------------------------------------------
    # Tab 4: Demand Forecasting
    # --------------------------------------------------------------------------
    with tab4:
        st.subheader("Predictive Demand Forecasting (with Hold-Out Validation)")
        st.caption(
            "Predicts future daily sales volume using lagged temporal regression and weekly cycles. "
            "Model accuracy is validated against an unseen chronological hold-out historical test set."
        )
        
        with st.container(border=True):
            col_f1, col_f2, col_f3 = st.columns([1.4, 1.4, 1.6])
            with col_f1:
                forecast_horizon = st.slider("Forecast Horizon (Days)", min_value=7, max_value=60, value=30, step=7, key="fc_slider")
            with col_f2:
                test_split = st.select_slider("Historical Hold-out Proportion", options=[0.15, 0.20, 0.25], value=0.20, key="fc_split")
            with col_f3:
                scenario = st.selectbox("Interactive Scenario Simulation", ["Base Baseline (1.0x)", "Optimistic Growth (+15%)", "Conservative (-15%)"], index=0, key="fc_scenario")
                
        forecast_results = None
        try:
            with st.spinner("Training time-series forecasting model..."):
                forecast_results = perform_sales_forecasting(
                    daily_sales_df=daily_df,
                    forecast_days=forecast_horizon,
                    test_ratio=test_split
                )
        except Exception as e:
            st.warning(f"⚠️ **Demand Forecasting Unavailable:** {str(e)}")
            st.info(
                "💡 **How to resolve:** Forecasting requires at least 14 days of historical transactions "
                "with valid dates and revenue values. Explore demand forecasting instantly by loading the sample dataset on the Home or Upload page."
            )
            
        if forecast_results is not None:
            metrics = forecast_results["evaluation_metrics"]
            scenario_mult = 1.15 if "Optimistic" in scenario else (0.85 if "Conservative" in scenario else 1.0)
            
            # Display validation metrics
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                render_kpi_card("Mean Absolute Error", format_currency(metrics["MAE"]), subtitle="Hold-out historical test")
            with mc2:
                render_kpi_card("Root Mean Sq Error", format_currency(metrics["RMSE"]), subtitle="Hold-out test penalty")
            with mc3:
                render_kpi_card("MAPE Accuracy", f"{metrics['MAPE_percent']:.1f}%", subtitle="Mean absolute % error")
            with mc4:
                render_kpi_card("Hold-out Test Window", f"{metrics['holdout_test_days']} Days", subtitle=f"Scenario: {scenario.split()[0]}")
                
            st.divider()
            
            # Plot Historical vs Hold-out Actuals vs Forecast
            history_df = pd.DataFrame(forecast_results.get("history", []))
            eval_df = pd.DataFrame(forecast_results.get("holdout_evaluation", []))
            future_df = pd.DataFrame(forecast_results.get("forecast", []))
            
            # Explicit schema resilience: Guarantee DailyRevenue and ActualRevenue on both frames
            if not history_df.empty:
                if "DailyRevenue" not in history_df.columns and "ActualRevenue" in history_df.columns:
                    history_df["DailyRevenue"] = history_df["ActualRevenue"]
                if "ActualRevenue" not in history_df.columns and "DailyRevenue" in history_df.columns:
                    history_df["ActualRevenue"] = history_df["DailyRevenue"]
                history_df["ScaledRevenue"] = history_df["DailyRevenue"] * rate
                
            if not eval_df.empty:
                if "DailyRevenue" not in eval_df.columns and "ActualRevenue" in eval_df.columns:
                    eval_df["DailyRevenue"] = eval_df["ActualRevenue"]
                if "ActualRevenue" not in eval_df.columns and "DailyRevenue" in eval_df.columns:
                    eval_df["ActualRevenue"] = eval_df["DailyRevenue"]
                eval_df["ScaledActual"] = eval_df["DailyRevenue"] * rate
                eval_df["ScaledPredicted"] = eval_df["PredictedRevenue"] * rate
                
            if not future_df.empty:
                if "ForecastedRevenue" not in future_df.columns and "PredictedRevenue" in future_df.columns:
                    future_df["ForecastedRevenue"] = future_df["PredictedRevenue"]
                future_df["ScaledForecast"] = future_df["ForecastedRevenue"] * rate * scenario_mult
                future_df["ScaledUpper"] = future_df["UpperBound"] * rate * scenario_mult
                future_df["ScaledLower"] = future_df["LowerBound"] * rate * scenario_mult
                
            fig = go.Figure()
            
            # Historical actuals
            if not history_df.empty:
                fig.add_trace(go.Scatter(
                    x=history_df["Date"],
                    y=history_df["ScaledRevenue"],
                    mode="lines",
                    name=f"Actual Historical Revenue ({symbol})",
                    line=dict(color=CHART_COLORS["primary"], width=1.8),
                    hovertemplate=f"<b>Actual:</b> %{{x}}<br>{symbol}%{{y:,.2f}}<extra></extra>"
                ))
            
            # Test set predictions
            if not eval_df.empty:
                fig.add_trace(go.Scatter(
                    x=eval_df["Date"],
                    y=eval_df["ScaledPredicted"],
                    mode="lines",
                    name="Hold-Out Model Fit",
                    line=dict(color=CHART_COLORS["accent"], width=2, dash="dash"),
                    hovertemplate=f"<b>Validation Fit:</b> %{{x}}<br>{symbol}%{{y:,.2f}}<extra></extra>"
                ))
                
                # Hold-out actuals for clear validation comparison
                fig.add_trace(go.Scatter(
                    x=eval_df["Date"],
                    y=eval_df["ScaledActual"],
                    mode="markers",
                    name="Hold-Out Actuals (Ground Truth)",
                    marker=dict(color=CHART_COLORS["danger"], size=5, symbol="circle-open"),
                    hovertemplate=f"<b>Hold-Out Actual:</b> %{{x}}<br>{symbol}%{{y:,.2f}}<extra></extra>"
                ))
            
            # Future projections
            if not future_df.empty:
                fig.add_trace(go.Scatter(
                    x=future_df["Date"],
                    y=future_df["ScaledForecast"],
                    mode="lines+markers",
                    name=f"Projected Next {forecast_horizon} Days",
                    line=dict(color=CHART_COLORS["success"], width=2.5),
                    marker=dict(size=5),
                    hovertemplate=f"<b>Forecast:</b> %{{x}}<br>{symbol}%{{y:,.2f}}<extra></extra>"
                ))
                
                # Confidence interval band
                fig.add_trace(go.Scatter(
                    x=future_df["Date"].tolist() + future_df["Date"].tolist()[::-1],
                    y=future_df["ScaledUpper"].tolist() + future_df["ScaledLower"].tolist()[::-1],
                    fill="toself",
                    fillcolor="rgba(16, 185, 129, 0.15)",
                    line=dict(color="rgba(255,255,255,0)"),
                    hoverinfo="skip",
                    showlegend=True,
                    name="95% Confidence Interval"
                ))
            
            fig.update_layout(
                yaxis=dict(title=f"Daily Revenue ({symbol})", tickprefix=symbol, automargin=True, showgrid=True, gridcolor="#F1F5F9"),
                xaxis=dict(title="Date", automargin=True),
                legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1.0),
                margin=dict(l=60, r=40, t=60, b=40)
            )
            apply_chart_theme(fig, title=f"Revenue Actuals, Hold-Out Validation, and {forecast_horizon}-Day Projection ({symbol})")
            st.plotly_chart(fig, use_container_width=True)
            
            # Download forecast CSV
            if not future_df.empty:
                csv_forecast = future_df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Future Projections (CSV)", csv_forecast, "revenue_forecast.csv", "text/csv")


if __name__ == "__main__":
    render_page()
