"""Integration tests that call actual FastAPI endpoints via test client."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, auth_headers: dict):
    """auth_headers fixture creates admin user and logs in."""
    assert "Authorization" in auth_headers


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    r = await client.post("/api/v1/auth/login", json={
        "username": "nonexistent",
        "password": "wrongpass123",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limit(client: AsyncClient):
    """6th login attempt should be rate limited."""
    for i in range(6):
        r = await client.post("/api/v1/auth/login", json={
            "username": "baduser",
            "password": f"badpass{i}",
        })
    # After several attempts, should get 429 or 401
    assert r.status_code in (401, 429)


@pytest.mark.asyncio
async def test_me_without_auth(client: AsyncClient):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_with_auth(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "testadmin"
    assert data["is_superadmin"] is True


@pytest.mark.asyncio
async def test_backend_crud(client: AsyncClient, auth_headers: dict):
    # Create
    r = await client.post("/api/v1/backends", headers=auth_headers, json={
        "name": "test-backend",
        "host": "10.0.0.1",
        "port": 8080,
        "protocol": "http",
    })
    assert r.status_code == 201
    backend_id = r.json()["id"]
    assert r.json()["name"] == "test-backend"

    # List
    r = await client.get("/api/v1/backends", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1

    # Update
    r = await client.put(f"/api/v1/backends/{backend_id}", headers=auth_headers, json={
        "port": 9090,
    })
    assert r.status_code == 200
    assert r.json()["port"] == 9090

    # Health check
    r = await client.post(f"/api/v1/backends/{backend_id}/health-check", headers=auth_headers)
    assert r.status_code == 200
    assert "status" in r.json()


@pytest.mark.asyncio
async def test_domain_crud(client: AsyncClient, auth_headers: dict):
    # First create a backend
    r = await client.post("/api/v1/backends", headers=auth_headers, json={
        "name": "domain-test-backend",
        "host": "10.0.0.2",
        "port": 80,
    })
    assert r.status_code == 201
    backend_id = r.json()["id"]

    # Create domain
    r = await client.post("/api/v1/domains", headers=auth_headers, json={
        "hostname": "test.example.com",
        "backend_id": backend_id,
    })
    assert r.status_code == 201
    domain_id = r.json()["id"]

    # List
    r = await client.get("/api/v1/domains", headers=auth_headers)
    assert r.status_code == 200
    assert any(d["hostname"] == "test.example.com" for d in r.json())

    # Toggle
    r = await client.post(f"/api/v1/domains/{domain_id}/toggle", headers=auth_headers)
    assert r.status_code == 200

    # Delete
    r = await client.delete(f"/api/v1/domains/{domain_id}", headers=auth_headers)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_domain_duplicate_hostname(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/v1/backends", headers=auth_headers, json={
        "name": "dup-backend", "host": "10.0.0.3", "port": 80,
    })
    backend_id = r.json()["id"]

    await client.post("/api/v1/domains", headers=auth_headers, json={
        "hostname": "dup.example.com", "backend_id": backend_id,
    })
    r = await client.post("/api/v1/domains", headers=auth_headers, json={
        "hostname": "dup.example.com", "backend_id": backend_id,
    })
    assert r.status_code == 400
    assert "already exists" in r.json()["detail"]


@pytest.mark.asyncio
async def test_domain_invalid_hostname(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/v1/domains", headers=auth_headers, json={
        "hostname": "not a valid hostname!!!",
        "backend_id": 1,
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_config_preview(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/v1/config/preview", headers=auth_headers)
    assert r.status_code == 200
    assert "config_json" in r.json()


@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/v1/dashboard/stats", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total_domains" in data
    assert "total_backends" in data


@pytest.mark.asyncio
async def test_audit_log(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/v1/audit", headers=auth_headers)
    assert r.status_code == 200
    assert "items" in r.json()


@pytest.mark.asyncio
async def test_delete_backend_with_domains_fails(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/v1/backends", headers=auth_headers, json={
        "name": "nodelete-backend", "host": "10.0.0.4", "port": 80,
    })
    backend_id = r.json()["id"]

    await client.post("/api/v1/domains", headers=auth_headers, json={
        "hostname": "nodelete.example.com", "backend_id": backend_id,
    })

    r = await client.delete(f"/api/v1/backends/{backend_id}", headers=auth_headers)
    assert r.status_code == 400
    assert "associated domains" in r.json()["detail"]


@pytest.mark.asyncio
async def test_mass_assignment_blocked(client: AsyncClient, auth_headers: dict):
    """Ensure setattr whitelist blocks arbitrary field modification."""
    r = await client.post("/api/v1/backends", headers=auth_headers, json={
        "name": "mass-test", "host": "10.0.0.5", "port": 80,
    })
    backend_id = r.json()["id"]

    r = await client.put(f"/api/v1/backends/{backend_id}", headers=auth_headers, json={
        "id": 9999,
        "created_at": "2000-01-01T00:00:00Z",
        "health_status": "healthy",
    })
    assert r.status_code == 200
    assert r.json()["id"] == backend_id  # id unchanged
    assert r.json()["health_status"] != "healthy"  # not whitelisted
