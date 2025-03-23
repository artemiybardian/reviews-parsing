from pydantic import BaseModel
from typing import Dict, Optional, List, Union


class ReviewListSchema(BaseModel):
    status: str
    data: List[Dict]
    error: Union[Dict, None]
    filial_id: str


class YandexRequestSchema(BaseModel):
    filial_id: str
    encrypted_session_id: str
    https_proxy: Optional[str] = None
