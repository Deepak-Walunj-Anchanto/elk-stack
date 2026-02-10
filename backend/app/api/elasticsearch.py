"""
Elasticsearch proxy routes. All ES calls use API key auth (no basic auth).
Thin layer: validate input, call service, map errors to HTTP.
"""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Path, Query, Body
from app.core.deps import get_elasticsearch_service
from app.services.elasticsearch import ElasticsearchService, ElasticsearchClientError
from app.models.elasticsearch import (DataStreamLifecycleRequest, DataStreamModifyRequest, 
    SearchInIndexRequest, SearchMultipleDocumentsRequest, ReindexRequest, ClusterAllocationExplainRequest,
    IndexTemplateRequest, ComponentTemplateRequest, CreateIndexRequest, RollOverIndexRequest,
    CreateAliasRequest, ILMCreateUpdateRequest, ILMMoveToStepRequest, UpdateIndexSettingsRequest,
    FieldCapsRequest, QueryES)
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

######################################################## CLUSTER ENDPOINTS ########################################################

@router.get(
    "/cluster",
    summary="Get cluster information",
    description="GET /. Get cluster information (API key auth).",
)
async def get_cluster_information(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get cluster information."""
    try:
        result = await elasticsearch_service.get_cluster_information()
        return StandardResponse(success=True, message="Cluster information retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/cluster/allocation/explain",
    summary="Get cluster allocation explain",
    description="POST _cluster/allocation/explain. Explains the allocation of a shard to a node (API key auth).",
)
async def get_cluster_allocation_explain(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    body: Optional[ClusterAllocationExplainRequest] = Body(default=None, description="Cluster allocation explain request")
):
    """Get cluster allocation explain."""
    try:
        result = await elasticsearch_service.get_cluster_allocation_explain(body)
        return StandardResponse(success=True, message="Cluster allocation explain retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
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
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
######################################################## ALL DOCUMENT ENDPOINTS ########################################################

@router.get(
    "/{index}/search",
    summary="Search in an index",
    description="GET {index}/_search. Search in an index (API key auth).",
)
async def search_in_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
    body : SearchInIndexRequest = Body(..., description="Search Request") 
):
    """Search for documents in an index."""
    try:
        result = await elasticsearch_service.search_in_index(index, body)
        return StandardResponse(success=True, message="Documents retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/{index}/documents",
    summary="Search for multiple documents in an index",
    description="GET {index}/_mget. Search for multiple documents in an index (API key auth).",
)
async def search_multiple_documents(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
    body : SearchMultipleDocumentsRequest = Body(..., description="Search multiple doRequest") 
):
    """Search for documents in an index."""
    try:
        result = await elasticsearch_service.search_multiple_documents(index, body)
        return StandardResponse(success=True, message="Documents retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/{index}/document/{id}",
    summary="Search for document by id in an index",
    description="GET {index}/_doc/{id}. Search for document by id in an index (API key auth).",
)
async def search_document_by_id(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
    id: str = Path(
        ...,
        description="Document id"
    )
):
    """Search for documents in an index."""
    try:
        result = await elasticsearch_service.search_document_by_id(index, id)
        return StandardResponse(success=True, message="Document retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.delete(
    "/{index}/document/{id}",
    summary="Delete a document by id in an index",
    description="DELETE {index}/_doc/{id}. Delete a document by id in an index (API key auth).",
)
async def delete_document_by_id(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
    id: str = Path(
        ...,
        description="Document id"
    )
):
    """Delete a document by id in an index."""
    try:
        result = await elasticsearch_service.delete_document_by_id(index, id)
        return StandardResponse(success=True, message="Document deleted successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.head(
    "/{index}/document/{id}",
    summary="Check if a document exists by id in an index",
    description="HEAD {index}/_doc/{id}. Check if a document exists by id in an index (API key auth).",
)
async def check_document_exists_by_id(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
    id: str = Path(
        ...,
        description="Document id"
    )
):
    """Check if a document exists by id in an index."""
    try:
        result = await elasticsearch_service.check_document_exists_by_id(index, id)
        if not result:
            raise HTTPException(status_code=404)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.head(
    "/{index}/source/{id}",
    summary="Check if the source of a document by id in an index exists",
    description="HEAD {index}/_source/{id}. Get the source of a document by id in an index (API key auth).",
)
async def check_source_exists_by_id(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
    id: str = Path(
        ...,
        description="Document id"
    )
):
    """Check if the source of a document by id in an index exists."""
    try:
        result = await elasticsearch_service.check_source_exists_by_id(index, id)
        if not result:
            raise HTTPException(status_code=404)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/{index}/source/{id}",
    summary="Get the source of a document by id in an index",
    description="GET {index}/_source/{id}. Get the source of a document by id in an index (API key auth).",
)
async def get_document_source_by_id(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
    id: str = Path(
        ...,
        description="Document id"
    )
):
    """Get the source of a document by id in an index."""
    try:
        result = await elasticsearch_service.get_document_source_by_id(index, id)
        return StandardResponse(success=True, message="Document source retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/documents/reindex",
    summary="Reindex documents from one index to another",
    description="POST /_reindex. Reindex documents from one index to another (API key auth).",
)
async def reindex_documents(
    body: ReindexRequest = Body(..., description="Reindex Request"),
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Reindex documents from one index to another."""
    try:
        print(body.model_dump())
        result = await elasticsearch_service.reindex_documents(body)
        return StandardResponse(success=True, message="Documents reindexed successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/{index}/termvectors/{id}",
    summary="Get term vectors for a document in an index",
    description="GET {index}/_termvectors. Get term vectors for a document in an index (API key auth).",
)
async def get_term_vectors_for_document(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
    id: str = Path(
        ...,
        description="Document id"
    )
):
    """Get term vectors for a document in an index."""
    try:
        result = await elasticsearch_service.get_term_vectors_for_document(index, id)
        return StandardResponse(success=True, message="Term vectors retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
######################################################## FEATURES ENDPOINTS ########################################################
        
@router.get(
    "/features",
    summary="Get the features of the cluster",
    description="GET /_features. Get the features of the cluster (API key auth).",
)
async def get_features(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Get the features of the cluster."""
    try:
        result = await elasticsearch_service.get_features()
        return StandardResponse(success=True, message="Features retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/features/reset",
    summary="Reset the features of the cluster",
    description="POST /_features/_reset. Reset the features of the cluster (API key auth).",
)
async def reset_features(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service)
):
    """Reset the features of the cluster."""
    try:
        result = await elasticsearch_service.reset_features()
        return StandardResponse(success=True, message="Features reset successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
######################################################## Index ENDPOINTS ########################################################

@router.get(
    "/{index}",
    summary="Get an index",
    description="GET {index}. Get an index (API key auth).",
)
async def get_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    )
):
    """Get index information."""
    try:
        result = await elasticsearch_service.get_index(index)
        return StandardResponse(success=True, message="Index information retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/{index}",
    summary="Create an index",
    description="POST {index}. Create an index (API key auth).",
)
async def create_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
    body: CreateIndexRequest = Body(... , description="Create index request")
):
    """Create index."""
    try:
        print(body.model_dump(exclude_none=True, by_alias=True))
        result = await elasticsearch_service.create_index(index, body)
        return StandardResponse(success=True, message="Index created successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.delete(
    "/{index}",
    summary="Delete an index",
    description="DELETE {index}. Delete an index (API key auth).",
)
async def delete_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
):
    """Delete index."""
    try:
        result = await elasticsearch_service.delete_index(index)
        return StandardResponse(success=True, message="Index deleted successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.head(
    "/{index}",
    summary="Check if an index exists",
    description="HEAD {index}. Check if an index exists (API key auth).",
)
async def check_index_exists(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="Index name"
    ),
):
    """Check if an index exists."""
    try:
        result = await elasticsearch_service.check_index_exists(index)
        if not result:
            raise HTTPException(status_code=404)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.head(
    "/component/template/{name}",
    summary="Check if a component template exists by name",
    description="HEAD /_component_template/{name}. Check if a component template exists by name (API key auth).",
)
async def check_component_template_exists_by_name(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: str = Path(
        ...,
        description="Component template name"
    )
):
    """Check if a component template exists by name."""
    try:
        result = await elasticsearch_service.check_component_template_exists_by_name(name)
        if not result:
            raise HTTPException(status_code=404)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
 
@router.get(
    "/component/template",
    summary="Get the component template of the cluster",   
    description="GET /_component_template. Get the component template of the cluster (API key auth).",
)
async def get_component_templates(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Query(
        default=None,
        description="template name"
    )
):
    """Get the component template of the cluster."""
    try:
        result = await elasticsearch_service.get_component_template(name)
        return StandardResponse(success=True, message="Component template retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/component/template/{name}",
    summary="Create the component template of the cluster",
    description="POST /_component_template/{name}. Create the component template of the cluster (API key auth).",
)
async def create_component_template(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: str = Path(
        ...,
        description="template name"
    ),
    body: ComponentTemplateRequest = Body(..., description="Component template request")
):
    """Create the component template of the cluster."""
    try:
        print(body.model_dump(exclude_none=True, by_alias=True))
        result = await elasticsearch_service.create_component_template(name, body)
        return StandardResponse(success=True, message="Component template created successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.put(
    "/component/template/{name}",
    summary="Update the component template of the cluster",
    description="PUT /_component_template/{name}. Update the component template of the cluster (API key auth).",
)
async def update_component_template(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: str = Path(
        ...,
        description="template name"
    ),
    body: ComponentTemplateRequest = Body(..., description="Component template request")
):
    """Update the component template of the cluster."""
    try:
        print(body.model_dump(exclude_none=True, by_alias=True))
        result = await elasticsearch_service.update_component_template(name, body)
        return StandardResponse(success=True, message="Component template updated successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.delete(
    "/component/template/{name}",
    summary="Delete the component templates of the cluster",   
    description="Delete /_component_templates/{name}. Delete the component templates of the cluster (API key auth).",
)
async def delete_component_template(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: str = Path(
        ...,
        description="template name"
    )
):
    """Delete the component templates of the cluster."""
    try:
        result = await elasticsearch_service.delete_component_template(name)
        return StandardResponse(success=True, message="Component template deleted successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/index/template/{name}",
    summary="Get the index template of the cluster",   
    description="GET /_index_template/{name}. Get the index template of the cluster (API key auth).",
)
async def get_index_template(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Path(
        ...,
        description="template name"
    )
):
    """Get the index template of the cluster."""
    try:
        result = await elasticsearch_service.get_index_template(name)
        return StandardResponse(success=True, message="Index template retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/index/template/{name}",
    summary="Create the index template of the cluster",   
    description="POST /_index_template/{name}. Create the index template of the cluster (API key auth).",
)
async def create_index_template(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Path(
        ...,
        description="template name"
    ),
    body: IndexTemplateRequest = Body(...,description="Index template request")
):
    """Create the index template of the cluster."""
    try:
        result = await elasticsearch_service.create_index_template(name, body)
        return StandardResponse(success=True, message="Index template created successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.put(
    "/index/template/{name}",
    summary="Update the index template of the cluster",   
    description="PUT /_index_template/{name}. Update the index template of the cluster (API key auth).",
)
async def update_index_template(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Path(
        ...,
        description="template name"
    ),
    body: IndexTemplateRequest = Body(...,description="Index template request")
):
    """Update the index template of the cluster."""
    try:
        result = await elasticsearch_service.update_index_template(name, body)
        return StandardResponse(success=True, message="Index template updated successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.delete(
    "/index/template/{name}",
    summary="Delete the index template of the cluster",   
    description="DELETE /_index_template/{name}. Delete the index template of the cluster (API key auth).",
)
async def delete_index_template(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Path(
        ...,
        description="template name"
    ),
):
    """Delete the index template of the cluster."""
    try:
        result = await elasticsearch_service.delete_index_template(name)
        return StandardResponse(success=True, message="Index template deleted successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.head(
    "/index/template/{name}",
    summary="Check if an index template exists",   
    description="HEAD /_index_template/{name}. Check if an index template exists (API key auth).",
)
async def check_index_template_exists(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Path(
        ...,
        description="template name"
    ),
):
    """Check if an index template exists."""
    try:
        result = await elasticsearch_service.check_index_template_exists(name)
        if not result:
            raise HTTPException(status_code=404)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/index/disk/usage/{name}",
    summary="Get the disk usage of an index",   
    description="POST {index}/_disk_usage. Get the disk usage of an index (API key auth).",
)
async def get_disk_usage_of_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name : Optional[str] = Path(
        ..., 
        description="index name"
    )
):
    """Get the disk usage of an index."""
    try:
        result = await elasticsearch_service.get_disk_usage_of_index(name)
        return StandardResponse(success=True, message="Disk usage retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/clear/cache",
    summary="Clear the cache of the cluster",   
    description="POST /_clear_cache. Clear the cache of the cluster (API key auth).",
)
async def clear_cache_of_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name : Optional[str] = Query(
        ..., 
        description="index name"
    )
):
    """Clear the cache of the cluster."""
    try:
        result = await elasticsearch_service.clear_cache_of_index(name)
        return StandardResponse(success=True, message="Cache cleared successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/index/close/{name}",
    summary="Close an index",   
    description="POST {index}/_close. Close an index (API key auth).",
)
async def close_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name : Optional[str] = Path(
        ..., 
        description="index name"
    )
):
    """Close an index."""
    try:
        result = await elasticsearch_service.close_index(name)
        return StandardResponse(success=True, message="Index closed successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/index/open/{name}",
    summary="Open an index",   
    description="POST {index}/_open. Open an index (API key auth).",
)
async def open_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name : Optional[str] = Path(
        ..., 
        description="index name"
    )
):
    """Open an index."""
    try:
        result = await elasticsearch_service.open_index(name)
        return StandardResponse(success=True, message="Index opened successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/index/recovery",
    summary="Get the recovery status of an index",
    description="GET /_recovery. Get the recovery status of an index (API key auth).",
)
async def get_recovery_status_of_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Query(
        default=None,
        description="index name"
    )
):
    """Get the recovery status of an index."""
    try:
        result = await elasticsearch_service.get_recovery_status_of_index(name)
        return StandardResponse(success=True, message="Recovery status retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/index/refresh",
    summary="Refresh an index",
    description="GET /_refresh. Refresh an index (API key auth).",
)
async def refresh_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Query(
        default=None,
        description="index name"
    )
):
    """Refresh an index."""
    try:
        result = await elasticsearch_service.refresh_index(name)
        return StandardResponse(success=True, message="Refreshed index successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/resolve/cluster",
    summary="Resolve a cluster alias",
    description="GET /_resolve/cluster. Resolve a cluster alias (API key auth).",
)
async def resolve_cluster(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: Optional[str] = Query(
        default=None,
        description="index name"
    )
):
    """Resolve a cluster alias."""
    try:
        result = await elasticsearch_service.resolve_cluster(name)
        return StandardResponse(success=True, message="Cluster alias resolved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/resolve/index/{name}",
    summary="Resolve a cluster alias",
    description="GET /_resolve/index/{name}. Resolve a cluster alias (API key auth).",
)
async def resolve_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    name: str = Path(
        ...,
        description="index name"
    )
):
    """Resolve an index."""
    try:
        result = await elasticsearch_service.resolve_index(name)
        return StandardResponse(success=True, message="Index resolved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/index/alias",
    summary="Get an alias",
    description="GET /_alias. Get an alias (API key auth).",
)
async def get_alias(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="index name"
    ),
    alias_name: Optional[str] = Query(
        default=None,
        description="alias name"
    )
):
    """Get an alias."""
    try:
        result = await elasticsearch_service.get_alias(index, alias_name)
        return StandardResponse(success=True, message="Alias retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/index/{index}/alias/{alias_name}",
    summary="Create an alias",
    description="POST /{index}/_alias/{alias_name}. Create an alias (API key auth).",
)
async def create_alias(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="index name"
    ),
    alias_name: str = Path(
        ...,
        description="alias name"
    ),
    body: CreateAliasRequest = Body(...),
    single: Optional[bool] = Query(
        default=True,
        description="If true, creates a single alias, if false, creates a list of aliases"
    )
):
    """Create an alias."""
    try:
        result = await elasticsearch_service.create_alias(index, alias_name, body, single)
        return StandardResponse(success=True, message="Alias created successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.put(
    "/index/{index}/alias/{alias_name}",
    summary="Update an alias",
    description="PUT /{index}/_alias/{alias_name}. Update an alias (API key auth).",
)
async def update_alias(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="index name"
    ),
    alias_name: str = Path(
        ...,
        description="alias name"
    ),
    body: CreateAliasRequest = Body(...),
    single: Optional[bool] = Query(
        default=True,
        description="If true, creates a single alias, if false, creates a list of aliases"
    )
):
    """Update an alias."""
    try:
        result = await elasticsearch_service.update_alias(index, alias_name, body, single)
        return StandardResponse(success=True, message="Alias updated successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.delete(
    "/index/{index}/alias/{alias_name}",
    summary="Delete an alias",
    description="DELETE /{index}/_alias/{alias_name}. Delete an alias (API key auth).",
)
async def delete_alias(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str = Path(
        ...,
        description="index name"
    ),
    alias_name: str = Path(
        ...,
        description="alias name"
    ),
    single: Optional[bool] = Query(
        default=True,
        description="If true, deletes a single alias, if false, deletes a list of aliases"
    )
):
    """Delete an alias."""
    try:
        result = await elasticsearch_service.delete_alias(index, alias_name, single)
        return StandardResponse(success=True, message="Alias deleted successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/index/rollover/{alias_name}",
    summary="Roll over an index",
    description="POST {index}/_rollover. Roll over an index (API key auth).",
)
async def rollover_index(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    alias_name: str = Path(
        ...,
        description="index name"
    ),
    body: RollOverIndexRequest = Body(...),
    new_index_name: Optional[str] = Query(
        default=None,
        description="new index name"
    )
):
    """Roll over an index."""
    try:
        result = await elasticsearch_service.rollover_index(alias_name, new_index_name, body)
        return StandardResponse(success=True, message="Index rolled over successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/index/settings",
    summary="Get index settings",
    description="GET /{index}/_settings. Get index settings (API key auth).",
)
async def get_index_settings(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="index name"
    ),
    alias: Optional[str] = Query(
        default=None,
        description="alias name"
    ) 
):
    """Get index settings."""
    try:
        result = await elasticsearch_service.get_index_settings(index, alias)
        return StandardResponse(success=True, message="Index settings retrived successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.put(
    "/index/settings",
    summary="Update index settings",
    description="PUT /{index}/_settings. Update index settings (API key auth).",
)
async def update_index_settings(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="index name"
    ),
    body: UpdateIndexSettingsRequest = Body(..., description="Update index settings request"),
):
    """Update index settings."""
    try:
        print(body.model_dump())
        result = await elasticsearch_service.update_index_settings(body, index)
        return StandardResponse(success=True, message="Index settings updated successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/index/segments",
    summary="Get index segments",
    description="GET /{index}/_segments. Get index segments (API key auth).",
)
async def get_index_segments(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="index name"
    ),
):
    """Get index segments."""
    try:
        result = await elasticsearch_service.get_index_segments(index)
        return StandardResponse(success=True, message="Index segments retrived successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/index/shard/stores",
    summary="Get index shard stores",
    description="GET /{index}/_shard_stores. Get index shard stores (API key auth).",
)
async def get_index_shard_stores(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="index name"
    ),
):
    """Get index shard stores."""
    try:
        result = await elasticsearch_service.get_index_shard_stores(index)
        return StandardResponse(success=True, message="Index shard stores retrived successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/index/stats",
    summary="Get index statistics",
    description="GET /{index}/_stats. Get index stats (API key auth).",
)
async def get_index_stats(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="index name"
    ),
    metric: Optional[str] = Query(
        default=None,
        description="index name"
    ),
):
    """Get index statistics."""
    try:
        result = await elasticsearch_service.get_index_statistics(index, metric)
        return StandardResponse(success=True, message="Index statistics retrived successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
######################################################## Index Lifecycle Management ########################################################

@router.get(
    "/ilm/policy",
    summary="Get ILM policies",
    description="GET /_ilm/policy. Get ILM policies (API key auth).",
)
async def get_ilm_policies(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    policy_name: Optional[str] = Query(
        default=None,
        description="policy name"
    )
):
    """Get ILM policies."""
    try:
        result = await elasticsearch_service.get_ilm_policy(policy_name)
        return StandardResponse(success=True, message="ILM policies retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/ilm/policy/{policy_name}",
    summary="Create ILM policy",
    description="POST /_ilm/policy/{name}. Create ILM policy (API key auth).",
)
async def create_update_ilm_policy(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    policy_name: str =Path(
        ...,
        description="policy name"
    ),
    body: ILMCreateUpdateRequest = Body(..., description="ILM policy request")
):
    """Create ILM policy."""
    try:
        result = await elasticsearch_service.create_update_ilm_policy(policy_name, body)
        return StandardResponse(success=True, message="ILM policy created successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.delete(
    "/ilm/policy/{policy_name}",
    summary="Delete ILM policy",
    description="DELETE /_ilm/policy/{name}. Delete ILM policy (API key auth).",
)
async def delete_ilm_policy(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    policy_name: str =Path(
        ...,
        description="policy name"
    )
):
    """Delete ILM policy."""
    try:
        result = await elasticsearch_service.delete_ilm_policy(policy_name)
        return StandardResponse(success=True, message="ILM policy deleted successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/ilm/{index}/explain",
    summary="Explain ILM policy",
    description="GET /{index}/_ilm/explain. Explain ILM policy (API key auth).",
)
async def explain_ilm_policy(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str =Path(
        ...,
        description="index name"
    )
):
    """Explain ILM policy."""
    try:
        result = await elasticsearch_service.explain_ilm_policy(index)
        return StandardResponse(success=True, message="ILM policy explained successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    "/ilm/status",
    summary="Get ILM status",
    description="GET /_ilm/status. Get ILM status (API key auth).",
)
async def get_ilm_status(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
):
    """Get ILM status."""
    try:
        result = await elasticsearch_service.get_ilm_status()
        return StandardResponse(success=True, message="ILM status retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/ilm/move/{index}",
    summary="Move to next ILM step",
    description="POST /_ilm/move/{index}. Move to next ILM step (API key auth).",
)
async def move_to_next_ilm_step(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str =Path(
        ...,
        description="index name"
    ),
    body: ILMMoveToStepRequest = Body(..., description="ILM move to step request")
):
    """Move to next ILM step."""
    try:
        result = await elasticsearch_service.move_to_next_ilm_step(index, body)
        return StandardResponse(success=True, message="ILM move to step successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/ilm/remove/{index}",
    summary="Remove ILM policy",
    description="POST /_ilm/remove/{index}. Remove ILM policy (API key auth).",
)
async def remove_ilm_policy(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str =Path(
        ...,
        description="index name"
    )
):
    """Remove ILM policy."""
    try:
        result = await elasticsearch_service.remove_ilm_policy(index)
        return StandardResponse(success=True, message="ILM policy removed successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.post(
    "/ilm/retry/{index}",
    summary="Retry ILM policy",
    description="POST /_ilm/retry/{index}. Retry ILM policy (API key auth).",
)
async def retry_ilm_policy(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: str =Path(
        ...,
        description="index name"
    )
):
    """Retry ILM policy."""
    try:
        result = await elasticsearch_service.retry_ilm_policy(index)
        return StandardResponse(success=True, message="ILM policy retried successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
######################################################## SEARCH ENDPOINTS ########################################################

@router.get(
    '/document/count',
    summary="Get document count for a data stream, an index, or an entire cluster.",
    description="GET /{index}/_count. Get document count for a data stream, an index, or an entire cluster. (API key auth).",
)
async def get_document_count(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="A comma-separated list of data streams, indices, and aliases to search."
    ),
    body: Optional[QueryES] = Body(default=None, description="Query")
):
    """Get document count for a data stream, an index, or an entire cluster."""
    try:
        print("Hi")
        result = await elasticsearch_service.get_count(index, body)
        return StandardResponse(success=True, message="Document count retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    '/field/caps',
    summary="Get field capabilities",
    description="GET /{index}/_field_caps. Get field capabilities (API key auth).",
)
async def get_field_capabilities(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="Index name"
    ),
    body: FieldCapsRequest = Body(..., description="Field capabilities request")
):
    """Get field capabilities."""
    try:
        result = await elasticsearch_service.get_field_capabilities(body, index)
        return StandardResponse(success=True, message="Field capabilities retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)
        
@router.get(
    '/document/msearch',
    summary="Multiple search documents in an index",
    description="GET /{index}/_msearch. Multiple search documents in an index (API key auth).",
)
async def multiple_search(
    elasticsearch_service: ElasticsearchService = Depends(get_elasticsearch_service),
    index: Optional[str] = Query(
        default=None,
        description="A comma-separated list of data streams, indices, and aliases to search."
    ),
    body: Optional[QueryES] = Body(default=None, description="Query")
):
    """Multiple search documents in an index."""
    try:
        result = await elasticsearch_service.multiple_search(body, index)
        return StandardResponse(success=True, message="Multiple search documents in an index retrieved successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=e)
    except ElasticsearchClientError as e:
        _handle_es_error(e)