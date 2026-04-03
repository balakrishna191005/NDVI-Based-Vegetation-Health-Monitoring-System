"""Disk-backed cache for expensive GEE JSON responses."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

import diskcache

from app.config import get_settings


def _key(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class NDVICache:
    def __init__(self) -> None:
        settings = get_settings()
        self._cache = diskcache.Cache(settings.cache_dir)

    def get_json(self, namespace: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        k = f"{namespace}:{_key(payload)}"
        return self._cache.get(k)

    def set_json(self, namespace: str, payload: Dict[str, Any], value: Dict[str, Any], expire: int = 3600) -> None:
        k = f"{namespace}:{_key(payload)}"
        self._cache.set(k, value, expire=expire)


ndvi_cache = NDVICache()
