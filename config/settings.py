"""
SalesPulse Analytics - Central Configuration Module
Defines project-wide paths, PySpark settings, AWS credentials/prefixes, and business metric constants.
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

# Storage Mode: 'local' or 's3'
STORAGE_MODE = os.getenv("STORAGE_MODE", "local").lower()

# S3 Prefix Hierarchy (strictly adheres to cloud architecture requirements)
S3_PREFIXES = {
    "raw": "raw/",
    "processed": "processed/",
    "analytics": "analytics/",
    "reports": "reports/",
    "metadata": "metadata/"
}

# AWS Cloud Settings
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

CANCELLATION_PREFIXES = ("C", "c")

# Date format patterns supported during ingestion
SUPPORTED_DATE_FORMATS = [
    "dd-MM-yyyy HH:mm",
    "dd/MM/yyyy HH:mm",
    "yyyy-MM-dd HH:mm:ss",
    "yyyy/MM/dd HH:mm:ss",
    "MM/dd/yyyy HH:mm",
    "M/d/yyyy H:m",
    "d-M-yyyy H:m"
]
