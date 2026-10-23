"""
SalesPulse Analytics - Universal Data Ingestion Module
Supports diverse enterprise data formats: CSV, TSV, TXT, Excel (XLSX/XLS),
JSON, JSONL, Parquet, pasted tabular text, and safe ZIP archive inspection.
Feeds seamlessly into Apache Spark (PySpark) or Pandas analytical pipelines.
"""

import os
import io
import json
import zipfile
from pathlib import Path
from typing import Optional, Union, Dict, List, Tuple, Any
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
        f"3. Place the file at: {settings.RAW_DATA_DIR / 'OnlineRetail.csv'} (or upload via SalesPulse dashboard).\n"
        "4. The dataset contains 541,909 transactions from a UK-based online retail company between 01/12/2010 and 09/12/2011."
    )


# ------------------------------------------------------------------------------
# Delimiter & Encoding Utilities
# ------------------------------------------------------------------------------
def detect_delimiter(sample_text: str) -> str:
    """
    Intelligently determines the delimiter (comma, tab, semicolon, pipe)
    by counting character frequencies across the first few lines.
    """
    if not sample_text:
        return ","
        
    lines = [line for line in sample_text.splitlines() if line.strip()][:5]
    if not lines:
        return ","
        
    delimiters = [",", "\t", ";", "|"]
    scores = {}
    for d in delimiters:
        counts = [line.count(d) for line in lines]
        # Prefer delimiter with consistent count > 0 across lines
        if len(counts) > 0 and counts[0] > 0 and all(c == counts[0] for c in counts):
            scores[d] = counts[0] * 2  # bonus for perfect consistency
        else:
            scores[d] = sum(counts)
            
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ","


# ------------------------------------------------------------------------------
# Safe ZIP Archive Handling
# ------------------------------------------------------------------------------
def inspect_zip_archive(archive_file: Union[bytes, io.BytesIO, Path, str]) -> List[str]:
    """
    Safely inspects a ZIP archive without extracting to disk, preventing path traversal.
    Returns list of eligible data files inside the archive.
    """
    eligible_extensions = (".csv", ".xlsx", ".xls", ".tsv", ".txt", ".json", ".jsonl", ".parquet")
    valid_members = []
    
    file_obj = io.BytesIO(archive_file) if isinstance(archive_file, bytes) else archive_file
    with zipfile.ZipFile(file_obj, "r") as zf:
        for info in zf.infolist():
            # Security: Prevent Zip Slip / Path Traversal
            filename = info.filename
            if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
                continue
            if not info.is_dir() and any(filename.lower().endswith(ext) for ext in eligible_extensions):
                valid_members.append(filename)
                
    return valid_members


def extract_zip_member(
    archive_file: Union[bytes, io.BytesIO, Path, str],
    member_name: str
) -> Tuple[bytes, str]:
    """
    Safely extracts a single member from a ZIP file into memory, guarding against
    path traversal and zip bombs.
    """
    if ".." in member_name or member_name.startswith("/") or member_name.startswith("\\"):
        raise ValueError(f"Security error: Invalid path traversal in member '{member_name}'")
        
    file_obj = io.BytesIO(archive_file) if isinstance(archive_file, bytes) else archive_file
    with zipfile.ZipFile(file_obj, "r") as zf:
        # Enforce size limit (max 100MB uncompressed)
        info = zf.getinfo(member_name)
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if info.file_size > max_bytes:
            raise ValueError(f"Compressed file exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB.")
        data_bytes = zf.read(member_name)
        
    return data_bytes, member_name


