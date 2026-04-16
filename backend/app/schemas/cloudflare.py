import re
from pydantic import BaseModel, Field, field_validator


class DNSRecordCreate(BaseModel):
    zone_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    record_type: str = Field(pattern=r"^(A|AAAA|CNAME|TXT|MX|NS|SRV)$")
    name: str = Field(max_length=253)
    content: str = Field(max_length=1024)
    proxied: bool = True
    ttl: int = Field(default=1, ge=1, le=86400)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$", v):
            raise ValueError("Invalid DNS record name")
        return v.lower()


class DNSRecordUpdate(DNSRecordCreate):
    record_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class ProxyToggle(BaseModel):
    zone_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    record_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    proxied: bool


class SSLModeUpdate(BaseModel):
    mode: str = Field(pattern=r"^(off|flexible|full|strict)$")


class CloudflareZoneResponse(BaseModel):
    id: str
    name: str
    status: str
    paused: bool
    plan: str | None = None


class CloudflareDNSResponse(BaseModel):
    id: str
    type: str
    name: str
    content: str
    proxied: bool
    ttl: int


class CloudflareVerifyResponse(BaseModel):
    valid: bool
    message: str = ""
