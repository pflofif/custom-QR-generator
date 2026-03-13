"""
Async wrapper around the MinIO Python SDK.

All MinIO SDK calls are synchronous. They are run via asyncio.to_thread()
so they never block the FastAPI event loop.

Swap MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY / MINIO_USE_SSL
environment variables to point at a production MinIO instance without any
code changes.
"""
from __future__ import annotations

import io
import asyncio
from functools import lru_cache

from minio import Minio
from minio.error import S3Error

from app.config import settings


# ─── Singleton client ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _client() -> Minio:
    """Return (and cache) the MinIO client.  Thread-safe; created once."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )


# ─── Synchronous helpers (run in thread pool) ─────────────────────────────────

def _ensure_bucket_sync() -> None:
    c = _client()
    if not c.bucket_exists(settings.minio_bucket):
        c.make_bucket(settings.minio_bucket)


def _upload_sync(object_name: str, data: bytes, content_type: str) -> None:
    _client().put_object(
        settings.minio_bucket,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def _download_sync(object_name: str) -> bytes:
    response = _client().get_object(settings.minio_bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def _delete_sync(object_name: str) -> None:
    try:
        _client().remove_object(settings.minio_bucket, object_name)
    except S3Error as e:
        if e.code != "NoSuchKey":
            raise


# ─── Public async API ─────────────────────────────────────────────────────────

async def ensure_bucket() -> None:
    """Create the bucket if it does not already exist. Called once on startup."""
    await asyncio.to_thread(_ensure_bucket_sync)


async def upload_object(object_name: str, data: bytes, content_type: str) -> None:
    """Upload bytes to MinIO under *object_name*."""
    await asyncio.to_thread(_upload_sync, object_name, data, content_type)


async def download_object(object_name: str) -> bytes:
    """Download and return the raw bytes for *object_name*."""
    return await asyncio.to_thread(_download_sync, object_name)


async def delete_object(object_name: str) -> None:
    """Delete *object_name* from the bucket (no-op if it does not exist)."""
    await asyncio.to_thread(_delete_sync, object_name)
