import os
from urllib.parse import urlparse


def normalize_redirect_uri(value: str | None) -> str:
    """Normalize redirect URI so it matches Google OAuth expectations.

    Google requires the redirect URI to be an exact match to the URL registered
    in the OAuth client. For web apps, the canonical form usually ends in a
    trailing slash and uses https for public deployments.
    """
    if not value:
        return "http://localhost:8501/"

    candidate = value.strip()
    if not candidate:
        return "http://localhost:8501/"

    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        return candidate

    if parsed.path in ("", "/"):
        return f"{parsed.scheme}://{parsed.netloc}/"

    return candidate


def get_redirect_uri() -> str:
    configured = os.environ.get("GOOGLE_REDIRECT_URI")
    return normalize_redirect_uri(configured)
