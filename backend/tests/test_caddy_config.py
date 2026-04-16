import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.caddy_service import CaddyService


class MockBackend:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.name = kwargs.get("name", "test-backend")
        self.host = kwargs.get("host", "192.168.1.10")
        self.port = kwargs.get("port", 8080)
        self.protocol = kwargs.get("protocol", "http")
        self.health_check_enabled = kwargs.get("health_check_enabled", False)
        self.health_check_path = kwargs.get("health_check_path", "/")
        self.health_check_interval_sec = kwargs.get("health_check_interval_sec", 30)
        self.tls_skip_verify = kwargs.get("tls_skip_verify", False)


class MockDomain:
    def __init__(self, backend=None, **kwargs):
        self.id = kwargs.get("id", 1)
        self.hostname = kwargs.get("hostname", "app.example.com")
        self.is_active = kwargs.get("is_active", True)
        self.path_prefix = kwargs.get("path_prefix", "/")
        self.strip_prefix = kwargs.get("strip_prefix", False)
        self.force_https = kwargs.get("force_https", True)
        self.enable_websocket = kwargs.get("enable_websocket", False)
        self.enable_cors = kwargs.get("enable_cors", False)
        self.custom_headers = kwargs.get("custom_headers", None)
        self.basic_auth = kwargs.get("basic_auth", None)
        self.ip_allowlist = kwargs.get("ip_allowlist", None)
        self.maintenance_mode = kwargs.get("maintenance_mode", False)
        self.sort_order = kwargs.get("sort_order", 0)
        self.backend = backend or MockBackend()
        self.certificate = None


class TestCaddyConfigBuilder:
    def setup_method(self):
        self.service = CaddyService(admin_url="http://localhost:2019")

    def test_build_basic_route(self):
        backend = MockBackend()
        domain = MockDomain(backend=backend)
        route = self.service._build_route(domain, backend)

        assert route["@id"] == "domain-1"
        assert route["match"][0]["host"] == ["app.example.com"]
        assert route["terminal"] is True
        assert any(h["handler"] == "reverse_proxy" for h in route["handle"])

    def test_build_route_with_maintenance_mode(self):
        backend = MockBackend()
        domain = MockDomain(backend=backend, maintenance_mode=True)
        route = self.service._build_route(domain, backend)

        assert any(
            h.get("handler") == "static_response" and h.get("status_code") == "503"
            for h in route["handle"]
        )

    def test_build_route_with_custom_headers(self):
        backend = MockBackend()
        domain = MockDomain(backend=backend, custom_headers={"X-Custom": "value"})
        route = self.service._build_route(domain, backend)

        proxy_handler = next(h for h in route["handle"] if h.get("handler") == "reverse_proxy")
        headers = proxy_handler["headers"]["request"]["set"]
        assert "X-Custom" in headers
        assert headers["X-Custom"] == ["value"]

    def test_build_route_with_ip_allowlist(self):
        backend = MockBackend()
        domain = MockDomain(backend=backend, ip_allowlist="10.0.0.0/8,192.168.1.0/24")
        route = self.service._build_route(domain, backend)

        subroute = next(
            (h for h in route["handle"] if h.get("handler") == "subroute"), None
        )
        assert subroute is not None

    def test_build_route_with_cors(self):
        backend = MockBackend()
        domain = MockDomain(backend=backend, enable_cors=True)
        route = self.service._build_route(domain, backend)

        cors_handler = next(
            (h for h in route["handle"] if h.get("handler") == "headers"), None
        )
        assert cors_handler is not None
        assert "Access-Control-Allow-Origin" in cors_handler["response"]["set"]

    def test_build_route_with_websocket(self):
        backend = MockBackend()
        domain = MockDomain(backend=backend, enable_websocket=True)
        route = self.service._build_route(domain, backend)

        proxy_handler = next(h for h in route["handle"] if h.get("handler") == "reverse_proxy")
        keepalive = proxy_handler["transport"]["keepalive"]
        assert keepalive["max_idle_conns_per_host"] == 64

    def test_build_route_with_path_prefix_and_strip(self):
        backend = MockBackend()
        domain = MockDomain(backend=backend, path_prefix="/api", strip_prefix=True)
        route = self.service._build_route(domain, backend)

        assert route["match"][0]["path"] == ["/api*"]
        rewrite = next(
            (h for h in route["handle"] if h.get("handler") == "rewrite"), None
        )
        assert rewrite is not None
        assert rewrite["strip_path_prefix"] == "/api"

    def test_build_route_https_backend(self):
        backend = MockBackend(protocol="https", tls_skip_verify=True)
        domain = MockDomain(backend=backend)
        route = self.service._build_route(domain, backend)

        proxy_handler = next(h for h in route["handle"] if h.get("handler") == "reverse_proxy")
        assert proxy_handler["transport"]["tls"]["insecure_skip_verify"] is True

    def test_build_route_with_health_check(self):
        backend = MockBackend(health_check_enabled=True, health_check_path="/health")
        domain = MockDomain(backend=backend)
        route = self.service._build_route(domain, backend)

        proxy_handler = next(h for h in route["handle"] if h.get("handler") == "reverse_proxy")
        assert "health_checks" in proxy_handler
        assert proxy_handler["health_checks"]["active"]["path"] == "/health"

    def test_none_custom_headers_no_crash(self):
        backend = MockBackend()
        domain = MockDomain(backend=backend, custom_headers=None)
        route = self.service._build_route(domain, backend)
        assert route is not None

    def test_compression_handler_present(self):
        backend = MockBackend()
        domain = MockDomain(backend=backend)
        route = self.service._build_route(domain, backend)

        encode_handler = next(
            (h for h in route["handle"] if h.get("handler") == "encode"), None
        )
        assert encode_handler is not None
        assert "zstd" in encode_handler["encodings"]
        assert "gzip" in encode_handler["encodings"]


class TestRBAC:
    def test_admin_has_all_permissions(self):
        from app.security.rbac import has_permission
        user = MagicMock()
        user.is_superadmin = True
        user.role = "admin"
        assert has_permission(user, "config.rollback")
        assert has_permission(user, "settings.write")

    def test_viewer_has_read_only(self):
        from app.security.rbac import has_permission
        user = MagicMock()
        user.is_superadmin = False
        user.role = "viewer"
        assert has_permission(user, "domain.read")
        assert not has_permission(user, "domain.create")
        assert not has_permission(user, "config.apply")

    def test_editor_can_create_but_not_delete(self):
        from app.security.rbac import has_permission
        user = MagicMock()
        user.is_superadmin = False
        user.role = "editor"
        assert has_permission(user, "domain.create")
        assert has_permission(user, "config.apply")
        assert not has_permission(user, "domain.delete")
        assert not has_permission(user, "settings.write")
