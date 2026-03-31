from pydantic import BaseModel, Field
from typing import Optional


class DialoutResponse(BaseModel):
    call_sid: str
    status: str
    to_number: str


class DialoutRequest(BaseModel):
    to_number: str
    from_number: Optional[str] = None


class LeadSubmission(BaseModel):
    firstName: str = Field(..., description="First Name of the lead")
    lastName: str = Field(..., description="Last Name of the lead")
    phone: str = Field(..., description="Phone Number of the lead")
    email: str = Field(..., description="Email ID of the lead")
