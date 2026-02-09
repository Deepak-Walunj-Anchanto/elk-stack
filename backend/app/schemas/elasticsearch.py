from pydantic.generics import GenericModel
from pydantic import BaseModel, Field
from typing import Optional, TypeVar, Generic, List, Dict, Any

T = TypeVar("T")

class StandardResponse(GenericModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

class ShardsInfo(BaseModel):
    total: int
    successful: int
    skipped: int
    failed: int

class TotalHits(BaseModel):
    value: int
    relation: str

class SearchHit(BaseModel):
    index: str = Field(..., alias="_index")
    id: str = Field(..., alias="_id")
    score: Optional[float] = Field(default=None, alias="_score")
    source: Optional[Dict[str, Any]] = Field(default=None, alias="_source")
    sort: Optional[List[Any]] = None

class HitsBlock(BaseModel):
    total: TotalHits
    max_score: Optional[float] = None
    hits: List[SearchHit]
    
class SearchDocumentsResponse(BaseModel):
    ids_by_index: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Mapping of index name -> list of document ids"
    )
    total_ids_returned: int = Field(
        ...,
        description="Total number of ids returned in this search response"
    )
    total_ids_in_index: int = Field(
        ...,
        description="Total number of ids in the index"
    )
    took: int = Field(..., description="Time taken to execute the search request")
    timed_out: bool = Field(..., description="Whether the search request timed out")
    shards: ShardsInfo = Field(..., alias="_shards")
    hits: HitsBlock = Field(..., alias="hits")

    