from pydantic import BaseModel


class NormalizePhoneRequest(BaseModel):
    phone_number: str
    default_region: str = "US"


class NormalizePhoneResponse(BaseModel):
    original: str
    normalized: str
    valid: bool
