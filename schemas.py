from pydantic import BaseModel
from typing import Dict, Any, List, Union


class ReviewListSchema(BaseModel):
    status: str
    data: List[Dict]
    error: Union[Dict, None]
