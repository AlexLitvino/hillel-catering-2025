"""
    set(key: str, value: dict)
    get(key: str)
    delete(key: str)
"""
from typing import Any
from dataclasses import asdict, dataclass
import json

import redis

@dataclass
class Structure:
    id: int
    name: str


class CacheService:
    """
    set(namespace='user_activation', key='12', value=Activation(...))
    get(namespace='user_activation', key='12') -> Activation(...)
    """

    def __init__(self):
        self.connection: redis.Redis =  redis.Redis.from_url(
            "redis://localhost:6380/0"
        )

    @staticmethod
    def _build_key(namespace: str, key: str):
        return f"{namespace}:{key}"

    def set(self, namespace: str, key: str, value: dict, ttl: int | None = None):
        # if isinstance(value, Structure):
        #     payload = asdict(value)

        payload = json.dumps(value)
        self.connection.set(
            name=self._build_key(namespace, key),
            value=payload,
            ex=ttl
        )

    def get(self, namespace: str, key: str):
        result: str = self.connection.get(
            self._build_key(namespace, key)
        )

        return json.loads(result)

    def delete(self, namespace: str, key: str):
        self.connection.delete(
            self._build_key(namespace, key)
        )
