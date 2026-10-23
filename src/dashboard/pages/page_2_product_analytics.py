"""
SalesPulse Analytics - Product Insights Page
Provides deep inspection of catalog performance, top products by revenue and units,
unit price distribution, and interactive search with INR currency localization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard.utils import (
    load_top_products_revenue,
    load_top_products_quantity,
    format_currency,
    format_number,
    get_active_currency_config,
    apply_chart_theme,
    CHART_COLORS
)


def render_page():
    st.title("📦 Product Insights & Catalog Performance")
    st.caption("Detailed breakdown of catalog performance, ranking bestsellers by revenue, volume, and pricing bands.")
    
    top_rev_df = load_top_products_revenue()
    top_qty_df = load_top_products_quantity()
    
    if top_rev_df.empty or top_qty_df.empty:
        with st.container(border=True):
            st.markdown("### ℹ️ Product Insights Unavailable")
            st.markdown(
                "Product insights require product descriptions or item codes (SKUs) and unit pricing. "
                "No product summary is currently available. Please import a dataset to view product analytics."
            )
            if st.button("🚀 Upload or Select Dataset", type="primary"):
                st.session_state["nav_selection"] = "📥 Upload & Manage Data"
                st.rerun()
        return
        
    symbol, code, rate = get_active_currency_config()
    
    # Sample Data Banner Disclosure
    if st.session_state.get("active_dataset_type") == "sample":
        st.info("🧪 **Sample Dataset Active:** Showing product catalog performance for the included sample dataset.")
        
    tab1, tab2, tab3 = st.tabs(["💰 Highest Revenue Products", "📦 Top Selling by Volume", "🔍 Product Lookup & Search"])
    
    with tab1:
        st.subheader("Top Revenue Drivers")
        st.caption("Identifies the products generating the highest aggregate commercial revenue.")
        col_ctrl, col_chart = st.columns([1, 3])
        
        with col_ctrl:
            with st.container(border=True):
                top_n = st.slider("Display Count", min_value=5, max_value=20, value=10, key="rev_slider")
                show_data = st.checkbox("Show Table View", value=True, key="rev_table_chk")
                st.caption(f"Active Currency: `{code} ({symbol})`")
            
        with col_chart:
            display_df = top_rev_df.head(top_n).copy()
            display_df["ScaledRevenue"] = display_df["TotalRevenue"] * rate
            display_df["ScaledAvgUnitPrice"] = display_df["AvgUnitPrice"] * rate
            display_df["ShortDesc"] = display_df["Description"].apply(
                lambda x: str(x)[:30] + "..." if len(str(x)) > 32 else str(x)
            )
            fig = px.bar(
                display_df,
                x="ScaledRevenue",
                y="ShortDesc",
                orientation="h",
                text="ScaledRevenue",
                color="ScaledRevenue",
                color_continuous_scale="Viridis",
                labels={"ScaledRevenue": f"Total Revenue ({symbol})", "ShortDesc": ""},
                title=f"Top {top_n} Products by Total Revenue ({symbol})"
            )
            fig.update_traces(texttemplate=f"{symbol}%{{x:,.0f}}", textposition="inside")
            fig.update_layout(
                yaxis=dict(autorange="reversed", automargin=True, title=""),
                xaxis=dict(title=f"Revenue ({symbol})", tickprefix=symbol, automargin=True),
                coloraxis_showscale=False,
                margin=dict(l=20, r=30, t=60, b=40)
            )
            apply_chart_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
            
        if show_data:
            st.dataframe(
                display_df[["StockCode", "Description", "ScaledRevenue", "UnitsSold", "OrderCount", "ScaledAvgUnitPrice"]].style.format({
                    "ScaledRevenue": f"{symbol}{{:,.2f}}",
                    "UnitsSold": "{:,}",
                    "OrderCount": "{:,}",
                    "ScaledAvgUnitPrice": f"{symbol}{{:,.2f}}"
                }),
                use_container_width=True
            )
            
            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Top Revenue Products (CSV)", csv, "top_revenue_products.csv", "text/csv")
            
    with tab2:
        st.subheader("High Volume Movers")
        st.caption("Highlights items with the greatest physical units shipped to identify inventory velocity.")
        col_ctrl2, col_chart2 = st.columns([1, 3])
        
        with col_ctrl2:
            with st.container(border=True):
                top_n_qty = st.slider("Display Count", min_value=5, max_value=20, value=10, key="qty_slider")
            
        with col_chart2:
            display_qty_df = top_qty_df.head(top_n_qty).copy()
            display_qty_df["ShortDesc"] = display_qty_df["Description"].apply(
                lambda x: str(x)[:30] + "..." if len(str(x)) > 32 else str(x)
            )
            fig_qty = px.bar(
                display_qty_df,
                x="UnitsSold",
                y="ShortDesc",
                orientation="h",
                text="UnitsSold",
                color="UnitsSold",
                color_continuous_scale="Teal",
                labels={"UnitsSold": "Units Sold", "ShortDesc": ""},
                title=f"Top {top_n_qty} Products by Physical Units Sold"
            )
            fig_qty.update_traces(texttemplate="%{x:,}", textposition="inside")
            fig_qty.update_layout(
                yaxis=dict(autorange="reversed", automargin=True, title=""),
                xaxis=dict(title="Physical Units Sold", automargin=True),
                coloraxis_showscale=False,
                margin=dict(l=20, r=30, t=60, b=40)
            )
            apply_chart_theme(fig_qty)
            st.plotly_chart(fig_qty, use_container_width=True)
            
    with tab3:
        st.subheader("Search Product Catalog")
        st.caption("Search across catalog inventory by SKU or product title to inspect item-level metrics.")
        search_query = st.text_input("Enter SKU/StockCode or Description Keyword:", placeholder="e.g. WHITE HANGING HEART or 85123A")
        
        if search_query:
            matched = top_rev_df[
                top_rev_df["Description"].str.contains(search_query, case=False, na=False) |
                top_rev_df["StockCode"].str.contains(search_query, case=False, na=False)
            ].copy()
            
            matched["ScaledRevenue"] = matched["TotalRevenue"] * rate
            matched["ScaledAvgUnitPrice"] = matched["AvgUnitPrice"] * rate
            
            st.write(f"Found **{len(matched)}** matching catalog items:")
            st.dataframe(
                matched[["StockCode", "Description", "ScaledRevenue", "UnitsSold", "OrderCount", "ScaledAvgUnitPrice"]].style.format({
                    "ScaledRevenue": f"{symbol}{{:,.2f}}",
                    "UnitsSold": "{:,}",
                    "OrderCount": "{:,}",
                    "ScaledAvgUnitPrice": f"{symbol}{{:,.2f}}"
                }),
                use_container_width=True
            )
        else:
            st.info("Enter a search term above to filter and inspect individual catalog SKUs.")


if __name__ == "__main__":
    render_page()
