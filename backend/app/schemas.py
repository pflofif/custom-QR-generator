from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, HttpUrl, Field


# ─── Helpers ──────────────────────────────────────────────────────────────────

def doc_to_dict(doc: dict) -> dict:
    """Convert a MongoDB document (_id → id as str)."""
    if doc is None:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert nested ObjectIds if any
    for k, v in d.items():
        if hasattr(v, "__str__") and type(v).__name__ == "ObjectId":
            d[k] = str(v)
    return d


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None
    is_active: bool
    created_at: datetime


TokenResponse.model_rebuild()


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    telegram_chat_id: Optional[str] = None


# ─── Event ────────────────────────────────────────────────────────────────────

class EventCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)


class EventUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class EventResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    qr_count: Optional[int] = 0
    total_scans: Optional[int] = 0


# ─── QR Code ──────────────────────────────────────────────────────────────────

class QRCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    target_url: str = Field(..., min_length=5)


class QRUpdateRequest(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=100)
    target_url: Optional[str] = None
    is_active: Optional[bool] = None


class QRResponse(BaseModel):
    id: str
    short_id: str
    label: str
    target_url: str
    event_id: str
    owner_id: str
    is_active: bool
    proxy_url: str
    created_at: datetime
    updated_at: datetime
    scan_count: Optional[int] = 0


# ─── Analytics ────────────────────────────────────────────────────────────────

class ScanLogResponse(BaseModel):
    id: str
    short_id: str
    qr_id: str
    event_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    device_type: Optional[str]
    os: Optional[str]
    browser: Optional[str]
    scanned_at: datetime


class EventAnalytics(BaseModel):
    event_id: str
    event_name: str
    total_scans: int
    qr_breakdown: List[dict]        # [{label, short_id, scan_count}]
    time_series: List[dict]         # [{date, count}]
    device_breakdown: List[dict]    # [{device_type, count}]
    top_browsers: List[dict]        # [{browser, count}]
