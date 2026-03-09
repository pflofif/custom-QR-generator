from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from datetime import timedelta
from app.database import get_db
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    db = get_db()
    # Check uniqueness
    if await db.users.find_one({"email": body.email}):
        raise HTTPException(status_code=409, detail="Email already registered")
    if await db.users.find_one({"username": body.username}):
        raise HTTPException(status_code=409, detail="Username already taken")

    user_doc = {
        "username": body.username,
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "role": "user",
        "telegram_chat_id": None,
        "is_active": True,
        "created_at": __import__("datetime").datetime.utcnow(),
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    token = create_access_token(
        {"sub": user_id, "role": "user"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    user_response = UserResponse(
        id=user_id,
        username=body.username,
        email=body.email,
        role="user",
        telegram_chat_id=None,
        is_active=True,
        created_at=user_doc["created_at"],
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_response)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    db = get_db()
    user = await db.users.find_one({"email": body.email})
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is disabled")

    user_id = str(user["_id"])
    token = create_access_token(
        {"sub": user_id, "role": user.get("role", "user")},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    user_response = UserResponse(
        id=user_id,
        username=user["username"],
        email=user["email"],
        role=user.get("role", "user"),
        telegram_chat_id=user.get("telegram_chat_id"),
        is_active=user.get("is_active", True),
        created_at=user["created_at"],
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_response)


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user.get("role", "user"),
        telegram_chat_id=current_user.get("telegram_chat_id"),
        is_active=current_user.get("is_active", True),
        created_at=current_user["created_at"],
    )
