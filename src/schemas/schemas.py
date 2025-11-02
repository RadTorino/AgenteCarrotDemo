from pydantic import BaseModel
from typing import Optional, Literal

class NotificacionSchema(BaseModel):
    type: str
    data: dict
    user_id: Optional[str]