"""
Unit and integration tests for universal input methods, diverse file formats,
safe ZIP archive processing, delimiter sniffing, and analysis capability detection.
"""

import io
import json
import zipfile
import pytest
import pandas as pd
from pathlib import Path

from config import settings
from src.ingestion.loader import (
    parse_tabular_data,
    parse_pasted_text,
    detect_delimiter,
    inspect_zip_archive,
    extract_zip_member
)
from src.validation.validator import (
    detect_schema_mapping,
    normalize_pandas_dataframe
)
from src.dashboard.utils import (
    check_available_analyses,
    get_csv_template
)


# ------------------------------------------------------------------------------
# 1. Delimiter & Pasted Text Detection
# ------------------------------------------------------------------------------
def test_detect_delimiter():
    """Verifies automatic detection of comma, tab, semicolon, and pipe."""
    assert detect_delimiter("a,b,c\n1,2,3\n4,5,6") == ","
    assert detect_delimiter("a\tb\tc\n1\t2\t3\n4\t5\t6") == "\t"
    assert detect_delimiter("a;b;c\n1;2;3\n4;5;6") == ";"
    assert detect_delimiter("a|b|c\n1|2|3\n4|5|6") == "|"
    assert detect_delimiter("") == ","


def test_parse_pasted_text():
    """Verifies parsing of pasted spreadsheet text."""
    pasted_csv = "InvoiceNo,StockCode,Description,Quantity,UnitPrice\nINV1,SKU1,Widget,5,10.0\nINV2,SKU2,Gadget,2,25.0"
    df, meta, err = parse_pasted_text(pasted_csv)
    assert err is None
    assert df is not None
    assert len(df) == 2
    assert "Widget" in df["Description"].values

    # Test tab-separated pasted text (from Excel)
    pasted_tsv = "InvoiceNo\tStockCode\tDescription\tQuantity\tUnitPrice\nINV1\tSKU1\tWidget\t5\t10.0"
    df_tsv, meta_tsv, err_tsv = parse_pasted_text(pasted_tsv)
    assert err_tsv is None
    assert len(df_tsv) == 1

    # Empty text
    _, _, empty_err = parse_pasted_text("   \n  ")
    assert empty_err is not None


# ------------------------------------------------------------------------------
# 2. File Formats: CSV, TSV, TXT, JSON, JSONL, Parquet
# ------------------------------------------------------------------------------
def test_parse_csv_in_memory():
    """Verifies in-memory CSV parsing."""
    csv_bytes = b"Order ID,Item Code,Product Name,Units,Price\n1001,A1,Chair,2,45.00\n1002,B2,Desk,1,120.00"
    df, meta, err = parse_tabular_data(csv_bytes, filename="orders.csv")
    assert err is None
    assert len(df) == 2
    assert meta["format"] == "CSV/Tabular Text"
    assert meta["columns"] == 5


def test_parse_tsv_in_memory():
    """Verifies TSV parsing."""
    tsv_bytes = b"order_id\tsku\ttitle\tqty\tprice\nORD-1\tSKU-1\tBook\t3\t15.0"
    df, meta, err = parse_tabular_data(tsv_bytes, filename="data.tsv")
    assert err is None
    assert len(df) == 1
    assert "Book" in df["title"].values


def test_parse_json_records():
    """Verifies JSON format parsing."""
    records = [
        {"InvoiceNo": "101", "StockCode": "S1", "Description": "Lamp", "Quantity": 2, "UnitPrice": 19.99},
        {"InvoiceNo": "102", "StockCode": "S2", "Description": "Bulb", "Quantity": 10, "UnitPrice": 2.50}
    ]
    json_bytes = json.dumps(records).encode("utf-8")
    df, meta, err = parse_tabular_data(json_bytes, filename="records.json")
    assert err is None
    assert len(df) == 2
    assert meta["format"] == "JSON Document"


def test_parse_jsonl():
    """Verifies JSONL (line-delimited JSON) format parsing."""
    lines = [
        json.dumps({"InvoiceNo": "201", "StockCode": "P1", "Description": "Pen", "Quantity": 50, "UnitPrice": 1.0}),
        json.dumps({"InvoiceNo": "202", "StockCode": "P2", "Description": "Notebook", "Quantity": 20, "UnitPrice": 3.0})
    ]
    jsonl_bytes = "\n".join(lines).encode("utf-8")
    df, meta, err = parse_tabular_data(jsonl_bytes, filename="stream.jsonl")
    assert err is None
    assert len(df) == 2
    assert meta["format"] == "Line-Delimited JSON (JSONL)"


def test_parse_parquet_in_memory():
    """Verifies Apache Parquet format parsing."""
    src_df = pd.DataFrame({
        "InvoiceNo": ["301", "302"],
        "StockCode": ["X1", "X2"],
        "Description": ["Cable", "Adapter"],
        "Quantity": ["5", "3"],
        "UnitPrice": ["9.99", "14.99"]
    })
    buf = io.BytesIO()
    src_df.to_parquet(buf, index=False)
    parquet_bytes = buf.getvalue()

    df, meta, err = parse_tabular_data(parquet_bytes, filename="dataset.parquet")
    assert err is None
    assert len(df) == 2
    assert meta["format"] == "Apache Parquet"


