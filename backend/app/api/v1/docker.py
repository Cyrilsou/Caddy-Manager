import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.models.user import User
from app.security.rbac import require_permission

router = APIRouter(prefix="/docker", tags=["docker"])
logger = logging.getLogger(__name__)


async def _run_docker_cmd(cmd: str) -> str:
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode != 0:
            return ""
        return stdout.decode().strip()
    except (FileNotFoundError, asyncio.TimeoutError):
        return ""


@router.get("/containers")
async def list_containers(_: User = Depends(require_permission("settings.read"))):
    """List running Docker containers with resource usage."""
    raw = await _run_docker_cmd(
        'docker stats --no-stream --format "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.NetIO}}|{{.PIDs}}"'
    )
    if not raw:
        raise HTTPException(status_code=503, detail="Docker not available or no permission")

    containers = []
    for line in raw.splitlines():
        parts = line.split("|")
        if len(parts) >= 5:
            containers.append({
                "name": parts[0],
                "cpu": parts[1],
                "memory": parts[2],
                "network": parts[3],
                "pids": parts[4],
            })

    return containers


@router.get("/containers/{name}")
async def container_detail(name: str, _: User = Depends(require_permission("settings.read"))):
    """Get detailed info for a specific container."""
    raw = await _run_docker_cmd(
        f'docker inspect --format '
        f'"{{{{.State.Status}}}}|{{{{.State.StartedAt}}}}|{{{{.Config.Image}}}}|{{{{.HostConfig.RestartPolicy.Name}}}}" '
        f'{name}'
    )
    if not raw:
        raise HTTPException(status_code=404, detail=f"Container '{name}' not found")

    parts = raw.split("|")
    return {
        "name": name,
        "status": parts[0] if len(parts) > 0 else "unknown",
        "started_at": parts[1] if len(parts) > 1 else None,
        "image": parts[2] if len(parts) > 2 else None,
        "restart_policy": parts[3] if len(parts) > 3 else None,
    }


@router.post("/containers/{name}/restart")
async def restart_container(name: str, _: User = Depends(require_permission("settings.write"))):
    """Restart a Docker container."""
    allowed = {"caddy-proxy", "caddy-panel-api", "caddy-panel-ui", "caddy-panel-db", "caddy-panel-redis"}
    if name not in allowed:
        raise HTTPException(status_code=400, detail="Cannot restart this container")

    result = await _run_docker_cmd(f"docker restart {name}")
    if not result and result != name:
        raise HTTPException(status_code=502, detail="Failed to restart container")

    return {"message": f"Container '{name}' restarted"}
