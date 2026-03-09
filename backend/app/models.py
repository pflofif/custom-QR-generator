from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


# ─── User ─────────────────────────────────────────────────────────────────────

class UserInDB(BaseModel):
    id: Optional[str] = None
    username: str
    email: str
    hashed_password: str
    role: str = "user"          # "admin" | "user"
    telegram_chat_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# ─── Event ────────────────────────────────────────────────────────────────────

class EventInDB(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    owner_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# ─── QR Code ──────────────────────────────────────────────────────────────────

class QRCodeInDB(BaseModel):
    id: Optional[str] = None
    short_id: str           # e.g. "aB3kP9"  — used in /r/{short_id}
    label: str              # e.g. "Entrance Poster"
    target_url: str
    event_id: str
    owner_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# ─── Scan Log ─────────────────────────────────────────────────────────────────

class ScanLogInDB(BaseModel):
    id: Optional[str] = None
    short_id: str
    qr_id: str
    event_id: str
    owner_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    country: Optional[str] = None
    device_type: Optional[str] = None   # "mobile" | "desktop" | "tablet"
    os: Optional[str] = None
    browser: Optional[str] = None
    scanned_at: datetime = Field(default_factory=datetime.utcnow)
    telegram_user_id: Optional[str] = None  # future Telegram integration

    class Config:
        populate_by_name = True
