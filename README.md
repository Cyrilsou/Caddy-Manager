# Caddy-Manager

A self-hosted, production-ready web panel to manage a **Caddy reverse proxy** server. Built for **Proxmox VM** deployments with full **Cloudflare** integration.

> Manage all your domains, backends, TLS certificates and Caddy configuration from a single modern UI — no manual file editing.

## Features

- **Domain Management** — Add, edit, delete, toggle domains with automatic Caddy routing
- **Backend Management** — Configure backend servers with automatic health checks
- **Configuration Versioning** — Preview, validate, apply and rollback Caddy configs atomically
- **TLS Monitoring** — Track certificate status, expiration alerts, auto-renewal via Let's Encrypt
- **Cloudflare Integration** — DNS record management, proxy toggle, SSL mode, DNS-01 ACME for wildcards
- **RBAC** — Role-based access control (Admin, Editor, Viewer)
- **Audit Log** — Complete history of all actions with sensitive data masking
- **Export/Import** — Full configuration backup and restore as JSON
- **Security Hardened** — Argon2id, JWT with Redis blacklist, fail2ban, IP allowlist, rate limiting, security headers

## Architecture

```
Internet --> Cloudflare --> Proxmox VM (vmbr0) --> Docker Host
  |
  +-- Caddy (host network, :80/:443)
  |     +-- Panel HTTPS (panel.yourdomain.com)
  |     +-- Managed domain routing --> Backend VMs (private IPs)
  |     +-- Admin API (127.0.0.1:2019, never exposed)
  |
  +-- FastAPI Backend (internal network, :8000)
  |     +-- SQLAlchemy 2.0 async + Alembic migrations
  |     +-- Persistent HTTP clients (Caddy + Cloudflare)
  |     +-- Background tasks (health checks, cert monitoring)
  |
  +-- PostgreSQL 16 (internal only, no internet access)
  +-- Redis 7 (internal only, token blacklist + fail2ban + cache)
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0 async, Alembic, uvloop |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query |
| Database | PostgreSQL 16 + asyncpg (pool: 20 conns) |
| Cache | Redis 7 (rate limiting, fail2ban, token blacklist, cache) |
| Auth | Argon2id (64MB memory-hard) + JWT HS256 with Redis revocation |
| Proxy | Caddy 2 + cloudflare DNS module + ratelimit module (xcaddy) |
| Docker | 4 services, hardened (cap_drop ALL, read_only, no-new-privileges) |

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/Cyrilsou/Caddy-Manager.git
cd Caddy-Manager
cp .env.example .env
```

Edit `.env`:

```bash
# Generate secrets
python3 -c "import secrets; print(secrets.token_hex(32))"

# Required
SECRET_KEY=<generated-64-char-hex>
ADMIN_PASSWORD=<strong-password-min-8-chars>
DB_PASSWORD=<database-password>
REDIS_PASSWORD=<redis-password>
PANEL_DOMAIN=panel.yourdomain.com
ACME_EMAIL=you@example.com

# Optional: Cloudflare DNS management
CLOUDFLARE_API_TOKEN=<cf-api-token>

# Optional: Restrict panel access by IP
ALLOWED_IPS=203.0.113.0/24,198.51.100.5/32
```

### 2. Deploy

```bash
docker compose up -d --build
```

This starts 4 containers:
- **caddy** — Reverse proxy (host network, ports 80/443)
- **backend** — FastAPI API server
- **postgres** — Database
- **redis** — Cache and session store

On first boot: database migrations run automatically, admin user is created from `.env` credentials.

### 3. Access

Open `https://panel.yourdomain.com` and sign in.

## How It Works

### Adding a site (< 1 minute)

1. **Backends** page → Add Backend → enter name, private IP, port, protocol
2. **Domains** page → Add Domain → enter hostname, select backend, configure HTTPS/WebSocket/etc.
3. **Configuration** page → Preview → Apply to Caddy

Caddy validates the config atomically. If valid, it's applied with zero downtime. If invalid, nothing changes. Every version is saved for instant rollback.

### Automatic background tasks

