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
SPARK_DRIVER_MEMORY = os.getenv("SPARK_DRIVER_MEMORY", "1g")
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

# Documented Reference Conversion Rate (1 GBP = ₹106.50, 1 USD = ₹84.00 reference rate)
DEFAULT_GBP_TO_INR_RATE = 106.50
DEFAULT_USD_TO_INR_RATE = 84.00
REFERENCE_RATE_DATE = "2026-10-23"

# Pre-packaged Sample Data Files
SAMPLE_RAW_FILE = RAW_DATA_DIR / "sample_retail.csv"
SAMPLE_SHOPPING_FILE = RAW_DATA_DIR / "shopping.csv"

# Upload Limits
MAX_UPLOAD_SIZE_MB = 100

# ------------------------------------------------------------------------------
# Domain & Dataset Constants (Default Presentation Currency: INR)
# ------------------------------------------------------------------------------
DEFAULT_CURRENCY = "₹"
DEFAULT_CURRENCY_CODE = "INR"

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

# Business Field Metadata for guided user mapping and validation
FIELD_DEFINITIONS = {
    "InvoiceNo": {
        "label": "Order or Invoice ID",
        "description": "Unique identifier for each transaction or bill",
        "required": True,
        "is_identifier": True,
        "example": "536365, ORD-10294"
    },
    "StockCode": {
        "label": "Product Code or SKU",
        "description": "Unique catalog identifier or barcode for the item",
        "required": True,
        "is_identifier": True,
        "example": "85123A, SKU-001"
    },
    "Description": {
        "label": "Product Name or Title",
        "description": "Readable description or name of the merchandise",
        "required": True,
        "is_identifier": False,
        "example": "WHITE HANGING HEART T-LIGHT HOLDER"
    },
    "Quantity": {
        "label": "Units Sold (Quantity)",
        "description": "Number of product units purchased (negative indicates return)",
        "required": True,
        "is_identifier": False,
        "example": "6, 12, -1"
    },
    "InvoiceDate": {
        "label": "Order Date and Time",
        "description": "Date and timestamp when the order was placed",
        "required": True,
        "is_identifier": False,
        "example": "01-12-2010 08:26, 2023-05-15"
    },
    "UnitPrice": {
        "label": "Unit Selling Price",
        "description": "Price per single unit of the product",
        "required": True,
        "is_identifier": False,
        "example": "2.55, 149.00"
    },
    "SalesAmount": {
        "label": "Total Sales Amount (Optional)",
        "description": "Pre-computed line total (if present, prevents double-calculation)",
        "required": False,
        "is_identifier": False,
        "example": "15.30, 899.00"
    },
    "CustomerID": {
        "label": "Customer ID (Optional)",
        "description": "Unique identifier for registered buyer (empty for guest checkouts)",
        "required": False,
        "is_identifier": True,
        "example": "17850, CUST-883"
    },
    "Country": {
        "label": "Country or Region (Optional)",
        "description": "Geographical market or shipping destination",
        "required": False,
        "is_identifier": False,
        "example": "United Kingdom, India, Germany"
    }
}

# Aliases for robust, intelligent schema matching across diverse e-commerce datasets
COLUMN_ALIASES = {
    "InvoiceNo": [
        "invoiceno", "invoice_no", "invoice", "invoice_id", "invoicenum", "invoicenumber",
        "order_id", "orderid", "order_number", "ordernumber", "order_no", "orderno",
        "transaction_id", "transactionid", "transaction_no", "bill_no", "bill_number",
        "receipt_id", "receipt_no", "order"
    ],
    "StockCode": [
        "stockcode", "stock_code", "product_id", "productid", "item_code", "itemcode",
        "sku", "product_code", "productcode", "item_id", "itemid", "code", "barcode", "asin"
    ],
    "Description": [
        "description", "product_name", "productname", "item_name", "itemname", "product",
        "item", "title", "product_description", "item_desc", "item_description", "details",
        "name", "item_purchased", "itempurchased", "item purchased"
    ],
    "Quantity": [
        "quantity", "qty", "units", "unit", "units_sold", "items_count", "item_count",
        "itemcount", "count", "pieces", "volume", "order_quantity"
    ],
    "InvoiceDate": [
        "invoicedate", "invoice_date", "order_date", "orderdate", "date", "transaction_date",
        "timestamp", "datetime", "order_time", "sale_date", "purchased_at", "created_at"
    ],
    "UnitPrice": [
        "unitprice", "unit_price", "price", "rate", "item_price", "selling_price",
        "unit_cost", "cost_per_unit", "mrp", "item_cost", "purchase_amount_(usd)",
        "purchase_amount", "purchaseamount", "purchaseamountusd", "purchase_amount_usd",
        "purchase amount (usd)", "purchase amount", "amount (usd)", "amount_usd"
    ],
    "SalesAmount": [
        "sales", "revenue", "total", "total_amount", "sales_amount", "net_amount",
        "line_total", "linetotal", "total_price", "totalprice", "gross_amount", "amount",
        "purchase_amount_(usd)", "purchase_amount", "purchaseamount", "purchaseamountusd",
        "purchase_amount_usd", "purchase amount (usd)", "purchase amount"
    ],
    "CustomerID": [
        "customerid", "customer_id", "customer", "user_id", "userid", "client_id",
        "clientid", "cust_id", "custid", "buyer_id", "buyer", "shopper_id", "account_id"
    ],
    "Country": [
        "country", "region", "nation", "location", "state", "shipping_country",
        "delivery_location", "market", "territory", "zone", "city"
    ]
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
