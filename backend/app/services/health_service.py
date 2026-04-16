import time

import httpx


async def check_backend_connectivity(
    host: str, port: int, protocol: str = "http", path: str = "/", skip_verify: bool = False
) -> dict:
    url = f"{protocol}://{host}:{port}{path}"
    try:
        async with httpx.AsyncClient(timeout=5.0, verify=not skip_verify) as client:
            start = time.monotonic()
            response = await client.get(url)
            elapsed_ms = int((time.monotonic() - start) * 1000)

        return {
            "reachable": True,
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
        }
    except httpx.ConnectError:
        return {"reachable": False, "error": "Connection refused"}
    except httpx.ConnectTimeout:
        return {"reachable": False, "error": "Connection timeout"}
    except Exception as e:
        return {"reachable": False, "error": str(e)}
