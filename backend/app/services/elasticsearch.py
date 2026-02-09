"""
Elasticsearch HTTP client using API key authentication only (no basic auth).
Single place for all ES calls; keeps routes thin and testable.
"""
from __future__ import annotations

import httpx
from typing import Any, Optional, List, Dict

from app.models.elasticsearch import (DataStreamModifyRequest, SearchInIndexRequest, 
    SearchMultipleDocumentsRequest, ReindexRequest, ClusterAllocationExplainRequest,
    IndexTemplateRequest, ComponentTemplateRequest, CreateIndexRequest, RollOverIndexRequest,
    CreateAliasRequest, ILMCreateUpdateRequest, ILMMoveToStepRequest, UpdateIndexSettingsRequest)
from app.schemas.elasticsearch import SearchDocumentsResponse

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

    async def get_behavioral_analytics_collections(self) -> Dict[str, Any]:
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

    async def get_behavioral_analytics_collection(self, name: str) -> Dict[str, Any]:
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

######################################################## CLUSTER ENDPOINTS ########################################################

    async def get_cluster_information(self) -> Dict[str, Any]:
        """
        GET /
        Get cluster information.
        """
        path = "/"
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
    
    async def get_cluster_allocation_explain(self, explanation: Optional[ClusterAllocationExplainRequest] = None) -> Dict[str, Any]:
        """
        GET /_cluster/allocation/explain
        POST /_cluster/allocation/explain
        Explains the allocation of a shard to a node.
        If explanation is provided, it will be used to explain the allocation of a shard to a node.
        If explanation is not provided, it will return the allocation of all shards to all nodes.
        """
        path = "/_cluster/allocation/explain"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        if explanation:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=self._headers(), params=params, json=explanation.model_dump(exclude_none=True))
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

