from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import List, Dict, Any, Optional, Union

class DataStreamLifecycleRequest(BaseModel):
    data_retention: str = Field(
        ...,
        description="Minimum retention period (e.g. 30d, 7d, 12h)"
    )
    
class ClusterAllocationExplainRequest(BaseModel):
    index: Optional[str] = None
    shard: Optional[int] = None
    primary: Optional[bool] = None
    current_node: Optional[str] = None
    
class BackingIndexAction(BaseModel):
    data_stream: str = Field(..., description="Target data stream name")
    index: str = Field(..., description="Backing index name")
    
class DataStreamAction(BaseModel):
    remove_backing_index: Optional[BackingIndexAction] = None
    add_backing_index: Optional[BackingIndexAction] = None

    @model_validator(mode='after')
    def validate_single_action(self):
        actions = [
            self.remove_backing_index,
            self.add_backing_index,
        ]
        if sum(action is not None for action in actions) != 1:
            raise ValueError(
                "Exactly one of remove_backing_index or add_backing_index must be set"
            )
        return self
    
class DataStreamModifyRequest(BaseModel):
    actions: List[DataStreamAction] = Field(
        ...,
        description="List of actions to perform on the data stream"
    )
    
class SortFields(BaseModel):
    # example: {"@timestamp": "desc"}
    field: str 
    order: str = Field(..., pattern=r"^(asc|desc)$")
    
    def to_es(self) -> Dict[str, str]:
        return {self.field: self.order}
    
class SearchInIndexRequest(BaseModel):
    size: int = Field(default=10, ge=1,le=100000)
    source: Union[bool, List[str], Dict[str, Any]] = Field(default=False, alias="_source")
    sort: Optional[List[SortFields]] = None
    query: Optional[Dict[str, Any]] = None
    track_total_hits: Optional[Union[bool, int]] = None
    
    def to_es_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "size": self.size,
            "_source": self.source,
        }
        if self.sort:
            payload["sort"] = [s.to_es() for s in self.sort]
        if self.query:
            payload["query"] = self.query
        if self.track_total_hits is not None:
            payload["track_total_hits"] = self.track_total_hits
        return payload
    
class SearchMultipleDocumentsRequest(BaseModel):
    docs: List[Dict[str, str]] = Field(..., description="List of documents to search for, each document is a dictionary with the index name and the document id")

class ReindexSource(BaseModel):
    index: List[str] = Field(..., description="List of indices to reindex from")
    
class ReindexDestination(BaseModel):
    index: str = Field(..., description="Index to reindex to")
    
class ReindexRequest(BaseModel):
    source: ReindexSource
    dest: ReindexDestination
    
class IndexTemplateFieldType(BaseModel):
    type: str

class IndexTemplateMappings(BaseModel):
    properties: Dict[str, IndexTemplateFieldType]

class IndexTemplateSettings(BaseModel):
    number_of_shards: int
    number_of_replicas: int

class IndexTemplateBody(BaseModel):
    settings: IndexTemplateSettings
    mappings: IndexTemplateMappings

class IndexTemplateRequest(BaseModel):
    index_patterns: List[str] = Field(..., description="List of index patterns to create the template for")
    data_stream: Dict[str, Any] = Field(default_factory=dict, description="Data stream configuration")
    priority: int = Field(..., description="Priority of the template")
    template: IndexTemplateBody = Field(..., description="Template to create")
    
class ComponentTemplateMappings(BaseModel):
    source: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Source configuration", alias="_source")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Field mappings")
    dynamic: Optional[Union[bool, str]] = Field(default=None, description="Dynamic mapping setting (true/false/strict/runtime)")
    
class ComponentTemplateSettings(BaseModel):
    number_of_shards: int = Field(..., description="Number of shards to use for the template")
    number_of_replicas: Optional[int] = Field(None, description="Number of replicas to use for the template")
    index: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Index settings")

