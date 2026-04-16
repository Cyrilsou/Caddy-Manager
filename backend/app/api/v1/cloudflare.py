from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.cloudflare import (
    DNSRecordCreate,
    DNSRecordUpdate,
    ProxyToggle,
    SSLModeUpdate,
)
from app.services.cloudflare_service import CloudflareAPIError, CloudflareService

router = APIRouter(prefix="/cloudflare", tags=["cloudflare"])


def _get_cf_service() -> CloudflareService:
    if not settings.CLOUDFLARE_API_TOKEN:
        raise HTTPException(status_code=400, detail="Cloudflare API token not configured")
    return CloudflareService(settings.CLOUDFLARE_API_TOKEN)


@router.get("/verify")
async def verify_token(_: User = Depends(get_current_user)):
    cf = _get_cf_service()
    valid = await cf.verify_token()
    return {"valid": valid, "message": "Token is active" if valid else "Token is invalid or expired"}


@router.get("/zones")
async def list_zones(_: User = Depends(get_current_user)):
    cf = _get_cf_service()
    try:
        zones = await cf.list_zones()
        return [
            {
                "id": z["id"],
                "name": z["name"],
                "status": z["status"],
                "paused": z.get("paused", False),
                "plan": z.get("plan", {}).get("name"),
            }
            for z in zones
        ]
    except CloudflareAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/zones/{zone_id}/dns")
async def list_dns_records(zone_id: str, _: User = Depends(get_current_user)):
    cf = _get_cf_service()
    try:
        records = await cf.list_dns_records(zone_id)
        return [
            {
                "id": r["id"],
                "type": r["type"],
                "name": r["name"],
                "content": r["content"],
                "proxied": r.get("proxied", False),
                "ttl": r["ttl"],
            }
            for r in records
        ]
    except CloudflareAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/dns", status_code=201)
async def create_dns_record(data: DNSRecordCreate, _: User = Depends(get_current_user)):
    cf = _get_cf_service()
    try:
        result = await cf.create_dns_record(
            data.zone_id, data.record_type, data.name, data.content, data.proxied, data.ttl,
        )
        return result
    except CloudflareAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.put("/dns")
async def update_dns_record(data: DNSRecordUpdate, _: User = Depends(get_current_user)):
    cf = _get_cf_service()
    try:
        result = await cf.update_dns_record(
            data.zone_id, data.record_id, data.record_type, data.name,
            data.content, data.proxied, data.ttl,
        )
        return result
    except CloudflareAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/dns/{zone_id}/{record_id}")
async def delete_dns_record(zone_id: str, record_id: str, _: User = Depends(get_current_user)):
    cf = _get_cf_service()
    try:
        return await cf.delete_dns_record(zone_id, record_id)
    except CloudflareAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/dns/toggle-proxy")
async def toggle_proxy(data: ProxyToggle, _: User = Depends(get_current_user)):
    cf = _get_cf_service()
    try:
        return await cf.toggle_proxy(data.zone_id, data.record_id, data.proxied)
    except CloudflareAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/zones/{zone_id}/ssl")
async def get_ssl_mode(zone_id: str, _: User = Depends(get_current_user)):
    cf = _get_cf_service()
    try:
        mode = await cf.get_ssl_mode(zone_id)
        return {"mode": mode}
    except CloudflareAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.patch("/zones/{zone_id}/ssl")
async def set_ssl_mode(zone_id: str, data: SSLModeUpdate, _: User = Depends(get_current_user)):
    cf = _get_cf_service()
    try:
        return await cf.set_ssl_mode(zone_id, data.mode)
    except CloudflareAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
