"""
Unit tests for unified StorageManager, local persistence, and Amazon S3 error handling.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from botocore.exceptions import ClientError, NoCredentialsError
from src.storage.storage_manager import StorageManager


def test_local_storage_save_and_list(tmp_path):
    """Verifies that StorageManager saves files locally and lists them accurately."""
    manager = StorageManager(storage_mode="local", local_base_dir=tmp_path)
    
    # Create a dummy report file
    sample_file = tmp_path / "dummy_report.json"
    sample_file.write_text('{"status": "ok"}', encoding="utf-8")
    
    result = manager.save_file(sample_file, category="reports")
    assert result["category"] == "reports"
    assert result["s3_uploaded"] is False
    assert Path(result["local_path"]).exists()
    
    files = manager.list_files("reports")
    assert any(f["name"] == "dummy_report.json" for f in files)


def test_storage_invalid_category(tmp_path):
    """Verifies that invalid category strings are rejected."""
    manager = StorageManager(storage_mode="local", local_base_dir=tmp_path)
    sample_file = tmp_path / "dummy.txt"
    sample_file.write_text("test", encoding="utf-8")
    
    with pytest.raises(ValueError, match="Invalid category"):
        manager.save_file(sample_file, category="unsupported_category")


def test_storage_s3_graceful_missing_credentials(tmp_path):
    """Verifies graceful fallback when S3 credentials are unset or invalid."""
    manager = StorageManager(
        storage_mode="s3",
        bucket_name="non-existent-test-bucket-12345",
        local_base_dir=tmp_path
    )
    status = manager.check_s3_status()
    # Should not throw an unhandled exception, but report connection or credential failure
    assert status["connected"] is False or status["bucket_exists"] is False
    assert "bucket_name" in status


def test_storage_s3_upload_mock_failure(tmp_path):
    """Verifies graceful reporting when an S3 upload fails."""
    manager = StorageManager(storage_mode="s3", local_base_dir=tmp_path)
    
    # Mock S3 client with failure
    mock_s3 = MagicMock()
    mock_s3.upload_file.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
        "upload_file"
    )
    manager._s3_client = mock_s3
    
    sample_file = tmp_path / "summary.csv"
    sample_file.write_text("a,b\n1,2", encoding="utf-8")
    
    result = manager.save_file(sample_file, category="analytics")
    assert result["s3_uploaded"] is False
    assert "failed" in result["message"].lower()
    # Local file must still be safely saved
    assert Path(result["local_path"]).exists()
