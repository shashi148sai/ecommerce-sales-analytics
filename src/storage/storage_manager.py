"""
SalesPulse Analytics - Unified Storage Management Layer
Provides transparent storage abstraction supporting both ₹0 offline local filesystem
and AWS Amazon S3 cloud storage with private access controls and structured prefix hierarchies.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

from config import settings


class StorageManager:
    """
    Manages persistence of raw, processed, analytics, reports, and metadata objects
    across local disk and AWS Amazon S3.
    """

    CATEGORIES = ("raw", "processed", "analytics", "reports", "metadata")

    def __init__(
        self,
        storage_mode: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
        local_base_dir: Optional[Path] = None
    ):
        self.storage_mode = (storage_mode or settings.STORAGE_MODE).lower()
        self.bucket_name = bucket_name or settings.AWS_S3_BUCKET
        self.region_name = region_name or settings.AWS_REGION
        self.local_base_dir = Path(local_base_dir or settings.DATA_DIR)
        
        # Ensure local categories exist
        for cat in self.CATEGORIES:
            (self.local_base_dir / cat).mkdir(parents=True, exist_ok=True)
            
        self._s3_client = None

    def get_s3_client(self):
        """
        Lazily instantiates the boto3 S3 client using explicit or environment credentials.
        """
        if self._s3_client is not None:
            return self._s3_client
            
        kwargs = {"region_name": self.region_name}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
            if settings.AWS_SESSION_TOKEN:
                kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN
                
        try:
            self._s3_client = boto3.client("s3", **kwargs)
            return self._s3_client
        except Exception as e:
            return None

    def check_s3_status(self) -> Dict[str, Any]:
        """
        Probes S3 connectivity and verifies bucket existence without creating paid resources.
        """
        client = self.get_s3_client()
        if client is None:
            return {
                "connected": False,
                "bucket_exists": False,
                "bucket_name": self.bucket_name,
                "message": "AWS S3 client could not be initialized. Missing or invalid credentials."
            }
            
        try:
            client.head_bucket(Bucket=self.bucket_name)
            return {
                "connected": True,
                "bucket_exists": True,
                "bucket_name": self.bucket_name,
                "message": f"Successfully connected to private S3 bucket '{self.bucket_name}'."
            }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                msg = f"S3 Bucket '{self.bucket_name}' does not exist."
            elif error_code == "403":
                msg = f"Access denied to S3 Bucket '{self.bucket_name}'. Check IAM permissions."
            else:
                msg = f"AWS ClientError: {str(e)}"
            return {
                "connected": True,
                "bucket_exists": False,
                "bucket_name": self.bucket_name,
                "message": msg
            }
        except (NoCredentialsError, PartialCredentialsError):
            return {
                "connected": False,
                "bucket_exists": False,
                "bucket_name": self.bucket_name,
                "message": "No AWS credentials detected. Operating safely in local storage mode."
            }
        except Exception as e:
            return {
                "connected": False,
                "bucket_exists": False,
                "bucket_name": self.bucket_name,
                "message": f"Connection check failed: {str(e)}"
            }

    def save_file(
        self,
        source_path: Path,
        category: str,
        target_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Saves a file to local storage and optionally replicates to Amazon S3 if enabled.
        """
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of {self.CATEGORIES}")
            
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
            
        filename = target_filename or source_path.name
        local_dest = self.local_base_dir / category / filename
        
        # Always persist locally first
        if source_path.resolve() != local_dest.resolve():
            shutil.copy2(source_path, local_dest)
            
        result = {
            "category": category,
            "filename": filename,
            "local_path": str(local_dest),
            "size_bytes": local_dest.stat().st_size,
            "s3_uploaded": False,
            "s3_key": None,
            "message": "Saved to local storage."
        }
        
        if self.storage_mode == "s3":
            s3_client = self.get_s3_client()
            if s3_client:
                prefix = settings.S3_PREFIXES.get(category, f"{category}/")
                s3_key = f"{prefix}{filename}"
                try:
                    s3_client.upload_file(
                        str(local_dest),
                        self.bucket_name,
                        s3_key,
                        ExtraArgs={"ServerSideEncryption": "AES256"}  # Cloud security best practice
                    )
                    result["s3_uploaded"] = True
                    result["s3_key"] = s3_key
                    result["message"] = f"Persisted locally and synced to s3://{self.bucket_name}/{s3_key}."
                except Exception as e:
                    result["message"] = f"Local copy saved, but S3 sync failed: {str(e)}"
                    
        return result

    def list_files(self, category: str) -> List[Dict[str, Any]]:
        """
        Lists files under the given category from local disk, or S3 if connected.
        """
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of {self.CATEGORIES}")
            
        files = []
        cat_dir = self.local_base_dir / category
        if cat_dir.exists():
            for p in cat_dir.iterdir():
                if p.is_file() and p.name != ".gitkeep":
                    files.append({
                        "name": p.name,
                        "path": str(p),
                        "size_bytes": p.stat().st_size,
                        "storage_type": "local"
                    })
                    
        if self.storage_mode == "s3":
            s3_client = self.get_s3_client()
            if s3_client:
                prefix = settings.S3_PREFIXES.get(category, f"{category}/")
                try:
                    resp = s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
                    for obj in resp.get("Contents", []):
                        key = obj["Key"]
                        if not key.endswith("/"):
                            files.append({
                                "name": Path(key).name,
                                "path": f"s3://{self.bucket_name}/{key}",
                                "size_bytes": obj.get("Size", 0),
                                "storage_type": "s3",
                                "last_modified": str(obj.get("LastModified"))
                            })
                except Exception:
                    pass
                    
        return files

    def sync_local_to_s3(self) -> Dict[str, Any]:
        """
        Replicates all local datasets, summaries, reports, and metadata into Amazon S3.
        """
        s3_client = self.get_s3_client()
        if not s3_client:
            return {"status": "FAILED", "message": "No valid S3 credentials configured."}
            
        uploaded = []
        errors = []
        
        for cat in self.CATEGORIES:
            cat_dir = self.local_base_dir / cat
            if not cat_dir.exists():
                continue
            for item in cat_dir.iterdir():
                if item.is_file() and item.name != ".gitkeep":
                    prefix = settings.S3_PREFIXES.get(cat, f"{cat}/")
                    s3_key = f"{prefix}{item.name}"
                    try:
                        s3_client.upload_file(
                            str(item),
                            self.bucket_name,
                            s3_key,
                            ExtraArgs={"ServerSideEncryption": "AES256"}
                        )
                        uploaded.append(s3_key)
                    except Exception as e:
                        errors.append(f"{item.name}: {str(e)}")
                        
        return {
            "status": "SUCCESS" if not errors else "PARTIAL",
            "uploaded_count": len(uploaded),
            "uploaded_keys": uploaded,
            "errors": errors
        }
