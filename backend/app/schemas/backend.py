from datetime import datetime
from pydantic import BaseModel, Field


class BackendCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    protocol: str = Field(default="http", pattern=r"^(http|https)$")
    health_check_enabled: bool = False
    health_check_path: str = Field(default="/", max_length=255)
    health_check_interval_sec: int = Field(default=30, ge=5, le=3600)
    tls_skip_verify: bool = False
    notes: str | None = None


class BackendUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    protocol: str | None = Field(default=None, pattern=r"^(http|https)$")
    health_check_enabled: bool | None = None
    health_check_path: str | None = Field(default=None, max_length=255)
    health_check_interval_sec: int | None = Field(default=None, ge=5, le=3600)
    tls_skip_verify: bool | None = None
    notes: str | None = None


class BackendResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    protocol: str
    health_check_enabled: bool
    health_check_path: str
    health_check_interval_sec: int
    health_status: str
    health_checked_at: datetime | None
    health_response_time_ms: int | None
    tls_skip_verify: bool
    notes: str | None
    domain_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
