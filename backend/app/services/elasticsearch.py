"""
Elasticsearch HTTP client using API key authentication only (no basic auth).
Single place for all ES calls; keeps routes thin and testable.
"""
from __future__ import annotations

import httpx
from typing import Any

from app.core.settings import settings


class ElasticsearchClientError(Exception):
    """Raised when an ES request fails; status and body available for mapping to HTTP."""
    def __init__(self, status_code: int, body: dict[str, Any] | str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Elasticsearch error: {status_code}")


class ElasticsearchService:
    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError("ELASTICSEARCH_API_KEY is not set")
        return {"Content-Type": "application/json", "Authorization": f"ApiKey {self.api_key}"}

    async def get_behavioral_analytics_collections(self) -> dict[str, Any]:
        """
        GET /_application/analytics
        Returns all behavioral analytics collections.
        """
        url = f"{self.url}/_application/analytics"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers())
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

    async def get_behavioral_analytics_collection(self, name: str) -> dict[str, Any]:
        """
        GET /_application/analytics/{name}
        Returns a single behavioral analytics collection by name.
        """
        url = f"{self.url}/_application/analytics/{name}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers())
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

    async def get_cluster_allocation_explain(self) -> dict[str, Any]:
        """
        GET /_cluster/allocation/explain
        Explains the allocation of a shard to a node.
        """
        url = f"{self.url}/_cluster/allocation/explain"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers())
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

    async def list_all_shards(self) -> dict[str, Any]:
        """
        GET /_cat/shards
        Lists all shards in the cluster.
        """
        url = f"{self.url}/_cat/shards?format=json"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers())
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:   
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

    async def list_all_aliases(self) -> dict[str, Any]:
        """
        GET /_cat/aliases
        Lists all aliases in the cluster.
        """
        url = f"{self.url}/_cat/aliases?format=json"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers())
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:   
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()