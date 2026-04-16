import ipaddress
import re
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


HOSTNAME_PATTERN = re.compile(
    r"^(\*\.)?([a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


def _validate_hostname_value(v: str) -> str:
    v = v.lower().strip()
    if len(v) > 253:
        raise ValueError("Hostname too long (max 253)")
    if ".." in v or v.startswith("-") or v.endswith("-"):
        raise ValueError("Invalid hostname format")
    if not HOSTNAME_PATTERN.match(v):
        raise ValueError("Invalid hostname format (e.g. app.example.com)")
    return v


def _validate_custom_headers_value(v: dict[str, str] | None) -> dict[str, str] | None:
    if not v:
        return v
    if len(v) > 20:
        raise ValueError("Maximum 20 custom headers allowed")
    for key, value in v.items():
        if len(key) > 100:
            raise ValueError(f"Header name '{key[:20]}...' too long (max 100)")
        if len(value) > 1000:
            raise ValueError(f"Header value for '{key}' too long (max 1000)")
        if not key.isascii() or not value.isascii():
            raise ValueError("Header names/values must be ASCII")
        if "\n" in key or "\r" in key or "\n" in value or "\r" in value:
            raise ValueError("Header names/values must not contain newlines")
    return v


def _validate_ip_allowlist_value(v: str | None) -> str | None:
    if not v:
        return v
    cidrs = [c.strip() for c in v.split(",") if c.strip()]
    if len(cidrs) > 50:
        raise ValueError("Maximum 50 IP ranges allowed")
    for cidr in cidrs:
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            raise ValueError(f"Invalid CIDR: '{cidr}'")
    return v


def _validate_basic_auth_value(v: str | None) -> str | None:
    if not v:
        return v
    parts = v.strip().split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Basic auth must be 'username:bcrypt_hash'")
    if not re.match(r"^\$2[aby]\$", parts[1]):
        raise ValueError("Password must be bcrypt-hashed (use: caddy hash-password)")
    return v


def _validate_redirect_url_value(v: str | None) -> str | None:
    if not v:
        return v
    try:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Redirect URL must use http:// or https://")
        if not parsed.netloc:
            raise ValueError("Redirect URL must include a domain")
    except Exception:
        raise ValueError("Invalid redirect URL")
    return v


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
    redirect_url: str | None = Field(default=None, max_length=500)
    redirect_code: int = Field(default=0, ge=0, le=302)
    maintenance_mode: bool = False
    zone_id: str | None = Field(default=None, max_length=32)
    dns_record_id: str | None = Field(default=None, max_length=32)
    proxied: bool = True
    ssl_mode: str = Field(default="full", pattern=r"^(off|flexible|full|strict)$")
    notes: str | None = Field(default=None, max_length=1000)
    sort_order: int = 0

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        return _validate_hostname_value(v)

    @field_validator("custom_headers")
    @classmethod
    def validate_custom_headers(cls, v):
        return _validate_custom_headers_value(v)

    @field_validator("ip_allowlist")
    @classmethod
    def validate_ip_allowlist(cls, v):
        return _validate_ip_allowlist_value(v)

    @field_validator("basic_auth")
    @classmethod
    def validate_basic_auth(cls, v):
        return _validate_basic_auth_value(v)

    @field_validator("redirect_url")
    @classmethod
    def validate_redirect_url(cls, v):
        return _validate_redirect_url_value(v)

    @field_validator("redirect_code")
    @classmethod
    def validate_redirect_code(cls, v):
        if v != 0 and v not in (301, 302):
            raise ValueError("Redirect code must be 0 (disabled), 301, or 302")
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
    redirect_url: str | None = Field(default=None, max_length=500)
    redirect_code: int | None = Field(default=None, ge=0, le=302)
    maintenance_mode: bool | None = None
    zone_id: str | None = Field(default=None, max_length=32)
    dns_record_id: str | None = Field(default=None, max_length=32)
    proxied: bool | None = None
    ssl_mode: str | None = Field(default=None, pattern=r"^(off|flexible|full|strict)$")
    notes: str | None = Field(default=None, max_length=1000)
    sort_order: int | None = None

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v):
        return _validate_hostname_value(v) if v else v

    @field_validator("custom_headers")
    @classmethod
    def validate_custom_headers(cls, v):
        return _validate_custom_headers_value(v)

    @field_validator("ip_allowlist")
    @classmethod
    def validate_ip_allowlist(cls, v):
        return _validate_ip_allowlist_value(v)

    @field_validator("basic_auth")
    @classmethod
    def validate_basic_auth(cls, v):
        return _validate_basic_auth_value(v)

    @field_validator("redirect_url")
    @classmethod
    def validate_redirect_url(cls, v):
        return _validate_redirect_url_value(v)


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
