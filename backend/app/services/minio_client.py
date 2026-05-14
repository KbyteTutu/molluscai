from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import settings

_client: Optional[Minio] = None


def get_minio() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
    return _client


def ensure_bucket(bucket: str) -> None:
    client = get_minio()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def put_bytes(bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = get_minio()
    ensure_bucket(bucket)
    client.put_object(
        bucket,
        object_name,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return f"{bucket}/{object_name}"


def object_exists(bucket: str, object_name: str) -> bool:
    client = get_minio()
    try:
        client.stat_object(bucket, object_name)
        return True
    except S3Error:
        return False
