"""
SalesPulse Analytics - PySpark Session Manager
Configures and initializes a lightweight local SparkSession optimized for single-machine execution.
Ensures Windows path and Python executable compatibility.
"""

import os
import sys
from pyspark.sql import SparkSession
from config import settings


def get_windows_short_path(path_str: str) -> str:
    """Returns 8.3 short path on Windows to avoid space-related execution errors in PySpark."""
    if sys.platform == "win32" and " " in path_str:
        try:
            import ctypes
            from ctypes import wintypes
            _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
            _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            _GetShortPathNameW.restype = wintypes.DWORD
            buf = ctypes.create_unicode_buffer(1024)
            res = _GetShortPathNameW(path_str, buf, 1024)
            if res and buf.value:
                return buf.value
        except Exception:
            pass
    return path_str


def get_spark_session(app_name: str = None, master: str = None) -> SparkSession:
    """
    Creates or retrieves an active SparkSession with Windows-safe environment variables.
    
    Args:
        app_name: Optional name for the Spark application.
        master: Master URL, default configured in settings (local[2]).
        
    Returns:
        SparkSession instance.
    """
    # Ensure Spark workers use the identical Python interpreter as the driver (Windows space-safe)
    safe_python = get_windows_short_path(sys.executable)
    os.environ["PYSPARK_PYTHON"] = safe_python
    os.environ["PYSPARK_DRIVER_PYTHON"] = safe_python
    
    # Configure lightweight JVM memory to respect laptop RAM constraints
    builder = (
        SparkSession.builder
        .appName(app_name or settings.SPARK_APP_NAME)
        .master(master or settings.SPARK_MASTER)
        .config("spark.driver.memory", settings.SPARK_DRIVER_MEMORY)
        .config("spark.sql.shuffle.partitions", settings.SPARK_SQL_SHUFFLE_PARTITIONS)
        .config("spark.ui.enabled", "false")  # Avoid port conflicts in local runs
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
    )
    
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


def stop_spark_session(spark: SparkSession) -> None:
    """Safely terminates an active SparkSession."""
    if spark is not None:
        try:
            spark.stop()
        except Exception:
            pass
