from pydantic.generics import GenericModel
from typing import Optional, TypeVar, Generic

T = TypeVar("T")

class StandardResponse(GenericModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None


