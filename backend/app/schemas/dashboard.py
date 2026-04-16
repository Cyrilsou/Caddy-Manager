from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_domains: int
    active_domains: int
    total_backends: int
    healthy_backends: int
    unhealthy_backends: int
    unknown_backends: int
    certs_valid: int
    certs_expiring_soon: int
    certs_expired: int
    caddy_reachable: bool
    config_version: int | None
