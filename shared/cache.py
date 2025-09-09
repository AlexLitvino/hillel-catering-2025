"""
set(key: str, value: dict)
get(key: str)
delete(key: str)
"""

import json
import os
from dataclasses import dataclass  # , asdict
from typing import Any

from django.core.cache import cache  # uses whatever BACKEND is configured
import redis

@dataclass
class Structure:
    id: int
    name: str

# Class oriented exactly to Redis
# class CacheService:
#     """
#     set(namespace='user_activation', key='12', value=Activation(...))
#     get(namespace='user_activation', key='12') -> Activation(...)
#     """
#
#     def __init__(self):
#         self.connection: redis.Redis = redis.Redis.from_url(
#             os.getenv("DJANGO_CACHE_URL", default="redis://cache:6379/0")
#         )
#
#     @staticmethod
#     def _build_key(namespace: str, key: str):
#         return f"{namespace}:{key}"
#
#     def set(self, namespace: str, key: str, value: dict, ttl: int | None = None):
#         # if isinstance(value, Structure):
#         #     payload = asdict(value)
#
#         payload = json.dumps(value)
#         self.connection.set(name=self._build_key(namespace, key), value=payload, ex=ttl)
#
#     def get(self, namespace: str, key: str):
#         result: str = self.connection.get(self._build_key(namespace, key))
#
#         return json.loads(result)
#
#     def delete(self, namespace: str, key: str):
#         self.connection.delete(self._build_key(namespace, key))


class CacheService:
    """
    set(namespace='user_activation', key='12', value=Activation(...))
    get(namespace='user_activation', key='12') -> Activation(...)
    """

    @staticmethod
    def _build_key(namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def set(self, namespace: str, key: str, value: dict | Structure, ttl: int | None = None):
        payload = json.dumps(value if isinstance(value, dict) else value.__dict__)
        cache.set(self._build_key(namespace, key), payload, timeout=ttl)

    def get(self, namespace: str, key: str) -> Any | None:
        result: str | None = cache.get(self._build_key(namespace, key))
        if result is None:
            return None
        return json.loads(result)

    def delete(self, namespace: str, key: str) -> None:
        cache.delete(self._build_key(namespace, key))