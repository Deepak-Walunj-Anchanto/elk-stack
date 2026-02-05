from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional

class DataStreamLifecycleRequest(BaseModel):
    data_retention: str = Field(
        ...,
        description="Minimum retention period (e.g. 30d, 7d, 12h)"
    )
    
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
