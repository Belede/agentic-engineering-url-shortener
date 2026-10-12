"""URL validation: scheme allow-list + SSRF-style private/loopback block.
FR-002, NFR-001, CL-05, ADR-011."""
import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}
MAX_URL_LENGTH = 2048


class InvalidUrlError(ValueError):
    """Malformed URL, disallowed scheme, or over length limit."""


class SsrfBlockedError(ValueError):
    """Target resolves to a loopback, private, or link-local address."""


def _is_private_or_loopback(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # Hostname, not a literal IP — resolve it.
        try:
            resolved = socket.gethostbyname(host)
            addr = ipaddress.ip_address(resolved)
        except (socket.gaierror, ValueError):
            # Cannot resolve — treat as not-blockable-by-this-check; the
            # request will simply fail downstream (not a security bypass,
            # since an unresolvable host cannot be redirected to anyway).
            return False
    return addr.is_loopback or addr.is_private or addr.is_link_local


def validate_target_url(url: str) -> None:
    """Raise InvalidUrlError or SsrfBlockedError if url fails validation.

    Returns None (does not return a normalized URL) — validation only.
    """
    if not url or len(url) > MAX_URL_LENGTH:
        raise InvalidUrlError("URL is empty or exceeds maximum length")

    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise InvalidUrlError(f"Scheme '{parsed.scheme}' is not allowed")
    if not parsed.hostname:
        raise InvalidUrlError("URL has no hostname")

    host = parsed.hostname
    if host == "localhost" or _is_private_or_loopback(host):
        raise SsrfBlockedError(f"Target host '{host}' is a private/loopback address")
