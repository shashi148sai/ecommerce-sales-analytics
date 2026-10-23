"""
SalesPulse Analytics - Central Configuration Module
Defines project-wide paths, PySpark settings, AWS credentials/prefixes,
Indian localization, and business metric constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if available
load_dotenv(dotenv_path=BASE_DIR / ".env")

# ------------------------------------------------------------------------------
# Storage and Path Configurations
# ------------------------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ANALYTICS_DATA_DIR = DATA_DIR / "analytics"
REPORTS_DIR = DATA_DIR / "reports"
METADATA_DIR = DATA_DIR / "metadata"

DEFAULT_RAW_FILE = RAW_DATA_DIR / "OnlineRetail.csv"
SAMPLE_RAW_FILE = RAW_DATA_DIR / "sample_retail.csv"

# Ensure directories exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, ANALYTICS_DATA_DIR, REPORTS_DIR, METADATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Storage Mode: 'local' (default and strictly enforced until cloud authorized) or 's3'
STORAGE_MODE = os.getenv("STORAGE_MODE", "local").lower()

# S3 Prefix Hierarchy (strictly adheres to cloud architecture requirements)
S3_PREFIXES = {
    "raw": "raw/",
    "processed": "processed/",
    "analytics": "analytics/",
    "reports": "reports/",
    "metadata": "metadata/"
}

# AWS Cloud Settings (Mocked and strictly offline by default)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "salespulse-analytics-default")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", None)

# ------------------------------------------------------------------------------
# Apache Spark Configuration
# ------------------------------------------------------------------------------
SPARK_APP_NAME = os.getenv("SPARK_APP_NAME", "SalesPulse-Analytics")
SPARK_MASTER = os.getenv("SPARK_MASTER", "local[2]")
SPARK_DRIVER_MEMORY = os.getenv("SPARK_DRIVER_MEMORY", "2g")
SPARK_SQL_SHUFFLE_PARTITIONS = os.getenv("SPARK_SQL_SHUFFLE_PARTITIONS", "4")

# ------------------------------------------------------------------------------
# Indian-First Localization & Currency Settings
# ------------------------------------------------------------------------------
LOCALE = "en-IN"
TIMEZONE = "Asia/Kolkata"
DATE_DISPLAY_FORMAT = "DD-MM-YYYY"
FIRST_DAY_OF_WEEK = "Monday"

# Canonical Source Currency
SOURCE_CURRENCY = "£"
SOURCE_CURRENCY_CODE = "GBP"

# Target Converted Currency for Indian Business Context
TARGET_CURRENCY = "₹"
TARGET_CURRENCY_CODE = "INR"

# Documented Reference Conversion Rate (1 GBP = ₹106.50 reference rate)
DEFAULT_GBP_TO_INR_RATE = 106.50
REFERENCE_RATE_DATE = "2026-10-23"

# Upload Limits
MAX_UPLOAD_SIZE_MB = 100

# ------------------------------------------------------------------------------
# Domain & Dataset Constants
# ------------------------------------------------------------------------------
DEFAULT_CURRENCY = "£"
DEFAULT_CURRENCY_CODE = "GBP"

REQUIRED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country"
]

# Aliases for intelligent schema matching across varied e-commerce datasets
COLUMN_ALIASES = {
    "InvoiceNo": ["invoiceno", "invoice_no", "invoice_id", "invoicenum", "order_id", "orderid", "bill_no", "bill_number"],
    "StockCode": ["stockcode", "stock_code", "product_id", "productid", "item_code", "sku", "product_code"],
    "Description": ["description", "product_name", "item_name", "title", "product_description", "item_desc"],
    "Quantity": ["quantity", "qty", "units", "items_count", "item_count"],
    "InvoiceDate": ["invoicedate", "invoice_date", "order_date", "orderdate", "date", "timestamp"],
    "UnitPrice": ["unitprice", "unit_price", "price", "rate", "item_price", "selling_price"],
    "CustomerID": ["customerid", "customer_id", "user_id", "client_id", "cust_id"],
    "Country": ["country", "region", "nation", "location", "state", "shipping_country"]
}

CANCELLATION_PREFIXES = ("C", "c")

# Date format patterns supported during ingestion
SUPPORTED_DATE_FORMATS = [
    "dd-MM-yyyy HH:mm",
    "dd/MM/yyyy HH:mm",
    "yyyy-MM-dd HH:mm:ss",
    "yyyy/MM/dd HH:mm:ss",
    "MM/dd/yyyy HH:mm",
    "M/d/yyyy H:m",
    "d-M-yyyy H:m",
    "dd-MM-yyyy",
    "yyyy-MM-dd"
]
