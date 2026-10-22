"""
SalesPulse Analytics - Data Ingestion Module
Handles loading of e-commerce transaction data from CSV and XLSX formats into Apache Spark.
Includes automated timestamp normalization across varying date representations.
"""

import os
from pathlib import Path
from typing import Optional, Union
import pandas as pd
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
    TimestampType
)

from config import settings
from src.processing.spark_session import get_spark_session


RAW_SCHEMA = StructType([
    StructField("InvoiceNo", StringType(), True),
    StructField("StockCode", StringType(), True),
    StructField("Description", StringType(), True),
    StructField("Quantity", StringType(), True),  # Read as string first to validate safely
    StructField("InvoiceDate", StringType(), True),
    StructField("UnitPrice", StringType(), True),
    StructField("CustomerID", StringType(), True),
    StructField("Country", StringType(), True),
])


def get_download_instructions() -> str:
    """Returns step-by-step instructions for downloading the canonical dataset."""
    return (
        "UCI Online Retail Dataset Instructions:\n"
        "1. Visit: https://archive.ics.uci.edu/dataset/352/online+retail\n"
        "2. Download 'Online Retail.xlsx' or 'Online Retail.csv'.\n"
        f"3. Place the file at: {settings.RAW_DATA_DIR / 'OnlineRetail.csv'} (or upload via the SalesPulse dashboard).\n"
        "4. The dataset contains 541,909 transactions from a UK-based online retail company between 01/12/2010 and 09/12/2011."
    )


def load_raw_data(
    file_path: Union[str, Path],
    spark: Optional[SparkSession] = None,
    limit: Optional[int] = None
) -> DataFrame:
    """
    Loads raw transaction data from CSV or XLSX into a PySpark DataFrame.
    
    Args:
        file_path: Path to the raw CSV or XLSX data file.
        spark: Active SparkSession; if None, an instance is initialized.
        limit: Optional maximum number of rows to ingest.
        
    Returns:
        PySpark DataFrame containing the raw transactions.
        
    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If an unsupported file extension is provided.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path_obj}.\n{get_download_instructions()}"
        )
        
    if spark is None:
        spark = get_spark_session()
        
    suffix = path_obj.suffix.lower()
    
    if suffix == ".csv":
        df = (
            spark.read
            .option("header", "true")
            .option("mode", "PERMISSIVE")
            .option("quote", "\"")
            .option("escape", "\"")
            .schema(RAW_SCHEMA)
            .csv(str(path_obj))
        )
    elif suffix in (".xlsx", ".xls"):
        # For Excel files, read via Pandas and transfer to PySpark
        pdf = pd.read_excel(path_obj, nrows=limit)
        # Ensure all columns are stringified for uniform raw representation
        for col in pdf.columns:
            pdf[col] = pdf[col].astype(str)
        df = spark.createDataFrame(pdf, schema=RAW_SCHEMA)
    else:
        raise ValueError(f"Unsupported file format '{suffix}'. Supported: .csv, .xlsx, .xls")
        
    if limit is not None and suffix == ".csv":
        df = df.limit(limit)
        
    return df


def parse_invoice_timestamp(df: DataFrame, date_col: str = "InvoiceDate") -> DataFrame:
    """
    Parses heterogeneous string dates into a unified Spark TimestampType and DateType.
    Supports formats including 'dd-MM-yyyy HH:mm', 'yyyy-MM-dd HH:mm:ss', etc.
    """
    # Build a coalesce chain over the supported date patterns
    timestamp_exprs = [
        F.to_timestamp(F.col(date_col), fmt) for fmt in settings.SUPPORTED_DATE_FORMATS
    ]
    
    # Fallback to standard Spark default parser if custom patterns do not match
    timestamp_exprs.append(F.to_timestamp(F.col(date_col)))
    
    df_parsed = df.withColumn("InvoiceTimestamp", F.coalesce(*timestamp_exprs))
    df_parsed = df_parsed.withColumn("InvoiceDateOnly", F.to_date(F.col("InvoiceTimestamp")))
    return df_parsed
