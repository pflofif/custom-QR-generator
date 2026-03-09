"""
Async HTTP client that wraps all backend API calls.
Every method raises APIError on failure, so handlers can
simply call await api.xxx() and catch APIError for user messages.
"""
from __future__ import annotations
import httpx
from config import API_BASE_URL


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=15.0)
    return _client


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _raise(r: httpx.Response) -> None:
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise APIError(str(detail), r.status_code)


# ─── Auth ─────────────────────────────────────────────────────────────────────

async def login(email: str, password: str) -> dict:
    r = await get_client().post("/api/auth/login", json={"email": email, "password": password})
    _raise(r)
    return r.json()      # {access_token, user}


async def get_me(token: str) -> dict:
    r = await get_client().get("/api/auth/me", headers=_auth(token))
    _raise(r)
    return r.json()


async def link_telegram(token: str, chat_id: int, tg_username: str | None) -> dict:
    payload: dict = {"telegram_chat_id": str(chat_id)}
    if tg_username:
        payload["telegram_username"] = tg_username
    r = await get_client().patch("/api/auth/me", json=payload, headers=_auth(token))
    _raise(r)
    return r.json()


# ─── Events ───────────────────────────────────────────────────────────────────

async def list_events(token: str) -> list:
    r = await get_client().get("/api/events", headers=_auth(token))
    _raise(r)
    return r.json()


async def get_event(token: str, event_id: str) -> dict:
    r = await get_client().get(f"/api/events/{event_id}", headers=_auth(token))
    _raise(r)
    return r.json()


async def create_event(token: str, name: str, description: str = "") -> dict:
    payload = {"name": name}
    if description:
        payload["description"] = description
    r = await get_client().post("/api/events", json=payload, headers=_auth(token))
    _raise(r)
    return r.json()


async def update_event(token: str, event_id: str, **fields) -> dict:
    r = await get_client().put(f"/api/events/{event_id}", json=fields, headers=_auth(token))
    _raise(r)
    return r.json()


async def delete_event(token: str, event_id: str) -> None:
    r = await get_client().delete(f"/api/events/{event_id}", headers=_auth(token))
    _raise(r)


# ─── QR Codes ─────────────────────────────────────────────────────────────────

async def list_qrcodes(token: str, event_id: str) -> list:
    r = await get_client().get(f"/api/events/{event_id}/qrcodes", headers=_auth(token))
    _raise(r)
    return r.json()


async def create_qrcode(token: str, event_id: str, label: str, target_url: str) -> dict:
    r = await get_client().post(
        f"/api/events/{event_id}/qrcodes",
        json={"label": label, "target_url": target_url},
        headers=_auth(token),
    )
    _raise(r)
    return r.json()


async def update_qrcode(token: str, event_id: str, qr_id: str, **fields) -> dict:
    r = await get_client().put(
        f"/api/events/{event_id}/qrcodes/{qr_id}",
        json=fields,
        headers=_auth(token),
    )
    _raise(r)
    return r.json()


async def delete_qrcode(token: str, event_id: str, qr_id: str) -> None:
    r = await get_client().delete(f"/api/events/{event_id}/qrcodes/{qr_id}", headers=_auth(token))
    _raise(r)


async def get_qr_image(token: str, event_id: str, qr_id: str) -> bytes:
    r = await get_client().get(
        f"/api/events/{event_id}/qrcodes/{qr_id}/image",
        headers=_auth(token),
    )
    _raise(r)
    return r.content


# ─── Analytics ────────────────────────────────────────────────────────────────

async def get_overview(token: str) -> dict:
    r = await get_client().get("/api/analytics/overview", headers=_auth(token))
    _raise(r)
    return r.json()


async def get_event_analytics(token: str, event_id: str, days: int = 30) -> dict:
    r = await get_client().get(
        f"/api/analytics/events/{event_id}",
        params={"days": days},
        headers=_auth(token),
    )
    _raise(r)
    return r.json()


# ─── Admin – users ────────────────────────────────────────────────────────────

async def admin_list_users(token: str) -> list:
    r = await get_client().get("/api/admin/users", headers=_auth(token))
    _raise(r)
    return r.json()


async def admin_create_user(
    token: str, username: str, email: str, password: str,
    role: str = "user", telegram_username: str | None = None,
) -> dict:
    payload = {"username": username, "email": email, "password": password, "role": role}
    if telegram_username:
        payload["telegram_username"] = telegram_username
    r = await get_client().post("/api/admin/users", json=payload, headers=_auth(token))
    _raise(r)
    return r.json()


async def admin_update_user(token: str, user_id: str, **fields) -> dict:
    r = await get_client().patch(f"/api/admin/users/{user_id}", json=fields, headers=_auth(token))
    _raise(r)
    return r.json()


async def admin_delete_user(token: str, user_id: str) -> None:
    r = await get_client().delete(f"/api/admin/users/{user_id}", headers=_auth(token))
    _raise(r)
