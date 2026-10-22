"""
SalesPulse Analytics - Scalability and Performance Benchmarking Module
Conducts controlled Big Data scalability experiments across varying dataset sizes.
Clearly labels synthetic scaling datasets to separate experimental benchmarks from real data.
"""

import time
from typing import List, Dict, Any, Optional
import pandas as pd
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from src.processing.transformer import transform_and_clean_data
from src.analytics.aggregations import register_spark_views, get_overall_kpis


def generate_synthetic_benchmark_dataset(
    spark: SparkSession,
    sample_df: DataFrame,
    target_row_count: int
) -> DataFrame:
    """
    Synthesizes an expanded transactional dataset of specified size for controlled
    benchmarking experiments. Clearly prefixes invoices to avoid polluting real audits.
    """
    initial_count = sample_df.count()
    if initial_count == 0:
        raise ValueError("Sample DataFrame cannot be empty for synthetic generation.")
        
    repeat_times = max(1, int(target_row_count / initial_count) + 1)
    
    # Union copies to reach target scale
    synthetic_df = sample_df
    for _ in range(repeat_times - 1):
        synthetic_df = synthetic_df.union(sample_df)
        
    synthetic_df = synthetic_df.limit(target_row_count)
    
    # Tag rows distinctly as synthetic experiment data
    synthetic_df = (
        synthetic_df
        .withColumn(
            "InvoiceNo",
            F.concat(F.lit("SYN-"), F.monotonically_increasing_id())
        )
    )
    return synthetic_df


def run_scalability_benchmark(
    spark: SparkSession,
    base_raw_df: DataFrame,
    dataset_sizes: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Executes controlled scalability tests measuring execution time and throughput (rows/sec)
    across progressive dataset dimensions.
    
    Args:
        spark: Active SparkSession.
        base_raw_df: Baseline raw DataFrame.
        dataset_sizes: List of row counts to evaluate (default: [10000, 50000, 100000]).
        
    Returns:
        Pandas DataFrame detailing execution duration, throughput, and scalability metrics.
    """
    if dataset_sizes is None:
        dataset_sizes = [10000, 25000, 50000, 100000]
        
    results = []
    
    for size in dataset_sizes:
        # 1. Synthesize target batch
        t0 = time.time()
        bench_df = generate_synthetic_benchmark_dataset(spark, base_raw_df, size)
        actual_rows = bench_df.count()
        synth_duration = round(time.time() - t0, 3)
        
        # 2. Measure Transformation Pipeline
        t1 = time.time()
        master_df, sales_df, returns_df = transform_and_clean_data(bench_df)
        # Force evaluation via count action
        valid_sales_count = sales_df.count()
        transform_duration = round(time.time() - t1, 3)
        
        # 3. Measure Spark SQL Aggregations
        t2 = time.time()
        register_spark_views(spark, master_df, sales_df, returns_df)
        kpis = get_overall_kpis(spark)
        aggregation_duration = round(time.time() - t2, 3)
        
        total_time = round(transform_duration + aggregation_duration, 3)
        # Safe throughput
        throughput = round(actual_rows / total_time, 1) if total_time > 0 else 0.0
        
        results.append({
            "DatasetType": "Synthetic Scalability Benchmark",
            "TargetSize": size,
            "ActualRows": actual_rows,
            "ValidSalesRows": valid_sales_count,
            "TransformTimeSec": transform_duration,
            "AggregationTimeSec": aggregation_duration,
            "TotalPipelineTimeSec": total_time,
            "ThroughputRowsPerSec": throughput,
            "ExecutionEngine": "Apache Spark (Local Mode)"
        })
        
    return pd.DataFrame(results)