class ComponentTemplateInner(BaseModel):
    settings: Optional[ComponentTemplateSettings] = Field(default_factory=ComponentTemplateSettings, description="Index settings")
    mappings: Optional[ComponentTemplateMappings] = Field(default_factory=ComponentTemplateMappings, description="Mappings configuration")
    aliases: Optional[Dict[str, Any]] = Field(default=None, description="Aliases configuration")

    # Added in 8.11+
    lifecycle: Optional[Dict[str, Any]] = Field(default=None, description="Data stream lifecycle configuration")

    # Added in 8.19+
    data_stream_options: Optional[Union[Dict[str, Any], str, None]] = Field(default=None, description="Data stream options configuration")
    failure_store: Optional[Union[Dict[str, Any], str, None]] = Field(default=None, description="Failure store configuration")

class ComponentTemplateRequest(BaseModel):
    template: ComponentTemplateInner = Field(..., description="Template definition")
    version: Optional[int] = Field(default=None, description="Version for external management")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="User metadata", alias="_meta")
    deprecated: Optional[bool] = Field(default=None, description="Mark template as deprecated")

class IndexSettings(BaseModel):
    # allows nested index settings, e.g. index.number_of_shards
    index: Optional[Dict[str, Any]] = Field(default=None, description="Root index settings object")
    # convenience top-level shortcuts
    number_of_shards: Optional[int] = Field(default=None, description="Number of primary shards (shorthand)")
    number_of_replicas: Optional[int] = Field(default=None, description="Number of replicas (shorthand)")

class UpdateIndexSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    index: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    
class FieldMapping(BaseModel):
    type: str
    # you can extend this with other mapping options
    properties: Optional[Dict[str, Any]] = Field(default=None)

class IndexMappings(BaseModel):
    properties: Optional[Dict[str, FieldMapping]] = Field(default=None, description="Mapping properties")
    # you can also add other mapping-level options here

class CreateIndexRequest(BaseModel):
    settings: Optional[IndexSettings] = Field(default=None, description="Index settings")
    mappings: Optional[IndexMappings] = Field(default=None, description="Index mappings")
    
class RollOverConditions(BaseModel):
    max_age: Optional[str] = Field(default=None, description="Maximum age of the index")
    max_docs: Optional[int] = Field(default=None, description="Maximum number of documents in the index")
    max_primary_shard_size: Optional[str] = Field(default=None, description="Maximum size of the index")
    max_primary_shard_docs: Optional[int] = Field(default=None, description="Maximum number of documents in the index") 

class CreateAliasRequest(BaseModel):
    filter: Optional[Dict[str, Any]] = Field(default=None, description="Query DSL filter used to limit documents the alias can access")
    is_write_index: Optional[bool] = Field(default=None, description="If true, sets the write index for the alias")
    routing: Optional[Union[str, List[str]]] = Field(default=None, description="Routing value for indexing and search operations")
    index_routing: Optional[Union[str, List[str]]] = Field(default=None, description="Routing value for indexing operations only")
    search_routing: Optional[Union[str, List[str]]] = Field(default=None, description="Routing value for search operations only")

class RollOverIndexRequest(BaseModel):
    rollover_conditions: Optional[RollOverConditions] = Field(default=None, description="Roll over conditions")
    
class ILMPhase(BaseModel):
    actions: Dict[str, Any] = Field(default_factory=dict, description="Actions to perform in the phase")

class ILMPhases(BaseModel):
    hot: Optional[ILMPhase] = None
    warm: Optional[ILMPhase] = None
    cold: Optional[ILMPhase] = None
    frozen: Optional[ILMPhase] = None
    delete: Optional[ILMPhase] = None

class ILMPolicy(BaseModel):
    phases: ILMPhases
    meta: Optional[Dict[str, Any]] = Field(default=None, description="User metadata", alias="_meta")

class ILMCreateUpdateRequest(BaseModel):
    policy: ILMPolicy
    
class ILMStep(BaseModel):
    phase: str
    action: Optional[str] = None
    name: Optional[str] = None

class ILMMoveToStepRequest(BaseModel):
    current_step: ILMStep
    next_step: ILMStep
    
class QueryES(BaseModel):
    query: Dict[str, Any] = Field(..., description="Query")
    
class FieldCapsRequest(BaseModel):
    fields: Optional[List[str]] = Field(default=None, description="List of fields to get capabilities for")
    index_filter: Optional[Dict[str, Any]] = Field(default=None, description="Filter to apply to the index")
    runtime_mappings: Optional[Dict[str, Any]] = Field(default=None, description="Runtime mappings to apply to the index")