# ------------------------------------------------------------------------------
# 3. Safe ZIP Archive Inspection & Extraction
# ------------------------------------------------------------------------------
def test_safe_zip_archive_processing():
    """Verifies safe in-memory inspection and extraction of ZIP files."""
    csv_content = b"InvoiceNo,StockCode,Description,Quantity,UnitPrice\nZIP1,SKU1,Shirt,2,25.0"
    
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("transactions.csv", csv_content)
        zf.writestr("notes.txt", b"Ignore this note")
        
    zip_bytes = zip_buf.getvalue()
    
    # 1. Inspection
    members = inspect_zip_archive(zip_bytes)
    assert "transactions.csv" in members
    assert "notes.txt" in members
    
    # 2. Parsing through universal loader
    df, meta, err = parse_tabular_data(zip_bytes, filename="bundle.zip")
    assert err is None
    assert len(df) == 1
    assert "Shirt" in df["Description"].values


def test_zip_path_traversal_security():
    """Verifies that malicious Zip Slip path traversal attempts are rejected."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("../../etc/passwd.csv", b"dummy")
        zf.writestr("/root/secret.csv", b"dummy")
        
    members = inspect_zip_archive(zip_buf.getvalue())
    assert len(members) == 0  # Both malicious paths skipped
    
    with pytest.raises(ValueError):
        extract_zip_member(zip_buf.getvalue(), "../../etc/passwd.csv")


# ------------------------------------------------------------------------------
# 4. Error Handling: Empty Files, Size Limits, Unsupported Formats
# ------------------------------------------------------------------------------
def test_empty_file_handling():
    """Verifies graceful handling of empty 0-byte files."""
    df, meta, err = parse_tabular_data(b"", filename="empty.csv")
    assert df is None
    assert "empty (0 bytes)" in err


def test_file_size_limit_enforcement():
    """Verifies rejection of files exceeding the configured maximum size limit."""
    # Temporarily set limit to 1KB for test
    orig_limit = settings.MAX_UPLOAD_SIZE_MB
    settings.MAX_UPLOAD_SIZE_MB = 0.001  # ~1 KB
    try:
        large_bytes = b"a" * 2000
        df, meta, err = parse_tabular_data(large_bytes, filename="large.csv")
        assert df is None
        assert "exceeds maximum allowed limit" in err
    finally:
        settings.MAX_UPLOAD_SIZE_MB = orig_limit


def test_unsupported_file_extension():
    """Verifies clear error and guidance for unsupported file types."""
    df, meta, err = parse_tabular_data(b"binary content", filename="report.pdf")
    assert df is None
    assert "Unsupported file format" in err


# ------------------------------------------------------------------------------
# 5. Template Generation & Available Analyses Detection
# ------------------------------------------------------------------------------
def test_csv_template_generation():
    """Verifies downloadable template headers and content."""
    template = get_csv_template()
    assert "InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice" in template
    assert "WHITE HANGING HEART" in template


def test_check_available_analyses():
    """Verifies accurate detection of which analytical pages are supported."""
    # Full e-commerce dataset
    full_cols = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
    caps = check_available_analyses(full_cols)
    assert caps["revenue_analysis"] is True
    assert caps["time_series_analysis"] is True
    assert caps["product_analysis"] is True
    assert caps["customer_analysis"] is True
    assert caps["regional_analysis"] is True
    assert len(caps["explanations"]) == 0

    # Minimal dataset (only product, qty, price) - no customer or country
    min_cols = ["product_name", "qty", "selling_price"]
    caps_min = check_available_analyses(min_cols)
    assert caps_min["revenue_analysis"] is True
    assert caps_min["product_analysis"] is True
    assert caps_min["time_series_analysis"] is False
    assert caps_min["customer_analysis"] is False
    assert caps_min["regional_analysis"] is False
    assert "customer" in caps_min["explanations"]
    assert "regional" in caps_min["explanations"]


# ------------------------------------------------------------------------------
# 6. Normalization & Pre-computed Sales Amount Handling
# ------------------------------------------------------------------------------
def test_normalize_precomputed_sales_amount():
    """Verifies that pre-existing sales amount is respected without double calculation."""
    df_raw = pd.DataFrame({
        "order_id": ["1", "2"],
        "product": ["Widget", "Gadget"],
        "units": ["2", "1"],
        "rate": ["10.0", "50.0"],
        "total_amount": ["25.0", "50.0"]  # E.g. order 1 has 5.0 tax/shipping included
    })
    mapping = {
        "order_id": "InvoiceNo",
        "product": "Description",
        "units": "Quantity",
        "rate": "UnitPrice",
        "total_amount": "SalesAmount"
    }
    normalized, summary = normalize_pandas_dataframe(df_raw, mapping)
    assert summary["has_sales_amount_precomputed"] is True
    assert normalized["LineTotal"].iloc[0] == 25.0  # Uses total_amount, does NOT overwrite with 20.0!


def test_normalize_identifiers_as_strings():
    """Verifies that numeric IDs (InvoiceNo, CustomerID, StockCode) remain strings."""
    df_raw = pd.DataFrame({
        "InvoiceNo": [536365, 536366],
        "StockCode": [85123, 71053],
        "CustomerID": [17850, 13047],
        "Quantity": [6, 12],
        "UnitPrice": [2.55, 1.85]
    })
    mapping = {c: c for c in df_raw.columns}
    normalized, _ = normalize_pandas_dataframe(df_raw, mapping)
    assert isinstance(normalized["InvoiceNo"].iloc[0], str)
    assert isinstance(normalized["StockCode"].iloc[0], str)
    assert isinstance(normalized["CustomerID"].iloc[0], str)
    assert normalized["InvoiceNo"].iloc[0] == "536365"
