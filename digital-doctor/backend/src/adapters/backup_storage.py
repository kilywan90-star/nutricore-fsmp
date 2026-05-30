"""Backup storage adapters — local filesystem and S3/MinIO backends."""

import os
import shutil
from pathlib import Path
from typing import Protocol

from src.config import settings


class BackupStorageBackend(Protocol):
    def store(self, source_path: str, dest_name: str) -> str:
        """Store backup file, return storage path/URI."""
        ...

    def retrieve(self, storage_path: str, dest_path: str) -> None:
        """Retrieve backup file to local path."""
        ...

    def delete(self, storage_path: str) -> None:
        """Delete backup from storage."""
        ...


class LocalStorage:
    """Store backups on local filesystem."""

    def __init__(self, base_dir: str = "backups"):
        self.base_dir = Path(base_dir)

    def store(self, source_path: str, dest_name: str) -> str:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        dest_path = self.base_dir / dest_name
        shutil.copy2(source_path, dest_path)
        return str(dest_path.absolute())

    def retrieve(self, storage_path: str, dest_path: str) -> None:
        shutil.copy2(storage_path, dest_path)

    def delete(self, storage_path: str) -> None:
        p = Path(storage_path)
        if p.exists():
            p.unlink()


class S3Storage:
    """Store backups on S3/MinIO."""

    def __init__(
        self,
        bucket: str | None = None,
        endpoint: str | None = None,
    ):
        self.bucket = bucket or settings.BACKUP_S3_BUCKET
        self.endpoint = endpoint or settings.BACKUP_S3_ENDPOINT

    def _get_client(self):
        import boto3

        kwargs: dict = {}
        if self.endpoint:
            kwargs["endpoint_url"] = self.endpoint
        return boto3.client("s3", **kwargs)

    def store(self, source_path: str, dest_name: str) -> str:
        client = self._get_client()
        client.upload_file(source_path, self.bucket, dest_name)
        if self.endpoint:
            return f"s3://{self.endpoint}/{self.bucket}/{dest_name}"
        return f"s3://{self.bucket}/{dest_name}"

    def retrieve(self, storage_path: str, dest_path: str) -> None:
        client = self._get_client()
        key = self._extract_key(storage_path)
        client.download_file(self.bucket, key, dest_path)

    def delete(self, storage_path: str) -> None:
        client = self._get_client()
        key = self._extract_key(storage_path)
        client.delete_object(Bucket=self.bucket, Key=key)

    @staticmethod
    def _extract_key(storage_path: str) -> str:
        if storage_path.startswith("s3://"):
            parts = storage_path.replace("s3://", "").split("/", 1)
            if len(parts) > 1:
                return parts[1]
        return storage_path


def get_storage() -> BackupStorageBackend:
    """Factory: return configured storage backend based on settings."""
    if settings.BACKUP_STORAGE_TYPE == "s3":
        return S3Storage()
    return LocalStorage()
