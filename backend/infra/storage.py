"""
infra/storage.py

对象存储访问层（统一 StorageClient 接口）。
- local      → 本地文件系统（适合开发调试，无需任何云账号）
- aliyun_oss → 阿里云 OSS
- aws_s3     → Amazon S3

使用方法（Skills 中统一调用）：
    from infra.storage import get_storage

    storage = get_storage()
    url = storage.put("raw/user_1/q1.jpg", image_bytes, content_type="image/jpeg")
    data = storage.get("raw/user_1/q1.jpg")
    storage.delete("raw/user_1/q1.jpg")
"""
from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from .config import infra_config, StorageConfig


class StorageClient(ABC):
    """统一存储客户端抽象基类"""

    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """上传文件，返回可访问的 URL"""
        ...

    @abstractmethod
    def get(self, key: str) -> bytes:
        """按 key 下载文件，返回字节内容"""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除文件"""
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查文件是否存在"""
        ...

    def public_url(self, key: str) -> str:
        """返回文件的可访问 URL（子类可覆盖）"""
        raise NotImplementedError


# ── 本地文件系统实现 ────────────────────────────────────────────

class LocalStorageClient(StorageClient):
    """将文件存储到本地目录，模拟 OSS 行为"""

    def __init__(self, cfg: StorageConfig):
        self.root = Path(cfg.root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.base_url = cfg.base_url.rstrip("/")
        print(f"[Storage] 📁 LocalStorage root={self.root}")

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._path(key).write_bytes(data)
        return self.public_url(key)

    def get(self, key: str) -> bytes:
        p = self._path(key)
        if not p.exists():
            raise FileNotFoundError(f"LocalStorage: key not found: {key}")
        return p.read_bytes()

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def public_url(self, key: str) -> str:
        return f"{self.base_url}/{key}"


# ── 阿里云 OSS 实现 ─────────────────────────────────────────────

class AliyunOSSClient(StorageClient):
    """阿里云 OSS 客户端（依赖 oss2 包：pip install oss2）"""

    def __init__(self, cfg: StorageConfig):
        try:
            import oss2
        except ImportError:
            raise ImportError("阿里云 OSS 需要安装 oss2：pip install oss2")

        auth = oss2.Auth(cfg.access_key_id, cfg.access_key_secret)
        self.bucket = oss2.Bucket(auth, cfg.endpoint, cfg.bucket)
        self.base_url = cfg.base_url.rstrip("/")
        print(f"[Storage] ☁ AliyunOSS bucket={cfg.bucket} region={cfg.region}")

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.bucket.put_object(key, data, headers={"Content-Type": content_type})
        return self.public_url(key)

    def get(self, key: str) -> bytes:
        result = self.bucket.get_object(key)
        return result.read()

    def delete(self, key: str) -> None:
        self.bucket.delete_object(key)

    def exists(self, key: str) -> bool:
        import oss2
        return oss2.ObjectExists(self.bucket, key)

    def public_url(self, key: str) -> str:
        return f"{self.base_url}/{key}"


# ── AWS S3 实现 ─────────────────────────────────────────────────

class AWSS3Client(StorageClient):
    """AWS S3 客户端（依赖 boto3：pip install boto3）"""

    def __init__(self, cfg: StorageConfig):
        try:
            import boto3
        except ImportError:
            raise ImportError("AWS S3 需要安装 boto3：pip install boto3")

        self._s3 = boto3.client(
            "s3",
            region_name=cfg.region,
            aws_access_key_id=cfg.access_key_id,
            aws_secret_access_key=cfg.secret_access_key,
        )
        self.bucket_name = cfg.bucket
        self.base_url = cfg.base_url.rstrip("/")
        print(f"[Storage] ☁ AWSS3 bucket={cfg.bucket} region={cfg.region}")

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._s3.put_object(Bucket=self.bucket_name, Key=key, Body=data, ContentType=content_type)
        return self.public_url(key)

    def get(self, key: str) -> bytes:
        obj = self._s3.get_object(Bucket=self.bucket_name, Key=key)
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self.bucket_name, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def public_url(self, key: str) -> str:
        return f"{self.base_url}/{key}"


# ── 工厂函数 ────────────────────────────────────────────────────

_storage_instance: StorageClient | None = None


def get_storage() -> StorageClient:
    """懒加载并缓存 StorageClient 单例（Skills 统一调用此函数）"""
    global _storage_instance
    if _storage_instance is None:
        cfg = infra_config.get_storage_config()
        if cfg.driver == "local":
            _storage_instance = LocalStorageClient(cfg)
        elif cfg.driver == "aliyun_oss":
            _storage_instance = AliyunOSSClient(cfg)
        elif cfg.driver == "aws_s3":
            _storage_instance = AWSS3Client(cfg)
        else:
            raise ValueError(f"Unsupported storage driver: {cfg.driver}")
    return _storage_instance