| Task | Interval | Action |
|------|----------|--------|
| Health Checker | 30s | Pings all backends in parallel, updates status |
| Cert Checker | 6h | Checks TLS certificate expiration for all domains |

### API endpoints

| Group | Prefix | Auth | Description |
|-------|--------|------|-------------|
| Health | `/api/health` | No | Liveness + readiness checks |
| Auth | `/api/v1/auth` | Partial | Login, logout, refresh, password change |
| Backends | `/api/v1/backends` | Yes | CRUD + health check trigger |
| Domains | `/api/v1/domains` | Yes | CRUD + toggle + pagination |
| Config | `/api/v1/config` | Yes | Preview, apply, rollback, version history, diff |
| Certificates | `/api/v1/certificates` | Yes | List + force refresh |
| Cloudflare | `/api/v1/cloudflare` | Yes | Zones, DNS CRUD, proxy toggle, SSL mode |
| Dashboard | `/api/v1/dashboard` | Yes | Aggregated stats |
| Audit | `/api/v1/audit` | Yes | Paginated, filterable action log |
| Settings | `/api/v1/settings` | Yes | App settings (secrets masked) |
| Export | `/api/v1/export` | Yes | Export/import full configuration |

## Proxmox VM Setup

### Recommended specs
- 2-4 vCPUs (type: `host`)
- 4 GB RAM minimum
- VirtIO NIC on `vmbr0`
- VirtIO SCSI disk, SSD preferred

### Kernel tuning

Create `/etc/sysctl.d/99-caddy-proxy.conf`:

```ini
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_fastopen = 3
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.netfilter.nf_conntrack_max = 1048576
fs.file-max = 2097152
vm.swappiness = 10
```

Apply: `sysctl --system`

### Docker daemon

Create `/etc/docker/daemon.json`:

```json
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "3" },
  "default-ulimits": { "nofile": { "Soft": 1048576, "Hard": 1048576 } },
  "userland-proxy": false,
  "live-restore": true
}
```

Restart: `systemctl restart docker`

## Security

### Network isolation
- **Caddy** runs in `host` network mode — direct access to VM network, zero NAT overhead
- **Admin API** bound to `127.0.0.1:2019` — never exposed externally
- **PostgreSQL & Redis** on `internal: true` Docker network — no internet access
- **Backend** joins both internal (DB/Redis) and api_net (outbound for Cloudflare API)

### Authentication & authorization
- **Argon2id** password hashing (time_cost=3, memory_cost=64MB, parallelism=4)
- **JWT** access tokens (15min) + refresh tokens (24h) with Redis revocation blacklist
- **Fail2ban** via Redis: 5 failed attempts → 15min IP ban
- **Account lockout** after 5 failed logins (15min)
- **RBAC** roles: Admin (full access), Editor (create/update), Viewer (read-only)

### Container hardening
- `cap_drop: ALL` on every container
- `cap_add: NET_BIND_SERVICE` only for Caddy
- `read_only: true` with tmpfs for temp files
- `security_opt: no-new-privileges:true`
- Resource limits (memory, CPU) on all services

### Security headers
- `Strict-Transport-Security` (HSTS, 2 years, includeSubDomains, preload)
- `Content-Security-Policy` (strict, self-only)
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Cross-Origin-Opener-Policy: same-origin`
- `Permissions-Policy` (camera, microphone, geolocation disabled)

### Rate limiting
- Dual layer: Caddy (L7) + FastAPI/SlowAPI (application)
- Login: 5/min per IP
- Password change: 3/min
- Config apply: 10/min
- Global: 100/min per IP

### Secrets management
- Cloudflare API tokens encrypted at rest with Fernet (derived from SECRET_KEY)
- Secrets masked as `***` in API responses and audit logs
- Sensitive audit log fields auto-redacted (passwords, tokens, API keys)

## Cloudflare Integration

Requires an API token with permissions:
- `Zone:Zone:Read`
- `Zone:DNS:Edit`
- `Zone:Zone Settings:Edit`

Scope to specific zones for security.

### Features
- List zones and DNS records
- Create/update/delete DNS records (A, AAAA, CNAME, TXT, MX, NS, SRV)
- Toggle proxy mode (orange cloud) per record
- Change SSL mode (Off, Flexible, Full, Strict) per zone
- DNS-01 ACME challenges for wildcard certificates (via caddy-dns/cloudflare module)
- Cloudflare API rate limiting (1200 req/5min) with automatic throttling

## Backup & Restore

### Database backup

```bash
./scripts/backup-db.sh
```

Keeps last 30 backups automatically.

### Full config export

```bash
curl -H "Authorization: Bearer <token>" https://panel.yourdomain.com/api/v1/export > backup.json
```

### Config import

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -F "file=@backup.json" \
  https://panel.yourdomain.com/api/v1/export/import
```

