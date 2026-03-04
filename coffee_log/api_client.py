"""API client for Streamlit - HTTP requests with JWT auth."""

from typing import Any, Optional

import httpx
import streamlit as st


class APIError(Exception):
    """API request failed."""

    def __init__(self, message: str, status_code: Optional[int] = None, detail: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


def get_base_url() -> str:
    """Get API base URL from secrets."""
    try:
        return st.secrets.api.base_url.rstrip("/")
    except Exception:
        return "http://localhost:8000"


def get_timeout() -> float:
    """Get request timeout from secrets (optional)."""
    try:
        return float(st.secrets.api.get("timeout", 30))
    except Exception:
        return 30.0


def get_headers() -> dict[str, str]:
    """Get request headers with Bearer token if logged in."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if "access_token" in st.session_state and st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    return headers


def _request(
    method: str,
    path: str,
    *,
    params: Optional[dict] = None,
    json: Optional[dict] = None,
) -> httpx.Response:
    """Make authenticated HTTP request to API."""
    url = f"{get_base_url()}{path}"
    with httpx.Client(timeout=get_timeout()) as client:
        return client.request(
            method,
            url,
            params=params,
            json=json or None,
            headers=get_headers(),
        )


def get(path: str, params: Optional[dict] = None) -> dict[str, Any]:
    """GET request. Raises APIError on failure. Returns JSON."""
    try:
        resp = _request("GET", path, params=params)
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except httpx.HTTPStatusError as e:
        detail = None
        try:
            data = e.response.json()
            detail = data.get("detail", str(data))
        except Exception:
            detail = e.response.text
        raise APIError(
            detail or str(e),
            status_code=e.response.status_code,
            detail=detail,
        ) from e


def post(path: str, json: Optional[dict] = None, params: Optional[dict] = None) -> dict[str, Any]:
    """POST request. Raises APIError on failure. Returns JSON."""
    try:
        resp = _request("POST", path, json=json, params=params)
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except httpx.HTTPStatusError as e:
        detail = None
        try:
            data = e.response.json()
            detail = data.get("detail", str(data))
        except Exception:
            detail = e.response.text
        raise APIError(
            detail or str(e),
            status_code=e.response.status_code,
            detail=detail,
        ) from e


def patch(path: str, json: Optional[dict] = None) -> dict[str, Any]:
    """PATCH request. Raises APIError on failure. Returns JSON."""
    try:
        resp = _request("PATCH", path, json=json)
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except httpx.HTTPStatusError as e:
        detail = None
        try:
            data = e.response.json()
            detail = data.get("detail", str(data))
        except Exception:
            detail = e.response.text
        raise APIError(
            detail or str(e),
            status_code=e.response.status_code,
            detail=detail,
        ) from e
