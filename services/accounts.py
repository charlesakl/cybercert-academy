"""Supabase Auth and user-scoped PostgREST persistence.

Uses the publishable/anon key and a *user JWT*, never a service-role key.
Database RLS is mandatory and defined in supabase/schema.sql.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests


class AccountError(RuntimeError):
    """An authentication or persistence request failed."""


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    key: str

    def __post_init__(self):
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("SUPABASE_URL must be a valid HTTPS URL")
        if not self.key.strip():
            raise ValueError("SUPABASE_ANON_KEY is required")


def get_config(secrets: Any = None) -> SupabaseConfig | None:
    """Read credentials from Streamlit secrets, falling back to environment."""
    section = {}
    if secrets is not None:
        try:
            section = secrets.get("supabase", {})
        except (KeyError, FileNotFoundError, OSError):
            section = {}
    url = str(section.get("url") or os.getenv("SUPABASE_URL", "")).strip().rstrip("/")
    key = str(section.get("anon_key") or os.getenv("SUPABASE_ANON_KEY", "")).strip()
    return SupabaseConfig(url, key) if url and key else None


class AccountClient:
    def __init__(self, config: SupabaseConfig, transport=None):
        self.config = config
        self.transport = transport or requests

    def _request(self, method: str, endpoint: str, *, token: str | None = None,
                 data: dict | None = None, params: dict | None = None) -> Any:
        headers = {"apikey": self.config.key, "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if method == "POST" and endpoint.startswith("/rest/"):
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        try:
            response = self.transport.request(method, self.config.url + endpoint,
                                              headers=headers, json=data, params=params, timeout=15)
        except requests.RequestException as exc:
            raise AccountError("Cannot reach the account service. Check your connection.") from exc
        if not 200 <= response.status_code < 300:
            try:
                details = response.json()
                msg = details.get("msg") or details.get("message") or details.get("error_description")
            except ValueError:
                msg = None
            # Avoid displaying raw request internals or credentials.
            raise AccountError(str(msg or f"Account service returned HTTP {response.status_code}")[:300])
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def sign_up(self, email: str, password: str) -> dict:
        return self._request("POST", "/auth/v1/signup", data={"email": email, "password": password})

    def sign_in(self, email: str, password: str) -> dict:
        return self._request("POST", "/auth/v1/token?grant_type=password", data={"email": email, "password": password})

    def refresh(self, refresh_token: str) -> dict:
        return self._request("POST", "/auth/v1/token?grant_type=refresh_token", data={"refresh_token": refresh_token})

    def send_reset(self, email: str) -> dict:
        return self._request("POST", "/auth/v1/recover", data={"email": email})

    def load_progress(self, access_token: str, user_id: str) -> dict:
        rows = self._request("GET", "/rest/v1/user_progress", token=access_token,
                             params={"user_id": f"eq.{user_id}", "select": "payload"})
        return rows[0].get("payload", {}) if rows else {}

    def save_progress(self, access_token: str, user_id: str, payload: dict) -> None:
        self._request("POST", "/rest/v1/user_progress?on_conflict=user_id", token=access_token,
                      data={"user_id": user_id, "payload": payload})
