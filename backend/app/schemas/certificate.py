from datetime import datetime
from pydantic import BaseModel


class CertificateResponse(BaseModel):
    id: int
    domain_id: int
    hostname: str
    issuer: str | None
    not_before: datetime | None
    not_after: datetime | None
    serial_number: str | None
    status: str
    last_checked_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
