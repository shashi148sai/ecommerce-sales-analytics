"""
SalesPulse Analytics - Upload & Manage Data Page
Provides a dedicated 4-stage data import and engineering wizard:
Choose Input ➔ Preview & Validate ➔ Match Columns & Analyze ➔ Results & Export.
Supports CSV, Excel (XLSX/XLS), TSV, TXT, JSON, JSONL, Parquet, pasted text, manual entry, and safe ZIP archives.
"""

import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path

from config import settings
from src.dashboard.utils import (
    load_pipeline_metadata,
    load_data_quality_report,
    load_kpis,
    format_number,
    format_currency,
    format_percent,
    render_kpi_card,
    get_csv_template,
    get_active_currency_config,
    check_available_analyses
)
from src.ingestion.loader import (
    parse_tabular_data,
    parse_pasted_text,
    inspect_zip_archive,
    extract_zip_member
)
from src.validation.validator import (
    detect_schema_mapping,
    normalize_pandas_dataframe
)
from src.processing.pipeline import run_pipeline


def render_page():
    st.title("📥 Upload & Manage Data")
    st.caption("Import, inspect, map, and process your e-commerce transaction data using distributed Big Data analytics.")
    
    # Initialize session state variables for wizard
    if "wizard_step" not in st.session_state:
        st.session_state["wizard_step"] = 1
    if "imported_df" not in st.session_state:
        st.session_state["imported_df"] = None
    if "imported_meta" not in st.session_state:
        st.session_state["imported_meta"] = {}
    if "confirmed_mapping" not in st.session_state:
        st.session_state["confirmed_mapping"] = {}
    if "is_processing" not in st.session_state:
        st.session_state["is_processing"] = False
        
    symbol, code, rate = get_active_currency_config()
    
    # --------------------------------------------------------------------------
    # Step Indicator Banner (Sleek SaaS Wizard Breadcrumbs)
    # --------------------------------------------------------------------------
    step_num = st.session_state.get("wizard_step", 1)
    st.progress(step_num / 4.0)
    
    step_cols = st.columns(4)
    steps_meta = [
        ("1. Ingestion Source", 1),
        ("2. Health & Preview", 2),
        ("3. Auto-Mapping & Engine", 3),
        ("4. Insights & Exports", 4)
    ]
    for idx, (title, s_num) in enumerate(steps_meta):
        with step_cols[idx]:
            if step_num == s_num:
                st.markdown(f"**🔷 {title}** *(Active)*")
            elif step_num > s_num:
                st.markdown(f"**✅ {title}**")
            else:
                st.caption(f"⚪ {title}")
                
    st.divider()
    
    # ==========================================================================
    # STAGE 1: Choose Input Method
    # ==========================================================================
    if st.session_state["wizard_step"] == 1:
        st.subheader("Step 1: Choose Your Data Input Method")
        st.markdown(
            "Select how you would like to provide your transaction data. "
            "You can upload a file, paste copied table rows, enter rows manually, or load pre-packaged sample data."
        )
        
        input_method = st.radio(
            "Select Input Source:",
            options=[
                "📁 Upload a File (CSV, Excel XLSX/XLS, TSV, TXT, JSON, JSONL, Parquet, ZIP)",
                "📋 Paste Tabular Text (Copied from Excel or CSV)",
                "✍️ Enter Data Manually (Editable spreadsheet table)",
                "🧪 Use Included Sample Dataset (Instant one-click demo)",
                "📥 Download CSV Template (Blank template with standard headers)"
            ],
            index=0
        )
        
        parsed_df = None
        parsed_meta = {}
        error_msg = None
        
        # ----------------------------------------------------------------------
        # A. File Upload
        # ----------------------------------------------------------------------
        if input_method.startswith("📁"):
            st.markdown("##### Upload File")
            st.caption(f"Supported formats: `.csv`, `.xlsx`, `.xls`, `.tsv`, `.txt`, `.json`, `.jsonl`, `.parquet`, `.zip`. Maximum file size: **{settings.MAX_UPLOAD_SIZE_MB} MB**.")
            
            uploaded_file = st.file_uploader(
                "Drag and drop file here or click to browse:",
                type=["csv", "xlsx", "xls", "tsv", "txt", "json", "jsonl", "ndjson", "parquet", "zip"],
                help="Safe in-memory processing. Your data remains strictly local on this computer."
            )
            
            if uploaded_file is not None:
                fn_lower = uploaded_file.name.lower()
                
                # Check for ZIP archive
                if fn_lower.endswith(".zip"):
                    try:
                        zip_bytes = uploaded_file.read()
                        uploaded_file.seek(0)
                        members = inspect_zip_archive(zip_bytes)
                        if not members:
                            error_msg = "No eligible data files (.csv, .xlsx, .json, .parquet) found in the ZIP archive."
                        else:
                            selected_member = st.selectbox("Select file inside ZIP to extract and analyze:", members)
                            ext_bytes, chosen_fn = extract_zip_member(zip_bytes, selected_member)
                            parsed_df, parsed_meta, error_msg = parse_tabular_data(ext_bytes, filename=chosen_fn)
                    except Exception as e:
                        error_msg = f"ZIP extraction failed: {str(e)}"
                elif fn_lower.endswith((".xlsx", ".xls")):
                    # Inspect Excel sheets
                    try:
                        xl = pd.ExcelFile(uploaded_file)
                        sheet_choice = 0
                        if len(xl.sheet_names) > 1:
                            sheet_choice = st.selectbox("Select Excel Worksheet:", xl.sheet_names)
                        uploaded_file.seek(0)
                        parsed_df, parsed_meta, error_msg = parse_tabular_data(uploaded_file, filename=uploaded_file.name, sheet_name=sheet_choice)
                    except Exception as e:
                        error_msg = f"Excel reading failed: {str(e)}"
                else:
                    parsed_df, parsed_meta, error_msg = parse_tabular_data(uploaded_file, filename=uploaded_file.name)
                    
        # ----------------------------------------------------------------------
        # B. Paste Data
        # ----------------------------------------------------------------------
        elif input_method.startswith("📋"):
            st.markdown("##### Paste Tabular Text")
            st.caption("Paste comma-separated, tab-separated, or rows copied directly from an Excel / Google spreadsheet.")
            
            pasted_text = st.text_area(
                "Paste transactions here:",
                height=220,
                placeholder="InvoiceNo\tStockCode\tDescription\tQuantity\tInvoiceDate\tUnitPrice\tCustomerID\tCountry\n536365\t85123A\tWHITE HANGING HEART\t6\t01-12-2010 08:26\t2.55\t17850\tUnited Kingdom"
            )
            if pasted_text.strip():
                parsed_df, parsed_meta, error_msg = parse_pasted_text(pasted_text)
                
        # ----------------------------------------------------------------------
        # C. Enter Data Manually
        # ----------------------------------------------------------------------
        elif input_method.startswith("✍️"):
            st.markdown("##### Manual Data Entry Table")
            st.caption("Add, edit, and delete rows interactively. You only need to fill product, quantity, and unit price for revenue analysis.")
            
            initial_data = pd.DataFrame([
                {"InvoiceNo": "INV-1001", "StockCode": "ITEM-A", "Description": "Wireless Optical Mouse", "Quantity": "2", "InvoiceDate": "15-10-2023", "UnitPrice": "499.00", "CustomerID": "CUST-01", "Country": "India"},
                {"InvoiceNo": "INV-1002", "StockCode": "ITEM-B", "Description": "Mechanical Keyboard RGB", "Quantity": "1", "InvoiceDate": "16-10-2023", "UnitPrice": "2499.00", "CustomerID": "CUST-02", "Country": "India"},
                {"InvoiceNo": "INV-1003", "StockCode": "ITEM-C", "Description": "USB-C Fast Charging Cable", "Quantity": "5", "InvoiceDate": "18-10-2023", "UnitPrice": "199.00", "CustomerID": "CUST-01", "Country": "India"},
                {"InvoiceNo": "INV-1004", "StockCode": "ITEM-D", "Description": "Laptop Stand Ergonomic", "Quantity": "1", "InvoiceDate": "20-10-2023", "UnitPrice": "1299.00", "CustomerID": "CUST-03", "Country": "India"},
                {"InvoiceNo": "CINV-1005", "StockCode": "ITEM-A", "Description": "Wireless Optical Mouse (Returned)", "Quantity": "-1", "InvoiceDate": "22-10-2023", "UnitPrice": "499.00", "CustomerID": "CUST-01", "Country": "India"}
            ])
            
            edited_df = st.data_editor(
                initial_data,
                num_rows="dynamic",
                use_container_width=True,
                key="manual_editor"
            )
            
            c_m1, c_m2 = st.columns([1, 3])
            with c_m1:
                if st.button("Use Entered Table Data", type="primary"):
                    if edited_df.empty:
                        error_msg = "Entered table has no records."
                    else:
                        parsed_df = edited_df.copy()
                        parsed_meta = {
                            "filename": "manually_entered_data.csv",
                            "format": "Manual Spreadsheet Entry",
                            "rows": len(parsed_df),
                            "columns": len(parsed_df.columns)
                        }
                        
        # ----------------------------------------------------------------------
        # D. Sample Data
        # ----------------------------------------------------------------------
        elif input_method.startswith("🧪"):
            st.markdown("##### Pre-Packaged Sample Data")
            st.caption("Use the included e-commerce retail dataset to evaluate dashboard charts immediately.")
            
            sample_type = st.radio(
                "Choose sample scale:",
                ["Lightweight Validation Sample (sample_retail.csv - Fast)", "Canonical UCI Online Retail (OnlineRetail.csv - 541k Rows)"],
                index=0
            )
            
            target_path = settings.SAMPLE_RAW_FILE if "sample_retail.csv" in sample_type else settings.DEFAULT_RAW_FILE
            
            if st.button("Load Selected Sample Data", type="primary"):
                if target_path.exists():
                    try:
                        parsed_df = pd.read_csv(target_path, nrows=5000 if "sample_retail" in target_path.name else 25000, dtype=str)
                        parsed_meta = {
                            "filename": target_path.name,
                            "format": "Canonical UCI Sample",
                            "rows": len(parsed_df),
                            "columns": len(parsed_df.columns),
                            "source_path": str(target_path)
                        }
                        st.session_state["active_dataset_type"] = "sample"
                        st.session_state["dataset_source_currency"] = "GBP"
                    except Exception as e:
                        error_msg = f"Failed to load sample data: {str(e)}"
                else:
                    error_msg = f"Sample file not found at {target_path}."
                    
        # ----------------------------------------------------------------------
        # E. Download Template
        # ----------------------------------------------------------------------
        else:
            st.markdown("##### Download Blank CSV Template")
            st.caption("Download our standardized template with example headers and sample rows to format your data easily.")
            st.download_button(
                label="📥 Download salespulse_template.csv",
                data=get_csv_template(),
                file_name="salespulse_template.csv",
                mime="text/csv",
                type="primary"
            )
            st.markdown(
                "**Template Instructions:**\n"
                "- Required for sales analytics: `Description` (or Product Name), `Quantity`, and `UnitPrice`.\n"
                "- Optional for time trends: `InvoiceDate` (formats like `DD-MM-YYYY` or `YYYY-MM-DD`).\n"
                "- Optional for customer loyalty: `CustomerID`.\n"
                "- Optional for regional breakdown: `Country`."
            )
            
        # Display errors or advance to Step 2
        if error_msg:
            st.error(f"❌ {error_msg}")
        elif parsed_df is not None and not parsed_df.empty:
            st.session_state["imported_df"] = parsed_df
            st.session_state["imported_meta"] = parsed_meta
            
            st.success(f" Successfully loaded **{len(parsed_df):,}** rows and **{len(parsed_df.columns)}** columns from `{parsed_meta.get('filename')}`.")
            
            if st.button("Continue to Step 2: Preview & Validate ➔", type="primary"):
                st.session_state["wizard_step"] = 2
                st.rerun()

    # ==========================================================================
    # STAGE 2: Preview and Validate
    # ==========================================================================
    elif st.session_state["wizard_step"] == 2:
        df = st.session_state.get("imported_df")
        meta = st.session_state.get("imported_meta", {})
        
        if df is None or df.empty:
            st.warning("⚠️ No data loaded yet. Please return to Step 1.")
            if st.button("⬅️ Back to Step 1"):
                st.session_state["wizard_step"] = 1
                st.rerun()
            return
            
        st.subheader("Step 2: Preview & Validate Dataset")
        st.caption("Inspect the first records, check inferred data types, examine missing values, and verify dataset health.")
        
        # Summary Row Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_kpi_card("Total Rows Found", format_number(len(df)), subtitle=meta.get("filename", "Imported Dataset"))
        with c2:
            render_kpi_card("Columns Identified", f"{len(df.columns)} Columns", subtitle=meta.get("format", "Tabular"))
        with c3:
            null_count = df.isna().sum().sum()
            render_kpi_card("Total Null Values", format_number(null_count), subtitle="Across all columns")
        with c4:
            dup_count = df.duplicated().sum()
            render_kpi_card("Duplicate Rows", format_number(dup_count), subtitle="Exact identical lines")
            
        st.divider()
        
        # Plain-English Summary Messages
        raw_cols = df.columns.tolist()
        detected_mapping, missing_reqs = detect_schema_mapping(raw_cols)
        analysis_caps = check_available_analyses(df)
        
        st.markdown("##### 📋 Plain-English Dataset Health Summary")
        with st.container(border=True):
            st.write(f"- We found **{len(df):,} rows** in your dataset (`{meta.get('filename')}`).")
            if analysis_caps["revenue_analysis"]:
                st.write("- ✅ We identified the product price and quantity/sales columns for **Revenue Analytics**.")
            else:
                st.write("- ⚠️ We could not find unit price and quantity columns. Revenue calculations will be restricted.")
                
            if analysis_caps["time_series_analysis"]:
                st.write("- ✅ We identified transaction dates for **Temporal Trends & Forecasting**.")
            else:
                st.write("- ℹ️ Order date column was not identified. Monthly/daily trends will be unavailable.")
                
            if analysis_caps["customer_analysis"]:
                st.write("- ✅ Customer identifiers found. **Customer Loyalty & Retention** analysis is active.")
            else:
                st.write("- ℹ️ We could not identify a Customer ID. Transactions will be analyzed as guest checkouts.")
                
            if analysis_caps["regional_analysis"]:
                st.write("- ✅ Country or market location detected for **Regional Analytics**.")
            else:
                st.write("- ℹ️ Geographic country field is not present. Regional mapping will be skipped.")
                
        st.divider()
        st.markdown("##### 📄 Data Preview (First 15 Records):")
        st.dataframe(df.head(15), use_container_width=True)
        
        # Navigation buttons
        nav_col1, nav_col2 = st.columns([1, 4])
        with nav_col1:
            if st.button("⬅️ Back to Step 1"):
                st.session_state["wizard_step"] = 1
                st.rerun()
        with nav_col2:
            if st.button("Continue to Step 3: Match Columns & Analyze ➔", type="primary"):
                st.session_state["wizard_step"] = 3
                st.rerun()

    # ==========================================================================
    # STAGE 3: Match Columns & Analyze
    # ==========================================================================
    elif st.session_state["wizard_step"] == 3:
        df = st.session_state.get("imported_df")
        meta = st.session_state.get("imported_meta", {})
        
        if df is None or df.empty:
            st.warning("⚠️ No data loaded yet. Please return to Step 1.")
            if st.button("⬅️ Back to Step 1"):
                st.session_state["wizard_step"] = 1
                st.rerun()
            return
            
        st.subheader("Step 3: Match Columns & Launch Analytics")
        st.markdown(
            "SalesPulse automatically maps recognized column headers using intelligent alias matching. "
            "You can review or override any mapping below, confirm your source currency, and execute the analytical engine."
        )
        
        raw_cols = df.columns.tolist()
        auto_mapping, missing_reqs = detect_schema_mapping(raw_cols)
        
        # Inverted auto mapping (target -> source)
        target_to_source = {v: k for k, v in auto_mapping.items()}
        
        user_mapping = {}
        
        with st.container(border=True):
            st.markdown("#### 🧩 Column Mapping Table")
            st.caption("Match your uploaded columns to the standard business fields:")
            
            none_option = "— None / Not in File —"
            col_options = [none_option] + raw_cols
            
            # Display mapping controls for each standard field
            fields_to_map = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "SalesAmount", "CustomerID", "Country"]
            
            for field in fields_to_map:
                field_meta = settings.FIELD_DEFINITIONS.get(field, {})
                label = field_meta.get("label", field)
                req_badge = "**(Required)**" if field_meta.get("required") else "*(Optional)*"
                desc = field_meta.get("description", "")
                
                # Determine default selected index
                default_matched_src = target_to_source.get(field)
                default_idx = col_options.index(default_matched_src) if default_matched_src in col_options else 0
                
                c_lbl, c_sel, c_ex = st.columns([1.5, 1.5, 1.5])
                with c_lbl:
                    st.markdown(f"**{label}** {req_badge}")
                    st.caption(desc)
                with c_sel:
                    selected_col = st.selectbox(
                        f"Source Column for {field}",
                        col_options,
                        index=default_idx,
                        key=f"map_sel_{field}",
                        label_visibility="collapsed"
                    )
                    if selected_col != none_option:
                        user_mapping[selected_col] = field
                with c_ex:
                    if selected_col != none_option and selected_col in df.columns:
                        sample_val = str(df[selected_col].dropna().iloc[0]) if not df[selected_col].dropna().empty else "None"
                        st.text(f"Sample: {sample_val[:25]}")
                    else:
                        st.caption("Not mapped")
                        
        st.session_state["confirmed_mapping"] = user_mapping
        
        # Source Currency Selection
        st.divider()
        st.markdown("#### 💱 Dataset Currency Confirmation")
        st.caption("Confirm the native currency of the prices in this dataset. Default presentation currency is Indian Rupees (₹).")
        
        curr_col1, curr_col2 = st.columns([1.5, 2])
        with curr_col1:
            detected_curr = st.selectbox(
                "Source Currency of Uploaded Prices:",
                options=["GBP (£) - British Pounds (Canonical)", "INR (₹) - Indian Rupees", "USD ($) - US Dollars", "Other / Native"],
                index=0 if st.session_state.get("dataset_source_currency") == "GBP" else 1
            )
            src_code = "GBP" if "GBP" in detected_curr else ("INR" if "INR" in detected_curr else "USD")
            st.session_state["dataset_source_currency"] = src_code
            
        with curr_col2:
            if src_code == "GBP":
                st.info(f"💡 Values will be dynamically converted to **INR (₹)** at the documented reference exchange rate (**₹{rate:.2f} per £1**).")
            elif src_code == "INR":
                st.success("✅ Dataset is already in Indian Rupees (**₹**). Values will be presented directly without exchange rate multiplication.")
            else:
                st.caption(f"Native currency: {src_code}. Displayed using active currency symbol.")
                
        st.divider()
        
        # Execution Controls
        st.markdown("#### ⚡ Launch Analytics Engine")
        st.caption("Calculates sales KPIs, product rankings, temporal patterns, and customer cohorts using PySpark & Spark SQL.")
        
        # Check minimum requirements (Quantity + UnitPrice OR SalesAmount)
        mapped_targets = set(user_mapping.values())
        has_min_rev = ("Quantity" in mapped_targets and "UnitPrice" in mapped_targets) or ("SalesAmount" in mapped_targets)
        
        if not has_min_rev:
            st.warning("⚠️ To run the sales analytics engine, please map either **(Quantity + Unit Price)** or **Total Sales Amount** above.")
            
        exec_col1, exec_col2 = st.columns([1.5, 1])
        with exec_col1:
            run_btn = st.button("⚡ Analyze My Data", type="primary", disabled=(not has_min_rev or st.session_state["is_processing"]))
            
        if run_btn:
            st.session_state["is_processing"] = True
            with st.status("Executing Big Data Analytics Pipeline...", expanded=True) as status_box:
                try:
                    st.write("1️⃣ Normalizing dataset headers and applying field mappings...")
                    norm_df, norm_summary = normalize_pandas_dataframe(df, user_mapping)
                    time.sleep(0.4)
                    
                    st.write("2️⃣ Segregating returns and calculating line-item sales totals...")
                    # Save normalized temporary CSV in RAW_DATA_DIR for Spark ingestion
                    temp_raw_file = settings.RAW_DATA_DIR / "active_processed_input.csv"
                    norm_df.to_csv(temp_raw_file, index=False)
                    time.sleep(0.4)
                    
                    st.write("3️⃣ Initializing PySpark engine and executing distributed SQL aggregations...")
                    # Run the end-to-end Big Data pipeline
                    pipeline_res = run_pipeline(input_file_path=temp_raw_file)
                    
                    st.write("4️⃣ Persisting analytical summaries and generating data quality reports...")
                    time.sleep(0.4)
                    
                    status_box.update(label="✅ Analytics Pipeline Completed Successfully!", state="complete", expanded=False)
                    st.session_state["is_processing"] = False
                    st.session_state["wizard_step"] = 4
                    st.rerun()
                except Exception as e:
                    status_box.update(label="❌ Pipeline Execution Failed", state="error", expanded=True)
                    st.error(f"Error during analytics processing: {str(e)}")
                    st.session_state["is_processing"] = False
                    
        # Navigation
        st.write("")
        if st.button("⬅️ Back to Step 2"):
            st.session_state["wizard_step"] = 2
            st.rerun()

    # ==========================================================================
    # STAGE 4: Results and Export
    # ==========================================================================
    elif st.session_state["wizard_step"] == 4:
        st.subheader("Step 4: Processing Results & Analytics Access")
        st.caption("Your data has been processed by the Big Data analytics pipeline. Review results and access your dashboard.")
        
        meta = load_pipeline_metadata()
        quality_report = load_data_quality_report()
        kpis = load_kpis()
        
        if meta and kpis:
            st.success("🎉 **Data Processing Complete!** Your dataset has been transformed and aggregated.")
            
            # KPI Results Row
            r1, r2, r3, r4, r5 = st.columns(5)
            with r1:
                render_kpi_card("Total Ingested", format_number(meta.get("total_records_ingested")), subtitle="Transaction lines")
            with r2:
                render_kpi_card("Accepted Sales", format_number(meta.get("clean_sales_records_count")), subtitle="Valid revenue lines")
            with r3:
                render_kpi_card("Gross Revenue", format_currency(kpis.get("gross_revenue"), compact=True))
            with r4:
                render_kpi_card("Net Revenue", format_currency(kpis.get("net_revenue"), compact=True))
            with r5:
                render_kpi_card("Execution Time", f"{meta.get('timings_seconds', {}).get('total_pipeline_duration', 0.0):.2f}s", subtitle=f"{meta.get('throughput_rows_per_second', 0):,.1f} rows/s")
                
            st.divider()
            
            # Prominent Action: View My Dashboard
            dash_col1, dash_col2 = st.columns([1.5, 2.5])
            with dash_col1:
                if st.button("💼 View My Dashboard ➔", type="primary", use_container_width=True):
                    st.session_state["nav_selection"] = "💼 Sales Overview"
                    st.rerun()
            with dash_col2:
                st.caption("Open the interactive commercial sales dashboard to explore revenue progression, product rankings, and customer insights.")
                
            st.divider()
            
            # Record Accounting & Exclusion Audit Table
            st.markdown("##### 🛡️ Record Accounting & Quality Audit")
            rec_accounting = [
                {"Category": "Total Input Lines", "Count": format_number(meta.get("total_records_ingested")), "Status": "Ingested", "Notes": "Raw records parsed from selected source"},
                {"Category": "Accepted Commercial Sales", "Count": format_number(meta.get("clean_sales_records_count")), "Status": "Included in Analytics", "Notes": "Passed all business validations"},
                {"Category": "Return / Cancellation Rows", "Count": format_number(meta.get("returns_records_count")), "Status": "Segregated", "Notes": "Invoices starting with 'C' or negative quantities"},
                {"Category": "Excluded Incomplete Records", "Count": format_number(meta.get("excluded_records_count")), "Status": "Excluded", "Notes": "Missing SKU or invalid zero/negative unit prices"}
            ]
            st.dataframe(pd.DataFrame(rec_accounting), use_container_width=True)
            
            st.divider()
            
            # Data Exports Section
            st.markdown("##### 📥 Download Processed Results & Reports")
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                monthly_csv_path = settings.ANALYTICS_DATA_DIR / "monthly_sales_trends.csv"
                if monthly_csv_path.exists():
                    with open(monthly_csv_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="📥 Monthly Trends (CSV)",
                            data=f.read(),
                            file_name="salespulse_monthly_trends.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
            with col_exp2:
                kpis_json_path = settings.ANALYTICS_DATA_DIR / "kpis_summary.json"
                if kpis_json_path.exists():
                    with open(kpis_json_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="📥 Executive KPIs (JSON)",
                            data=f.read(),
                            file_name="salespulse_kpis_summary.json",
                            mime="application/json",
                            use_container_width=True
                        )
                        
            with col_exp3:
                quality_json_path = settings.REPORTS_DIR / "data_quality_report.json"
                if quality_json_path.exists():
                    with open(quality_json_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="📥 Quality Audit Report (JSON)",
                            data=f.read(),
                            file_name="salespulse_data_quality_report.json",
                            mime="application/json",
                            use_container_width=True
                        )
        else:
            st.info("No analytics results recorded yet. Return to Step 3 and click Analyze My Data.")
            
        st.write("")
        if st.button("🔄 Import or Process Another Dataset"):
            st.session_state["wizard_step"] = 1
            st.session_state["imported_df"] = None
            st.session_state["imported_meta"] = {}
            st.rerun()


if __name__ == "__main__":
    render_page()
