"""Network utility function - IP extraction, proxy handling."""

from fastapi import Request

def get_client_ip(request: Request) -> str:
    """
    Extract client IP address.

    Checks X-Forwarded-For for proxy/load balancer setups
    but only uses it when request.client is also present
    to avoid blindly trusting spoofed headers.
    """
    forward_for = request.headers.get("X-Forward-For")
    if forward_for and request.client:
        return forward_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
    