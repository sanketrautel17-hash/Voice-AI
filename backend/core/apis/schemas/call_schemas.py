from pydantic import BaseModel, Field
from typing import Optional


class DialoutResponse(BaseModel):
    call_sid: str
    status: str
    to_number: str


class DialoutRequest(BaseModel):
    to_number: str
    from_number: Optional[str] = None
