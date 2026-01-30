"""
Elasticsearch proxy routes. All ES calls use API key auth (no basic auth).
Thin layer: validate input, call service, map errors to HTTP.
"""
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from app.core.deps import get_elasticsearch_service
from app.services.elasticsearch import ElasticsearchService, ElasticsearchClientError

router = APIRouter(prefix="/es", tags=["Elasticsearch"])


def _es_reason(body: Any) -> str | None:
    """Extract Elasticsearch error reason from response body for debugging."""
    if isinstance(body, dict) and "error" in body and isinstance(body["error"], dict):
        return body["error"].get("reason") or body["error"].get("type")
    return None


def _handle_es_error(exc: ElasticsearchClientError) -> None:
    """Map ES client errors to HTTP responses; include ES reason when available."""
    reason = _es_reason(exc.body)
    detail: str | dict[str, Any] = "Invalid request to search service"
    if reason:
        detail = {"message": "Elasticsearch rejected the request", "es_reason": reason}

    if exc.status_code == 401:
        raise HTTPException(status_code=503, detail="Elasticsearch authentication not configured")
    if exc.status_code == 404:
        raise HTTPException(status_code=404, detail=reason or "Resource not found")
    if 400 <= exc.status_code < 500:
        # 403 = forbidden (e.g. missing privilege); 400 = bad request
        raise HTTPException(status_code=422, detail=detail)
    raise HTTPException(status_code=503, detail="Search service temporarily unavailable")

@router.get(
    "/application/analytics",
    summary="List behavioral analytics collections",
    description="GET _application/analytics. Returns all behavioral analytics collections (API key auth).",
)
async def list_behavioral_analytics_collections(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """List all behavioral analytics collections."""
    try:
        return await elasticsearch_service.get_behavioral_analytics_collections()
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)

@router.get(
    "/application/analytics/{name}",
    summary="Get behavioral analytics collection by name",
    description="GET _application/analytics/{name}. Returns one collection by name (API key auth).",
)
async def get_behavioral_analytics_collection_by_name(
    name: str, 
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
    ):
    """Get a single behavioral analytics collection by name."""
    try:
        return await elasticsearch_service.get_behavioral_analytics_collection(name)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)

@router.get(
    "/cluster/allocation/explain",
    summary="Get cluster allocation explain",
    description="POST _cluster/allocation/explain. Explains the allocation of a shard to a node (API key auth).",
)
async def get_cluster_allocation_explain(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
):
    """Get cluster allocation explain."""
    try:
        return await elasticsearch_service.get_cluster_allocation_explain()
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)

@router.get(
    "/cat/shards",
    summary="List all shards",
    description="GET _cat/shards. Lists all shards in the cluster (API key auth).",
)
async def list_all_shards(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """List all shards."""
    try:
        return await elasticsearch_service.list_all_shards()
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)

@router.get(
    "/cat/aliases",
    summary="List all aliases",
    description="GET _cat/aliases. Lists all aliases in the cluster (API key auth).",
)
async def list_all_aliases(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """List all aliases."""
    try:
        return await elasticsearch_service.list_all_aliases()
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)