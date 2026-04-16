import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


HOSTNAME_PATTERN = re.compile(
    r"^(\*\.)?([a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


class DomainCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=253)
    backend_id: int
    is_active: bool = True
    path_prefix: str = Field(default="/", max_length=255)
    strip_prefix: bool = False
    force_https: bool = True
    enable_websocket: bool = False
    enable_cors: bool = False
    custom_headers: dict[str, str] | None = None
    basic_auth: str | None = None
    ip_allowlist: str | None = None
    maintenance_mode: bool = False
    zone_id: str | None = Field(default=None, max_length=32)
    dns_record_id: str | None = Field(default=None, max_length=32)
    proxied: bool = True
    ssl_mode: str = Field(default="full", pattern=r"^(off|flexible|full|strict)$")
    notes: str | None = None
    sort_order: int = 0

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        v = v.lower().strip()
        if not HOSTNAME_PATTERN.match(v):
            raise ValueError("Invalid hostname format")
        return v


class DomainUpdate(BaseModel):
    hostname: str | None = Field(default=None, min_length=1, max_length=253)
    backend_id: int | None = None
    is_active: bool | None = None
    path_prefix: str | None = Field(default=None, max_length=255)
    strip_prefix: bool | None = None
    force_https: bool | None = None
    enable_websocket: bool | None = None
    enable_cors: bool | None = None
    custom_headers: dict[str, str] | None = None
    basic_auth: str | None = None
    ip_allowlist: str | None = None
    maintenance_mode: bool | None = None
    zone_id: str | None = Field(default=None, max_length=32)
    dns_record_id: str | None = Field(default=None, max_length=32)
    proxied: bool | None = None
    ssl_mode: str | None = Field(default=None, pattern=r"^(off|flexible|full|strict)$")
    notes: str | None = None
    sort_order: int | None = None

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.lower().strip()
        if not HOSTNAME_PATTERN.match(v):
            raise ValueError("Invalid hostname format")
        return v


class DomainResponse(BaseModel):
    id: int
    hostname: str
    backend_id: int
    backend_name: str = ""
    backend_address: str = ""
    is_active: bool
    path_prefix: str
    strip_prefix: bool
    force_https: bool
    enable_websocket: bool
    enable_cors: bool
    custom_headers: dict[str, str] | None
    basic_auth: str | None
    ip_allowlist: str | None
    maintenance_mode: bool
    zone_id: str | None
    dns_record_id: str | None
    proxied: bool
    ssl_mode: str
    notes: str | None
    sort_order: int
    cert_status: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