### Volume backup

```bash
docker run --rm -v caddy-manager_caddy_data:/data -v $(pwd):/backup alpine tar czf /backup/caddy-data.tar.gz /data
docker run --rm -v caddy-manager_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-data.tar.gz /data
```

## Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dev server runs on `http://localhost:5173` with API proxy to `:8000`.

### Tests

```bash
cd backend
pytest -v
```

## Performance

Key optimizations implemented:
- **Caddy in host network mode** — zero Docker NAT overhead (10-20% more throughput)
- **Parallel health checks** — `asyncio.gather` instead of sequential (20 backends: 60s → 3s)
- **Parallel cert checks** — ThreadPoolExecutor with 20 workers + gather (100 domains: 300s → 15s)
- **Persistent HTTP clients** — connection pooling for Caddy and Cloudflare APIs (-50-150ms/call)
- **Aggregated DB queries** — single query with JOIN+GROUP BY instead of N+1
- **Composite indexes** — on audit_logs (action+created_at, user_id+created_at)
- **Connection pool** — 20 connections + 30 overflow for PostgreSQL
- **Frontend code splitting** — React.lazy() on all pages
- **Query deduplication** — 5min staleTime, background refetch disabled
- **Zstd + Gzip compression** — on all Caddy responses
- **HTTP/3 (QUIC)** — supported natively by Caddy

## Project Structure

```
Caddy-Manager/
+-- docker-compose.yml          # 4 services: caddy, backend, postgres, redis
+-- .env.example                # All configuration variables documented
+-- caddy/
|   +-- Dockerfile              # xcaddy build with cloudflare + ratelimit modules
|   +-- Caddyfile               # Panel HTTPS + security headers + reverse proxy
+-- backend/
|   +-- Dockerfile              # Python 3.12 slim, non-root user
|   +-- entrypoint.sh           # Smart migration check + uvicorn start
|   +-- requirements.txt        # All Python dependencies pinned
|   +-- alembic/                # Database migrations
|   +-- tests/                  # pytest test suite
|   +-- app/
|       +-- main.py             # FastAPI app with lifespan, middleware stack
|       +-- config.py           # Pydantic settings from environment
|       +-- database.py         # Async SQLAlchemy engine + session
|       +-- models/             # 7 SQLAlchemy models
|       +-- schemas/            # Pydantic request/response schemas
|       +-- api/v1/             # 11 route modules
|       +-- services/           # Business logic layer
|       +-- security/           # Auth, RBAC, fail2ban, encryption, middleware
|       +-- tasks/              # Background scheduler, health + cert checkers
|       +-- core/               # Structured JSON logging, request ID middleware
+-- frontend/
|   +-- Dockerfile              # Node 22 build + nginx serve
|   +-- nginx.conf              # SPA routing + API proxy
|   +-- src/
|       +-- pages/              # 9 pages (lazy loaded)
|       +-- components/         # UI primitives + layout + shared
|       +-- api/                # Axios client with JWT refresh interceptor
|       +-- stores/             # Zustand auth store
|       +-- hooks/              # useDebounce, useToast
|       +-- lib/                # Utils, Zod validation schemas
+-- scripts/
    +-- init-db.sh              # Database initialization
    +-- backup-db.sh            # PostgreSQL backup with rotation
```

## License

MIT
