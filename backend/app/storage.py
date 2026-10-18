from __future__ import annotations

import io
import re
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from .config import get_settings

_KEY = re.compile(r"^[A-Za-z0-9/_.-]+$")


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...


def _check(key: str) -> str:
    if not _KEY.match(key) or ".." in key:
        raise ValueError(f"invalid object key: {key!r}")
    return key


class LocalStore:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key, data, content_type):
        p = self.root / _check(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key):
        return (self.root / _check(key)).read_bytes()


class MinioStore:
    def __init__(self, endpoint, access_key, secret_key, bucket, secure=False):
        from minio import Minio

        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = bucket
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def put(self, key, data, content_type):
        self.client.put_object(self.bucket, _check(key), io.BytesIO(data), len(data), content_type=content_type)

    def get(self, key):
        resp = self.client.get_object(self.bucket, _check(key))
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()


@lru_cache
def get_store() -> ObjectStore:
    s = get_settings()
    if s.storage_backend == "minio":
        return MinioStore(s.minio_endpoint, s.minio_access_key, s.minio_secret_key, s.minio_bucket, s.minio_secure)
    return LocalStore(s.local_storage_dir)
