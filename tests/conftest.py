"""
SalesPulse Analytics - Test Fixtures and Configuration
Provides a shared, lightweight SparkSession and sample transaction fixtures for automated testing.
"""

import os
import sys
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType


@pytest.fixture(scope="session")
def spark_session():
    """Session-scoped SparkSession for unit and integration tests."""
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    
    spark = (
        SparkSession.builder
        .appName("SalesPulse-Test-Suite")
        .master("local[1]")
        .config("spark.driver.memory", "1g")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    try:
        spark.stop()
    except Exception:
        pass


@pytest.fixture
def sample_raw_dataframe(spark_session):
    """Provides a synthetic DataFrame representing varied transactional conditions."""
    data = [
        # Normal purchase
        ("536365", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", "6", "01-12-2010 8:26", "2.55", "17850.0", "United Kingdom"),
        # Another normal purchase from same invoice
        ("536365", "71053", "WHITE METAL LANTERN", "2", "01-12-2010 8:26", "3.39", "17850.0", "United Kingdom"),
        # Unregistered customer (guest checkout)
        ("536366", "22633", "HAND WARMER UNION JACK", "4", "01-12-2010 8:28", "1.85", None, "United Kingdom"),
        # Exact duplicate of the second row (should be dropped)
        ("536365", "71053", "WHITE METAL LANTERN", "2", "01-12-2010 8:26", "3.39", "17850.0", "United Kingdom"),
        # Cancellation with negative quantity and 'C' prefix
        ("C536379", "D", "Discount", "-1", "01-12-2010 9:41", "27.50", "14527.0", "United Kingdom"),
        # Negative quantity without C prefix (return/adjustment)
        ("536380", "84347", "ROTATING SILVER ANGELS T-LIGHT HLDR", "-3", "01-12-2010 9:45", "1.25", "15311", "United Kingdom"),
        # Zero unit price (e.g. sample or freebie)
        ("536381", "84029E", "RED WOOLLY HOTTIE WHITE HEART.", "1", "01-12-2010 9:50", "0.00", "16000", "France"),
        # International normal purchase
        ("536382", "22728", "ALARM CLOCK BAKELIKE PINK", "4", "01-12-2010 10:00", "3.75", "12583", "France")
    ]
    
    schema = StructType([
        StructField("InvoiceNo", StringType(), True),
        StructField("StockCode", StringType(), True),
        StructField("Description", StringType(), True),
        StructField("Quantity", StringType(), True),
        StructField("InvoiceDate", StringType(), True),
        StructField("UnitPrice", StringType(), True),
        StructField("CustomerID", StringType(), True),
        StructField("Country", StringType(), True)
    ])
    
    return spark_session.createDataFrame(data, schema)
