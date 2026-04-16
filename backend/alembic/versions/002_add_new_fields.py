"""Add new fields: TOTP, RBAC, cache, redirects, load balancing, templates, upstreams

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User: TOTP + RBAC
    op.add_column("users", sa.Column("totp_secret", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="admin"))

    # Domain: redirects
    op.add_column("domains", sa.Column("redirect_url", sa.String(500), nullable=True))
    op.add_column("domains", sa.Column("redirect_code", sa.Integer(), nullable=False, server_default="0"))

    # Domain: load balancing
    op.add_column("domains", sa.Column("lb_policy", sa.String(20), nullable=False, server_default=""))

    # Domain: local cache
    op.add_column("domains", sa.Column("cache_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("domains", sa.Column("cache_ttl", sa.Integer(), nullable=False, server_default="3600"))
    op.add_column("domains", sa.Column("cache_stale_ttl", sa.Integer(), nullable=False, server_default="86400"))
    op.add_column("domains", sa.Column("cache_max_body_bytes", sa.Integer(), nullable=False, server_default="50000000"))
    op.add_column("domains", sa.Column("cache_extensions", sa.Text(), nullable=False,
        server_default=".js,.css,.png,.jpg,.jpeg,.gif,.svg,.woff,.woff2,.ttf,.eot,.ico,.webp,.avif"))

    # Domain upstreams (load balancing many-to-many)
    op.create_table(
        "domain_upstreams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domain_id", sa.Integer(), sa.ForeignKey("domains.id", ondelete="CASCADE"), index=True),
        sa.Column("backend_id", sa.Integer(), sa.ForeignKey("backends.id", ondelete="CASCADE"), index=True),
        sa.Column("weight", sa.Integer(), default=1),
    )

    # Domain templates
    op.create_table(
        "domain_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("force_https", sa.Boolean(), default=True),
        sa.Column("enable_websocket", sa.Boolean(), default=False),
        sa.Column("enable_cors", sa.Boolean(), default=False),
        sa.Column("custom_headers", sa.JSON(), nullable=True),
        sa.Column("strip_prefix", sa.Boolean(), default=False),
        sa.Column("maintenance_mode", sa.Boolean(), default=False),
        sa.Column("lb_policy", sa.String(20), default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Add composite indexes for audit performance
    op.create_index("idx_audit_action_created", "audit_logs", ["action", "created_at"])
    op.create_index("idx_audit_user_created", "audit_logs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_user_created", table_name="audit_logs")
    op.drop_index("idx_audit_action_created", table_name="audit_logs")
    op.drop_table("domain_templates")
    op.drop_table("domain_upstreams")
    op.drop_column("domains", "cache_extensions")
    op.drop_column("domains", "cache_max_body_bytes")
    op.drop_column("domains", "cache_stale_ttl")
    op.drop_column("domains", "cache_ttl")
    op.drop_column("domains", "cache_enabled")
    op.drop_column("domains", "lb_policy")
    op.drop_column("domains", "redirect_code")
    op.drop_column("domains", "redirect_url")
    op.drop_column("users", "role")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