# ------------------------------------------------------------------------------
# Universal Tabular Parsing (Pandas Engine)
# ------------------------------------------------------------------------------
def parse_tabular_data(
    file_or_data: Any,
    filename: str = "uploaded_file.csv",
    sheet_name: Optional[Union[str, int]] = 0,
    delimiter: Optional[str] = None,
    nrows: Optional[int] = None
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any], Optional[str]]:
    """
    Parses any supported tabular data format into a pandas DataFrame.
    Returns:
        (DataFrame, metadata_dict, error_string)
    """
    meta = {
        "filename": filename,
        "format": "UNKNOWN",
        "size_bytes": 0,
        "rows": 0,
        "columns": 0,
        "sheets": []
    }
    
    try:
        # 1. Determine bytes or stream
        if isinstance(file_or_data, bytes):
            buffer = io.BytesIO(file_or_data)
            meta["size_bytes"] = len(file_or_data)
        elif hasattr(file_or_data, "read") and hasattr(file_or_data, "seek"):
            # Streamlit UploadedFile or file-like
            file_or_data.seek(0)
            raw_bytes = file_or_data.read()
            file_or_data.seek(0)
            buffer = io.BytesIO(raw_bytes)
            meta["size_bytes"] = len(raw_bytes)
        elif isinstance(file_or_data, (str, Path)) and os.path.exists(str(file_or_data)):
            path_obj = Path(file_or_data)
            meta["size_bytes"] = path_obj.stat().st_size
            buffer = path_obj
        else:
            return None, meta, "Unsupported data source provided."
            
        # Check size limit
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if meta["size_bytes"] > max_bytes:
            return None, meta, f"File size ({meta['size_bytes'] / (1024*1024):.2f} MB) exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
            
        if meta["size_bytes"] == 0:
            return None, meta, "The selected file is completely empty (0 bytes)."
            
        fn_lower = filename.lower()
        df: Optional[pd.DataFrame] = None
        
        # Format detection and parsing
        if fn_lower.endswith(".csv") or fn_lower.endswith(".tsv") or fn_lower.endswith(".txt"):
            meta["format"] = "CSV/Tabular Text"
            # Read first chunk to detect delimiter and encoding
            if isinstance(buffer, io.BytesIO):
                buffer.seek(0)
                sample_bytes = buffer.read(8192)
                buffer.seek(0)
            else:
                with open(buffer, "rb") as f:
                    sample_bytes = f.read(8192)
                    
            sample_text = ""
            encoding_used = "utf-8"
            for enc in ["utf-8", "latin1", "cp1252"]:
                try:
                    sample_text = sample_bytes.decode(enc)
                    encoding_used = enc
                    break
                except UnicodeDecodeError:
                    continue
                    
            inferred_sep = delimiter or detect_delimiter(sample_text)
            df = pd.read_csv(
                buffer,
                sep=inferred_sep,
                encoding=encoding_used,
                nrows=nrows,
                dtype=str,
                on_bad_lines="skip"
            )
            meta["delimiter"] = inferred_sep
            meta["encoding"] = encoding_used
            
        elif fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls"):
            meta["format"] = "Excel Spreadsheet"
            # Inspect sheet names
            xl = pd.ExcelFile(buffer)
            meta["sheets"] = xl.sheet_names
            target_sheet = sheet_name if sheet_name in xl.sheet_names else 0
            df = pd.read_excel(buffer, sheet_name=target_sheet, nrows=nrows, dtype=str)
            meta["selected_sheet"] = target_sheet
            
        elif fn_lower.endswith(".parquet"):
            meta["format"] = "Apache Parquet"
            df = pd.read_parquet(buffer)
            if nrows:
                df = df.head(nrows)
            for c in df.columns:
                df[c] = df[c].astype(str)
                
        elif fn_lower.endswith(".jsonl") or fn_lower.endswith(".ndjson"):
            meta["format"] = "Line-Delimited JSON (JSONL)"
            df = pd.read_json(buffer, lines=True, nrows=nrows, dtype=False)
            for c in df.columns:
                df[c] = df[c].astype(str)
                
        elif fn_lower.endswith(".json"):
            meta["format"] = "JSON Document"
            df = pd.read_json(buffer, dtype=False)
            if nrows:
                df = df.head(nrows)
            for c in df.columns:
                df[c] = df[c].astype(str)
                
        elif fn_lower.endswith(".zip"):
            meta["format"] = "ZIP Archive"
            members = inspect_zip_archive(buffer)
            meta["zip_members"] = members
            if not members:
                return None, meta, "No eligible data files (.csv, .xlsx, .json, .parquet) found in the ZIP archive."
            # Automatically parse the first member if not specified
            extracted_bytes, chosen_name = extract_zip_member(buffer, members[0])
            return parse_tabular_data(extracted_bytes, filename=chosen_name, nrows=nrows)
        else:
            return None, meta, f"Unsupported file format '{filename}'. Supported: CSV, Excel (XLSX/XLS), TSV, TXT, JSON, JSONL, Parquet, ZIP."
            
        if df is None or df.empty:
            return None, meta, "The file contains valid headers but zero data records."
            
        meta["rows"] = len(df)
        meta["columns"] = len(df.columns)
        return df, meta, None
        
    except Exception as e:
        return None, meta, f"Error parsing data file '{filename}': {str(e)}"


