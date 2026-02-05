"""
Elasticsearch proxy routes. All ES calls use API key auth (no basic auth).
Thin layer: validate input, call service, map errors to HTTP.
"""
from typing import Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Path, Query, Body
from app.core.deps import get_elasticsearch_service
from app.services.elasticsearch import ElasticsearchService, ElasticsearchClientError
from app.models.elasticsearch import DataStreamLifecycleRequest, DataStreamModifyRequest
from app.schemas.elasticsearch import StandardResponse

router = APIRouter(prefix="/es", tags=["Elasticsearch"])

def _es_reason(body: Any) -> Optional[str]:
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
        raise HTTPException(status_code=401, detail="Elasticsearch authentication not configured")
    if exc.status_code == 404:
        raise HTTPException(status_code=404, detail=reason or "Resource not found")
    if 400 <= exc.status_code < 500:
        # 403 = forbidden (e.g. missing privilege); 400 = bad request
        raise HTTPException(status_code=422, detail=detail)
    raise HTTPException(status_code=503, detail="Search service temporarily unavailable")

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
        result = await elasticsearch_service.get_cluster_allocation_explain()
        return StandardResponse(success=True, message="Cluster allocation explain retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)

######################################################## ALL CAT ENDPOINTS ########################################################
@router.get(
    "/cat/shards",
    summary="List all shards",
    description="GET _cat/shards. Lists all shards in the cluster (API key auth).",
)
async def list_all_shards(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="Comma-separated index names"
    )
):
    """List all shards."""
    try:
        result = await elasticsearch_service.list_all_shards(index)
        return StandardResponse(success=True, message="Shards retrieved successfully", data=result)
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
    alias_name: Optional[str] = Query(
        default=None,
        description="Comma-separated alias names"
    ),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """List all aliases."""
    try:
        result = await elasticsearch_service.list_all_aliases(alias_name)
        return StandardResponse(success=True, message="Aliases retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/cat/indices",
    summary="List all indices",
    description="GET _cat/indices. Lists all indices in the cluster (API key auth).",
)
async def list_all_indices(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="Comma-separated index names"
    )
):
    """List all indices."""
    try:
        result = await elasticsearch_service.list_all_indices(index)
        return StandardResponse(success=True, message="Indices retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/cat/shard/allocation",
    summary="Get shard allocation information",
    description="GET _cat/allocation. Get shard allocation information (API key auth).",
)
async def get_shard_allocation_information(
    node_id: Optional[str] = Query(
        default=None,
        description="Comma-separated node IDs or names"
    ),  
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get shard allocation information."""
    try:
        result = await elasticsearch_service.get_shard_allocation_information(node_id)
        return StandardResponse(success=True, message="Shard allocation information retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/cat/document/count",
    summary="Get document count for a data stream, an index, or an entire cluster.",
    description="POST _cat/count. Get quick access to a document count for a data stream, an index, or an entire cluster. (API key auth).",
)
async def get_document_count(
    index: Optional[str] = Query(
        default=None,
        description="Comma-separated index names"
    ),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get document count for a data stream, an index, or an entire cluster."""
    try:
        result = await elasticsearch_service.get_document_count(index)
        return StandardResponse(success=True, message="Document count retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/cat/master",
    summary="Get the master of the cluster.",
    description="GET _cat/master. Get the master of the cluster (API key auth).",
)
async def get_master(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the master of the cluster."""
    try:
        result = await elasticsearch_service.get_master()
        return StandardResponse(success=True, message="Master retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/cat/ml/data_frame/analytics",
    summary="Get the data frame analytics of the cluster.",
    description="GET _cat/ml/data_frame/analytics. Get the data frame analytics of the cluster (API key auth).",
)
async def get_data_frame_analytics(
    id: Optional[str] = Query(
        default=None,
        description="Comma-separated data frame analytics IDs"
    ),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the data frame analytics of the cluster."""
    try:
        result = await elasticsearch_service.get_data_frame_analytics(id)
        return StandardResponse(success=True, message="Data frame analytics retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/cat/nodes",
    summary="Get the nodes of the cluster.",
    description="GET _cat/nodes. Get the nodes of the cluster (API key auth).",
)
async def get_nodes(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the nodes of the cluster."""
    try:
        result = await elasticsearch_service.get_nodes()
        return StandardResponse(success=True, message="Nodes retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/cat/templates",
    summary="Get the templates of the cluster.",
    description="GET _cat/templates. Get the templates of the cluster (API key auth).",
)
async def get_templates(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Query(
        default=None,
        description="Comma-separated template names"
    )
):
    """Get the templates of the cluster."""
    try:
        result = await elasticsearch_service.get_templates(name)
        return StandardResponse(success=True, message="Templates retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/cat/thread_pool",
    summary="Get the thread pool of the cluster.",
    description="GET _cat/thread_pool. Get the thread pool of the cluster (API key auth).",
)
async def get_thread_pool(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    thread_pool: Optional[str] = Query(
        default=None,
        description="Comma-separated thread pool names"
    )
):
    """Get the thread pool of the cluster."""
    try:
        result = await elasticsearch_service.get_thread_pool(thread_pool)
        return StandardResponse(success=True, message="Thread pool retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)

@router.get(
    "/cat/health",
    summary="Get the health of the cluster.",
    description="GET _cat/health. Get the health of the cluster (API key auth).",
)
async def get_health(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the health of the cluster."""
    try:
        result = await elasticsearch_service.get_health()
        return StandardResponse(success=True, message="Health retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
######################################################## ALL DATA STREAM ENDPOINTS ########################################################

@router.get(
    "/data_stream",
    summary="Get the data streams of the cluster.",
    description="GET _data_stream. Get the data streams of the cluster (API key auth).",
)
async def get_data_streams(
    name: Optional[str] =Query(
        default=None,
        description="Comma-separated data stream names"
    ),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
):
    """Get the data streams of the cluster."""
    try:
        result = await elasticsearch_service.get_data_streams(name)
        return StandardResponse(success=True, message="Data streams retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.delete(
    "/data_stream",
    summary="Delete a data stream",
    description="DELETE _data_stream. Delete a data stream (API key auth).",
)
async def delete_data_stream(
    name: str = Query(
        description="Data stream name"
    ),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
):
    """Delete a data stream."""
    try:
        result = await elasticsearch_service.delete_data_stream(name)
        return StandardResponse(success=True, message="Data stream deleted successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/data_stream/lifecycle/{name}",
    summary="Get the data stream lifecycle configs of the data streams",
    description="GET _data_stream/{name}/_lifecycle. Get the data stream lifecycle configs of the data streams (API key auth).",
)
async def get_data_stream_lifecycle(
    name: str = Path(
        ...,
        description="Data stream name"
    ),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the data stream lifecycle configs of the data streams."""
    try:
        result = await elasticsearch_service.get_data_stream_lifecycle(name)
        return StandardResponse(success=True, message="Data stream lifecycle configs retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.put(
    "/data_stream/lifecycle/{name}",
    summary="Update the data stream lifecycle configs of the data streams",
    description="PUT _data_stream/{name}/_lifecycle. Update the data stream lifecycle configs of the data streams (API key auth).",
)
async def update_data_stream_lifecycle(
    name: str = Path(
        ...,
        description="Data stream name"
    ),
    body: DataStreamLifecycleRequest = Body(...),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the data stream lifecycle configs of the data streams."""
    try:
        result = await elasticsearch_service.update_data_stream_lifecycle(name, body.data_retention)
        return StandardResponse(success=True, message="Data stream lifecycle configs updated successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.put(
    "/data_stream/lifecycle/{name}",
    summary="Update the data stream lifecycle configs of the data streams",
    description="PUT _data_stream/{name}/_lifecycle. Update the data stream lifecycle configs of the data streams (API key auth).",
)
async def update_data_stream_lifecycle(
    name: str = Path(
        ...,
        description="Data stream name"
    ),
    body: DataStreamLifecycleRequest = Body(...),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the data stream lifecycle configs of the data streams."""
    try:
        result = await elasticsearch_service.update_data_stream_lifecycle(name, body.data_retention)
        return StandardResponse(success=True, message="Data stream lifecycle configs updated successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/data_stream/mappings/{name}",
    summary="Get the data stream mappings of the data streams",
    description="GET _data_stream/{name}/_mappings. Get the data stream mappings of the data streams (API key auth).",
)
async def get_data_stream_mappings(
    name: str = Path(
        ...,
        description="Data stream name"
    ),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the data stream mappings of the data streams."""
    try:
        result = await elasticsearch_service.get_data_stream_mappings(name)
        return StandardResponse(success=True, message="Data stream mappings retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/data_stream/modify",
    summary="Modify a data stream",
    description="POST _data_stream/_modify. Modify a data stream (API key auth).",
)
async def modify_data_stream(
    body: DataStreamModifyRequest = Body(...),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the data stream mappings of the data streams."""
    try:
        result = await elasticsearch_service.modify_data_stream(body)
        return StandardResponse(success=True, message="Data stream modified successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/data_stream/promote/{name}",
    summary="Promote a data stream from a replicated data stream managed by cross-cluster replication (CCR) to a regular data stream.",
    description="POST _data_stream/_promote/{name}. Promote a data stream (API key auth).",
)
async def modify_data_stream(
    name: str = Path(
        ...,
        description="Data stream name"
    ),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """With CCR auto following, a data stream from a remote cluster can be replicated to the local cluster. 
    These data streams can't be rolled over in the local cluster. These replicated data streams roll over only if the upstream data stream rolls over. 
    In the event that the remote cluster is no longer available, the data stream in the local cluster can be promoted to a regular data stream, which allows these data streams to be rolled over in the local cluster.
    """
    try:
        result = await elasticsearch_service.promote_data_stream(name)
        return StandardResponse(success=True, message="Data stream promoted successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Elasticsearch API key not configured")
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        