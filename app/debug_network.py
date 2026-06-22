"""
Temporary debug endpoint — add this to your FastAPI app, deploy, then
curl it from outside to see what's actually happening on the Space's
network from the inside.

Add this route to your main app, redeploy, then visit:
https://<your-space>.hf.space/debug-network
"""

import asyncio
import socket
import time
import httpx
from fastapi import APIRouter

router = APIRouter()


@router.get("/debug-network")
async def debug_network():
    results = {}

    # 1. DNS resolution check - does it resolve, and to what (v4 vs v6)?
    for host in ["graph.facebook.com", "api.github.com", "www.google.com"]:
        try:
            infos = socket.getaddrinfo(host, 443)
            addrs = sorted(set(info[4][0] for info in infos))
            results[f"dns_{host}"] = addrs
        except Exception as e:
            results[f"dns_{host}"] = f"FAILED: {type(e).__name__}: {e}"

    # 2. Actual HTTPS connect test with short timeout, several targets
    for url in [
        "https://graph.facebook.com/v25.0/",
        "https://api.github.com",
        "https://www.google.com",
    ]:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=5.0)) as client:
                r = await client.get(url)
                elapsed = time.monotonic() - start
                results[f"http_{url}"] = {"status": r.status_code, "elapsed_s": round(elapsed, 2)}
        except Exception as e:
            elapsed = time.monotonic() - start
            results[f"http_{url}"] = {
                "error": f"{type(e).__name__}: {e}",
                "elapsed_s": round(elapsed, 2),
            }

    # 3. Raw TCP connect test (bypasses TLS entirely - isolates whether
    # it's the TCP handshake or the TLS handshake that's hanging)
    for host, port in [("graph.facebook.com", 443), ("api.github.com", 443)]:
        start = time.monotonic()
        try:
            fut = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(fut, timeout=5.0)
            writer.close()
            elapsed = time.monotonic() - start
            results[f"tcp_{host}:{port}"] = {"ok": True, "elapsed_s": round(elapsed, 2)}
        except Exception as e:
            elapsed = time.monotonic() - start
            results[f"tcp_{host}:{port}"] = {
                "error": f"{type(e).__name__}: {e}",
                "elapsed_s": round(elapsed, 2),
            }

    # 4. Force IPv4-only connect to Facebook specifically - isolates
    # whether an IPv6 routing gap is the cause (skip if no IPv4 address
    # was found in the DNS step above).
    fb_addrs = results.get("dns_graph.facebook.com")
    if isinstance(fb_addrs, list):
        ipv4_addrs = [a for a in fb_addrs if ":" not in a]
        if ipv4_addrs:
            ip = ipv4_addrs[0]
            start = time.monotonic()
            try:
                fut = asyncio.open_connection(ip, 443)
                reader, writer = await asyncio.wait_for(fut, timeout=5.0)
                writer.close()
                elapsed = time.monotonic() - start
                results["tcp_facebook_ipv4_forced"] = {
                    "ok": True,
                    "ip_used": ip,
                    "elapsed_s": round(elapsed, 2),
                }
            except Exception as e:
                elapsed = time.monotonic() - start
                results["tcp_facebook_ipv4_forced"] = {
                    "ip_used": ip,
                    "error": f"{type(e).__name__}: {e}",
                    "elapsed_s": round(elapsed, 2),
                }
        else:
            results["tcp_facebook_ipv4_forced"] = "no IPv4 address found in DNS results"

    return results
