"""
SalesPulse Analytics - System Performance & Benchmarking Page
Inspects Big Data pipeline execution metrics, Spark SQL throughput, and runs
controlled scalability experiments across varying synthetic dataset scales.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from config import settings
from src.dashboard.utils import (
    load_pipeline_metadata,
    format_number,
    render_kpi_card,
    apply_chart_theme,
    CHART_COLORS
)
from src.processing.spark_session import get_spark_session
from src.ingestion.loader import load_raw_data
from src.analytics.benchmark import run_scalability_benchmark


def render_page():
    st.title("⚡ Big Data & Cloud System Performance")
    st.caption("Monitor pipeline throughput, stage latency, and run controlled scalability benchmarks.")
    
    metadata = load_pipeline_metadata()
    
    tab1, tab2 = st.tabs(["⏱️ Production Pipeline Latency", "📊 Scalability Experiments (Synthetic Benchmarks)"])
    
    # --------------------------------------------------------------------------
    # Tab 1: Production Pipeline Latency
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Actual PySpark Pipeline Metrics")
        
        if metadata:
            timings = metadata.get("timings_seconds", {})
            total_duration = timings.get("total_pipeline_duration", 0.0)
            throughput = metadata.get("throughput_rows_per_second", 0.0)
            rows = metadata.get("total_records_ingested", 0)
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                render_kpi_card("Total Ingested", format_number(rows), subtitle=metadata.get("dataset_file"))
            with c2:
                render_kpi_card("Pipeline Duration", f"{total_duration:.2f}s", subtitle="End-to-end execution")
            with c3:
                render_kpi_card("Throughput", f"{throughput:,.1f}", subtitle="Rows per second")
            with c4:
                render_kpi_card("Spark Master", metadata.get("spark_master", "local[2]"), subtitle="Local CPU Cores Allocated")
                
            st.divider()
            st.markdown("##### ⏱️ Execution Latency by Pipeline Stage")
            stage_data = [
                {"Stage": "1. Data Ingestion & Schema Binding", "Seconds": timings.get("ingestion", 0.0)},
                {"Stage": "2. Data Quality Audit & Rules Check", "Seconds": timings.get("data_quality_audit", 0.0)},
                {"Stage": "3. PySpark Transformations & Cleaning", "Seconds": timings.get("pyspark_transformation", 0.0)},
                {"Stage": "4. Spark SQL Aggregations & Storage", "Seconds": timings.get("spark_sql_aggregations", 0.0)}
            ]
            stage_df = pd.DataFrame(stage_data)
            
            fig_stages = px.bar(
                stage_df,
                x="Seconds",
                y="Stage",
                orientation="h",
                text="Seconds",
                color="Seconds",
                color_continuous_scale="Teal",
                title="Duration by Pipeline Stage (Seconds)"
            )
            fig_stages.update_layout(
                yaxis=dict(autorange="reversed", automargin=True, title=""),
                xaxis=dict(automargin=True, title="Seconds"),
                coloraxis_showscale=False,
                margin=dict(l=20, r=40, t=60, b=40)
            )
            fig_stages.update_traces(texttemplate="%{text:.2f}s", textposition="outside")
            apply_chart_theme(fig_stages)
            st.plotly_chart(fig_stages, width="stretch")
            
            st.info(
                "💡 **Big Data Architectural Note for Viva:** In this local development profile, "
                "PySpark runs on `local[2]` (2 worker threads in JVM). In a cloud deployment (AWS EMR or EC2 cluster), "
                "the exact same PySpark codebase runs distributed across an arbitrary number of worker nodes "
                "without requiring any code modifications."
            )
        else:
            st.info("Pipeline metadata not yet recorded. Please run the pipeline from the Data Management page.")
            
    # --------------------------------------------------------------------------
    # Tab 2: Scalability Experiments (Synthetic Benchmarks)
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Controlled Scalability Benchmark")
        st.caption(
            "Conduct controlled scalability experiments evaluating PySpark throughput and latency "
            "as data volume scales. *Note: Benchmark datasets are clearly labeled synthetic records generated for testing scalability.*"
        )
        
        with st.container(border=True):
            bench_sizes = st.multiselect(
                "Select Benchmark Dataset Sizes (Rows):",
                [5000, 10000, 25000, 50000, 100000],
                default=[10000, 25000, 50000]
            )
            run_bench_btn = st.button("🚀 Run Scalability Benchmark Experiments", type="primary")
            
        if run_bench_btn:
            if not bench_sizes:
                st.warning("Please select at least one dataset size.")
            else:
                with st.spinner("Executing Spark benchmarking stages across synthetic workloads..."):
                    try:
                        spark = get_spark_session()
                        base_df = load_raw_data(settings.SAMPLE_RAW_FILE, spark=spark)
                        bench_results_df = run_scalability_benchmark(spark, base_df, dataset_sizes=bench_sizes)
                        
                        st.session_state["bench_results"] = bench_results_df
                        st.success(" Benchmark experiments completed successfully!")
                    except Exception as e:
                        st.error(f"Benchmark failed: {str(e)}")
                        
        if "bench_results" in st.session_state:
            res_df = st.session_state["bench_results"]
            
            st.divider()
            st.markdown("##### 📊 Benchmark Workload Results")
            st.dataframe(
                res_df.style.format({
                    "TargetSize": "{:,}",
                    "ActualRows": "{:,}",
                    "ValidSalesRows": "{:,}",
                    "TransformTimeSec": "{:.3f}s",
                    "AggregationTimeSec": "{:.3f}s",
                    "TotalPipelineTimeSec": "{:.3f}s",
                    "ThroughputRowsPerSec": "{:,.1f} rows/s"
                }),
                width="stretch"
            )
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                fig_latency = px.line(
                    res_df,
                    x="ActualRows",
                    y="TotalPipelineTimeSec",
                    markers=True,
                    title="Total Pipeline Latency vs Dataset Volume",
                    labels={"ActualRows": "Dataset Records (Synthetic)", "TotalPipelineTimeSec": "Total Time (s)"}
                )
                fig_latency.update_traces(line_color=CHART_COLORS["primary"], line_width=2.5)
                fig_latency.update_layout(
                    yaxis=dict(automargin=True),
                    xaxis=dict(automargin=True),
                    margin=dict(l=50, r=30, t=60, b=40)
                )
                apply_chart_theme(fig_latency)
                st.plotly_chart(fig_latency, width="stretch")
                
            with col_b2:
                fig_tp = px.bar(
                    res_df,
                    x="ActualRows",
                    y="ThroughputRowsPerSec",
                    color="ThroughputRowsPerSec",
                    color_continuous_scale="Viridis",
                    title="Processing Throughput (Rows/sec)",
                    labels={"ActualRows": "Dataset Records (Synthetic)", "ThroughputRowsPerSec": "Rows/sec"}
                )
                fig_tp.update_layout(
                    coloraxis_showscale=False,
                    yaxis=dict(automargin=True),
                    xaxis=dict(automargin=True),
                    margin=dict(l=50, r=30, t=60, b=40)
                )
                apply_chart_theme(fig_tp)
                st.plotly_chart(fig_tp, width="stretch")


if __name__ == "__main__":
    render_page()
