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


def extract_category(code_str: str) -> str:
    """Extracts human-readable product category from StockCode prefix or SKU."""
    prefix_map = {
        "CLO": "Clothing",
        "ACC": "Accessories",
        "FOO": "Footwear",
        "OUT": "Outerwear"
    }
    if isinstance(code_str, str) and "-" in code_str:
        p = code_str.split("-")[0].upper()
        return prefix_map.get(p, p)
    return "General Merchandise"


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
    
    # Assign extracted categories
    top_rev_df["Category"] = top_rev_df["StockCode"].apply(extract_category)
    top_qty_df["Category"] = top_qty_df["StockCode"].apply(extract_category)
    has_categories = top_rev_df["Category"].nunique() > 1
    
    # Sample Data Banner Disclosure
    if st.session_state.get("active_dataset_type") == "sample":
        st.info("🧪 **Sample Dataset Active:** Showing product catalog performance for the included sample dataset.")
        
    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Highest Revenue Products",
        "📦 Top Selling by Volume",
        "🏷️ Department & Category Breakdown",
        "🔍 Product Lookup & Search"
    ])
    
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
                if has_categories:
                    cat_options = ["All Categories"] + sorted(top_rev_df["Category"].unique().tolist())
                    selected_cat_filter = st.selectbox("Filter Category:", cat_options, index=0, key="cat_rev_filter")
                else:
                    selected_cat_filter = "All Categories"
                    st.caption(f"Active Valuation: `{code} ({symbol})` | Sorted by Total Revenue")
            
        pool_rev = top_rev_df if selected_cat_filter == "All Categories" else top_rev_df[top_rev_df["Category"] == selected_cat_filter]
        display_df = pool_rev.head(top_n).copy()
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
            title=f"Top {len(display_df)} Products by Total Revenue ({symbol})" + (f" — {selected_cat_filter}" if selected_cat_filter != "All Categories" else "")
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
            show_cols = ["StockCode", "Description", "Category", "ScaledRevenue", "UnitsSold", "OrderCount", "ScaledAvgUnitPrice"] if has_categories else ["StockCode", "Description", "ScaledRevenue", "UnitsSold", "OrderCount", "ScaledAvgUnitPrice"]
            st.dataframe(
                display_df[show_cols].style.format({
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
                if has_categories:
                    cat_options_qty = ["All Categories"] + sorted(top_qty_df["Category"].unique().tolist())
                    selected_cat_qty = st.selectbox("Filter Category:", cat_options_qty, index=0, key="cat_qty_filter")
                else:
                    selected_cat_qty = "All Categories"
                    st.caption("Sorted by physical units sold across all completed transactions")
            
        pool_qty = top_qty_df if selected_cat_qty == "All Categories" else top_qty_df[top_qty_df["Category"] == selected_cat_qty]
        display_qty_df = pool_qty.head(top_n_qty).copy()
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
            title=f"Top {len(display_qty_df)} Products by Physical Units Sold" + (f" — {selected_cat_qty}" if selected_cat_qty != "All Categories" else "")
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
        st.subheader("Department & Category Breakdown")
        st.caption("Aggregates catalog performance across product departments to evaluate product mix and merchandise share.")
        
        if has_categories:
            cat_summary = (
                top_rev_df.groupby("Category")
                .agg(
                    TotalRevenue=("TotalRevenue", "sum"),
                    UnitsSold=("UnitsSold", "sum"),
                    ProductCount=("StockCode", "count"),
                    AvgItemPrice=("AvgUnitPrice", "mean")
                )
                .reset_index()
                .sort_values("TotalRevenue", ascending=False)
            )
            cat_summary["ScaledRevenue"] = cat_summary["TotalRevenue"] * rate
            cat_summary["ScaledAvgPrice"] = cat_summary["AvgItemPrice"] * rate
            
            top_cat_row = cat_summary.iloc[0]
            total_cat_rev = cat_summary["ScaledRevenue"].sum()
            
            ck1, ck2, ck3, ck4 = st.columns(4)
            with ck1:
                render_kpi_card("Active Categories", format_number(len(cat_summary)), subtitle="Distinct departments")
            with ck2:
                render_kpi_card("Top Category", str(top_cat_row["Category"]), subtitle=f"{(top_cat_row['ScaledRevenue']/total_cat_rev*100):.1f}% of catalog revenue")
            with ck3:
                render_kpi_card(f"Top Dept Revenue ({symbol})", format_currency(top_cat_row["TotalRevenue"], compact=True), subtitle=f"{int(top_cat_row['UnitsSold']):,} units")
            with ck4:
                render_kpi_card("Total Catalog Units", format_number(int(cat_summary["UnitsSold"].sum())), subtitle="Across top SKUs")
                
            st.divider()
            
            col_cat_pie, col_cat_tbl = st.columns([1, 1])
            with col_cat_pie:
                fig_cat = px.pie(
                    cat_summary,
                    names="Category",
                    values="ScaledRevenue",
                    hole=0.45,
                    color_discrete_sequence=[CHART_COLORS["primary"], CHART_COLORS["accent_teal"], CHART_COLORS["accent_purple"], CHART_COLORS["warning"], CHART_COLORS["info"]],
                    title=f"Revenue Distribution by Department ({symbol})"
                )
                fig_cat.update_traces(textinfo="percent+label")
                apply_chart_theme(fig_cat)
                st.plotly_chart(fig_cat, use_container_width=True)
                
            with col_cat_tbl:
                st.markdown("##### 📊 Department Sales Summary")
                st.dataframe(
                    cat_summary[["Category", "ScaledRevenue", "UnitsSold", "ProductCount", "ScaledAvgPrice"]].style.format({
                        "ScaledRevenue": f"{symbol}{{:,.2f}}",
                        "UnitsSold": "{:,}",
                        "ProductCount": "{:,}",
                        "ScaledAvgPrice": f"{symbol}{{:,.2f}}"
                    }),
                    use_container_width=True
                )
                
                cat_csv = cat_summary.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Department Breakdown (CSV)", cat_csv, "department_sales_breakdown.csv", "text/csv")
        else:
            with st.container(border=True):
                st.info(
                    "💡 **Single Department Catalog:** Current catalog items do not have distinct category prefixes. "
                    "Department breakdown activates automatically when dataset contains category fields or prefixed item codes (e.g., `shopping.csv`)."
                )
            
    with tab4:
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
