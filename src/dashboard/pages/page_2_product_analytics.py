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
    render_kpi_card,
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
        
        with st.container(border=True):
            col_s1, col_s2, col_s3 = st.columns([1.5, 1.5, 2])
            with col_s1:
                top_n = st.slider("Display Count", min_value=5, max_value=25, value=10, key="rev_slider")
            with col_s2:
                show_data = st.checkbox("Show Table View", value=True, key="rev_table_chk")
            with col_s3:
                st.caption(f"Active Valuation: `{code} ({symbol})` | Sorted by Total Revenue")
            
        display_df = top_rev_df.head(top_n).copy()
        display_df["ScaledRevenue"] = display_df["TotalRevenue"] * rate
        display_df["ScaledAvgUnitPrice"] = display_df["AvgUnitPrice"] * rate
        display_df["ShortDesc"] = display_df["Description"].apply(
            lambda x: str(x)[:36] + "..." if len(str(x)) > 38 else str(x)
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
        
        with st.container(border=True):
            col_q1, col_q2 = st.columns([1.5, 3.5])
            with col_q1:
                top_n_qty = st.slider("Display Count", min_value=5, max_value=25, value=10, key="qty_slider")
            with col_q2:
                st.caption("Sorted by physical units sold across all completed transactions")
            
        display_qty_df = top_qty_df.head(top_n_qty).copy()
        display_qty_df["ShortDesc"] = display_qty_df["Description"].apply(
            lambda x: str(x)[:36] + "..." if len(str(x)) > 38 else str(x)
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
        st.subheader("Interactive Product Catalog Explorer")
        st.caption("Search, filter, and drill into individual catalog SKUs by description, unit price, and velocity.")
        
        # Filter Control Panel
        with st.container(border=True):
            col_search, col_sort = st.columns([2, 1.2])
            with col_search:
                search_query = st.text_input(
                    "🔍 Search SKU or Product Description Keyword:",
                    placeholder="e.g. HEART, LANTERN, MUG, or 85123A",
                    help="Filter catalog items by title substring or exact alphanumeric StockCode."
                )
            with col_sort:
                sort_metric = st.selectbox(
                    "Sort Results By:",
                    options=["Total Revenue (High to Low)", "Units Sold (High to Low)", "Average Price (High to Low)", "Order Volume (High to Low)"],
                    index=0
                )
                
            col_min_units, col_min_price = st.columns(2)
            with col_min_units:
                min_units = st.slider("Minimum Units Sold Filter:", min_value=0, max_value=5000, value=0, step=50)
            with col_min_price:
                max_price_val = float((top_rev_df["AvgUnitPrice"] * rate).max()) if not top_rev_df.empty else 1000.0
                price_ceiling = min(max_price_val, 10000.0)
                selected_price_range = st.slider(
                    f"Unit Price Range ({symbol}):",
                    min_value=0.0,
                    max_value=round(price_ceiling, 0),
                    value=(0.0, round(price_ceiling, 0)),
                    step=5.0
                )
        
        # Filtering logic
        catalog_pool = top_rev_df.copy()
        catalog_pool["ScaledRevenue"] = catalog_pool["TotalRevenue"] * rate
        catalog_pool["ScaledAvgUnitPrice"] = catalog_pool["AvgUnitPrice"] * rate
        
        if search_query:
            catalog_pool = catalog_pool[
                catalog_pool["Description"].str.contains(search_query, case=False, na=False) |
                catalog_pool["StockCode"].str.contains(search_query, case=False, na=False)
            ]
            
        if min_units > 0:
            catalog_pool = catalog_pool[catalog_pool["UnitsSold"] >= min_units]
            
        catalog_pool = catalog_pool[
            (catalog_pool["ScaledAvgUnitPrice"] >= selected_price_range[0]) &
            (catalog_pool["ScaledAvgUnitPrice"] <= selected_price_range[1])
        ]
        
        # Sorting
        if sort_metric == "Total Revenue (High to Low)":
            catalog_pool = catalog_pool.sort_values("ScaledRevenue", ascending=False)
        elif sort_metric == "Units Sold (High to Low)":
            catalog_pool = catalog_pool.sort_values("UnitsSold", ascending=False)
        elif sort_metric == "Average Price (High to Low)":
            catalog_pool = catalog_pool.sort_values("ScaledAvgUnitPrice", ascending=False)
        elif sort_metric == "Order Volume (High to Low)":
            catalog_pool = catalog_pool.sort_values("OrderCount", ascending=False)
            
        # Display Results
        if not catalog_pool.empty:
            st.markdown(f"##### 🎯 Catalog Results ({len(catalog_pool):,} items found)")
            
            # Interactive SKU Single Item Inspector
            with st.expander("🔬 Single SKU Detail Deep Dive Inspector", expanded=False):
                sku_choices = [f"{row['StockCode']} — {str(row['Description'])[:45]}" for _, row in catalog_pool.head(50).iterrows()]
                chosen_sku_label = st.selectbox("Select Item to Inspect:", sku_choices)
                if chosen_sku_label:
                    chosen_code = chosen_sku_label.split(" — ")[0]
                    chosen_row = catalog_pool[catalog_pool["StockCode"] == chosen_code].iloc[0]
                    
                    sk1, sk2, sk3, sk4 = st.columns(4)
                    with sk1:
                        render_kpi_card(f"Gross Revenue ({symbol})", format_currency(chosen_row["TotalRevenue"]))
                    with sk2:
                        render_kpi_card("Physical Units", format_number(chosen_row["UnitsSold"]))
                    with sk3:
                        render_kpi_card("Orders", format_number(chosen_row["OrderCount"]))
                    with sk4:
                        render_kpi_card(f"Avg Unit Price ({symbol})", format_currency(chosen_row["AvgUnitPrice"]))
            
            st.dataframe(
                catalog_pool[["StockCode", "Description", "ScaledRevenue", "UnitsSold", "OrderCount", "ScaledAvgUnitPrice"]].head(100).style.format({
                    "ScaledRevenue": f"{symbol}{{:,.2f}}",
                    "UnitsSold": "{:,}",
                    "OrderCount": "{:,}",
                    "ScaledAvgUnitPrice": f"{symbol}{{:,.2f}}"
                }),
                use_container_width=True
            )
            
            csv_filtered = catalog_pool[["StockCode", "Description", "ScaledRevenue", "UnitsSold", "OrderCount", "ScaledAvgUnitPrice"]].to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"📥 Download Filtered Catalog View ({len(catalog_pool)} SKUs) (CSV)",
                data=csv_filtered,
                file_name="filtered_catalog_export.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ No products match the current keyword, unit, and price filter criteria. Try broadening your search or resetting sliders.")


if __name__ == "__main__":
    render_page()
