"""
Elasticsearch HTTP client using API key authentication only (no basic auth).
Single place for all ES calls; keeps routes thin and testable.
"""
from __future__ import annotations

import httpx
from typing import Any, Optional, List

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
        path = "/_cluster/allocation/explain"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

    async def list_all_shards(self, index: Optional[str] = None) -> List[dict[str, Any]]:
        """
        GET /_cat/shards
        Lists all shards in the cluster.
        """
        path = "/_cat/shards"
        if index:
            path += f"/{index}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:   
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

    async def list_all_aliases(self, alias_name: Optional[str] = None) -> List[dict[str, Any]]:
        """
        GET /_cat/aliases
        Lists all aliases in the cluster.
        """
        path = "/_cat/aliases"
        if alias_name:
            path += f"/{alias_name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:   
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def list_all_indices(self, index: Optional[str] = None) -> List[dict[str, Any]]:
        """
        GET /_cat/indices
        Lists all indices in the cluster.
        """
        path = "/_cat/indices"
        if index:
            path += f"/{index}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_shard_allocation_information(self, node_id: Optional[str] = None) -> List[dict[str, Any]]:
        """
        GET /_cat/allocation
        Get shard allocation information.
        """
        path = "/_cat/allocation"
        if node_id:
            path += f"/{node_id}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_document_count(self, index: Optional[str] = None) -> List[dict[str, Any]]:
        """
        GET /_cat/count
        Get document count for a data stream, an index, or an entire cluster.
        """
        path = "/_cat/count"
        if index:
            path += f"/{index}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_master(self) -> dict[str, Any]:
        """
        GET /_cat/master
        Get the master of the cluster.
        """
        path = "/_cat/master"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_data_frame_analytics(self, id: Optional[str] = None) -> List[dict[str, Any]]:
        """
        GET /_cat/ml/data_frame/analytics
        Get the data frame analytics of the cluster.
        """
        path = "/_cat/ml/data_frame/analytics"
        if id:
            path += f"/{id}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_nodes(self) -> List[dict[str, Any]]:
        """
        GET /_cat/nodes
        Get the nodes of the cluster.
        """
        path = "/_cat/nodes"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_templates(self, name: Optional[str] = None) -> List[dict[str, Any]]:
        """
        GET /_cat/templates
        Get the templates of the cluster.
        """
        path = "/_cat/templates"
        if name:
            path+=f"/{name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_thread_pool(self, thread_pool: Optional[str] = None) -> List[dict[str, Any]]:
        """
        GET /_cat/thread_pool
        Get the thread pool of the cluster.
        """
        path = "/_cat/thread_pool"
        url = f"{self.url}{path}"
        if thread_pool:
            path += f"/{thread_pool}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_health(self) -> dict[str, Any]:
        """
        GET /_cat/health
        Get the health of the cluster.
        """
        path = "/_cat/health"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()