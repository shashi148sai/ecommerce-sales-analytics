"""
SalesPulse Analytics - Customer Insights Page
Analyzes geographic revenue distributions, customer retention / repeat purchase metrics,
and behavioral RFM customer segmentation with INR currency localization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard.utils import (
    load_country_revenue,
    load_repeat_customers,
    load_cleaned_sales_sample,
    format_currency,
    format_number,
    format_percent,
    render_kpi_card,
    get_active_currency_config,
    apply_chart_theme,
    CHART_COLORS
)
from src.analytics.advanced import compute_rfm_segmentation


def render_page():
    st.title("👥 Customer & Regional Insights")
    st.caption("Examine geographic revenue concentration, customer repeat purchasing patterns, and behavioral loyalty tiers.")
    
    country_df = load_country_revenue()
    repeat_stats = load_repeat_customers()
    sales_df = load_cleaned_sales_sample(limit=50000)
    symbol, code, rate = get_active_currency_config()
    
    # --------------------------------------------------------------------------
    # Empty State Handling
    # --------------------------------------------------------------------------
    if country_df.empty and not repeat_stats:
        with st.container(border=True):
            st.markdown("### ℹ️ Customer Insights Unavailable")
            st.markdown(
                "Customer and regional insights require `CustomerID` and `Country` fields. "
                "No customer retention summary has been generated for the active session."
            )
            if st.button("🚀 Upload or Select Dataset", type="primary"):
                st.session_state["nav_selection"] = "📥 Upload & Manage Data"
                st.rerun()
        return
        
    # Sample Data Banner Disclosure
    if st.session_state.get("active_dataset_type") == "sample":
        st.info("🧪 **Sample Dataset Active:** Showing customer loyalty and regional breakdown for the sample dataset.")
        
    tab1, tab2, tab3 = st.tabs(["🗺️ Geographic Performance", "👥 Customer Loyalty & Retention", "🔮 RFM Behavioral Clusters"])
    
    # --------------------------------------------------------------------------
    # Tab 1: Geographic Performance
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Regional Revenue Distribution")
        st.caption("Analyzes how commercial revenue is distributed geographically across domestic and international markets.")
        
        if not country_df.empty:
            sorted_countries = country_df.sort_values("TotalRevenue", ascending=False)
            top_country = sorted_countries.iloc[0]["Country"]
            primary_row = sorted_countries[sorted_countries["Country"] == top_country]
            other_rows = sorted_countries[sorted_countries["Country"] != top_country].copy()
            
            total_rev = country_df["TotalRevenue"].sum()
            primary_rev = primary_row["TotalRevenue"].iloc[0] if not primary_row.empty else 0.0
            other_rev = other_rows["TotalRevenue"].sum()
            primary_share = (primary_rev / total_rev) if total_rev > 0 else 0.0
            is_concentrated = primary_share >= 0.30
            
            c1, c2, c3 = st.columns(3)
            with c1:
                render_kpi_card(
                    "Total Territory Revenue",
                    format_currency(total_rev, compact=True),
                    subtitle=f"Across {len(country_df)} regional markets"
                )
            with c2:
                render_kpi_card(
                    f"{'Primary Market' if is_concentrated else 'Top Territory'} ({top_country})",
                    format_currency(primary_rev, compact=True),
                    subtitle=f"{format_percent(primary_share * 100)} of total"
                )
            with c3:
                render_kpi_card(
                    "International Markets" if is_concentrated else "Other Regional Territories",
                    format_currency(other_rev, compact=True),
                    subtitle=f"{format_percent((other_rev / total_rev) * 100)} of total"
                )
                
            st.divider()
            
            # Interactive Country Drilldown Inspector
            with st.container(border=True):
                country_options = ["-- Global Overview (All Countries) --"] + sorted_countries["Country"].tolist()
                selected_country = st.selectbox(
                    "🔍 Interactive Country Deep Dive Inspector:",
                    options=country_options,
                    index=0,
                    help="Select any individual country to inspect localized sales metrics, orders, customer count, and AOV."
                )
                
            if selected_country != "-- Global Overview (All Countries) --":
                cdetail = sorted_countries[sorted_countries["Country"] == selected_country].iloc[0]
                c_rev = cdetail["TotalRevenue"] * rate
                c_aov = cdetail["CountryAOV"] * rate
                c_orders = int(cdetail["OrderCount"])
                c_cust = int(cdetail["CustomerCount"])
                c_units = int(cdetail["UnitsSold"])
                c_share = (cdetail["TotalRevenue"] / total_rev) * 100
                
                st.markdown(f"#### 📍 Regional Performance: **{selected_country}**")
                dk1, dk2, dk3, dk4, dk5 = st.columns(5)
                with dk1:
                    render_kpi_card(f"Revenue ({symbol})", format_currency(cdetail["TotalRevenue"], compact=True), subtitle=f"{c_share:.2f}% of Global")
                with dk2:
                    render_kpi_card("Order Volume", format_number(c_orders), subtitle="Completed transactions")
                with dk3:
                    render_kpi_card("Buyers", format_number(c_cust), subtitle="Unique customers")
                with dk4:
                    render_kpi_card(f"AOV ({symbol})", format_currency(cdetail["CountryAOV"]), subtitle="Avg per order")
                with dk5:
                    render_kpi_card("Units Sold", format_number(c_units), subtitle="Total items shipped")
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
                st.plotly_chart(fig_country, use_container_width=True)
                
            with col_intl:
                market_label = "International" if is_concentrated else "Regional"
                st.markdown(f"##### 🌐 Other Top {market_label} Markets ({symbol})")
                top_intl = other_rows.head(8).copy()
                top_intl["ScaledRevenue"] = top_intl["TotalRevenue"] * rate
                top_intl["ScaledCountryAOV"] = top_intl["CountryAOV"] * rate
                st.dataframe(
                    top_intl[["Country", "ScaledRevenue", "OrderCount", "ScaledCountryAOV"]].style.format({
                        "ScaledRevenue": f"{symbol}{{:,.2f}}",
                        "OrderCount": "{:,}",
                        "ScaledCountryAOV": f"{symbol}{{:,.2f}}"
                    }),
                    use_container_width=True
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
                use_container_width=True
            )
        else:
            st.info("ℹ️ Country or regional data is not present in this dataset.")
            
    # --------------------------------------------------------------------------
    # Tab 2: Customer Loyalty & Retention
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Customer Loyalty & Lifetime Dynamics")
        st.caption("Measures repeat buyer rates, single-order cohorts, and guest checkout revenue share.")
        
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
                st.plotly_chart(fig_loyalty, use_container_width=True)
                
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
            st.info("ℹ️ Customer retention metrics require identifiable Customer IDs. Uploaded dataset does not have customer identifiers.")
            
    # --------------------------------------------------------------------------
    # Tab 3: RFM Behavioral Clusters (K-Means)
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("RFM Customer Behavioral Segmentation (K-Means)")
        st.caption(
            "Segments registered customers across three quantitative dimensions: "
            "**Recency** (days since last purchase), **Frequency** (total distinct orders), "
            f"and **Monetary** (aggregate spend in {symbol})."
        )
        
        if not sales_df.empty:
            with st.container(border=True):
                clusters_count = st.slider("Select Number of Customer Clusters (k)", min_value=3, max_value=5, value=4, key="rfm_slider_cust")
                
            with st.spinner("Computing customer RFM vectors and fitting K-Means..."):
                rfm_df, summary_df = compute_rfm_segmentation(sales_df, n_clusters=clusters_count)
                
            summary_display = summary_df.copy()
            summary_display["ScaledAvgMonetary"] = summary_display["AvgMonetary"] * rate
            summary_display["ScaledTotalRevenue"] = summary_display["TotalRevenue"] * rate
            
            # Interactive Segment Drilldown Selector
            with st.container(border=True):
                segment_options = ["-- All Customer Segments --"] + summary_df["Segment"].tolist()
                selected_seg = st.selectbox(
                    "🎯 Drill into Customer Segment:",
                    options=segment_options,
                    index=0,
                    help="Select a specific customer tier to inspect cohort size, spend behavior, and export targeting lists."
                )
                
            rfm_display = rfm_df.copy()
            rfm_display["ScaledMonetary"] = rfm_display["Monetary"] * rate
            
            if selected_seg != "-- All Customer Segments --":
                seg_summary = summary_display[summary_display["Segment"] == selected_seg].iloc[0]
                seg_customers = rfm_display[rfm_display["Segment"] == selected_seg].sort_values("ScaledMonetary", ascending=False)
                
                # Dynamic Segment KPI Cards
                sk1, sk2, sk3, sk4 = st.columns(4)
                with sk1:
                    render_kpi_card("Segment Buyers", format_number(int(seg_summary["CustomerCount"])), subtitle=f"{(int(seg_summary['CustomerCount'])/len(rfm_df)*100):.1f}% of total base")
                with sk2:
                    render_kpi_card(f"Avg Spend ({symbol})", format_currency(seg_summary["AvgMonetary"]), subtitle="Per buyer lifetime")
                with sk3:
                    render_kpi_card(f"Total Revenue ({symbol})", format_currency(seg_summary["TotalRevenue"], compact=True), subtitle="Cumulative cohort spend")
                with sk4:
                    render_kpi_card("Avg Recency", f"{seg_summary['AvgRecency']:.1f} days", subtitle=f"Avg {seg_summary['AvgFrequency']:.1f} orders")
                    
                # Actionable Business Strategy Insight
                strat_text = ""
                if "Champion" in selected_seg:
                    strat_text = "🌟 **Recommended Action:** VIP appreciation rewards, preview access to new product drops, and exclusive referral incentives."
                elif "Loyal" in selected_seg:
                    strat_text = "🤝 **Recommended Action:** Upsell higher-margin SKUs, cross-sell related categories, and introduce loyalty tier milestones."
                elif "Risk" in selected_seg or "Lost" in selected_seg or "Hibernating" in selected_seg:
                    strat_text = "⚠️ **Recommended Action:** Win-back reactivation campaigns with personalized discount vouchers or customer satisfaction surveys."
                else:
                    strat_text = "🌱 **Recommended Action:** Post-purchase onboarding drip sequences and personalized recommendations to drive that crucial 2nd order."
                st.info(strat_text)
                
                st.markdown(f"##### 📋 Top Customers in {selected_seg}")
                st.dataframe(
                    seg_customers[["CustomerID", "Recency", "Frequency", "ScaledMonetary"]].head(100).style.format({
                        "CustomerID": "{:.0f}",
                        "Recency": "{:.0f} days ago",
                        "Frequency": "{:.0f} orders",
                        "ScaledMonetary": f"{symbol}{{:,.2f}}"
                    }),
                    use_container_width=True
                )
                
                csv_seg = seg_customers[["CustomerID", "Recency", "Frequency", "ScaledMonetary"]].to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"📥 Download {selected_seg} Cohort for Campaigns (CSV)",
                    data=csv_seg,
                    file_name=f"customer_cohort_{selected_seg.lower().replace(' ', '_')}.csv",
                    mime="text/csv"
                )
                st.divider()

            # Display Global Segment Summary Table
            st.markdown(f"##### 👥 Segment Overview and Commercial Impact ({symbol})")
            st.dataframe(
                summary_display[["Segment", "CustomerCount", "AvgRecency", "AvgFrequency", "ScaledAvgMonetary", "ScaledTotalRevenue"]].style.format({
                    "CustomerCount": "{:,}",
                    "AvgRecency": "{:.1f} days",
                    "AvgFrequency": "{:.1f} orders",
                    "ScaledAvgMonetary": f"{symbol}{{:,.2f}}",
                    "ScaledTotalRevenue": f"{symbol}{{:,.2f}}"
                }),
                use_container_width=True
            )
            
            st.divider()
            
            # Scatter Plot of Frequency vs Monetary colored by Segment
            fig_rfm = px.scatter(
                rfm_display,
                x="Recency",
                y="ScaledMonetary",
                size="Frequency",
                color="Segment",
                hover_name="CustomerID",
                hover_data={"Recency": True, "Frequency": True, "ScaledMonetary": ":,.2f"},
                title=f"Customer Clusters: Recency vs Monetary Value ({symbol}) (Bubble Size = Frequency)",
                labels={"Recency": "Recency (Days since last purchase)", "ScaledMonetary": f"Monetary Spend ({symbol})"},
                log_y=True
            )
            fig_rfm.update_layout(
                yaxis=dict(tickprefix=symbol, automargin=True),
                xaxis=dict(automargin=True),
                margin=dict(l=60, r=40, t=60, b=40)
            )
            apply_chart_theme(fig_rfm)
            st.plotly_chart(fig_rfm, use_container_width=True)
            
            # Download RFM table
            csv_rfm = rfm_display.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Complete Customer Segments (CSV)", csv_rfm, "customer_rfm_segments.csv", "text/csv")
        else:
            st.info("ℹ️ RFM segmentation requires customer transaction logs.")


if __name__ == "__main__":
    render_page()
