"""
SalesPulse Analytics - Product Analytics Page
Provides deep inspection of catalog performance, top products by revenue and units,
unit price distribution, and interactive search.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard.utils import (
    load_top_products_revenue,
    load_top_products_quantity,
    format_currency,
    format_number,
    apply_chart_theme,
    CHART_COLORS
)


def render_page():
    st.title("📦 Product Performance Analytics")
    st.caption("Detailed breakdown of catalog performance, ranking bestsellers by revenue, volume, and pricing bands.")
    
    top_rev_df = load_top_products_revenue()
    top_qty_df = load_top_products_quantity()
    
    if top_rev_df.empty or top_qty_df.empty:
        st.warning("⚠️ Product analytics summary is empty. Please process the dataset first.")
        return
        
    tab1, tab2, tab3 = st.tabs(["💰 Highest Revenue Products", "📦 Top Selling by Volume", "🔍 Product Lookup & Search"])
    
    with tab1:
        st.subheader("Top Revenue Drivers")
        col_ctrl, col_chart = st.columns([1, 3])
        
        with col_ctrl:
            with st.container(border=True):
                top_n = st.slider("Display Count", min_value=5, max_value=20, value=10, key="rev_slider")
                show_data = st.checkbox("Show Table View", value=True, key="rev_table_chk")
            
        with col_chart:
            display_df = top_rev_df.head(top_n).copy()
            display_df["ShortDesc"] = display_df["Description"].apply(
                lambda x: str(x)[:30] + "..." if len(str(x)) > 32 else str(x)
            )
            fig = px.bar(
                display_df,
                x="TotalRevenue",
                y="ShortDesc",
                orientation="h",
                text="TotalRevenue",
                color="TotalRevenue",
                color_continuous_scale="Viridis",
                labels={"TotalRevenue": "Total Revenue (£)", "ShortDesc": ""},
                title=f"Top {top_n} Products by Total Revenue (£)"
            )
            fig.update_traces(texttemplate="£%{x:,.0f}", textposition="inside")
            fig.update_layout(
                yaxis=dict(autorange="reversed", automargin=True, title=""),
                xaxis=dict(title="Revenue (£)", tickprefix="£", automargin=True),
                coloraxis_showscale=False,
                margin=dict(l=20, r=30, t=60, b=40)
            )
            apply_chart_theme(fig)
            st.plotly_chart(fig, width="stretch")
            
        if show_data:
            st.dataframe(
                display_df[["StockCode", "Description", "TotalRevenue", "UnitsSold", "OrderCount", "AvgUnitPrice"]].style.format({
                    "TotalRevenue": "£{:,.2f}",
                    "UnitsSold": "{:,}",
                    "OrderCount": "{:,}",
                    "AvgUnitPrice": "£{:.2f}"
                }),
                width="stretch"
            )
            
            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Top Revenue Products (CSV)", csv, "top_revenue_products.csv", "text/csv")
            
    with tab2:
        st.subheader("High Volume Movers")
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
                title=f"Top {top_n_qty} Products by Units Sold"
            )
            fig_qty.update_traces(texttemplate="%{x:,}", textposition="inside")
            fig_qty.update_layout(
                yaxis=dict(autorange="reversed", automargin=True, title=""),
                xaxis=dict(title="Units Sold", automargin=True),
                coloraxis_showscale=False,
                margin=dict(l=20, r=30, t=60, b=40)
            )
            apply_chart_theme(fig_qty)
            st.plotly_chart(fig_qty, width="stretch")
            
        st.dataframe(
            display_qty_df[["StockCode", "Description", "UnitsSold", "TotalRevenue", "OrderCount"]].style.format({
                "TotalRevenue": "£{:,.2f}",
                "UnitsSold": "{:,}",
                "OrderCount": "{:,}"
            }),
            width="stretch"
        )
        
    with tab3:
        st.subheader("Product Catalog Search")
        search_query = st.text_input("Enter Product Description or StockCode", placeholder="e.g. HEART, LANTERN, 85123A")
        
        merged_products = pd.concat([top_rev_df, top_qty_df]).drop_duplicates(subset=["StockCode"])
        
        if search_query:
            filtered = merged_products[
                merged_products["Description"].str.contains(search_query, case=False, na=False) |
                merged_products["StockCode"].str.contains(search_query, case=False, na=False)
            ]
            st.write(f"Found **{len(filtered)}** matching products:")
            st.dataframe(
                filtered[["StockCode", "Description", "TotalRevenue", "UnitsSold", "OrderCount"]].style.format({
                    "TotalRevenue": "£{:,.2f}",
                    "UnitsSold": "{:,}",
                    "OrderCount": "{:,}"
                }),
                width="stretch"
            )
        else:
            st.info("Type a keyword or StockCode above to filter products.")


if __name__ == "__main__":
    render_page()
