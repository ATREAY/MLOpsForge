"""Thin wrapper around a MinIO/S3-compatible bucket. Postgres only ever stores the
object key (storage_uri); actual bytes (dataset files, checkpoints, logs) live here.

Presigned URLs mean the frontend/plugin uploads/downloads directly against MinIO
instead of proxying large files through the FastAPI process.
"""

from functools import lru_cache

import boto3
from botocore.client import Config

from app.core.config import get_settings


@lru_cache
def get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    settings = get_settings()
    client = get_s3_client()
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if settings.S3_BUCKET not in existing:
        client.create_bucket(Bucket=settings.S3_BUCKET)


def presigned_put_url(key: str, expires_in: int = 3600) -> str:
    settings = get_settings()
    return get_s3_client().generate_presigned_url(
        "put_object", Params={"Bucket": settings.S3_BUCKET, "Key": key}, ExpiresIn=expires_in
    )


def presigned_get_url(key: str, expires_in: int = 3600) -> str:
    settings = get_settings()
    return get_s3_client().generate_presigned_url(
        "get_object", Params={"Bucket": settings.S3_BUCKET, "Key": key}, ExpiresIn=expires_in
    )


def object_uri(key: str) -> str:
    return f"s3://{get_settings().S3_BUCKET}/{key}"