def parse_pasted_text(pasted_text: str) -> Tuple[Optional[pd.DataFrame], Dict[str, Any], Optional[str]]:
    """
    Parses pasted spreadsheet, CSV, or tab-delimited text into a clean DataFrame.
    """
    if not pasted_text or not pasted_text.strip():
        return None, {}, "Pasted text area is empty. Please paste your tabular data."
        
    sep = detect_delimiter(pasted_text)
    try:
        buffer = io.StringIO(pasted_text.strip())
        df = pd.read_csv(buffer, sep=sep, dtype=str, on_bad_lines="skip")
        if df.empty:
            return None, {}, "Pasted data contains headers but zero data rows."
            
        meta = {
            "format": "Pasted Tabular Text",
            "delimiter": "\\t (Tab)" if sep == "\t" else sep,
            "rows": len(df),
            "columns": len(df.columns)
        }
        return df, meta, None
    except Exception as e:
        return None, {}, f"Could not parse pasted text: {str(e)}"


# ------------------------------------------------------------------------------
# Apache Spark Loading Engine
# ------------------------------------------------------------------------------
def load_raw_data(
    file_path: Union[str, Path],
    spark: Optional[SparkSession] = None,
    limit: Optional[int] = None,
    column_mapping: Optional[Dict[str, str]] = None
) -> DataFrame:
    """
    Loads raw transaction data into a PySpark DataFrame.
    Supports CSV, XLSX, TSV, JSON, JSONL, and Parquet.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path_obj}.\n{get_download_instructions()}"
        )
        
    if spark is None:
        spark = get_spark_session()
        
    suffix = path_obj.suffix.lower()
    
    if suffix in (".csv", ".tsv", ".txt"):
        if column_mapping:
            raw_df = (
                spark.read
                .option("header", "true")
                .option("mode", "PERMISSIVE")
                .option("quote", "\"")
                .option("escape", "\"")
                .csv(str(path_obj))
            )
            for file_col, target_col in column_mapping.items():
                if file_col in raw_df.columns:
                    raw_df = raw_df.withColumnRenamed(file_col, target_col)
            for col_name in RAW_SCHEMA.names:
                if col_name not in raw_df.columns:
                    raw_df = raw_df.withColumn(col_name, F.lit(None).cast("string"))
            df = raw_df.select(RAW_SCHEMA.names)
        else:
            df = (
                spark.read
                .option("header", "true")
                .option("mode", "PERMISSIVE")
                .option("quote", "\"")
                .option("escape", "\"")
                .schema(RAW_SCHEMA)
                .csv(str(path_obj))
            )
    elif suffix in (".xlsx", ".xls", ".parquet", ".json", ".jsonl"):
        # Read via pandas universal parser and load to Spark
        pdf, _, err = parse_tabular_data(path_obj, filename=path_obj.name, nrows=limit)
        if err or pdf is None:
            raise ValueError(err or "Failed to parse file into PySpark DataFrame.")
        if column_mapping:
            pdf = pdf.rename(columns=column_mapping)
        for col_name in RAW_SCHEMA.names:
            if col_name not in pdf.columns:
                pdf[col_name] = None
            else:
                pdf[col_name] = pdf[col_name].astype(str)
        pdf = pdf[RAW_SCHEMA.names]
        df = spark.createDataFrame(pdf, schema=RAW_SCHEMA)
    else:
        raise ValueError(f"Unsupported file format '{suffix}'. Supported: .csv, .xlsx, .xls, .tsv, .txt, .parquet, .json, .jsonl")
        
    if limit is not None and suffix in (".csv", ".tsv", ".txt"):
        df = df.limit(limit)
        
    return df


def parse_invoice_timestamp(df: DataFrame, date_col: str = "InvoiceDate") -> DataFrame:
    """
    Parses heterogeneous string dates into a unified Spark TimestampType and DateType.
    Supports formats including 'dd-MM-yyyy HH:mm', 'yyyy-MM-dd HH:mm:ss', etc.
    """
    timestamp_exprs = [
        F.to_timestamp(F.col(date_col), fmt) for fmt in settings.SUPPORTED_DATE_FORMATS
    ]
    timestamp_exprs.append(F.to_timestamp(F.col(date_col)))
    
    df_parsed = df.withColumn("InvoiceTimestamp", F.coalesce(*timestamp_exprs))
    df_parsed = df_parsed.withColumn("InvoiceDateOnly", F.to_date(F.col("InvoiceTimestamp")))
    return df_parsed
