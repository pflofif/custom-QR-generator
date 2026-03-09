"""
Admin-only: manage users (create, list, update, delete).
Account creation is intentionally restricted to admins —
end-users cannot self-register.
"""
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.auth import hash_password, require_admin
from app.schemas import UserResponse

router = APIRouter(prefix="/api/admin/users", tags=["admin"])


# ─── Request models ───────────────────────────────────────────────────────────

class AdminCreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"          # "user" | "admin"
    telegram_username: Optional[str] = None   # e.g. "@john_doe" — used to link bot


class AdminUpdateUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    telegram_username: Optional[str] = None
    telegram_chat_id: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _map_user(doc: dict) -> UserResponse:
    return UserResponse(
        id=str(doc["_id"]),
        username=doc["username"],
        email=doc["email"],
        role=doc.get("role", "user"),
        telegram_chat_id=doc.get("telegram_chat_id"),
        telegram_username=doc.get("telegram_username"),
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=UserResponse, status_code=201)
async def admin_create_user(body: AdminCreateUserRequest, _=Depends(require_admin)):
    db = get_db()
    if await db.users.find_one({"email": body.email}):
        raise HTTPException(409, "Email already registered")
    if await db.users.find_one({"username": body.username}):
        raise HTTPException(409, "Username already taken")
    if body.telegram_username:
        clash = await db.users.find_one({"telegram_username": body.telegram_username})
        if clash:
            raise HTTPException(409, "Telegram username already assigned to another account")

    doc = {
        "username": body.username,
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "role": body.role,
        "telegram_username": body.telegram_username,
        "telegram_chat_id": None,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _map_user(doc)


@router.get("", response_model=list[UserResponse])
async def admin_list_users(_=Depends(require_admin)):
    db = get_db()
    users = []
    async for doc in db.users.find().sort("created_at", -1):
        users.append(_map_user(doc))
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def admin_get_user(user_id: str, _=Depends(require_admin)):
    db = get_db()
    doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(404, "User not found")
    return _map_user(doc)


@router.patch("/{user_id}", response_model=UserResponse)
async def admin_update_user(user_id: str, body: AdminUpdateUserRequest, _=Depends(require_admin)):
    db = get_db()
    doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(404, "User not found")

    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if "password" in updates:
        updates["hashed_password"] = hash_password(updates.pop("password"))
    if "email" in updates:
        clash = await db.users.find_one({"email": updates["email"], "_id": {"$ne": ObjectId(user_id)}})
        if clash:
            raise HTTPException(409, "Email already in use")
    if "username" in updates:
        clash = await db.users.find_one({"username": updates["username"], "_id": {"$ne": ObjectId(user_id)}})
        if clash:
            raise HTTPException(409, "Username already taken")
    if "telegram_username" in updates and updates["telegram_username"]:
        clash = await db.users.find_one({"telegram_username": updates["telegram_username"], "_id": {"$ne": ObjectId(user_id)}})
        if clash:
            raise HTTPException(409, "Telegram username already assigned to another account")

    if updates:
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})

    updated = await db.users.find_one({"_id": ObjectId(user_id)})
    return _map_user(updated)


@router.delete("/{user_id}", status_code=204)
async def admin_delete_user(user_id: str, current_admin=Depends(require_admin)):
    db = get_db()
    if user_id == current_admin["id"]:
        raise HTTPException(400, "Cannot delete your own account")
    doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(404, "User not found")
    await db.users.delete_one({"_id": ObjectId(user_id)})