######################################################## CAT ENDPOINTS ########################################################

    async def list_all_shards(self, index: Optional[str] = None) -> List[Dict[str, Any]]:
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

    async def list_all_aliases(self, alias_name: Optional[str] = None) -> List[Dict[str, Any]]:
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
    
    async def list_all_indices(self, index: Optional[str] = None) -> List[Dict[str, Any]]:
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
    
    async def get_shard_allocation_information(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
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
    
    async def get_document_count(self, index: Optional[str] = None) -> List[Dict[str, Any]]:
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
    
    async def get_master(self) -> Dict[str, Any]:
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
    
    async def get_data_frame_analytics(self, id: Optional[str] = None) -> List[Dict[str, Any]]:
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
    
    async def get_nodes(self) -> List[Dict[str, Any]]:
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
    
    async def get_templates(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
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
    
    async def get_thread_pool(self, thread_pool: Optional[str] = None) -> List[Dict[str, Any]]:
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
    
    async def get_health(self) -> Dict[str, Any]:
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
    
    ######################################################## ALL DATA STREAM ENDPOINTS ########################################################
    
    async def get_data_streams(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        GET /_data_stream
        Get the data streams of the cluster.
        """
        path = "/_data_stream"
        if name:
            path += f"/{name}"
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
    
    async def delete_data_stream(self, name: str) -> Dict[str, Any]:
        """
        DELETE /_data_stream/{name}
        Delete a data stream.
        """
        path = f"/_data_stream/{name}"
        url = f"{self.url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self._headers())
    
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_data_stream_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        GET /_data_stream/_stats
        Get the stats of the data streams.
        """
        path = "/_data_stream/_stats"
        if name:
            path = f"/_data_stream/{name}/_stats"
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
    
    async def get_data_stream_lifecycle(self, name: str) -> Dict[str, Any]:
        f"""
        GET /_data_stream/{name}/_lifecycle
        Get the data stream lifecycle configuration of one or more data streams.
        """
        path = f"/_data_stream/{name}/_lifecycle"
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
    
    async def update_data_stream_lifecycle(self, name: str, data_retention: str) -> Dict[str, Any]:
        f"""
        PUT /_data_stream/{name}/_lifecycle
        Update the data stream lifecycle configuration of the data stream.
        """
        path = f"/_data_stream/{name}/_lifecycle"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        json = {
            "data_retention": data_retention
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=self._headers(), params=params, json=json)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_data_stream_mappings(self, name: str) -> Dict[str, Any]:
        f"""
        GET /_data_stream/{name}/_mappings
        Get the data stream mappings of the data stream.
        """
        path = f"/_data_stream/{name}/_mappings"
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
    
    async def modify_data_stream(self, actions: DataStreamModifyRequest) -> Dict[str, Any]:
        f"""
        POST /_data_stream/_modify
        Update the data stream of the data stream.
        """
        path = f"/_data_stream/_modify"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=actions.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def promote_data_stream(self, name: str) -> Dict[str, Any]:
        f"""
        POST /_data_stream/_promote/{name}
        Promote a data stream from a replicated data stream managed by cross-cluster replication (CCR) to a regular data stream.
        """
        path = f"/_data_stream/_promote/{name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
######################################################## ALL DOCUMENT ENDPOINTS ########################################################
    async def search_in_index(self, index: str, body: SearchInIndexRequest) -> Dict[str, Any]:
        f"""
        GET /{index}/_search
        Search for documents in an index.
        """
        path = f"/{index}/_search"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        } 
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=body.to_es_payload())
        if response.status_code != 200:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            raise ElasticsearchClientError(response.status_code, error_body)
        es_data = response.json()
        total_ids_in_index = es_data["hits"]["total"]["value"]
        ids_by_index : Dict[str, List[str]] = {}
        hits_list = es_data["hits"]["hits"]
        for hit in hits_list:
            idx = hit["_index"]
            doc_id = hit["_id"]
            if idx and doc_id:
                ids_by_index.setdefault(idx, []).append(doc_id)
            total_ids_returned = sum(len(v) for v in ids_by_index.values())
        es_data["ids_by_index"] = ids_by_index
        es_data["total_ids_returned"] = total_ids_returned
        es_data["total_ids_in_index"] = total_ids_in_index
        return SearchDocumentsResponse.model_validate(es_data)
    
    async def search_multiple_documents(self, index: str, docs: SearchMultipleDocumentsRequest) -> Dict[str, Any]:
        f"""
        POST /{index}/_mget
        Search for multiple documents in an index.
        """
        path = f"/{index}/_mget"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=docs.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            raise ElasticsearchClientError(response.status_code, error_body)
        return response.json()

    async def search_document_by_id(self, index: str, id: str) -> Dict[str, Any]:
        f"""
        GET /{index}/_doc/{id}
        Search for a document by id in an index.
        """
        path = f"/{index}/_doc/{id}"
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

    async def delete_document_by_id(self, index: str, id: str) -> Dict[str, Any]:
        f"""
        DELETE /{index}/_doc/{id}
        Delete a document by id in an index.
        """
        path = f"/{index}/_doc/{id}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def check_document_exists_by_id(self, index: str, id: str) -> bool:
        f"""
        HEAD /{index}/_doc/{id}
        Check if a document exists by id in an index.
        """
        path = f"/{index}/_doc/{id}"
        url = f"{self.url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.head(url, headers=self._headers())
        return response.status_code == 200
    
    async def check_source_exists_by_id(self, index: str, id: str) -> bool:
        f"""
        HEAD /{index}/_source/{id}
        Check if a source exists by id in an index.
        """
        path = f"/{index}/_source/{id}"
        url = f"{self.url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.head(url, headers=self._headers())
        return response.status_code == 200
    
    async def get_document_source_by_id(self, index:str, id:str) -> Dict[str, Any]:
        f"""
        GET /{index}/_source/{id}
        Get the source of a document by id in an index.
        """
        path = f"/{index}/_source/{id}"
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
    
    async def reindex_documents(self, body: ReindexRequest) -> Dict[str, Any]:
        f"""
        POST /_reindex
        Reindex documents from one index to another.
        """
        path = "/_reindex"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
                                    
    async def get_term_vectors_for_document(self, index: str, id: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /{index}/_termvectors
        Get term vectors for a document in an index.
        """
        path = f"/{index}/_termvectors"
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
    
######################################################## FEATURES ENDPOINTS ########################################################
    
    async def get_features(self) -> Dict[str, Any]:
        f"""
        GET /_features
        Get the features of the cluster.
        """
        path = f"/_features"
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
    
    async def reset_features(self) -> Dict[str, Any]:
        f"""
        POST /_features/_reset
        RESET the features of the cluster.
        """
        path = f"/_features/_reset"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
######################################################## INDEX ENDPOINTS ########################################################

    async def get_index(self, index: str) -> Dict[str, Any]:
        f"""
        GET /{index}
        Get the information of an index.
        """
        path = f"/{index}"
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
    
    async def create_index(self, index: str, body: CreateIndexRequest) -> Dict[str, Any]:
        f"""
        POST /{index}
        Create an index.
        """
        path = f"/{index}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True, by_alias=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def delete_index(self, index: str) -> Dict[str, Any]:
        f"""
        DELETE /{index}
        Delete an index.
        """
        path = f"/{index}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def check_index_exists(self, index: str) -> bool:
        f"""
        HEAD /{index}
        Check if an index exists.
        """
        path = f"/{index}"
        url = f"{self.url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.head(url, headers=self._headers())
        return response.status_code == 200
    
    async def get_component_template(self, name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /_component_template
        Get the component templates of the cluster.
        If name is provided, get the component template with the given name.
        """
        path = f"/_component_template"
        if name:
            path += f"/{name}"
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
    
    async def create_component_template(self, name: str, body: ComponentTemplateRequest) -> Dict[str, Any]:
        f"""
        POST /_component_template/{name}
        Create the component template of the cluster.
        """
        path = f"/_component_template/{name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True, by_alias=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def update_component_template(self, name: str, body: ComponentTemplateRequest) -> Dict[str, Any]:
        f"""
        PUT /_component_template/{name}
        Update the component template of the cluster.
        """
        path = f"/_component_template/{name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True, by_alias=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def check_component_template_exists_by_name(self, name: str) -> bool:
        f"""
        HEAD /_component_template/{name}
        Check if a component template exists by name.
        """
        path = f"/_component_template/{name}"
        url = f"{self.url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.head(url, headers=self._headers())
        return response.status_code == 200
    
    async def delete_component_template(self, name: str = None) -> Dict[str, Any]:
        f"""
        DELETE /_component_template/{name}
        Delete the component template of the cluster.
        """
        path = f"/_component_template/{name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_index_template(self, name: str = None) -> Dict[str, Any]:
        f"""
        GET /_index_template/{name}
        Get the index template of the cluster.
        """
        path = f"/_index_template/{name}"
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
    
    async def create_index_template(self, name: str, body: IndexTemplateRequest) -> Dict[str, Any]:
        f"""
        POST /_index_template/{name}
        Create the index template of the cluster.
        """
        path = f"/_index_template/{name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def update_index_template(self, name: str, body: IndexTemplateRequest) -> Dict[str, Any]:
        f"""
        PUT /_index_template/{name}
        Update the index template of the cluster.
        """
        path = f"/_index_template/{name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def delete_index_template(self, name: str) -> Dict[str, Any]:
        f"""
        DELETE /_index_template/{name}
        Delete the index template of the cluster.
        """
        path = f"/_index_template/{name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

    async def check_index_template_exists(self, name: str) -> bool:
        f"""
        HEAD /_index_template/{name}
        Check if an index template exists.
        """
        path = f"/_index_template/{name}"
        url = f"{self.url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.head(url, headers=self._headers())
        return response.status_code == 200
    
    async def get_disk_usage_of_index(self, name: str) -> Dict[str, Any]:
        f"""
        POST /{name}/_disk_usage
        Get the disk usage of an index.
        """
        path = f"/{name}/_disk_usage"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def clear_cache_of_index(self, name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        POST /{name}/_cache/clear
        Clear the cache of an index.
        """
        if name:
            path = f"/{name}/_cache/clear"
        else:
            path = f"/_cache/clear"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def close_index(self, name: str) -> Dict[str, Any]:
        f"""
        POST /{name}/_close
        Close an index.
        """
        path = f"/{name}/_close"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def open_index(self, name: str) -> Dict[str, Any]:
        f"""
        POST /{name}/_open
        Open an index.
        """
        path = f"/{name}/_open"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

    async def get_recovery_status_of_index(self, name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /_recovery
        Get index recovery information
        """
        if name:
            path = f"/{name}/_recovery"
        else:
            path = f"/_recovery"
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
    
    async def refresh_index(self, name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /_refresh
        Get index recovery information
        """
        if name:
            path = f"/{name}/_refresh"
        else:
            path = f"/_refresh"
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
    
    async def resolve_cluster(self, name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /_resolve/cluster
        Resolve a cluster.
        """
        if name:
            path = f"/_resolve/cluster/{name}"
        else:
            path = f"/_resolve/cluster"
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
    
    async def resolve_index(self, name: str) -> Dict[str, Any]:
        f"""
        GET /_resolve/index/{name}
        Resolve an index.
        """
        path = f"/_resolve/index/{name}"
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
    
    async def get_alias(self, index: Optional[str] = None, alias_name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /_alias
        GET /_alias/{alias_name}
        GET /{index}/_alias
        GET /{index}/_alias/{alias_name}
        Get an alias.   
        """
        if index:
            path = f"/{index}/_alias"
        else:
            path = f"/_alias"
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
    
    async def create_alias(self, index: str, alias_name: str, body: CreateAliasRequest, single: bool) -> Dict[str, Any]:
        f"""
        POST /{index}/_alias/{alias_name}
        POST /{index}/_aliases/{alias_name}
        Create an alias.   
        If single is true, creates a single alias, if false, creates a list of aliases
        """
        if single:
            path = f"/{index}/_alias/{alias_name}"
        else:
            path = f"/{index}/_aliases/{alias_name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def update_alias(self, index: str, alias_name: str, body: CreateAliasRequest, single: bool) -> Dict[str, Any]:
        f"""
        PUT /{index}/_alias/{alias_name}
        PUT /{index}/_aliases/{alias_name}
        Update an alias.   
        If single is true, updates a single alias, if false, updates a list of aliases
        """
        if single:
            path = f"/{index}/_alias/{alias_name}"  
        else:
            path = f"/{index}/_aliases/{alias_name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def delete_alias(self, index: str, alias_name: str, single: bool) -> Dict[str, Any]:
        f"""
        DELETE /{index}/_alias/{alias_name}
        DELETE /{index}/_aliases/{alias_name}
        Delete an alias.   
        If single is true, deletes a single alias, if false, deletes a list of aliases
        """
        if single:
            path = f"/{index}/_alias/{alias_name}"  
        else:
            path = f"/{index}/_aliases/{alias_name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def rollover_index(self, alias_name: str, new_index_name: Optional[str] = None, body: RollOverIndexRequest = None) -> Dict[str, Any]:
        f"""
        POST /{alias_name}/_rollover
        Roll over an index.
        """
        path = f"/{alias_name}/_rollover"
        if new_index_name:
            path += f"/{new_index_name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_index_settings(self, index_name: Optional[str] = None, alias_name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /_settings
        GET /_settings/{alias_name}
        GET /{index_name}/_settings
        GET /{index_name}/_settings/{alias_name}
        Get index settings.
        """
        if index_name:
            path = f"/{index_name}/_settings"
        else:
            path = f"/_settings"
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
    
    async def update_index_settings(self, body: UpdateIndexSettingsRequest, index_name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        PUT /_settings
        PUT /{index_name}/_settings
        Update index settings.
        """
        if index_name:
            path = f"/{index_name}/_settings"
        else:
            path = f"/_settings"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_index_segments(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /_segments
        GET /{index_name}/_segments
        Get index segments.
        """
        if index_name:
            path = f"/{index_name}/_segments"
        else:
            path = f"/_segments"
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
    
    async def get_index_shard_stores(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /_shard_stores
        GET /{index_name}/_shard_stores
        Get index shard stores.
        """
        if index_name:
            path = f"/{index_name}/_shard_stores"
        else:
            path = f"/_shard_stores"
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
    
    async def get_index_statistics(self, index_name: Optional[str] = None, metric: Optional[str] = None) -> Dict[str, Any]:
        f"""
        GET /_stats
        GET /{index_name}/_stats
        GET /_stats/{metric}
        GET /{index_name}/_stats/{metric}
        Get index statistics.
        """
        if index_name:
            path = f"/{index_name}/_stats"
        else:
            path = f"/_stats"
        if metric:
            path += f"/{metric}"
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
    
######################################################## Index Lifecycle Management ########################################################

    async def get_ilm_policy(self, policy_name: Optional[str] = None) -> Dict[str, Any]:
        """
        GET /_ilm/policy
        GET /_ilm/policy/{policy_name}
        Get ILM policy.
        """
        if policy_name:
            path = f"/_ilm/policy/{policy_name}"
        else:
            path = f"/_ilm/policy"
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

    async def create_update_ilm_policy(self, policy_name: str, body: ILMCreateUpdateRequest) -> Dict[str, Any]:
        """
        PUT /_ilm/policy/{policy_name}
        Create or update ILM policy.
        """
        path = f"/_ilm/policy/{policy_name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True, by_alias=True))
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()

    async def delete_ilm_policy(self, policy_name: str) -> Dict[str, Any]:
        """
        DELETE /_ilm/policy/{policy_name}
        Delete ILM policy.
        """
        path = f"/_ilm/policy/{policy_name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def explain_ilm_policy(self, index: str) -> Dict[str, Any]:
        """
        GET /{index}/_ilm/explain
        Explain ILM policy.
        """
        path = f"/{index}/_ilm/explain"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body= response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def get_ilm_status(self) -> Dict[str, Any]:
        """
        GET /_ilm/status
        Get ILM status.
        """
        path = f"/_ilm/status"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body= response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def move_to_next_ilm_step(self, index_name: str, body: ILMMoveToStepRequest) -> Dict[str, Any]:
        """
        POST /_ilm/move/{index}
        Move to next ILM step.
        """
        path = f"/_ilm/move/{index_name}"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=body.model_dump(exclude_none=True))
        if response.status_code != 200:
            try:
                body= response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def remove_ilm_policy(self, index: str) -> Dict[str, Any]:
        f"""
        POST {index}/_ilm/remove
        Remove ILM policy.
        """
        path = f"/{index}/_ilm/remove"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body= response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()
    
    async def retry_ilm_policy(self, index: str) -> Dict[str, Any]:
        f"""
        POST {index}/_ilm/retry
        Retry ILM policy.
        """
        path = f"/{index}/_ilm/retry"
        url = f"{self.url}{path}"
        params = {
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), params=params)
        if response.status_code != 200:
            try:
                body= response.json()
            except Exception:
                body = response.text
            raise ElasticsearchClientError(response.status_code, body)
        return response.json()