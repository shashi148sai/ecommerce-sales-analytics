"""
SalesPulse Analytics - Forecasting & Customer Segmentation Page
Interactive machine learning module providing time-series sales forecasting (with hold-out evaluation)
and RFM customer tier segmentation using K-Means clustering.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.utils import (
    load_daily_trends,
    load_cleaned_sales_sample,
    format_currency,
    format_number,
    format_percent,
    render_kpi_card,
    apply_chart_theme,
    CHART_COLORS
)
from src.analytics.advanced import perform_sales_forecasting, compute_rfm_segmentation


def render_page():
    st.title("🔮 Advanced Analytics: Forecasting & Segmentation")
    st.caption("Machine learning algorithms applied to commercial transaction logs: predictive revenue forecasting and behavioral RFM clustering.")
    
    daily_df = load_daily_trends()
    sales_df = load_cleaned_sales_sample(limit=50000)
    
    tab1, tab2 = st.tabs(["📈 Sales Demand Forecasting", "👥 RFM Customer Segmentation"])
    
    # --------------------------------------------------------------------------
    # Tab 1: Sales Demand Forecasting
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Time-Series Sales Projection with Historical Hold-Out Validation")
        st.caption(
            "Predicts future daily sales volume using lagged temporal regression and weekly cycles. "
            "Model generalizability is validated against a chronologically separated historical test set."
        )
        
        if daily_df.empty:
            st.warning("⚠️ Daily sales history is not available. Please run the pipeline first.")
            return
            
        with st.container(border=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                forecast_horizon = st.slider("Forecast Horizon (Days)", min_value=7, max_value=60, value=30, step=7)
            with col_f2:
                test_split = st.select_slider("Historical Hold-out Test Proportion", options=[0.15, 0.20, 0.25], value=0.20)
            
        with st.spinner("Training time-series forecasting model..."):
            forecast_results = perform_sales_forecasting(
                daily_sales_df=daily_df,
                forecast_days=forecast_horizon,
                test_ratio=test_split
            )
            
        metrics = forecast_results["evaluation_metrics"]
        
        # Display validation metrics
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            render_kpi_card("Mean Absolute Error", format_currency(metrics["MAE"]), subtitle="Hold-out historical test")
        with mc2:
            render_kpi_card("Root Mean Sq Error", format_currency(metrics["RMSE"]), subtitle="Hold-out test penalty")
        with mc3:
            render_kpi_card("MAPE Accuracy", f"{metrics['MAPE_percent']:.1f}%", subtitle="Mean absolute % error")
        with mc4:
            render_kpi_card("Hold-out Test Window", f"{metrics['holdout_test_days']} Days", subtitle=f"Trained on {metrics['train_days']} days")
            
        st.divider()
        
        # Plot Historical vs Hold-out Actuals vs Forecast
        history_df = pd.DataFrame(forecast_results["history"])
        eval_df = pd.DataFrame(forecast_results["holdout_evaluation"])
        future_df = pd.DataFrame(forecast_results["forecast"])
        
        fig = go.Figure()
        
        # Historical actuals
        fig.add_trace(go.Scatter(
            x=history_df["Date"],
            y=history_df["DailyRevenue"],
            mode="lines",
            name="Actual Historical Revenue",
            line=dict(color=CHART_COLORS["primary"], width=1.8),
            hovertemplate="<b>Actual:</b> %{x}<br>£%{y:,.2f}<extra></extra>"
        ))
        
        # Test set predictions
        fig.add_trace(go.Scatter(
            x=eval_df["Date"],
            y=eval_df["PredictedRevenue"],
            mode="lines",
            name="Hold-Out Model Fit",
            line=dict(color=CHART_COLORS["accent"], width=2, dash="dash"),
            hovertemplate="<b>Validation Fit:</b> %{x}<br>£%{y:,.2f}<extra></extra>"
        ))
        
        # Future projections
        fig.add_trace(go.Scatter(
            x=future_df["Date"],
            y=future_df["ForecastedRevenue"],
            mode="lines+markers",
            name=f"Projected Next {forecast_horizon} Days",
            line=dict(color=CHART_COLORS["success"], width=2.5),
            marker=dict(size=5),
            hovertemplate="<b>Forecast:</b> %{x}<br>£%{y:,.2f}<extra></extra>"
        ))
        
        # Confidence interval band
        fig.add_trace(go.Scatter(
            x=future_df["Date"].tolist() + future_df["Date"].tolist()[::-1],
            y=future_df["UpperBound"].tolist() + future_df["LowerBound"].tolist()[::-1],
            fill="toself",
            fillcolor="rgba(16, 185, 129, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            showlegend=True,
            name="95% Confidence Interval"
        ))
        
        fig.update_layout(
            yaxis=dict(title="Daily Revenue (£)", tickprefix="£", automargin=True, showgrid=True, gridcolor="#F1F5F9"),
            xaxis=dict(title="Date", automargin=True),
            legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1.0),
            margin=dict(l=60, r=40, t=60, b=40)
        )
        apply_chart_theme(fig, title=f"Revenue Actuals, Hold-Out Validation, and {forecast_horizon}-Day Projection")
        st.plotly_chart(fig, width="stretch")
        
        # Download forecast CSV
        csv_forecast = future_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Future Projections (CSV)", csv_forecast, "revenue_forecast.csv", "text/csv")
        
    # --------------------------------------------------------------------------
    # Tab 2: RFM Customer Segmentation
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("RFM Customer Behavioral Segmentation (K-Means)")
        st.caption(
            "Segments registered customers across three quantitative dimensions: "
            "**Recency** (days since last purchase), **Frequency** (total distinct orders), "
            "and **Monetary** (aggregate spend in £)."
        )
        
        if sales_df.empty:
            st.warning("⚠️ Cleaned sales data is unavailable for RFM segmentation.")
            return
            
        with st.container(border=True):
            clusters_count = st.slider("Select Number of Customer Clusters (k)", min_value=3, max_value=5, value=4)
            
        with st.spinner("Computing customer RFM vectors and fitting K-Means..."):
            rfm_df, summary_df = compute_rfm_segmentation(sales_df, n_clusters=clusters_count)
            
        # Display Segment Summary Cards
        st.markdown("##### 👥 Segment Overview and Commercial Impact")
        st.dataframe(
            summary_df.style.format({
                "CustomerCount": "{:,}",
                "AvgRecency": "{:.1f} days",
                "AvgFrequency": "{:.1f} orders",
                "AvgMonetary": "£{:,.2f}",
                "TotalRevenue": "£{:,.2f}"
            }),
            width="stretch"
        )
        
        st.divider()
        # Scatter Plot of Frequency vs Monetary colored by Segment
        fig_rfm = px.scatter(
            rfm_df,
            x="Recency",
            y="Monetary",
            size="Frequency",
            color="Segment",
            hover_name="CustomerID",
            hover_data={"Recency": True, "Frequency": True, "Monetary": ":,.2f"},
            title="Customer Clusters: Recency vs Monetary Value (Bubble Size = Frequency)",
            labels={"Recency": "Recency (Days since last purchase)", "Monetary": "Monetary Spend (£)"},
            log_y=True
        )
        fig_rfm.update_layout(
            yaxis=dict(tickprefix="£", automargin=True),
            xaxis=dict(automargin=True),
            margin=dict(l=60, r=40, t=60, b=40)
        )
        apply_chart_theme(fig_rfm)
        st.plotly_chart(fig_rfm, width="stretch")
        
        # Download RFM table
        csv_rfm = rfm_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Customer Segment Assignments (CSV)", csv_rfm, "customer_rfm_segments.csv", "text/csv")


if __name__ == "__main__":
    render_page()
